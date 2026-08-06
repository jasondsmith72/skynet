# ClarityOS Desktop

A machine that boots from firmware straight into an AI, which *is* the shell. No desktop
environment, no application menu, no browser. You talk to it, and it generates whatever
interface your request needs.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the design — in particular the **substrate /
generated split**, which is the decision everything else follows from.

## Status

| | Milestone | State |
|---|---|---|
| **M0** | UEFI → GRUB → kernel → OpenRC → serial console | **verified in QEMU** |
| **M1** | `llama-server` + GGUF model autostart, chat on the console | **verified in QEMU** |
| M2 | seatd + kiosk compositor + rendering engine, no browser chrome | not started |
| M3 | tool broker (`fetch`/`read`/`write`/`exec`) + surface cache | **written but NOT installed** |
| M4 | USB boot on physical hardware, GPU offload, wifi | not started |

`clarity-shell.py` is not wired into the build at all — the Dockerfile does not copy
`build/files/`, and nothing creates an init script or runlevel entry for it. It is
unreachable code, not merely untested, and it has known security defects (see the
"injection boundary" section of [ARCHITECTURE.md](ARCHITECTURE.md)). Do not install it as-is.

Measured on the dev host (i7-9750H, 4 vCPU, CPU-only, Qwen2.5-1.5B-Instruct Q4_K_M):
**~11.6 tok/s** generation, 23 s model load.

## Requirements

- **Docker** — builds the image. An ordinary unprivileged container: no loop devices, no
  `--privileged`. `mke2fs -d` populates ext4 from a directory, `mtools` populates the FAT
  ESP, and `sfdisk` writes the partition table to a plain file.
- **QEMU** (`winget install SoftwareFreedomConservancy.QEMU`) — boot testing under OVMF
  UEFI firmware, hardware-accelerated via WHPX.
- ~4 GB free disk, plus ~1.1 GB for the cached model.

Hyper-V is *not* required and is unavailable on Windows Home anyway.

## Build

```bash
./make.sh m0
```

```bash
./make.sh m1
```

`m1` downloads a ~1.1 GB GGUF into `cache/` on first run and reuses it afterwards. Output
is `out/clarityos.qcow2`. The raw disk image is only produced on request, because copying
multi-gigabyte files across the Windows↔WSL2 bind mount is roughly an order of magnitude
slower than keeping them container-local:

```bash
EXPORT_RAW=1 ./make.sh m1
```

Pick a different model with `MODEL_URL=... ./make.sh m1`. Stage m3 quality really wants a
7B-class model; the 1.5B default is chosen so the build-and-boot loop stays fast.

## Boot it

```powershell
.\run-qemu.ps1 -Mode gui
```

- `-Mode gui` opens a QEMU window; serial is still captured to `out/serial.log`.
- `-Mode log` runs headless and reports a verdict once the boot outcome is unambiguous.
- `-Mode console` gives the guest serial console this terminal (exit with `Ctrl-A X`).

At m1 the serial console autologins into the chat REPL, so powering on the VM drops you
into a conversation with a model running locally. Inference itself needs no network — but
note the image does bring up `eth0` by DHCP at boot, so the machine is not offline.

Both harnesses pass `snapshot=on` for the disk, so guest writes are discarded and a test run
cannot mutate the image it is testing.

## Verify end to end

```bash
python test-m1.py
```

Boots the image with the guest serial console on a TCP socket, waits for the model to load,
then actually sends a prompt and captures the reply. "The service started" and "a model is
doing inference" are different claims; only the second is the milestone, so the test checks
the second.

## Layout

```
build/Dockerfile          multi-stage: compiles llama.cpp, then the image toolchain
build/build.sh            the image build (stages m0, m1)
build/files/              programs installed into the guest
  clarity-shell.py        tool broker, LLM relay, surface generator (M3)
make.sh                   build wrapper; bind-mounts build.sh so edits take effect
run-qemu.ps1              QEMU launcher (UEFI + WHPX)
test-m1.py                end-to-end boot + inference test
out/                      built images and serial logs (not committed)
cache/                    downloaded models (not committed)
```

## Notes that cost time to learn

**The guest CPU model is load-bearing.** `-cpu max` inherits VMX from the host. WHPX has no
nested-virt support, so OVMF's `PlatformPei` writes `IA32_FEATURE_CONTROL` (MSR `0x3A`),
WHPX rejects the write, and every CPU dies with `#GP` before GRUB is ever reached. `vmx=off`
does *not* help — WHPX rejects any write to that MSR whatever the value. The fix is to build
*up* from `qemu64` (which never advertises VMX) and add AVX2/FMA/F16C back explicitly, since
llama.cpp is compiled requiring them and bare `qemu64` exposes none.

**Root is mounted by filesystem LABEL, not PARTUUID.** Alpine's initramfs resolves `LABEL=`
and `UUID=` but not `PARTUUID=`; a `PARTUUID=` root drops you into the initramfs emergency
shell. Labels are also portable across `vda` / `sda` / `nvme0n1p2`, so one image boots under
QEMU, from USB, and off NVMe unchanged.

**`build.sh` is bind-mounted by `make.sh`, not baked in.** The Dockerfile `COPY`s it so the
builder image is self-contained, which makes it very easy to edit `build.sh`, rerun, and
silently get the stale copy. Always build through `make.sh`.
