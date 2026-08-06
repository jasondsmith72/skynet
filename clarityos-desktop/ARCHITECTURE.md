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

The **Installed** column is the honest current state, not the intent. Only two rows ship in
an image this repo can build today.

| Component | Role | Installed |
|---|---|---|
| Linux kernel (`linux-lts`) | Drivers, scheduling, memory, block/net/DRM | **yes** (m0) |
| `llama.cpp` + a GGUF model | The AI itself | **yes** (m1) |
| Rendering engine (WPE WebKit via `cog`, **engine only**) | Turns generated HTML/CSS/JS into pixels | no — M2 |
| Wayland compositor (`cage`, kiosk, single surface) | Owns the framebuffer, hands it to the engine | no — M2 |
| TLS + HTTP stack | Certificate chain validation, HTTP/1.1/2/3 | no — arrives with M2 |
| Font shaping (HarfBuzz) | Bidi, ligatures, complex scripts | no — arrives with M2 |
| Codecs (image/video/audio) | Decoding untrusted media | no — M2 |

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

The AI's tool surface is deliberately tiny and composable. Four tools exist:

```
fetch(url)                -> text       network; tag-stripped, capped at 8 KB
read(path) / write(path)  -> bytes      user data, confined to the documents directory
list(path)                -> entries
exec(name)                -> stdout     a NAME from a fixed 8-entry table, never an argv
```

`exec` takes a name, not a command line — the model cannot compose arguments, only choose
from a table. Rendering is not a tool: the model emits a fenced `html` block and the shell
turns it into a surface.

### Known-unsound: the injection boundary is not yet a boundary

`ALLOWED_AFTER` in `clarity-shell.py` is *intended* to stop content fetched from the network
from escalating into action. As written it does not, and this is recorded here rather than
quietly fixed later because the earlier version of this document claimed otherwise:

- `turn()` resets the taint (`last_tool = None`) at the start of every turn, while the
  poisoned tool result stays in conversation history permanently. The first tool call of the
  *next* turn is therefore ungated — so `exec` is always reachable one turn later.
- The surface branch returns before the gate is consulted, so fetch → render-from-fetched-
  content is unrestricted within a single turn.
- `ALLOWED_AFTER` lists `render` in four of five entries, but `render` is not a tool and is
  never looked up. Those entries are inert.
- Surfaces are injected with `innerHTML` under no CSP, so an injected `onerror` handler runs
  same-origin and can `POST /api/message` to manufacture the "next turn" with no human
  involved. `tool_fetch` also unescapes entities *after* stripping tags, so `&lt;img
  onerror=...&gt;` survives.

A correct version needs sticky per-message taint rather than per-turn, the surface path
routed through the same gate, server-side sanitisation to an element/attribute allowlist
delivered under a strict CSP (or an iframe `srcdoc` sandbox), and an `Origin` check plus a
per-session token on `/api/message`. Until then, treat `clarity-shell` as unsafe to install.

### Deliberately *not* generated: user data

Documents, settings, and history are stable, plain, inspectable files. The interface onto them
is fluid; the data underneath is not. A system where your files are as regenerable as your UI
is a system that loses your files.

## Generation should be cached, not repeated — PLANNED, not built

Naively regenerating a UI on every use is wrong twice over: a local 4B model needs seconds to
emit a view, and a UI that differs slightly each time is unusable — muscle memory never forms.

The intended loop:

1. Request arrives; hash the *intent*, not the literal words.
2. Cache hit → render the cached surface immediately.
3. Cache miss → generate, render, cache.
4. User can **pin** a surface, freezing it against regeneration.
5. User can say "change it" → regenerate from the pinned version plus the delta.

**None of this is implemented yet.** What exists in `clarity-shell.py` today: surfaces are
written to disk, and `load_surface` is called only when the engine requests a surface by id.
The generation path never consults the cache, so step 2 never happens; there is no pinning
and no delta regeneration. `surface_id` also hashes the lowercased literal request string,
which is the opposite of "hash the intent" — two phrasings of the same request miss.

## Boot chain

What an image built from this repo does **today** (stage m1):

```
UEFI firmware
  └─ GRUB (standalone EFI binary, embedded config, /EFI/BOOT/BOOTX64.EFI)
       └─ linux-lts + initramfs
            └─ OpenRC
                 └─ llama-server   (the model, OpenAI-compatible API on 127.0.0.1:8080)
                      └─ getty on ttyS0 → clarity-chat (console REPL)
```

Where M2/M3 are going — **none of these services exist in a buildable image yet**, and
`clarity-shell` is not even installed by the build (no `COPY` of `build/files/`, no init
script, no runlevel entry):

```
            └─ OpenRC
                 ├─ seatd            (device access)
                 ├─ llama-server
                 ├─ clarity-shell    (tool broker + generation cache)
                 └─ cage             (kiosk Wayland, single fullscreen surface)
                      └─ cog / WPE WebKit — rendering engine, no browser chrome
```

`/EFI/BOOT/BOOTX64.EFI` is the removable-media path, so the same image boots under QEMU,
Hyper-V Gen2, and real UEFI desktop hardware with no NVRAM entries and no per-machine install.

## Disk layout

GPT, two partitions. Partition GUIDs are fixed and recorded in `/etc/clarityos-build`, but
the **boot path does not use them**: the kernel command line is `root=LABEL=CLARITYROOT`,
because Alpine's initramfs resolves `LABEL=` and `UUID=` but not `PARTUUID=` (a `PARTUUID=`
root drops you into the initramfs emergency shell). Labels are also portable across
`vda` / `sda` / `nvme0n1p2`.

| # | Label | Type | Size | Contents |
|---|---|---|---|---|
| 1 | `CLARITYESP` | EFI System (FAT32) | 256 MiB | `BOOTX64.EFI`, `vmlinuz-lts`, `initramfs-lts` |
| 2 | `CLARITYROOT` | Linux root (ext4) | 3 GiB (m0) / 6 GiB (m1) | Alpine userland, `llama-server`, model |

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
