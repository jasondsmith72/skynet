# M4 — Real hardware

Target: Dell laptop, i7-9750H (6c/12t, Coffee Lake-H), 15.8 GB DDR4, RTX 2070 Max-Q (TU106,
sm_75, 8 GB), Intel UHD 630, internal disk an **Intel RST RAID 0 volume**. Authoring host is
Windows 11 Home.

M0–M3 are verified under QEMU. M4 is the first rung where the substrate meets firmware it did
not write, a GPU it cannot see from a VM, and a screen instead of a serial port. This document
covers four things, in the order you will hit them:

1. [Writing the image to USB from Windows](#1-writing-the-image-to-usb-from-windows)
2. [GPU-accelerated inference on the RTX 2070](#2-gpu-accelerated-inference-on-the-rtx-2070)
3. [Firmware for wifi, Intel graphics and NVIDIA](#3-firmware)
4. [UEFI and Secure Boot](#4-uefi-and-secure-boot)

Then [real-hardware gotchas already visible in `build.sh`](#5-gotchas-already-visible-in-buildsh)
and a [verification ledger](#6-verification-ledger) saying exactly which claims here were tested
and which were not.

Everything marked **verified** was checked empirically on this machine with Docker or PowerShell
during the writing of this document. Everything else is marked.

---

## 1. Writing the image to USB from Windows

`write-usb.ps1` in the project root does this. Run it with no arguments first:

```powershell
.\write-usb.ps1
```

That lists every physical disk with model, bus type, size, partitions and volume labels, marks
which ones are plausible USB targets, and writes nothing. Then:

```powershell
.\write-usb.ps1 -DiskNumber 2 -DryRun      # every check + destruction summary, writes nothing
.\write-usb.ps1 -DiskNumber 2 -Verify      # for real; needs an elevated shell
```

The raw image is only produced on request — the build defaults to qcow2 only:

```bash
EXPORT_RAW=1 STAGE=m1 ./make.sh
```

At stage m1 the image is 4354 MiB (1 MiB gap + 256 MiB ESP + `ROOT_MIB`=4096 root + 1 MiB tail),
so a nominal 8 GB stick is comfortable. Re-check this against `ROOT_MIB` in `build.sh` before
buying a stick — it has already been retuned once (6144 → 4096) and M2's graphics stack is meant
to land in that same 4 GiB. A 16 GB stick costs nothing and leaves room to grow the root
partition on-device for a larger model. Write time is entirely the stick's: roughly 40 seconds on
a decent USB 3 drive, 3 minutes on USB 2, and 8+ minutes on a cheap one.

### Why a .NET FileStream and not dd-for-windows

The options were raw `System.IO.FileStream` against `\\.\PhysicalDriveN`, the chrysocome
`dd.exe` port, or delegating to Rufus/balenaEtcher in DD mode. FileStream wins for this script:

- **No dependency to fetch and trust.** `dd.exe` is a single unsigned third-party binary. Worse,
  its device addressing (`of=\\?\Device\Harddisk1\Partition0`) is a different namespace from the
  disk numbers Windows shows you in Disk Management, so the one thing you must not get wrong is
  expressed in the one syntax you have no independent way to check. Rufus and Etcher are good
  interactive tools but are not scriptable with the guard rails this script needs.
- **One process owns the whole sequence.** Enumeration, the safety checks, the dismount and the
  write all happen in the same script with the same disk handle, so there is no gap between
  "we established disk 2 is a 32 GB SanDisk with no system volume" and "something writes to disk
  2". A shell-out to `dd` reopens that gap.
- **It is verified to work.** `New-Object System.IO.FileStream('\\.\PhysicalDrive0', ...)` on this
  box fails with *"Access to the path '\\.\PhysicalDrive0' is denied"* when not elevated — a
  permission error, not a path-format error. .NET Framework 4.x resolves the DOS device path
  natively; no P/Invoke to `CreateFile` is needed.

Two mechanical details that this choice forces, both handled in the script:

- **Unbuffered, sector-aligned writes.** A raw physical-drive handle only accepts writes whose
  length is a multiple of the logical sector size at sector-aligned offsets. `FileStream` is
  constructed with `bufferSize = 1` (which disables its own buffering) plus
  `FileOptions.WriteThrough`, the loop writes 4 MiB chunks, and the final short chunk is
  zero-padded up to the sector size taken from `Get-Disk`'s `LogicalSectorSize` (512 here, but
  4 Kn drives exist).
- **Dismounting.** Windows refuses raw writes to sectors owned by a mounted volume, and the mount
  manager will happily re-mount a volume in the middle of a write. The script therefore
  `Clear-Disk -RemoveData -RemoveOEM` (which removes the volumes outright), then
  `Set-Disk -IsOffline $true` (which stops the mount manager touching the disk at all), and only
  then opens the device. Both are native Storage-module cmdlets — no `FSCTL_LOCK_VOLUME` /
  `FSCTL_DISMOUNT_VOLUME` P/Invoke required. It is put back online at the end.

### The safety rails

This script destroys disks, so the rails matter more than the write loop. In order:

1. **`-DiskNumber` is mandatory and has no default.** The script uses two parameter sets:
   running it bare selects the `List` set and cannot write anything. There is deliberately no
   "we found one removable disk, that must be it" path.
2. **Hard refusals — `-Force` does not override these:**
   - disk 0,
   - a disk Windows flags `IsBoot` or `IsSystem`,
   - the disk holding `%SystemDrive%`,
   - the disk holding this script (`$PSScriptRoot`),
   - the disk holding the image file being written,
   - any disk smaller than the image.
3. **Soft refusals — `-Force` overrides, after printing why:**
   - bus type is not `USB`/`SD`/`MMC` and `Win32_DiskDrive.MediaType` is not removable,
   - the disk is larger than `-MaxSizeGB` (default 256 GB) — a 2 TB target is far more likely to
     be your backup drive than your USB stick.
4. **The image is validated before the disk is touched.** The first 4 KiB must carry a protective
   MBR signature at 0x1FE and `EFI PART` at the start of LBA 1, or the script refuses. It also
   looks for a `CLARITY*` GPT partition name (UTF-16LE) and warns if absent. A typo in `-Image`
   cannot write a text file over a partition table.
5. **A destruction summary and a typed phrase.** Every partition, drive letter, label, filesystem
   and free-space figure that is about to disappear is printed in red, and you must type
   `ERASE DISK <n>` exactly (case-sensitive) to continue.
6. **Elevation is checked and refused, not worked around.** The script tells you the command to
   re-run elevated rather than half-running and failing at the write.

Refusal paths 1, 2 (disk 0), the "no such disk" path, the missing-image path and the
GPT-validation path were all exercised on this machine. The write loop, the dismount sequence and
`-Verify` were **not** — there is no USB stick attached and the shell is not elevated. See
[§6](#6-verification-ledger).

`-Verify` re-reads the written region and compares SHA256 against the image. It roughly doubles
the run time and is worth it once per stick: cheap flash fails exactly this way, silently.

### After writing

Windows will see the 256 MiB FAT32 ESP (`CLARITYESP`) and an ext4 partition it cannot read
(`CLARITYROOT`). It may offer to format the second one. Say no. Eject from the tray icon before
unplugging.

---

## 2. GPU-accelerated inference on the RTX 2070

### The blocking fact: there is no CUDA on musl, and there never will be

Searched the APKINDEX of `v3.21`, `v3.22`, `v3.23`, `v3.24` and `edge` (main + community +
testing) for `^cuda`, `nvidia`, `nccl`, `^opencl`. **Verified** results — the complete set of
NVIDIA-related packages in all of Alpine:

| Package | Branch | Size (dl / installed) | What it actually is |
|---|---|---|---|
| `linux-firmware-nvidia` | v3.21 main | 39.5 M / 39.4 M | GPU firmware blobs for **nouveau**, incl. Turing GSP |
| `linux-firmware-nvidia` | v3.24 main | 103.5 M / 103.5 M | same, newer snapshot |
| `nvidia-src` | edge **testing** | 23.0 M / 121.0 M | NVIDIA *open* GPU **kernel module** source, built by AKMS |
| `xf86-video-nouveau` | community | 79 K / 176 K | X.org DDX, irrelevant here |

There is no `nvidia-utils`, no `libcuda`, no `cuda-toolkit`, no `nvidia-driver`, in any branch.
This is not an Alpine packaging gap, it is structural:

- Alpine's own wiki: *"The proprietary NVIDIA driver is not available for musl C library used in
  Alpine Linux. However, Nouveau, the open-source driver for NVIDIA GPUs is supported as an
  alternative."*
- NVIDIA's answer on their own tracker is that the kernel module is not the problem — it links
  against the kernel, not libc — the problem is the closed userspace components, which are built
  against glibc. Their position on shipping a musl build is that it is not planned.
- `nvidia-container-toolkit` issue #1526 documents the second-order version of the same problem:
  musl has no `ldconfig`/`ld.so.cache`, so even library *injection* into an Alpine container does
  not work.

So `nvidia-src` is a trap for this purpose. NVIDIA's open kernel modules do support Turing and
later (they are built on GSP, which Turing introduced), so `nvidia.ko` would build for the
RTX 2070 via AKMS against `linux-lts`. But a kernel module with no `libcuda.so.1` and no
`libnvidia-glcore` gets you a GPU that is initialised and idle. There is no route from there to
`GGML_CUDA=ON` without glibc.

### Vulkan, on the other hand, works on musl — verified by building it

The Vulkan backend has no glibc dependency at all. Built inside `alpine:3.21`:

```
apk add build-base cmake git linux-headers vulkan-loader vulkan-loader-dev \
        vulkan-headers shaderc glslang glslang-dev glslang-libs
cmake -B build -DGGML_VULKAN=ON -DGGML_NATIVE=OFF -DGGML_AVX2=ON ... -DBUILD_SHARED_LIBS=OFF
```

Result (**verified**, llama.cpp `b4585`, ~20 min at `-j12`):

```
-- Found Vulkan: /usr/lib/libvulkan.so (found version "1.3.296") found components: glslc glslangValidator
-- Vulkan found
-- GL_KHR_cooperative_matrix supported by glslc
-- GL_NV_cooperative_matrix2 not supported by glslc
-- Including Vulkan backend
...
-rwxr-xr-x  16359440  build/bin/llama-server
=== dynamic deps of llama-server ===
        libvulkan.so.1 => /usr/lib/libvulkan.so.1
```

Two things matter here. First, the *only* new runtime dependency is `libvulkan.so.1`, i.e. the
`vulkan-loader` package — 502 KiB installed on v3.21, 586 KiB on v3.24. Everything else stays
statically linked exactly as it is today. Second, `GL_KHR_cooperative_matrix` shaders **were**
compiled, so llama.cpp will use Turing's tensor cores through `VK_KHR_cooperative_matrix` *if the
driver exposes that extension*. That "if" is the whole risk in this section; see below.

Corroboration that this is a supported configuration rather than a lucky build: Alpine
**v3.24/community ships a prebuilt `llama.cpp-vulkan`** (0.0.9564-r0, 16.3 M download / 55.6 M
installed), and edge/community carries 0.0.10250-r0. Somebody else is already maintaining a musl
Vulkan llama.cpp.

### But the Vulkan *driver* for the RTX 2070 is NVK, and that has two conditions

The open Vulkan driver for NVIDIA hardware is NVK, shipped in Mesa as `mesa-vulkan-nouveau`.
**Verified** availability by branch:

| Alpine branch | Mesa | `mesa-vulkan-nouveau` | `linux-lts` |
|---|---|---|---|
| **v3.21** (current base) | 24.2.8 | **absent** | 6.12.98 |
| v3.22 | 25.1.9 | 3.3 M / 14.4 M | 6.12.101 |
| v3.23 | 25.2.7 | 3.1 M / 14.5 M | 6.18.42 |
| **v3.24** (latest) | 26.1.6 | 3.3 M / 16.3 M | 6.18.42 |

**The current base cannot do this at all.** On Alpine 3.21 the only Vulkan ICDs available are
`mesa-vulkan-intel` (UHD 630) and `mesa-vulkan-swrast` (lavapipe, CPU). A Vulkan build on 3.21
would enumerate no NVIDIA device.

Condition two is GSP, and it is the part most likely to bite. Nouveau cannot reclock Turing
without the GPU System Processor firmware; without it the card sits in its lowest power state and
will be *slower than the CPU*. **Verified** from the shipped kernel configs:

- `linux-lts` 6.12.98 (Alpine 3.21/3.22): `CONFIG_DRM_NOUVEAU_GSP_DEFAULT` is present and
  **`is not set`**. GSP is off for Turing unless you pass `nouveau.config=NvGspRm=1` on the
  kernel command line. The `config` module parameter exists (`parm: config:option string to pass
  to driver core (charp)`), so the knob is there.
- `linux-lts` 6.18.42 (Alpine 3.23/3.24): the `CONFIG_DRM_NOUVEAU_GSP_DEFAULT` symbol is **gone
  from the config entirely** — consistent with the upstream change that made GSP the default path
  for Turing and Ampere in 6.18. No boot flag needed.

The firmware itself is in `linux-firmware-nvidia`. **Verified** layout for TU106:

```
nvidia/tu106/gr/{fecs,gpccs}_{inst,data,sig}.bin      60 KiB
nvidia/tu106/acr/, sec2/, nvdec/
nvidia/tu106/gsp -> ../tu102/gsp                      (relative symlink)
nvidia/tu102/gsp/gsp-535.113.01.bin
nvidia/tu102/gsp/bootloader-535.113.01.bin
nvidia/tu102/gsp/booter_{load,unload}-535.113.01.bin  12.6 MiB total
```

So the whole Turing GSP payload is **12.7 MiB** if you copy `nvidia/tu102` and `nvidia/tu106`,
not the full 39.4 MiB package. Preserve the relative symlink.

### Expected throughput

Anchors. From the llama.cpp Vulkan scoreboard (discussion #10879), Llama-2 7B Q4_0 on the
NVIDIA **proprietary** Vulkan driver: RTX 2070 Super `pp512 = 1199 t/s`, `tg128 = 64.6 t/s`;
RTX 2080 Ti `pp512 ≈ 1900 t/s`, `tg128 ≈ 98–101 t/s`. From Phoronix's May 2026 Nouveau/NVK
review, llama.cpp on Nouveau reached at best about 70% of the proprietary R595 driver and
"more often than not ... 50% or less".

A 7B Q4_K_M is ~4.4 GB of weights. The RTX 2070 Max-Q has ~448 GB/s of VRAM bandwidth against
the laptop's ~35 GB/s of usable DDR4-2666, and Max-Q is power-limited to roughly 80–90 W against
the desktop 2070's 175 W. Token generation is bandwidth-bound; prompt processing is compute-bound
and is where a missing cooperative-matrix path hurts most.

| Path | pp512 (t/s) | tg128 (t/s) | Confidence |
|---|---|---|---|
| CPU only, AVX2, 6c/12t, bare metal | 20–35 | 4–7 | High. 4.4 GB / ~35 GB/s caps tg near 8. |
| Intel UHD 630 via Vulkan (ANV) | 30–60 | 3–6 | Medium. Same DDR4, no bandwidth win. Not worth it. |
| Vulkan + NVK, **GSP off** (6.12 default) | <50 | <5 | High that it is bad. No reclocking. |
| Vulkan + NVK, GSP on (6.18) | 150–450 | 20–35 | **Low–medium.** Extrapolated from Phoronix's 50–70%; no Turing-specific NVK llama.cpp benchmark exists that I could find. |
| Vulkan + proprietary driver | 900–1100 | 45–55 | Medium-high, but **impossible on musl** — glibc rootfs only. |
| CUDA (`GGML_CUDA=ON`, `sm_75`) on glibc | 1000–1400 | 50–60 | Medium-high. |

Note the range on the NVK row. It is the widest row in the table and it is the one the
recommendation depends on, which is why the recommendation is staged.

8 GB of VRAM is not a constraint: 7B Q4_K_M (~4.4 GB) plus a 4096-token KV cache (~0.5 GB)
offloads fully with `-ngl 99` and leaves headroom.

### Recommendation

**Stage it. Do not couple "boots on real hardware" to "uses the GPU".**

**m4a — first, and independently valuable.** Keep Alpine 3.21 and CPU inference exactly as they
are. Add firmware and wifi (§3), fix the console problems (§5), boot from the USB stick, and
measure a real CPU baseline on bare metal with `llama-bench`. The current 11.6 tok/s figure is
from a 4-vCPU WHPX guest; bare metal on 6c/12t should be substantially better, and you need that
number before any GPU claim means anything.

**m4b — the recommended GPU path: Vulkan/NVK on Alpine 3.24.** Bump the rootfs branch to v3.24,
which gets you kernel 6.18 (GSP by default on Turing), Mesa 26.1 (NVK), and a
community-maintained musl Vulkan llama.cpp as a fallback if your own build misbehaves.

Why this over CUDA:

- It preserves the thing the architecture document is actually about — one thin, all-musl
  substrate. No glibc, no second libc, no chroot.
- The cost is tiny and now measured: `vulkan-loader` 0.6 MiB + `mesa-vulkan-nouveau` 16.3 MiB +
  12.7 MiB of Turing firmware ≈ **30 MiB** of rootfs, against roughly 1.5–2 GiB for a glibc base
  plus the NVIDIA driver plus cuBLAS/cuBLASLt.
- It degrades safely. A Vulkan-enabled `llama-server` with no usable Vulkan device falls back to
  CPU; you do not get an unbootable machine, you get the m4a behaviour.
- The build is proven to work on musl (above), not assumed.

Its risk is honestly stated: NVK on Turing may not expose `VK_KHR_cooperative_matrix`, in which
case prompt processing will be poor even though generation is fine. That is measurable in about
five minutes on the real box.

**Decision gate — run these on the hardware before committing to m4b or m4c:**

```sh
lspci -nnk | grep -A3 -i vga            # is the dGPU bound to nouveau at all?
dmesg | grep -iE 'nouveau|gsp'          # did GSP init, or did firmware loading fail?
cat /sys/kernel/debug/dri/*/pstate      # reclocking state; stuck at the lowest = no GSP
vulkaninfo --summary                    # is there a device that is not llvmpipe?
vulkaninfo | grep -i cooperative_matrix # tensor-core path available?
llama-bench -m /opt/clarity/models/<7b>.gguf -ngl 99 -p 512 -n 128
```

Pass criterion: `tg128` at least 3× the m4a CPU baseline. If NVK clears that, stop; you are done
and the substrate stayed clean.

**m4c — only if m4b fails the gate: glibc rootfs and CUDA.** Concretely, replace the Alpine
rootfs with Debian 13 built by `mmdebstrap`, which — usefully — still runs unprivileged, so
`build.sh`'s "no loop devices, no privileged container" property survives. Then the NVIDIA
non-free driver plus `-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75`. Budget 1.5–2 GiB of extra
image for the driver and cuBLAS/cuBLASLt, and raise `ROOT_MIB`. The boot chain is unchanged; GRUB
does not care what userland it loads.

**Explicitly rejected:**

- *NVIDIA proprietary userspace on musl via `gcompat`.* The blobs depend on glibc-specific
  loader behaviour and on `ld.so.cache`, which musl does not have. This is the configuration
  NVIDIA's own container toolkit cannot make work.
- *`nvidia-src` alone.* Kernel module without userspace. Also `edge/testing`, so not available on
  a released branch.
- *An Alpine substrate with a Debian chroot just for `llama-server`.* Technically possible — build
  the open kernel module with AKMS, put the glibc userspace and a CUDA `llama-server` in a chroot.
  It gets you CUDA speed while keeping Alpine. It also gets you two libcs, two package managers
  and a driver-version coupling between them, which is precisely the maintenance surface this
  project is built to avoid. If m4b fails the gate, m4c is cleaner than this.

---

## 3. Firmware

`build.sh` installs `linux-firmware-none` (0 bytes) to dodge the ~1 GB `linux-firmware` meta.
That is right for QEMU, where virtio needs no firmware, and wrong for this laptop.

Budget note before the numbers: `ROOT_MIB` is 4096 for m1 and the m1 rootfs measures ~1.3 GB, so
there is room, but M2's graphics stack is already earmarked for part of it. The surgical subset
below is ~21 MiB; the naive package set is ~121 MiB. Either fits, but m4 will also want a bigger
model than the 1 GB Qwen2.5-1.5B, so raise `ROOT_MIB` for the m4 stage rather than squeezing.

**A packaging trap first:** there is **no `linux-firmware-iwlwifi` package in any Alpine branch.**
Verified. Intel wifi firmware moved between subpackages across releases, and getting this wrong
means silently no wifi:

- **Alpine 3.21** (`linux-firmware` 20241210): `iwlwifi-*.ucode` files sit at the *top level* of
  `/lib/firmware` and belong to **`linux-firmware-other`** (72.2 MiB installed). Verified with
  `apk info --who-owns /lib/firmware/iwlwifi-cc-a0-77.ucode.zst` →
  `linux-firmware-other-20241210-r0`. `linux-firmware-intel` at 3.21 is 21.5 MiB of Bluetooth
  (`ibt-*`, 99 files) and contains **zero** iwlwifi files.
- **Alpine 3.24** (`linux-firmware` 20260519): they moved into `/lib/firmware/intel/iwlwifi/` and
  now belong to **`linux-firmware-intel`**, which grew to 116.1 MiB. `linux-firmware-other`
  shrank to 5.4 MiB.

### Exact packages, verified sizes

Alpine **v3.21** (the current base):

| Hardware | Package | Download | Installed |
|---|---|---|---|
| Intel wifi — AX200 / AX201 / 9560 | `linux-firmware-other` | 72.2 M | 72.2 M |
| Intel UHD 630 (i915 DMC/GuC/HuC) | `linux-firmware-i915` | 9.3 M | 9.2 M |
| NVIDIA TU106 (nouveau + GSP) | `linux-firmware-nvidia` | 39.5 M | 39.4 M |
| Realtek GbE (`r8169`) | `linux-firmware-rtl_nic` | 62 K | 152 K |
| Intel Bluetooth (optional) | `linux-firmware-intel` | 21.5 M | 21.5 M |

Alpine **v3.24**, if you bump for m4b: `linux-firmware-intel` 116.1 M (now includes iwlwifi),
`linux-firmware-i915` 9.3 M, `linux-firmware-nvidia` 103.5 M, `linux-firmware-rtl_nic` 0.1 M.

Naive total on 3.21: **~121 MiB** for wifi + graphics, on a 6 GiB root. Workable, but 95% of it
is firmware for hardware this laptop does not have.

### The surgical subset — about 21 MiB

All sizes below are compressed-on-disk (`.zst`) from an actual install, **verified**.

**Intel wifi.** A 9750H-class Dell ships one of: AX200 (`iwlwifi-cc-a0-*`), AX201
(`iwlwifi-QuZ-a0-hr-b0-*` or `iwlwifi-Qu-c0-hr-b0-*`), or Wireless-AC 9560
(`iwlwifi-9000-pu-b0-jf-b0-*`). Killer 1650x is an AX200 rebadge and uses the `cc-a0` files.
`iwlwifi` requests the highest API version it supports and steps down, so ship the whole family
rather than one file:

| Family | Files | Size | Covers |
|---|---|---|---|
| `iwlwifi-cc-a0-*` | 7 | 3.3 MiB | AX200, Killer 1650x |
| `iwlwifi-QuZ-a0-hr-b0-*` | 7 | 3.3 MiB | AX201 |
| `iwlwifi-Qu-b0-hr-b0-*`, `-Qu-c0-hr-b0-*` | 7 each | 3.3 MiB each | AX201 stepping variants |
| `iwlwifi-9000-pu-b0-jf-b0-*` | 3 | 1.3 MiB | Wireless-AC 9560 |

Individual files are ~500 KiB (`iwlwifi-cc-a0-77.ucode.zst` = 500.5 KiB,
`iwlwifi-QuZ-a0-hr-b0-77.ucode.zst` = 507.7 KiB, `iwlwifi-9000-pu-b0-jf-b0-46.ucode.zst` =
461.8 KiB). All 153 iwlwifi files together are 68 MiB, which is why the subset is worth it.
Cheapest correct answer: ship the three families above, ~8 MiB. Cheapest possible answer: run
`lspci -nn | grep -i network` on the box once and ship one family, ~3.3 MiB.

**Intel UHD 630.** Coffee Lake graphics is gen9.5 and uses the Kaby Lake blobs. Exactly three
files, **158 KiB total**:

| File | Size | Needed for |
|---|---|---|
| `i915/kbl_dmc_ver1_04.bin` | 2.5 KiB | Display microcode — display power states. Without it you get a dmesg warning and lose DC power savings; the display still works. |
| `i915/kbl_guc_70.1.1.bin` | 85.6 KiB | GuC submission |
| `i915/kbl_huc_4.0.0.bin` | 70.1 KiB | HuC, media offload |

Only the DMC file is load-bearing for a framebuffer, and even that is not strictly required. The
9.2 MiB package is 128 files spanning every Intel GPU generation.

**NVIDIA TU106.** Copy `nvidia/tu102` (12.8 MiB — the GSP blobs live here) and `nvidia/tu106`
(60 KiB), preserving `tu106/gsp -> ../tu102/gsp`. **12.7 MiB** where the package is 39.4.

**Realtek GbE.** `linux-firmware-rtl_nic` is 152 KiB whole. Not worth subsetting; just install it.

### Suggested `build.sh` change

Not applied — `build.sh` is untouched by this document. Gated on stage so m0/m1 stay lean. Note
that `m4` is not yet a case in `build.sh`'s `case "$STAGE"` block, so it needs adding there first
along with its own `ROOT_MIB`.

```bash
# Stage m4 needs firmware for hardware QEMU does not have. The builder container is the
# same Alpine release as the rootfs, so its own /lib/firmware is the right source.
if [ "$STAGE" = "m4" ]; then
  PKGS+=( linux-firmware-i915 linux-firmware-rtl_nic wpa_supplicant iw pciutils
          eudev udev-init-scripts )
  # Vulkan path (m4b). vulkan-loader is the only new .so llama-server needs.
  PKGS+=( vulkan-loader mesa-vulkan-nouveau )     # mesa-vulkan-nouveau needs ALPINE_BRANCH>=v3.22
else
  PKGS+=( linux-firmware-none )
fi

...after the apk install into $ROOTFS...

if [ "$STAGE" = "m4" ]; then
  log "Installing the firmware subset this laptop actually needs"
  apk add --no-cache linux-firmware-other linux-firmware-nvidia   # into the BUILDER, not rootfs
  install -d "$ROOTFS/lib/firmware/nvidia"

  # Intel wifi: no linux-firmware-iwlwifi package exists. On v3.21 these live at the top
  # level of /lib/firmware and belong to linux-firmware-other (72 MiB); take ~8 MiB of it.
  # On v3.24+ they moved to intel/iwlwifi/ inside linux-firmware-intel -- adjust the source
  # path if you bump the branch.
  for fam in cc-a0 QuZ-a0-hr-b0 Qu-b0-hr-b0 Qu-c0-hr-b0 9000-pu-b0-jf-b0; do
    cp -a /lib/firmware/iwlwifi-$fam-*.ucode* "$ROOTFS/lib/firmware/" 2>/dev/null || true
  done

  # NVIDIA: tu106 plus tu102 (tu106/gsp is a relative symlink into tu102/gsp). 12.7 MiB.
  cp -a /lib/firmware/nvidia/tu102 /lib/firmware/nvidia/tu106 "$ROOTFS/lib/firmware/nvidia/"

  step "firmware in rootfs: $(du -sh "$ROOTFS/lib/firmware" | cut -f1)"
fi
```

Two related notes:

- **`eudev` over `mdev`.** `build.sh` currently runs `hwdrivers` with busybox `mdev`. That is fine
  for virtio; on real hardware, getting `iwlwifi`, `i915` and `nouveau` autoloaded together with
  their firmware is considerably more reliable under `eudev` (656 KiB) + `udev-init-scripts`.
  Swap `mdev`/`hwdrivers` in the sysinit runlevel for `udev`/`udev-trigger`/`udev-settle`.
- **initramfs.** `features="base kms ..."` already pulls DRM drivers into the initramfs, so once
  `i915`/`nouveau` are there they will want firmware early. `mkinitfs` copies firmware declared by
  the included modules, which for `nouveau` means it may try to pull all 65 GSP variants. Check
  `initramfs-lts` size after the change; if it balloons, drop `kms` from the initramfs and let
  KMS come up from the real root instead.
- Wifi itself needs `wpa_supplicant` (3.7 MiB) + `iw` (232 KiB), and
  `/etc/network/interfaces` currently only defines `lo` and `eth0`.

---

## 4. UEFI and Secure Boot

The image ships an **unsigned** `grub-mkstandalone` binary at `/EFI/BOOT/BOOTX64.EFI`. With
Secure Boot enabled, Dell firmware will either refuse it outright ("Invalid signature detected",
"Security Violation") or silently skip it and fall through to the next boot option, which looks
identical to "the USB stick did not boot".

### What to do on the machine

The partition layout on the internal disk (`WINRETOOLS`, `Image`, `DELLSUPPORT`) and the
`Intel Raid 0 Volume` identify this as a Dell with Intel RST. Menu paths vary a little by model.

**Before you touch anything, check BitLocker.** Changing the Secure Boot state changes PCR 7,
which invalidates a TPM-sealed BitLocker key and drops Windows into recovery on its next boot.
From an elevated Windows prompt:

```powershell
manage-bde -status C:
# If Protection Status is On, suspend it across the trip into firmware and back:
manage-bde -protectors -disable C: -RebootCount 2
```

Otherwise have the 48-digit recovery key in hand (it is in your Microsoft account or Entra, not
on the machine).

Then:

1. Power off. Power on and tap **F2** repeatedly for firmware setup. (**F12** is the one-time boot
   menu — you want that later, not now.)
2. **Boot Configuration** → **Secure Boot** → **Secure Boot Enable** = **Disabled**.
   On some Dells this control is greyed out until Boot List Option is UEFI (it already is) or
   until an admin password is set.
3. **POST Behaviour** → **Fast Boot** = **Thorough**. With Fast Boot on Minimal, USB controllers
   are not always fully enumerated in time and the stick will not appear in the boot menu.
4. Leave **Enable Legacy Option ROMs** / CSM **off**. The image is UEFI-only; enabling CSM can
   change how the firmware picks a boot target and gains you nothing.
5. **Do not touch SATA Operation.** It is set to *RAID On* (Intel RST) and Windows is installed on
   an Intel RAID 0 volume. Switching it to AHCI makes Windows unbootable with
   INACCESSIBLE_BOOT_DEVICE. ClarityOS boots from USB and does not need to see the internal disk
   at all — and in fact will not, or will see the raw RAID members, which is expected and should
   not be "fixed".
6. **Save & Exit.**
7. Power on with the stick inserted and tap **F12**. In the one-time boot menu, under the
   **UEFI BOOT** heading, choose the USB device — it appears as something like
   `UEFI: SanDisk Cruzer, Partition 1`. Partition 1 is the ESP; that is the right entry.

You do not need to change the persistent boot order and you do not need `efibootmgr`. The whole
point of using the removable-media path `/EFI/BOOT/BOOTX64.EFI` is that firmware finds it without
an NVRAM entry. Use F12 every time; leave the machine's normal boot order alone.

When you are done, re-enable Secure Boot if you want Windows and BitLocker in their normal state,
and re-enable BitLocker protectors if you suspended them (`manage-bde -protectors -enable C:`).

### What signing would involve

Three routes, cheapest to most invasive. Alpine has the tools: `sbsigntool` (98 K / 238 K) in
main, `mokutil` (23 K / 52 K) in community — both **verified** present.

**a) Enrol your own keys (own PK/KEK/db).** Put the firmware into Setup Mode via Dell's *Expert
Key Management*, clear the factory keys, enrol your own, then
`sbsign --key db.key --cert db.crt --output BOOTX64.EFI BOOTX64.EFI`. Full control, no third
party. The catch: if you clear the factory `db` you must also enrol Microsoft's Windows
Production CA or Windows stops booting, and some machines will then refuse signed option ROMs on
add-in cards. It also trips BitLocker, once.

**b) shim + MOK.** Use a distribution's shim (already signed by the Microsoft UEFI CA), enrol your
own certificate with `mokutil --import`, and sign GRUB and the kernel with it. No firmware key
surgery, and it works on machines whose firmware you do not control. The catch: shim only chains
to a shim-aware GRUB, and Secure Boot GRUB builds deliberately distrust configuration they did not
verify — which interacts awkwardly with `grub-mkstandalone`'s embedded-config trick. Getting your
*own* shim signed by Microsoft means going through the `shim-review` process.

**c) Drop GRUB and sign a unified kernel image.** **Verified:** Alpine's `linux-lts` is built with
`CONFIG_EFI_STUB=y`, so `vmlinuz-lts` is itself a valid EFI application. Build a UKI —
`objcopy` the command line into a `.cmdline` section and `initramfs-lts` into `.initrd`, then
`sbsign` the result and drop it at `/EFI/BOOT/BOOTX64.EFI`. One binary, one signature, no
bootloader in the substrate at all, which is very much in the spirit of the architecture. Note
`CONFIG_CMDLINE_BOOL` is **not set** in Alpine's config, so the command line has to come from the
UKI section rather than being compiled in. Cost: you lose GRUB's menu, so the "verbose" and
"device-path fallback" boot entries that have been useful through M0–M1 would need another
mechanism.

Also **verified**, and relevant if you ever go the AKMS route: `CONFIG_MODULE_SIG_FORCE` is *not*
set and `CONFIG_LOCK_DOWN_KERNEL_FORCE_NONE=y`, so Alpine does not enforce module signatures or
auto-engage the lockdown LSM when Secure Boot is on. Out-of-tree modules load either way.

**Recommendation for M4: just disable Secure Boot.** Signing is a self-contained project worth
doing when this becomes a machine someone carries around, and it buys nothing on a bench.

---

## 5. Gotchas already visible in `build.sh`

These come from reading the current build against this hardware. Each one is a thing that will
look like a hardware failure and is not.

**1. The chat REPL is only on the serial port — a laptop has no serial port.** At m1,
`/etc/clarity-login` is wired to the `ttyS0` getty:

```
ttyS0::respawn:/sbin/getty -n -l /etc/clarity-login 115200 ttyS0
tty1::respawn:/sbin/getty --noclear -n -l /bin/login 38400 tty1
```

On real hardware you boot to a bare `login:` prompt on `tty1` and the AI is invisible. For m4 the
autologin has to move to `tty1`. This is the single most likely way for a successful m4 boot to
look like a failure.

**2. `console=ttyS0,115200` is last on the kernel command line, so it wins.** Linux uses the last
`console=` as `/dev/console`. **Verified** that Alpine's kernel has `CONFIG_SERIAL_8250=y` and
`CONFIG_SERIAL_8250_CONSOLE=y`, so if the PCH exposes a legacy COM port through ACPI — which
plenty of laptops do, with nothing wired to it — the kernel will take it and the screen will stay
blank through the whole boot. Add an m4 menu entry with `console=tty0` only, or at minimum put
`tty0` last. Do not rely on the "no port detected, falls back to tty0" path; it is real but you
should not be betting a debugging session on it.

**3. Root has no password and getties autologin.** `sed -i 's|^root:[^:]*:|root::|'` plus
`getty -n`. Correct for a bench VM. On a laptop that leaves the building, it is a physical-access
root shell.

**4. `mkinitfs` features are right for USB already.** `features="base kms keymap scsi usb virtio
nvme ext4"` includes `usb`, so booting root-on-USB works. Keep `virtio` — it costs nothing and
keeps the same image bootable in QEMU, which is how you will bisect any m4 problem.

**5. LABEL-based root mount is the right call and pays off here.** `root=LABEL=CLARITYROOT`
resolves identically whether the stick enumerates as `/dev/sda2`, `/dev/sdb2` or `/dev/vda2`. The
GRUB fallback entry hardcodes `/dev/vda2`, which is virtio-only — on real hardware that entry
will fail, which is expected. Consider adding an `/dev/sda2` fallback for m4.

**6. Unused stick capacity.** The image is a fixed 4354 MiB at m1 regardless of the stick. On a
32 GB stick the remaining ~27 GB is unallocated. From a booted ClarityOS you can grow partition 2
to fill the device (`sfdisk` to extend, `resize2fs` to grow), which is the natural home for models
larger than the 1 GB Qwen2.5-1.5B. Do that after you trust the boot, not before.

**7. `build.sh` moves under you.** These notes were written against the version at the time; the
`m1` `ROOT_MIB` changed from 6144 to 4096 mid-writing, and M2 work is in flight. Re-read
`build.sh` before acting on §3's patch or §5's console fixes.

---

## 6. Verification ledger

Everything in this document that was checked, and how.

**Verified with Docker against real Alpine repositories** (parsed `S:`/`I:` size fields straight
out of `APKINDEX`, and inspected installed file trees):

- Complete NVIDIA-related package set across v3.21/v3.22/v3.23/v3.24/edge main+community+testing.
  No `cuda*`, no `nvidia-utils`, no `libcuda`, no `nvidia-driver` anywhere.
- `mesa-vulkan-nouveau` absent in v3.21; present from v3.22 onward, with per-branch sizes.
- `linux-firmware-*` subpackage sizes for v3.21 and v3.24.
- Intel wifi firmware ownership: `apk info --who-owns /lib/firmware/iwlwifi-cc-a0-77.ucode.zst`
  → `linux-firmware-other-20241210-r0` on v3.21. On v3.24 the same files are at
  `lib/firmware/intel/iwlwifi/` inside `linux-firmware-intel` (confirmed by listing the `.apk`
  tarball).
- Per-family iwlwifi file counts and byte sizes; per-file sizes for `cc-a0-77`, `QuZ-a0-hr-b0-77`,
  `9000-pu-b0-jf-b0-46`.
- `i915` firmware contents; exact sizes of `kbl_dmc_ver1_04`, `kbl_guc_70.1.1`, `kbl_huc_4.0.0`.
- `nvidia/tu106/gsp -> ../tu102/gsp` symlink and the 12.6 MiB GSP payload under `tu102`.
- `rtl_nic` contains `rtl8168*.fw`; package is 152 KiB installed.
- Kernel configs, extracted from the actual `.apk`: `CONFIG_DRM_NOUVEAU=m`, `CONFIG_DRM_I915=m`,
  `CONFIG_IWLWIFI=m`, `CONFIG_EFI_STUB=y`, `CONFIG_CMDLINE_BOOL` unset,
  `CONFIG_SERIAL_8250_CONSOLE=y`, `CONFIG_MODULE_SIG_FORCE` unset,
  `CONFIG_LOCK_DOWN_KERNEL_FORCE_NONE=y`. `CONFIG_DRM_NOUVEAU_GSP_DEFAULT` present-but-unset in
  6.12.98, absent from 6.18.42.
- `nouveau.ko` exists in Alpine's `linux-lts` and exposes the `config` module parameter used for
  `NvGspRm=1`.
- **llama.cpp `b4585` builds with `-DGGML_VULKAN=ON` inside `alpine:3.21`**, producing a
  16.4 MB `llama-server` whose only dynamic dependency is `libvulkan.so.1`. CMake reported
  Vulkan 1.3.296 and `GL_KHR_cooperative_matrix supported by glslc`.

**Verified on this Windows host:**

- `write-usb.ps1` parses clean and runs correctly in list mode.
- Refusals exercised and correct: missing image, non-existent disk number, disk 0 hard refusal
  (even with `-Force`), non-GPT file rejected before any disk access.
- `System.IO.FileStream` resolves `\\.\PhysicalDrive0` (fails with *"Access to the path is
  denied"* as a non-admin, i.e. a permission error rather than a path-format error).
- Internal disk is `Intel Raid 0 Volume`, BusType `RAID`, `IsBoot`/`IsSystem` true, with Dell
  recovery partitions — the basis for the Intel RST warning in §4.

**NOT verified — flagged:**

- **The actual write path in `write-usb.ps1`.** No USB stick was attached and the session was not
  elevated, so `Clear-Disk` → `Set-Disk -IsOffline` → FileStream write → `-Verify` →
  `Set-Disk -IsOffline $false` has not been executed end to end. The individual mechanisms are
  standard, but run `-DryRun` first and then a `-Verify` write on a stick you do not care about
  before trusting it with a stick you do.
- **Every performance number in the throughput table.** No GPU inference was run. The proprietary
  driver figures are other people's benchmarks on adjacent hardware (RTX 2070 Super, 2080 Ti); the
  NVK figures are extrapolated from Phoronix's percentage-of-proprietary finding on a *Blackwell*
  card, which is the most mature NVK target and therefore probably optimistic for Turing. Treat
  the NVK row as a hypothesis with a test attached, not a prediction.
- **Whether NVK on Turing exposes `VK_KHR_cooperative_matrix`.** This determines whether prompt
  processing is usable or dire, and I could not establish it from documentation. It is one
  `vulkaninfo | grep -i cooperative_matrix` on the real box.
- **Whether nouveau actually reclocks this specific Max-Q part under GSP on 6.18.** Max-Q cards
  have vendor-specific power tables and Optimus/hybrid-graphics power management. Check
  `/sys/kernel/debug/dri/*/pstate`.
- **Which wifi card is in this laptop.** AX200 / AX201 / 9560 all plausible for the model class;
  the firmware subset covers all three. `lspci -nn | grep -i network` settles it in one command
  and lets you drop ~5 MiB.
- **Dell firmware menu labels.** They differ between BIOS generations and model lines. The
  settings named are the right settings; the exact submenu names may not match.
- **That a v3.22+ rootfs still builds cleanly through `build.sh`.** The branch bump for m4b was
  not attempted. Mesa 25/26 and kernel 6.18 pull different dependencies than 3.21, and
  `mkinitfs` behaviour around `kms` and firmware differs across releases.
