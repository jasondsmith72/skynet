# ClarityOS Desktop — Architecture

**Goal:** a machine that boots from firmware directly into an AI, which *is* the shell — no
desktop environment, no app menu, no browser. You talk to it; it generates whatever interface
your request needs, right then.

This document exists because "the AI generates everything" is half right, and getting the other
half wrong is a security disaster. The split below is the core design decision.

## The substrate / generated split

Everything on this system is in exactly one of two categories.

### Substrate — pre-built, versioned, never AI-generated

This is the AI's *hardware*. It is the irreducible floor, and it is chosen to be as thin as
possible while still being sound.

| Component | Role |
|---|---|
| Linux kernel (`linux-lts`) | Drivers, scheduling, memory, block/net/DRM |
| Rendering engine (Chromium/WebKit **engine only**) | Turns generated HTML/CSS/JS into pixels |
| TLS + HTTP stack | Certificate chain validation, HTTP/1.1/2/3 |
| Font shaping (HarfBuzz) | Bidi, ligatures, complex scripts |
| Wayland compositor (kiosk, single surface) | Owns the framebuffer, hands it to the engine |
| `llama.cpp` + a GGUF model | The AI itself |
| Codecs (image/video/audio) | Decoding untrusted media |

**Why these are never generated.** Every item above parses input controlled by an attacker.
A subtly-wrong TLS implementation does not crash — it silently accepts a forged certificate,
and no test the AI can run will notice. A subtly-wrong HTML parser is a remote code execution
primitive. "The AI will regenerate it if it breaks" is not a recovery strategy for a class of
bug whose defining property is that it does not visibly break.

The rendering engine is also simply beyond generation: Chromium's engine is ~40M lines
encoding two decades of specification edge cases. No model — local or frontier — emits that.

### Generated on demand — every pixel the user sees

There are **no applications** on this system. No browser, no text editor, no file manager,
no settings panel. When the user makes a request, the model emits HTML/CSS/JS for that
request and the substrate renders it.

- "Show me the news" → the AI `fetch`es sources, extracts content, and generates a reading
  view. It does not open a browser.
- "I need to write a letter to the landlord" → generates an editor suited to that document.
- "Make it two columns and show a word count" → regenerates the editor with those affordances.
- "What's eating my disk?" → generates a treemap over the output of a filesystem scan.

The AI's tool surface is deliberately tiny and composable:

```
fetch(url)                -> bytes      network, through the substrate's TLS
read(path) / write(path)  -> bytes      user data
list(path)                -> entries
exec(argv)                -> stdout     allowlisted binaries only
render(html)              -> surface    hand a generated UI to the engine
```

Every interface is composed from those five primitives.

### Deliberately *not* generated: user data

Documents, settings, and history are stable, plain, inspectable files. The interface onto them
is fluid; the data underneath is not. A system where your files are as regenerable as your UI
is a system that loses your files.

## Generation is cached, not repeated

Naively regenerating a UI on every use is wrong twice over: a local 4B model needs seconds to
emit a view, and a UI that differs slightly each time is unusable — muscle memory never forms.

The actual loop:

1. Request arrives; hash the *intent*, not the literal words.
2. Cache hit → render the cached surface immediately.
3. Cache miss → generate, render, cache.
4. User can **pin** a surface, freezing it against regeneration.
5. User can say "change it" → regenerate from the pinned version plus the delta.

So the system is fluid when you want it to be and stable when you don't.

## Boot chain

```
UEFI firmware
  └─ GRUB (standalone EFI binary, embedded config, /EFI/BOOT/BOOTX64.EFI)
       └─ linux-lts + initramfs
            └─ OpenRC
                 ├─ seatd            (device access)
                 ├─ llama-server     (the model, OpenAI-compatible API on localhost)
                 ├─ clarity-shell    (tool broker + generation cache)
                 └─ compositor       (kiosk Wayland, single fullscreen surface)
                      └─ rendering engine, no browser chrome
```

`/EFI/BOOT/BOOTX64.EFI` is the removable-media path, so the same image boots under QEMU,
Hyper-V Gen2, and real UEFI desktop hardware with no NVRAM entries and no per-machine install.

## Disk layout

GPT, two partitions, fixed PARTUUIDs so the kernel command line is baked in at build time:

| # | Label | Type | Size | Contents |
|---|---|---|---|---|
| 1 | `CLARITYESP` | EFI System (FAT32) | 256 MiB | `BOOTX64.EFI`, `vmlinuz-lts`, `initramfs-lts` |
| 2 | `CLARITYROOT` | Linux root (ext4) | 4 GiB (M0) | Alpine userland, `llama-server`, model, shell |

Images are assembled **without loop devices or privileged containers** — `mke2fs -d` populates
ext4 from a directory, `mtools` populates FAT, and `sfdisk` writes the table to a plain file.
The build therefore runs in an ordinary unprivileged Docker container.

## Milestone ladder

Each rung is independently verifiable. No rung depends on a later one.

| | Milestone | Proves |
|---|---|---|
| **M0** | UEFI → GRUB → kernel → OpenRC → serial console | The boot chain works on this hardware |
| **M1** | `llama-server` + GGUF model autostarts; chat over the serial console | *An AI model boots from bare hardware* |
| **M2** | seatd + kiosk compositor + rendering engine, no browser chrome | Graphics stack; AI owns the framebuffer |
| **M3** | Tool broker live: `fetch`/`read`/`write`/`exec`/`render` + generation cache | AI generates real interfaces on demand |
| **M4** | USB image on the physical desktop; CUDA offload to the RTX 2070; wifi | Real hardware, usable speed |

## Development and test environment

The target box is Windows 11 Home, so **Hyper-V is unavailable** (Home edition cannot install
the Hyper-V role; `Get-VM` does not exist). WSL2 is present and running, which means the
Windows Hypervisor Platform is enabled — so QEMU accelerates via **WHPX**.

- **Build:** unprivileged Docker container (Alpine), producing a raw + qcow2 image.
- **Test:** QEMU with OVMF UEFI firmware, WHPX acceleration, serial redirected to stdout.
- **Deploy:** the same raw image written to USB, booted on physical UEFI hardware.

Host: i7-9750H (6c/12t), 15.8 GB RAM, RTX 2070 Max-Q 8 GB. The GPU is not visible to QEMU, so
M0–M3 run CPU-only inference; the RTX 2070 comes into play at M4 on real hardware.
