#!/bin/bash
# Build a bootable ClarityOS Desktop disk image.
#
# Runs inside the builder container (see Dockerfile). Stages are additive:
#   m0  boot chain only        UEFI -> GRUB -> kernel -> OpenRC -> serial console
#   m1  m0 + llama-server and a GGUF model, autostarting into a chat REPL on the console
#
# Everything heavy is assembled on the container's own filesystem and only the finished
# qcow2 is copied to /out. Writing multi-gigabyte intermediates straight to a Windows bind
# mount crosses the WSL2 filesystem bridge and is roughly an order of magnitude slower.
# Set EXPORT_RAW=1 when the raw image is actually needed (writing a USB stick).
set -euo pipefail

STAGE="${STAGE:-m0}"
ALPINE_BRANCH="${ALPINE_BRANCH:-v3.21}"
MIRROR="${MIRROR:-https://dl-cdn.alpinelinux.org/alpine}"
EXPORT_RAW="${EXPORT_RAW:-0}"

# A ~1 GB Q4 model: small enough to build and boot quickly, real enough to hold a
# conversation. Override MODEL_URL for anything larger.
MODEL_URL="${MODEL_URL:-https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf}"
MODEL_NAME="${MODEL_NAME:-$(basename "$MODEL_URL")}"

WORK=/build
ROOTFS=$WORK/rootfs
RAW=$WORK/clarityos.raw
QCOW=$WORK/clarityos.qcow2
OUT=/out
CACHE=/cache

# Fixed partition GUIDs, so the kernel command line is baked in at build time instead of
# discovered at boot.
ESP_GUID="A1C1A1C1-0001-4000-8000-000000000001"
ROOT_GUID="A1C1A1C1-0002-4000-8000-000000000002"
DISK_GUID="A1C1A1C1-0000-4000-8000-000000000000"

# Geometry in 512-byte sectors.
ESP_START=2048
ESP_SECTORS=$((256 * 2048))                       # 256 MiB
case "$STAGE" in
  m0) ROOT_MIB=3072 ;;
  m1) ROOT_MIB=6144 ;;                            # room for llama-server + model
  *)  echo "unknown STAGE: $STAGE" >&2; exit 2 ;;
esac
ROOT_SECTORS=$((ROOT_MIB * 2048))
ROOT_START=$((ESP_START + ESP_SECTORS))
TOTAL_SECTORS=$((ROOT_START + ROOT_SECTORS + 2048))

log()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
step() { printf '    %s\n' "$*"; }
die()  { printf '\n\033[1;31mFAILED: %s\033[0m\n' "$*" >&2; exit 1; }

log "ClarityOS Desktop build   stage=$STAGE  alpine=$ALPINE_BRANCH  root=${ROOT_MIB}MiB"
mkdir -p "$OUT" "$CACHE"
rm -rf "$ROOTFS"; mkdir -p "$ROOTFS"

# ---------------------------------------------------------------------------
# 1. Alpine root filesystem
# ---------------------------------------------------------------------------
log "Seeding apk database and keys"
mkdir -p "$ROOTFS/etc/apk/keys"
cp /etc/apk/keys/* "$ROOTFS/etc/apk/keys/"
cat > "$ROOTFS/etc/apk/repositories" <<EOF
$MIRROR/$ALPINE_BRANCH/main
$MIRROR/$ALPINE_BRANCH/community
EOF

PKGS=(
  alpine-base linux-lts linux-firmware-none mkinitfs
  openrc busybox-openrc
  e2fsprogs dosfstools util-linux
  ifupdown-ng dhcpcd ca-certificates tzdata
)
# llama-server links against libstdc++/libgomp/libgcc; python3 runs the chat REPL.
[ "$STAGE" = "m1" ] && PKGS+=( libstdc++ libgcc libgomp python3 )

log "Installing ${#PKGS[@]} packages into rootfs"
apk --root "$ROOTFS" --initdb --update-cache --no-progress add "${PKGS[@]}" \
  || die "apk install into rootfs failed"

KVER="$(basename "$(find "$ROOTFS/lib/modules" -maxdepth 1 -mindepth 1 -type d | head -1)")"
[ -n "$KVER" ] || die "could not determine kernel version under $ROOTFS/lib/modules"
step "kernel $KVER"

# ---------------------------------------------------------------------------
# 2. System configuration
# ---------------------------------------------------------------------------
log "Configuring system"
echo clarityos > "$ROOTFS/etc/hostname"

# Mount by filesystem LABEL, not PARTUUID: Alpine's initramfs resolves LABEL= and UUID=
# but not PARTUUID=, and labels are portable across vda / sda / nvme0n1p2 so the same
# image boots under QEMU, from USB, and off an NVMe drive without edits.
cat > "$ROOTFS/etc/fstab" <<EOF
LABEL=CLARITYROOT  /          ext4  rw,relatime  0 1
LABEL=CLARITYESP   /boot/efi  vfat  rw,noatime   0 2
tmpfs              /tmp       tmpfs rw,nosuid,nodev,size=512M 0 0
EOF
mkdir -p "$ROOTFS/boot/efi"

# Root login on both consoles; dev image, so no root password.
cat > "$ROOTFS/etc/securetty" <<'EOF'
console
tty1
tty2
tty3
ttyS0
ttyS1
EOF
sed -i 's|^root:[^:]*:|root::|' "$ROOTFS/etc/shadow"

# The initramfs needs whatever is required to *find* the root filesystem, plus KMS so the
# framebuffer is live early (that matters from M2 on).
printf 'features="base kms keymap scsi usb virtio nvme ext4"\n' \
  > "$ROOTFS/etc/mkinitfs/mkinitfs.conf"

log "Populating OpenRC runlevels"
for rl in sysinit boot default shutdown; do mkdir -p "$ROOTFS/etc/runlevels/$rl"; done
add_svc() {
  if [ -e "$ROOTFS/etc/init.d/$2" ]; then
    ln -sf "/etc/init.d/$2" "$ROOTFS/etc/runlevels/$1/$2"
  else
    step "(skip: no init script for $2)"
  fi
}
for s in devfs dmesg mdev hwdrivers cgroups; do add_svc sysinit "$s"; done
for s in modules sysctl hostname bootmisc syslog networking; do add_svc boot "$s"; done
for s in mount-ro killprocs savecache; do add_svc shutdown "$s"; done

cat > "$ROOTFS/etc/network/interfaces" <<'EOF'
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
EOF

# ---------------------------------------------------------------------------
# 3. Stage m1: the AI itself
# ---------------------------------------------------------------------------
if [ "$STAGE" = "m1" ]; then
  log "Installing llama-server"
  install -d "$ROOTFS/opt/clarity/bin" "$ROOTFS/opt/clarity/models" "$ROOTFS/root/Documents"
  cp /opt/llama/bin/* "$ROOTFS/opt/clarity/bin/" || die "llama binaries missing from builder"
  chmod +x "$ROOTFS/opt/clarity/bin"/*
  step "$(ls -1 "$ROOTFS/opt/clarity/bin" | tr '\n' ' ')"

  log "Fetching model: $MODEL_NAME"
  if [ -f "$CACHE/$MODEL_NAME" ]; then
    step "cache hit ($(du -h "$CACHE/$MODEL_NAME" | cut -f1))"
  else
    curl -fL --retry 3 --progress-bar -o "$CACHE/$MODEL_NAME.part" "$MODEL_URL" \
      || die "model download failed: $MODEL_URL"
    mv "$CACHE/$MODEL_NAME.part" "$CACHE/$MODEL_NAME"
    step "downloaded $(du -h "$CACHE/$MODEL_NAME" | cut -f1)"
  fi
  cp "$CACHE/$MODEL_NAME" "$ROOTFS/opt/clarity/models/$MODEL_NAME"

  # llama-server exposes an OpenAI-compatible API on localhost. Nothing binds externally:
  # from M3 the tool broker is the only thing that talks to it.
  cat > "$ROOTFS/etc/init.d/llama-server" <<EOF
#!/sbin/openrc-run

name="llama-server"
description="Local LLM inference server (OpenAI-compatible API on 127.0.0.1:8080)"
command="/opt/clarity/bin/llama-server"
command_args="--model /opt/clarity/models/$MODEL_NAME --host 127.0.0.1 --port 8080 --ctx-size 4096 --no-warmup"
command_background=true
pidfile="/run/llama-server.pid"
output_log="/var/log/llama-server.log"
error_log="/var/log/llama-server.log"

depend() {
    need localmount
    after bootmisc
}
EOF
  chmod +x "$ROOTFS/etc/init.d/llama-server"
  add_svc default llama-server

  cat > "$ROOTFS/opt/clarity/bin/clarity-chat" <<'PYEOF'
#!/usr/bin/env python3
"""Console chat REPL against the local llama-server.

This is the stage-m1 face of ClarityOS: the machine boots and you are talking to a model
that is running on this hardware, with no network dependency of any kind.
"""
import json
import sys
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:8080"
SYSTEM = (
    "You are ClarityOS, an AI running as the operating system of this computer. "
    "Be concise and direct."
)


def wait_for_server(timeout=600):
    """llama-server needs to mmap and warm the model; that can take a while on a cold boot."""
    start = time.time()
    spin = "|/-\\"
    i = 0
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{API}/health", timeout=3) as r:
                if r.status == 200:
                    sys.stdout.write("\r" + " " * 60 + "\r")
                    return True
        except Exception:
            pass
        i += 1
        sys.stdout.write(f"\rLoading model on this hardware... {spin[i % 4]}  ({int(time.time() - start)}s)")
        sys.stdout.flush()
        time.sleep(1)
    return False


def chat(messages):
    body = json.dumps({
        "messages": messages,
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 512,
    }).encode()
    req = urllib.request.Request(
        f"{API}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    out = []
    with urllib.request.urlopen(req, timeout=300) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            try:
                delta = json.loads(payload)["choices"][0]["delta"].get("content", "")
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
            if delta:
                out.append(delta)
                sys.stdout.write(delta)
                sys.stdout.flush()
    print()
    return "".join(out)


def main():
    print("\n  ClarityOS -- the AI is the shell")
    print("  " + "-" * 46)
    if not wait_for_server():
        print("  llama-server did not become healthy.")
        print("  Check /var/log/llama-server.log, then run: rc-service llama-server restart")
        return 1

    try:
        with urllib.request.urlopen(f"{API}/v1/models", timeout=5) as r:
            model = json.load(r)["data"][0]["id"]
        print(f"  model: {model.split('/')[-1]}")
    except Exception:
        pass
    print("  Type your message. Ctrl-D or /exit to drop to a shell.\n")

    messages = [{"role": "system", "content": SYSTEM}]
    while True:
        try:
            user = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nDropping to shell.")
            return 0
        if not user:
            continue
        if user in ("/exit", "/quit"):
            return 0
        messages.append({"role": "user", "content": user})
        print("ai>  ", end="")
        try:
            reply = chat(messages)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"\n[inference failed: {e}]")
            messages.pop()
            continue
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    sys.exit(main())
PYEOF
  chmod +x "$ROOTFS/opt/clarity/bin/clarity-chat"
  ln -sf /opt/clarity/bin/clarity-chat "$ROOTFS/usr/local/bin/clarity-chat" 2>/dev/null || \
    { mkdir -p "$ROOTFS/usr/local/bin"; ln -sf /opt/clarity/bin/clarity-chat "$ROOTFS/usr/local/bin/clarity-chat"; }
fi

# ---------------------------------------------------------------------------
# 4. Console setup
# ---------------------------------------------------------------------------
# At m1 the serial console autologins straight into the chat REPL, so powering on the
# machine lands you in a conversation with a model running locally. tty1 stays a plain
# login shell for debugging.
if [ "$STAGE" = "m1" ]; then
  cat > "$ROOTFS/etc/clarity-login" <<'EOF'
#!/bin/sh
/opt/clarity/bin/clarity-chat
exec /bin/login -f root
EOF
  chmod +x "$ROOTFS/etc/clarity-login"
  SERIAL_GETTY='ttyS0::respawn:/sbin/getty -n -l /etc/clarity-login 115200 ttyS0'
else
  SERIAL_GETTY='ttyS0::respawn:/sbin/getty -n -l /bin/login 115200 ttyS0'
fi

cat > "$ROOTFS/etc/inittab" <<EOF
::sysinit:/sbin/openrc sysinit
::sysinit:/sbin/openrc boot
::wait:/sbin/openrc default

tty1::respawn:/sbin/getty --noclear -n -l /bin/login 38400 tty1
$SERIAL_GETTY

::ctrlaltdel:/sbin/reboot
::shutdown:/sbin/openrc shutdown
EOF

cat > "$ROOTFS/etc/clarityos-build" <<EOF
stage=$STAGE
alpine=$ALPINE_BRANCH
kernel=$KVER
root_partuuid=$ROOT_GUID
esp_partuuid=$ESP_GUID
model=${MODEL_NAME:-none}
EOF

cat > "$ROOTFS/etc/motd" <<EOF
ClarityOS Desktop -- stage $STAGE, kernel $KVER

The AI is the shell: there are no applications, only interfaces generated on demand.
Build metadata: /etc/clarityos-build
EOF

log "Regenerating initramfs for $KVER"
chroot "$ROOTFS" /sbin/mkinitfs -c /etc/mkinitfs/mkinitfs.conf "$KVER" || die "mkinitfs failed"
[ -f "$ROOTFS/boot/vmlinuz-lts" ]   || die "missing $ROOTFS/boot/vmlinuz-lts"
[ -f "$ROOTFS/boot/initramfs-lts" ] || die "missing $ROOTFS/boot/initramfs-lts"

rm -rf "$ROOTFS/var/cache/apk"/* "$ROOTFS/tmp"/* 2>/dev/null || true
step "rootfs size: $(du -sh "$ROOTFS" | cut -f1)"

# ---------------------------------------------------------------------------
# 5. Bootloader: a single standalone GRUB EFI binary with the config baked in
# ---------------------------------------------------------------------------
log "Building standalone GRUB EFI binary"
# No grub-install, no modules directory, no NVRAM entry: the whole configuration lives
# inside BOOTX64.EFI. The removable-media path means UEFI firmware finds it automatically
# under QEMU, Hyper-V Gen2, and real hardware alike.
cat > "$WORK/grub-embedded.cfg" <<EOF
set timeout=3
set default=0
serial --unit=0 --speed=115200
terminal_input console serial
terminal_output console serial

menuentry "ClarityOS Desktop" {
  search --no-floppy --label CLARITYESP --set=root
  linux /vmlinuz-lts root=LABEL=CLARITYROOT rootfstype=ext4 rw console=tty0 console=ttyS0,115200
  initrd /initramfs-lts
}
# Fallback by device path. If this boots but the LABEL entry does not, label resolution is
# at fault; if neither boots, the block driver is missing from the initramfs.
menuentry "ClarityOS Desktop (root=/dev/vda2, virtio fallback)" {
  search --no-floppy --label CLARITYESP --set=root
  linux /vmlinuz-lts root=/dev/vda2 rootfstype=ext4 rw console=tty0 console=ttyS0,115200
  initrd /initramfs-lts
}
menuentry "ClarityOS Desktop (verbose)" {
  search --no-floppy --label CLARITYESP --set=root
  linux /vmlinuz-lts root=LABEL=CLARITYROOT rootfstype=ext4 rw console=tty0 console=ttyS0,115200 ignore_loglevel
  initrd /initramfs-lts
}
EOF

grub-mkstandalone \
  --format=x86_64-efi \
  --output="$WORK/BOOTX64.EFI" \
  --modules="part_gpt part_msdos fat ext2 normal linux echo all_video video video_fb gfxterm test true sleep search search_fs_uuid search_fs_file search_label serial terminal terminfo configfile minicmd" \
  "boot/grub/grub.cfg=$WORK/grub-embedded.cfg" || die "grub-mkstandalone failed"
step "BOOTX64.EFI $(stat -c %s "$WORK/BOOTX64.EFI") bytes"

# ---------------------------------------------------------------------------
# 6. Filesystem images
# ---------------------------------------------------------------------------
log "Creating ESP (FAT32, $((ESP_SECTORS / 2048)) MiB)"
rm -f "$WORK/esp.img"
truncate -s $((ESP_SECTORS * 512)) "$WORK/esp.img"
mkfs.vfat -F 32 -n CLARITYESP "$WORK/esp.img" >/dev/null || die "mkfs.vfat failed"
mmd   -i "$WORK/esp.img" ::/EFI ::/EFI/BOOT
mcopy -i "$WORK/esp.img" "$WORK/BOOTX64.EFI"           ::/EFI/BOOT/BOOTX64.EFI
mcopy -i "$WORK/esp.img" "$ROOTFS/boot/vmlinuz-lts"    ::/vmlinuz-lts
mcopy -i "$WORK/esp.img" "$ROOTFS/boot/initramfs-lts"  ::/initramfs-lts

log "Creating root filesystem (ext4, ${ROOT_MIB} MiB)"
rm -f "$WORK/root.img"
mke2fs -q -t ext4 -L CLARITYROOT -d "$ROOTFS" -b 4096 -N 65536 \
       "$WORK/root.img" $((ROOT_SECTORS / 8)) || die "mke2fs failed"
tune2fs -c 0 -i 0 "$WORK/root.img" >/dev/null

# ---------------------------------------------------------------------------
# 7. Assemble the GPT disk
# ---------------------------------------------------------------------------
log "Assembling GPT disk ($((TOTAL_SECTORS / 2048)) MiB)"
rm -f "$RAW"
truncate -s $((TOTAL_SECTORS * 512)) "$RAW"
sfdisk --no-tell-kernel --quiet "$RAW" <<EOF
label: gpt
label-id: $DISK_GUID
unit: sectors
first-lba: $ESP_START

start=$ESP_START,  size=$ESP_SECTORS,  type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B, uuid=$ESP_GUID,  name="CLARITYESP"
start=$ROOT_START, size=$ROOT_SECTORS, type=0FC63DAF-8483-4772-8E79-3D69D8477DE4, uuid=$ROOT_GUID, name="CLARITYROOT"
EOF
dd if="$WORK/esp.img"  of="$RAW" bs=1M seek=$((ESP_START / 2048))  conv=notrunc status=none
dd if="$WORK/root.img" of="$RAW" bs=1M seek=$((ROOT_START / 2048)) conv=notrunc status=none
sfdisk --list "$RAW" | sed 's/^/    /'

log "Converting to qcow2"
rm -f "$QCOW"
qemu-img convert -f raw -O qcow2 -c "$RAW" "$QCOW" || die "qemu-img convert failed"

log "Exporting to /out"
cp "$QCOW" "$OUT/clarityos.qcow2"
step "clarityos.qcow2  $(du -h "$OUT/clarityos.qcow2" | cut -f1)"
if [ "$EXPORT_RAW" = "1" ]; then
  cp "$RAW" "$OUT/clarityos.raw"
  step "clarityos.raw    $(du -h "$OUT/clarityos.raw" | cut -f1)  (dd this to a USB stick)"
else
  step "raw image not exported (set EXPORT_RAW=1 when you need a USB image)"
fi

log "Build complete: stage $STAGE"
