# Legacy Assessment

An audit of everything in this repository that predates `clarityos-desktop/`, written to answer one
question: what is worth carrying forward?

The short answer is that the legacy tree is a **design corpus with a thin shell of executable
scaffolding around it**. There is real, working code in it — roughly 4,000 of 32,000 Python lines —
but none of it is an operating system, none of it touches hardware, and no entry point in the tree
runs to completion. The documentation asserts the opposite in thirteen files.

- **Scope:** everything except `clarityos-desktop/`.
- **Method:** static reading plus execution. Where a claim below says something fails, it was run.
  The Rust kernel was compiled (in a scratch copy, source untouched); the Python entry points were
  executed; the test suite was collected and run.
- **Nothing in this audit modified the repository.** Artifacts created by test runs (`config/`,
  regenerated `.pyc`) were reverted.
- Verified against `HEAD = a307ddb`. Line numbers are from that commit.

---

## 1. What actually exists, and what actually works

### 1.1 The things that work

| Component | Path | Evidence |
|---|---|---|
| Message bus | `src/clarityos/core/message_bus.py` (226 ln) | Real asyncio pub/sub with priority queues. Zero simulation markers. |
| Agent manager | `src/clarityos/core/agent_manager.py` (583 ln) | Real lifecycle/dependency management. Zero simulation markers. |
| Clarity language front-end | `src/clarity/compiler/` (2,009 ln) | Lexer, parser, AST, semantic analyzer. Verified: `Lexer("module Test { }").tokenize()` returns 5 tokens. 13 of 24 passing tests cover it. |
| Dev-environment wrapper | `src/clarityos/development/environment_integration.py` (463 ln) | Genuine `subprocess` git/build/test wrapping. |
| System monitor | `src/clarityos/core/system_monitor.py` (354 ln) | Real `psutil` + `/proc` reads, with graceful fallback. Not wired into any boot path. |
| ~60 lines of real hardware detection | `src/clarityos/hardware/hal.py:175-376` | `/proc/meminfo`, `lsblk --json`, `ip -j addr`, `platform.processor()`. Linux-only. Never called by boot. |
| The design corpus | `docs/` (38 `.md`) | Speculative but honestly framed. See §3.4. |

That is the complete list. Everything else is scaffolding, simulation, a stub, an orphan, or a
duplicate.

### 1.2 No entry point in the legacy tree runs

Three programs claim to boot ClarityOS. All three fail, each for a different reason:

```
$ python -m src.clarityos.main
INFO:src.clarityos.core.message_bus:Message bus started
ERROR:__main__:Error during startup: object NoneType can't be used in 'await' expression
  File "src\clarityos\main.py", line 64, in startup
    await system_bus.start()
TypeError: object NoneType can't be used in 'await' expression
```

`main.py:64` awaits `system_bus.start()`, but `message_bus.py:57` declares `def start(self)` — not
`async def`. The most honest module in the tree is broken by a one-line type error that has never
been caught, because nothing tests it.

`boot.py` dies at HARDWARE_INIT. The chain is `boot.py:71` → `hardware/boot_integration.py:27` →
`hardware/hardware_integration.py:69`, which calls `self.extended_hal.initialize()`. `ExtendedHAL`
is the entire contents of `src/clarityos/hardware/extended_hal.py` — **13 lines, one `__init__`
containing `pass`, no `initialize` method**:

```python
# src/clarityos/hardware/extended_hal.py:7-13
class ExtendedHAL:
    """
    The Extended Hardware Abstraction Layer (HAL) provides a high-level interface
    to various hardware components, building upon the basic HAL.
    """
    def __init__(self):
        pass
```

The resulting `AttributeError` is swallowed by a blanket `except Exception` at
`hardware_integration.py:108`, converted to `return False`, and surfaced as the generic string
`"Boot sequence failed"` (`boot.py:588`). Three more latent `AttributeError`s sit downstream on the
same path (`hardware_integration.py:122`, `:142`, `:276`) — `start_all_components` is not defined
anywhere in the repository — which is proof this path has never executed.

`boot_integration.py` dies earlier still, at `boot_integration.py:312`, importing
`initialize_hardware_learning` from `hardware/integration.py`, which does not define it.

### 1.3 The hardware layer does not touch hardware

`src/clarityos/hardware/` plus `src/clarityos/core/hardware_interface.py` is 7,500 lines. The
detection is typed-in constants. `core/hardware_interface.py` carries 45 `simulat`/`in a real`
markers — the highest density in the repository:

```python
# src/clarityos/core/hardware_interface.py:280-291
def _simulate_linux_cpu_info(self):
    # In a real OS, this would read from /proc/cpuinfo
    ...  "cores": 8, "mhz": 3200.0, "vendor_id": "GenuineIntel"
```

There is no `wmi`, `win32com`, `ctypes`, or `subprocess` import in that file, despite six comments
promising WMI queries. CPU load returns the literal `25.5%` and `[20.1, 30.2, 15.5, 36.2]`
(`:501-507`). Device "monitoring" decrements a fabricated `free_space_gb` by 0.01 every ten seconds
(`:384-385`).

`boot_integration.py:171-228` is the most brazen instance. It appends four hardcoded dicts and logs
them with the word "Detected":

```python
# src/clarityos/boot_integration.py:171-183
self.detected_hardware.append({
    "type": "cpu", "manufacturer": "ClarityOS", "model": "AI-Quantum 9000",
    "specifications": {"cores": 16, "threads": 32, "frequency": 3.8, ...}})
logger.info("Detected CPU: AI-Quantum 9000 (16 cores, 32 threads)")
```

Also `"ClarityRAM Ultra-Fast DDR5"` (64 GB), `"DataWave NVMe-9000"` (2 TB),
`"NeuroGraphics Matrix-5000"`. None of these products exist.

The two components `PROGRESS-SUMMARY.md` singles out as implemented are likewise bookkeeping:

```python
# src/clarityos/core/memory_manager.py:140-150
# In a real OS, this would directly access memory information
# For now, we'll simulate it with reasonable defaults
self.stats.total_mb = 16384.0      # 16GB
self.stats.available_mb = 14336.0  # 14GB initially available
```

```python
# src/clarityos/core/process_isolation.py:377-382
# In a real OS, we would create an actual isolated process or container
# For now, we'll simulate it
    process.status = "running"
    process.process_handle = {"simulated": True}
```

`memory_manager.py` imports no `mmap` and no `ctypes`. `process_isolation.py` imports `subprocess`
but never uses it to create anything; per-process resource usage is
`10.0 + (hash(process.id) % 20)` (`:310-319`), and `_enforce_resource_limits` (`:323-339`)
terminates processes based on those hash values.

**Privileged access claimed in code comments, and whether it is even reachable from userspace
CPython:**

| Claim | Location | What the code does | Possible? |
|---|---|---|---|
| Port I/O (`inb`/`outb`) | `hardware/interfaces/io_interface.py:63-64`, `:264-267` | `_simulate_port_read` returns `(port * 0x100 + 0x42) & mask` — arithmetic on the port number | No. Ring-0 / IOPL-gated. |
| MMIO | `hardware/interfaces/memory_interface.py:237-254` | `_simulate_memory_read` returns `bytes([0xAA] * size)`; `_simulate_memory_map` returns `0x1000000 + hash(...) % 0x1000000` | No. Needs `/dev/mem` + root, blocked by `CONFIG_STRICT_DEVMEM`. |
| IRQ vectors | `hal.py:577-585` | `# Simulate interrupt mapping` → hardcoded legacy PC/AT IRQ table | No. IDT is ring-0. |
| PCI enumeration | `hardware/interfaces/pci_interface.py` | 12 lines; body is `super().__init__()` | **Yes, unprivileged** via `/sys/bus/pci/devices`. Not attempted. |
| `ExitBootServices` | `firmware_interface.py:283-309` | `# Simulate successful exit` → `logger.info("UEFI boot services exited successfully")` → `return True` | No. Boot services cease to exist once an OS is running. |
| ACPI tables | `firmware_interface.py:311-329` | Invented addresses `{"RSDT": {"address": 0xF0000000}, ...}` | Readable at `/sys/firmware/acpi/tables` as root. Not attempted. |
| DMA | — | No `dma` identifier exists anywhere in `src/clarityos/` | — |

`firmware_interface.py:9` imports `ctypes` and never uses it. That single import is the only thing
in 7,500 lines that made "direct firmware interaction" superficially plausible.

`firmware_interface.py:100-101` hardcodes `self.firmware_type = FirmwareType.UEFI` on every
platform, with no check of `/sys/firmware/efi` or `GetFirmwareEnvironmentVariable`.

### 1.4 Commit `dd3f6bb` did not implement real hardware detection

The message reads *"Fix broken test suite and implement real hardware detection"*. `git show --stat`:

```
 src/clarityos/hardware/hal.py            |  5 +++--
 src/clarityos/hardware/tests/test_hal.py | 15 +++++++++++++
 (+ 4 .pyc binary files)
 6 files changed, 18 insertions(+), 2 deletions(-)
```

The 5-line `hal.py` change is entirely inside `_discover_display`, and it *adds* an admission of
simulation:

```diff
+  # This is not feasible in a simple, cross-platform way without a graphical server.
+  logger.info("Display detection is simulated. Creating a virtual display device.")
-  # For simulation, create a basic display device
```

The 15 test lines add `test_discover_network` — which `test_hal.py` already defines at line 76, so
the new copy at line 94 silently shadows it and never runs. The modest real detection in `hal.py`
arrived in earlier commits in the same series (`72abd56`, `e604ec4`, `cd61eb6`).

Thirteen commits (`011950f` … `dd3f6bb`) carry near-identical messages, four of them titled *"Add a
minimal test file to diagnose a hang when importing ctypes"*. The same feature was announced
repeatedly and delivered once, partially.

`hal.py`'s real detection also has a live bug: `hal.py:286` does `int(device_info.get('size', 0))`
on `lsblk` output, but `lsblk --json` emits `"size"` as a human string (`"476.9G"`), so `int()`
raises `ValueError`, caught at `:295`, falling back to simulation **even on Linux**.

The tests are tautological. `test_hal.py:30` asserts
`cpu.name == platform.processor() or "Unknown CPU"` — the implementation equals itself, and it
passes when detection returns nothing.

### 1.5 The Rust kernel — verdict: archive

`src/clarityos/clarity_os_kernel/` (285 lines of Rust) was committed as *"Implement a bootable Rust
kernel with a simple LLM"*. Both halves of that claim are wrong.

**It does not compile.** On the installed toolchain (`rustc 1.97.1`, stable, the only toolchain
present):

```
error[E0554]: `#![feature]` may not be used on the stable release channel
 --> x86_64-0.14.13/src/lib.rs:5:35
```

`Cargo.toml:11` declares `x86_64 = "0.14.2"` with default features. `x86_64` 0.14's
`default = ["nightly", "instructions"]`, and `nightly = ["const_fn", "step_trait",
"abi_x86_interrupt"]`. So the crate requires nightly Rust, and there is no `rust-toolchain.toml` to
pin it. Adding `default-features = false, features = ["instructions"]` in a scratch copy makes it
build — so the fix is one line, but as committed, `cargo build` fails.

**It cannot produce a bootable image.** `bootloader` 0.9.x requires the external `bootimage` tool to
link the kernel into a disk image. The repository provides:

- no `runner = "bootimage runner"` in `.cargo/config.toml` — that file is two lines,
  `[build]` / `target = "x86_64-unknown-none"`, so `cargo run` cannot work;
- no `[unstable] build-std` stanza, which `bootimage` needs to compile the bootloader's own
  `x86_64-bootloader.json` target;
- no custom target JSON;
- no README, no build instructions, no CI, and `bootimage` is not installed.

`cargo build` yields an ELF at `x86_64-unknown-none/debug/clarity_os_kernel`. That is not a boot
image, and nothing in the repository turns it into one. **The commit that says "bootable" produced
nothing that boots.**

**`memory.rs` is not wired up.** The compiler says so directly:

```
warning: struct `BootInfoFrameAllocator` is never constructed
 --> src/memory.rs:8:12
warning: associated items `init` and `usable_frames` are never used
 --> src/memory.rs:19:19
```

`main.rs:32` signs the entry point as `fn kernel_main(_boot_info: &'static BootInfo)` — the
underscore prefix is the author suppressing the unused-parameter warning. The bootloader's memory
map is delivered and discarded. `vga_buffer.rs` (130 lines) is entirely dead too — 9 of the build's
11 warnings are its unused items, including `Writer` never constructed and `print` never called.
**135 of 285 Rust lines are dead on arrival.**

**The `DummyAllocator` is a hard ceiling, not a placeholder.**

```rust
// src/main.rs:20-28
unsafe impl GlobalAlloc for DummyAllocator {
    unsafe fn alloc(&self, _layout: Layout) -> *mut u8 { panic!("no allocator") }
    unsafe fn dealloc(&self, _ptr: *mut u8, _layout: Layout) { panic!("no allocator") }
}
```

It is required — removing it gives `error: no global memory allocator found`, because
`vectormatrix/src/lib.rs:78` does `extern crate alloc`. So the kernel links an allocator that panics
on first use. Any heap allocation kills the kernel. A language model needs multi-megabyte tensors on
the heap. The one file that could bridge that gap — `memory.rs`, a frame allocator — is the dead
code above. **There is no path from this kernel to an LLM that does not begin with writing the
allocator that was written and then not connected.**

**The "LLM" is compile-time arithmetic.** `llm.rs` is a `DenseLayer` with const generics and a
`relu`. `main.rs:36-60` hardcodes a 2→3→1 network with fixed weights and the fixed input
`[1.0, 2.0]`. No tokenizer, no weights loaded from anywhere, no text, no training, no inference over
input. `print_vector` casts to `i32` because f32 formatting is unavailable (`llm.rs:40-41`).

Working the arithmetic through: layer 1 gives `[0.6, 1.3, 2.0]`, ReLU is a **no-op** because all
three are already positive (so the "before ReLU" and "after ReLU" lines print identically), and
layer 2 gives `3.66`. Truncated to `i32`, the program's entire output is:

```
Input:                        [ 1 2 ]
Layer 1 Output (before ReLU):  [ 0 1 2 ]
Layer 1 Output (after ReLU):   [ 0 1 2 ]
Final Output:                  [ 3 ]
```

Three of the four printed hidden values are lost to truncation. This is 43 lines of matrix code
proving that `f32` multiplication works in `no_std`.

**Verdict: archive.** Not because bare-metal Rust is wrong — it may well be the right long-term
substrate — but because this specific crate is 285 lines of tutorial boilerplate (`vga_buffer.rs`
and `serial.rs` are verbatim from the *Writing an OS in Rust* series) on a bootloader generation
that was superseded four years ago, with the one non-boilerplate file disconnected and the
allocator story a dead end. Nothing in it would be reused when writing a real kernel; every file
would be rewritten. `docs/implementation/ai-os-implementation-plan.md:107-126` recommended the
opposite approach, and that recommendation is what `clarityos-desktop/` proved out. Keep the crate
in history, tag it, and move it under `legacy/`.

### 1.6 Half-finished refactors left two reproducible runtime failures

Three files carry a `_part2` suffix. The pattern behind them — split a large file, forget to wire
the halves back together — produced live bugs.

**`NetworkManager` cannot initialize.**
`src/clarityos/hardware/interfaces/network/network_manager.py` defines exactly four methods
(`:35`, `:51`, `:84`, `:130`), but `:68-69` subscribes `self._handle_connect_request` and
`self._handle_disconnect_request` → `AttributeError` inside `initialize()`. Eight methods it needs
exist only in `network_manager_part2.py` (`:18`, `:67`, `:105`, `:123`, `:159`, `:167`, `:176`,
`:190`), which **nothing imports**. And they are on a standalone `NetworkManagerPart2` class, not a
mixin, so importing it would not fix anything. `network_integration.py` additionally calls
`.connect_best_interface()` (`:114`), `.get_status()` (`:180`) and `.shutdown()` (`:194`) — all
missing. This is the code `src/clarityos/NETWORK-INTEGRATION.md:87` calls "fully implemented and
ready for testing".

**10 of 12 talent domains raise `NameError`.** `prototype/talent_execution.py:143-179` dispatches to
seven `generate_*_result` functions that live only in `talent_execution_part2.py`, from which
`talent_execution.py` imports nothing. Executed across every `TalentDomain`: `CODE_GENERATION` and
`SECURITY` work; the other ten raise `NameError: name 'generate_nlp_result' is not defined` and
similar.

**`restart_manager_part2.py` is a 4-line tombstone** — comments saying the content was merged
elsewhere — plus a tracked `.pyc`.

Both live bugs sit in code with **zero test coverage**, which is precisely why they went unnoticed.

### 1.7 The package cannot be imported with one `sys.path` root

28 statements use `from clarityos...` (needs `src/` on the path); 13 use `from src.clarityos...`
(needs the repo root) — including `boot.py:352`, `hal.py:18`, `driver_framework.py:18`,
`hardware_integration.py:14-16`, `integration.py:13-15`, `learning/strategies.py:15-16`,
`tests/test_hal.py:9`. With `PYTHONPATH=src` alone, `clarityos.hardware.hal` raises
`ModuleNotFoundError: No module named 'src'`. With the repo root alone, `clarityos` is not found.

Setting both makes imports succeed and loads every module **twice under two identities**. Verified:
`clarityos.hardware.hal.Device is not src.clarityos.hardware.hal.Device`. So `driver_framework`
(which imports `Device` from the `src.`-prefixed path) holds a different `Device` class from
everything importing the unprefixed path, and every `isinstance` check across that boundary silently
returns `False`. That is a latent whole-subsystem bug, not a style preference. `boot.py:352` also
creates a *second* `system_bus` singleton distinct from `main.py`'s.

There is no `src/__init__.py`; the tree works only via PEP 420 namespace packages.

### 1.8 The test suite runs, and measures nothing

`python -m pytest -q` → **24 passed in 1.78s**, zero collection errors, no hang. That green result is
misleading rather than reassuring.

| Path | Lines | Tests |
|---|---|---|
| `src/clarity/tests/test_compiler.py` | 214 | 13 |
| `src/clarity/tests/test_self_healing.py` | 148 | 5 |
| `src/clarity/tests/test_syntax.py` | 376 | **0** |
| `src/clarityos/agents/resource_manager/tests/test_resource_manager.py` | 8 | 1 (no-op) |
| `src/clarityos/hardware/tests/test_hal.py` | 128 | 5 |

- `test_syntax.py` is 376 lines with **all three test methods commented out** — `# def test_...` at
  lines 32, 138, 287. Its only live methods are the helpers `parse` (`:24`) and `assertNodeType`
  (`:28`). Confirmed: collecting that file alone yields "no tests collected".
- `test_resource_manager.py` is the whole of `assertTrue(True)`. Its 234-line predecessor sits beside
  it as `test_resource_manager.py.broken`, a **truncated fragment** whose line 1 is `_type)` →
  `SyntaxError: unmatched ')'`. Real coverage was deleted and replaced with a test that asserts
  nothing.
- 19 of 24 tests cover `src/clarity/` (the language front-end), not the OS. **Five real tests cover
  32,000 lines**, all in `test_hal.py`, and they pass on Windows purely via simulation fallbacks.
- Zero tests for `core/` (4,351), `agents/` (2,338 + subpackages), `prototype/` (5,196),
  `learning/` (928), `development/` (1,560), or the network stack.
- `pytest.ini` is two lines and its one setting is dead: `norecursedirs = src/clarity/test_driver.py`
  takes **directory** patterns, and that file does not exist (only a stale tracked `.pyc` of it
  remains).

### 1.9 Dead weight

- **~5,000 orphaned lines** (~15% of `src/`), no importer in any `.py` file. Largest:
  `hardware/experimentation_framework.py` (773), `agents/hardware_learning_agent.py` (609),
  `core/process_integration.py` (425), `boot_integration.py` (399),
  `hardware/interfaces/hardware_protocols.py` (327).
- **`src/clarityos/agents/update_system/` is entirely dead** — 1,190 lines, and
  `grep -rn "update_system" --include=*.py src/` returns zero hits. It holds near-total rewrites of
  two live files: `kernel_updater.py` (365 vs 401 lines, 725 diff lines) and `restart_manager.py`
  (370 vs 343, 681 diff lines).
- **Stub classes that documentation lists as features:** `extended_hal.py` (13 ln, `pass`),
  `driver_model.py:28-38` (`DriverRegistry`/`DriverStatus`, both `pass`, both docstringed "A
  placeholder"), `safety/security_manager.py` (10 ln, `apply_interface_policies(self, interface):
  pass`), `safety/io_safety.py` (12 ln), `interfaces/pci_interface.py` (12 ln).
- **`src/msp_integration/integration.py` is 22 lines of no-ops** — `connect()` →
  `{platform: True}`, `get_devices()` → `(True, [], None)`, `process_current_metrics()` → `[]`.
  `connectors/__init__.py` (3 ln) and `monitoring/__init__.py` (5 ln) are docstrings and nothing
  else. This is the "comprehensive integration module for MSPs" of `README.md:99`.
- **`src/clarityos/kernel/ai_init/` cannot build.** `Makefile:5` lists seven sources; three do not
  exist, including `init_main.c`, which would hold `main()`. `model_runtime.c:31-52`
  ("run inference") mallocs an output tensor and multiplies the input by 2.0.
  `kernel/ai_mem/` and `kernel/ai_sched/` contain **only a README.md** each.
- **Both root helper scripts are non-functional.** `check_imports.py:6` shells out to POSIX `find`;
  on Windows that resolves to `find.exe` → `FIND: Parameter format not correct` (executed,
  confirmed). It also sets `PYTHONPATH=src` while building `src.`-prefixed module names, so it
  validates imports under the exact dual-identity configuration described in §1.7.
  `restart_clarityos.py:125` looks for `run_clarityos.py`, which does not exist anywhere on disk or
  in the index, so the script logs "Main script not found" and returns — its entire purpose is a
  guaranteed no-op. Line 66 additionally drives the *dead* duplicate updater in
  `agents/update_system/`.
- **`requirements.txt` cannot be installed.** Line 5 is `python>=3.7` (not a PyPI package) and
  line 22 is `sklearn>=0.24.0` (the shim package that deliberately errors; should be
  `scikit-learn`). `requirements-msp.txt:4` repeats the first error. Meanwhile `numpy`, `pandas`,
  and `sklearn` are declared but imported nowhere in `src/`, while `aiofiles`, `aiohttp`, and
  `psutil` are imported and undeclared.
- **A missing dependency makes the whole network package unimportable:**
  `network/__init__.py:8` → `network_manager.py:19` → `safe_driver_manager.py:14` →
  `knowledge_repository.py:11` → `ModuleNotFoundError: No module named 'aiofiles'`.

---

## 2. Keep / archive / rewrite

"Archive" means move under `legacy/` with a short note, keep it in git history, stop maintaining it,
and stop letting the README advertise it.

| Component | Lines | Verdict | Reasoning |
|---|---|---|---|
| `clarityos-desktop/` | — | **Keep — this is the project** | Only artifact that boots. M0/M1 verified in QEMU, 11.6 tok/s measured. Its README is the honesty standard for the repo. |
| `docs/implementation/ai-os-implementation-plan.md` | 125 | **Keep** | §6 (`:107-126`) recommends Linux + custom initramfs + GRUB + KVM/QEMU — exactly what `clarityos-desktop` built. `:126` ("leveraging established technologies like Linux for the initial hardware abstraction layer") is the honest framing every other status doc abandoned. Makes no false claims. Add a note that §6.1 was executed and §6.2–6.3 were not. |
| `docs/implementation/practical-implementation-steps.md` | 138 | **Keep** | `:29-33` independently recommends the same thing: minimal Linux via buildroot/linuxkit, Python runtime, custom init launching AI first. Also vindicated. |
| `docs/concepts/`, `docs/msp-use-cases/`, `docs/examples/`, `docs/principles/` | 25 files | **Keep as concept corpus** | Speculative design, but honestly labelled — no status claims to correct. Genuine value: this is the vision `clarityos-desktop` is executing against. |
| `src/clarityos/core/message_bus.py` | 226 | **Keep, port** | Real, small, dependency-free, no simulation. Fix `start`/`stop` to `async def` (or fix the two call sites). `ai-os-implementation-plan.md:116-118` names exactly this as the thing to carry into the boot environment. |
| `src/clarityos/core/agent_manager.py` + `agent_base.py` | 720 | **Keep, port** | Real lifecycle/dependency management. The natural substrate for `clarity-shell.py`'s tool broker if it grows past one process. |
| `src/clarity/` (compiler front-end) | 3,722 | **Keep, separate** | Lexer/parser/semantic analyzer genuinely work and carry the repo's only real test coverage. But it is a **front-end, not a compiler** — no codegen, no backend, no interpreter. Unrelated to booting an AI. Split it into its own repo or `languages/clarity/`. Delete or restore `test_syntax.py`'s commented-out 340 lines. |
| `src/clarityos/development/environment_integration.py` | 463 | **Keep** | Honest `subprocess` git/build/test wrapper. Genuinely reusable; already correctly marked ✅ in `IMPLEMENTATION_STATUS.md:59-61`. |
| `src/clarityos/core/system_monitor.py` | 354 | **Keep** | Real `psutil` + `/proc` telemetry with graceful degradation. Useful to the desktop image as-is. |
| `src/clarityos/hardware/hal.py:175-376` | ~200 | **Extract, then archive the rest** | The `/proc/meminfo` + `lsblk` + `ip -j addr` detection is the only real hardware code. Salvage ~60 lines (fixing the `int("476.9G")` bug at `:286`); archive the surrounding 440. |
| `src/clarityos/clarity_os_kernel/` | 285 | **Archive** | Does not compile on stable; cannot produce a boot image (no runner, no build-std, no target JSON, no docs); 135 of 285 lines dead per compiler warnings; `memory.rs` not wired up; required allocator panics on first `alloc`, so no heap ever. "LLM" prints `0 1 2` and `3`. `vga_buffer.rs`/`serial.rs` are verbatim tutorial code. Nothing here survives contact with a real kernel. |
| `src/clarityos/hardware/` (rest) | ~7,300 | **Archive** | 57 "In a real OS, this would…" markers. `extended_hal.py`, `driver_model.py`, `security_manager.py`, `io_safety.py`, `pci_interface.py` are `pass`. `firmware_interface.py` fabricates a UEFI memory map and logs that it exited boot services. `NetworkManager` cannot initialize. Value is as a **design sketch of an interface taxonomy**, which is worth reading once and then rewriting against real Linux syscalls. |
| `src/clarityos/core/hardware_interface.py` | 566 | **Archive** | 45 simulation markers; six `_simulate_*` methods returning constants; no `wmi`/`ctypes`/`subprocess` despite promising WMI. Zero salvage. |
| `src/clarityos/boot.py` | 593 | **Archive** | Crashes at stage 2. Stages are `asyncio.sleep` + `logger.info` (15 sleeps). `_populate_detected_hardware` (`:264-323`) appends six hardcoded components. |
| `src/clarityos/boot_integration.py` | 399 | **Delete** | Zero importers. Crashes on import at `:312`. 18 `asyncio.sleep`. Invents `"AI-Quantum 9000"`. Superseded by `hardware/boot_integration.py`. Nothing to salvage and nothing depends on it. |
| `src/clarityos/main.py` | 278 | **Rewrite (small)** | The only structurally sound entry point. Fix `:64`/`await system_bus.start()`, drop the boot-update integration, keep the bus + agent registration. Under 100 lines of real work. |
| `src/clarityos/core/memory_manager.py` | 642 | **Archive** | `_detect_memory` hardcodes 16384.0. No `mmap`, no `ctypes`. A dict-based ledger over an imaginary machine. |
| `src/clarityos/core/process_isolation.py` | 666 | **Archive; salvage the permission model** | Isolation is `{"simulated": True}` (`:382`); resource usage is `hash(id) % 20` (`:310-319`). But the **capability-based permission model** (`:1-300`) is coherent, real Python and worth reading before designing the desktop tool broker's permission surface. |
| `src/clarityos/prototype/` | 5,196 | **Archive** | 10 of 12 talent domains raise `NameError`. The `_core`/`_implementation`/`_utils`/`_ext`/`_part2` splitting produced the bug. 34 simulation markers in `talent_execution.py` alone. Superseded in intent by `clarityos-desktop/build/files/clarity-shell.py`. |
| `src/clarityos/agents/update_system/` | 1,190 | **Delete** | Zero references anywhere in `src/`. Near-total duplicate rewrites of two live files. Actively dangerous: `restart_clarityos.py:66` loads *this* dead updater rather than the live one. |
| `src/clarityos/agents/` (rest) | 2,410 | **Archive** | `intent_agent.py:268-284` is keyword matching, self-described "for demo purposes"; `resource_agent.py:294-304` returns `random.uniform(0.8, 1.2)`. `hardware_learning_agent.py` (609) is orphaned. The *shapes* are useful; the bodies are not. |
| `src/clarityos/learning/` | 928 | **Archive** | `strategies.py:318-322` and `:484-488` both return `{"type": "placeholder", "description": "This is a placeholder for actual code changes"}`. The improvement pipeline terminates in literal placeholders. |
| `src/clarityos/development/` (rest) | 1,876 | **Archive** | `code_generation.py` (783) is real templating but `:780` is `TODO: Implement code modification based on AST transformation`. All four `examples/` files (779 lines) are orphans. |
| `src/clarityos/kernel/ai_init/` | 419 | **Archive** | `Makefile:5` names three sources that do not exist, including `init_main.c`. Cannot build or link. "Inference" multiplies by 2.0. |
| `src/clarityos/kernel/ai_mem/`, `ai_sched/` | 144 | **Delete** | README-only directories. `src/clarityos/README.md:33-34` lists them as components. |
| `src/clarityos/user/ai_shell/` | README only | **Delete** | Same. Superseded by `clarity-shell.py`. |
| `src/clarityos/kernel/kernel_updater.py`, `restart_manager.py` | 744 | **Archive** | `kernel_updater.py:141-147` is `asyncio.sleep(1)` under "we'll simulate a successful hot update"; `:253-256` admits `_create_backup` does not copy component files, so there is nothing to roll back to. `restart_manager.py:237` is "Placeholder implementation". `README.md:190` calls this "fully functional". |
| `src/msp_integration/` | 1,072 | **Archive or delete** | `integration.py` is 22 lines of `return True`. `connectors/` and `monitoring/` are empty. The 679-line Flask dashboard is real code that always renders `'No Devices'` (`examples/dashboard.py:194-196`) because it reads from the stub, and cannot be launched as documented (relative imports at `:23-24` run as a script). Orthogonal to the OS project; if MSP work matters, start fresh. |
| `check_imports.py` | 54 | **Delete** | Debug leftover. Fails on Windows. Tests the wrong `sys.path` configuration. Running it writes to a tracked `.log`. |
| `restart_clarityos.py` | 160 | **Delete** | Depends on `run_clarityos.py`, which does not exist. Guaranteed no-op. Drives the dead updater. |
| `pytest.ini` | 2 | **Rewrite** | Its one setting is a no-op pointing at a nonexistent file. Replace with `testpaths` and `pythonpath` that reflect a single import root. |
| `requirements.txt`, `requirements-msp.txt` | 40 | **Rewrite** | Neither installs. Remove `python>=3.7`, fix `sklearn` → `scikit-learn`, drop the four unused scientific packages, add `aiofiles`/`aiohttp`/`psutil`. |
| `README.md` | 289 | **Rewrite** | Least accurate document in the repository (see §3). Does not mention `clarityos-desktop/` at all. |
| `PROJECT_ASSESSMENT.md`, `PROGRESS-SUMMARY.md`, `src/clarityos/docs/CURRENT-STATUS.md`, `IMPLEMENTATION_STATUS.md`, `NETWORK-INTEGRATION.md`, `HARDWARE_LEARNING_*.md`, `src/clarityos/README.md`, `src/clarityos/hardware/README.md` | ~1,500 | **Archive with a header, do not edit in place** | These are dated status reports. Rewriting them loses the record of what was believed when. Move under `legacy/docs/` and prepend a one-line accuracy warning linking here. |
| `FUTURE-WORK.md`, `AI_Agent_Implementation_Plan.md` | 397 | **Keep** | Forward-looking, no status claims. `FUTURE-WORK.md` is redundant with `docs/implementation/roadmap.md` — consider merging. |
| 129 tracked `.pyc`, 3 empty `.log`, 1 `.broken` | — | **Untrack** | §4. |

---

## 3. Documentation claims that need correcting

The pattern is worth naming before the list, because it explains every entry: **claim inflation
increases monotonically with distance from the code.**

```
SELF_UPDATING_OS.md:164   "✅ Basic boot process simulation"
  → CURRENT-STATUS.md:97  "Boot System | ✅ Complete"
  → PROGRESS-SUMMARY.md:59 "direct hardware interaction without conventional OS dependencies"
  → README.md:161         "bootable on actual hardware … on physical machines"
```

Each summary drops the previous one's caveats. The root `README.md` — the first thing anyone reads —
is the least accurate file in the repository.

### 3.1 The two claims flagged for scrutiny

**`src/clarityos/PROGRESS-SUMMARY.md:59`** — *"We've enabled direct hardware interaction without
conventional OS dependencies"*. **False on both halves.**

- *Direct hardware interaction*: the code it credits (`boot.py`, `hardware_interface.py`) contains no
  hardware access. See §1.3.
- *Without conventional OS dependencies*: it is CPython. The **only** places anything real is read,
  it reads Linux — `/proc/meminfo` (`hal.py:212`), `lsblk`, `ip`, `psutil`. A conventional OS is a
  hard dependency, and `hal.py:238` logs `"Could not get memory info from /proc/meminfo. Falling
  back to simulation."` when it is absent. The "network layer" uses Python `socket` against the host
  TCP/IP stack (`network/base_interface.py:119-131`).
- The same file **contradicts itself 28 lines earlier**: `:31` lists *"Simulation capabilities for
  development and testing"* as a feature of `hardware_interface.py`.
- The only code in the repository that touches hardware without an OS underneath is
  `clarity_os_kernel/` and `clarityos-desktop/`. **`PROGRESS-SUMMARY.md` mentions neither.**

**`src/clarityos/PROGRESS-SUMMARY.md:9-13`** — *"Core OS Components: Implemented critical operating
system components"*:

| Sub-claim | Line | Reality |
|---|---|---|
| "Boot system for direct hardware initialization" | `:10` | `boot.py:383-470` — three stages of `asyncio.sleep(0.3)` + `logger.info`, comments at `:388`, `:416`, `:443` all reading "we'll simulate the process". Crashes at stage 2 anyway (§1.2). |
| "Hardware abstraction layer for cross-platform device access" | `:11` | §1.3. Simulation. |
| "Memory management system for AI-optimized resource allocation" | `:12` | `memory_manager.py:144` — `total_mb = 16384.0`. |
| "Process isolation framework with capability-based security" | `:13` | `process_isolation.py:382` — `{"simulated": True}`. The *permission model* is real; the *isolation* does not exist. |

`:57` — *"has established the critical foundation for ClarityOS to function as a true operating
system"* — is not supported by anything in the tree.

### 3.2 `docs/implementation/ai-os-implementation-plan.md` — preserve this one

§6, at `:107-126`, recommends:

```
111  1. Create a bootable Linux-based environment with:
112     - Custom initramfs containing AI components
113     - Modified GRUB bootloader with AI parameters
114     - Hypervisor (KVM/QEMU) for safe experimentation
...
126  This implementation provides a practical path to test the concept while leveraging
     established technologies like Linux for the initial hardware abstraction layer.
```

This is the only strategy in the entire 38-file doc corpus that has produced a working artifact.
`clarityos-desktop/build/build.sh` builds an Alpine rootfs → GPT + FAT ESP → GRUB → kernel →
OpenRC, and `run-qemu.ps1` boots it under OVMF. `clarityos-desktop/README.md:14-15` records M0 and
M1 as verified.

Its value is not just that it was right. Line 126's premise — Linux *as* the initial hardware
abstraction layer — is the honest framing the rest of the corpus abandoned in favour of asserting
bare-metal capability it never had. Sections 1–5 are unexecuted design, but they are labelled as a
plan and make no status claims. It is the only implementation doc that has aged well.

One correction to record when preserving it: **§6.1 was executed; §6.2 and §6.3 were not.** The
desktop image runs `llama-server` + `clarity-shell.py`, not the ClarityOS message bus or agent
manager. If those are still wanted, §6.2–6.3 remain the plan (see the Keep rows in §2).

`docs/implementation/practical-implementation-steps.md:29-33` independently recommends the same
approach and is equally worth keeping.

### 3.3 Overstated claims, with references

**`README.md`** (no badges exist, so that concern is moot):

| Line | Claim | Reality |
|---|---|---|
| 37, 161 | "makes ClarityOS bootable on actual hardware, providing a foundation for running the AI-native OS on physical machines" | CPython requiring a host OS. `firmware_interface.py:100-101` hardcodes UEFI; `:151-152` fabricates the memory map. Nothing bootable. |
| 39, 143-151 | "comprehensive network interface layer … enables ClarityOS to establish secure internet connectivity during the boot process" | `NetworkManager.initialize()` raises `AttributeError` (§1.6). `ethernet_interface.py:34` and `wifi_interface.py:34` call `get_driver_for_device`, which is not defined anywhere — the only similar definition is `get_safe_driver_for_device` at `safe_driver_manager.py:184`. Never executed. |
| 99, 105, 177 | "comprehensive integration module for MSPs" / "Production-ready code for immediate MSP value" / "Immediately deployable in MSP environments" | `msp_integration/integration.py` is 22 lines of `return True` / `return []`. |
| 101, 173 | "Full connector for ConnectWise Manage and Automate" | `connectors/__init__.py` is a 3-line docstring. No other file in the package. |
| 102, 174 | "Machine learning-based anomaly detection" | No ML code in `src/`. Zero imports of `sklearn`/`numpy`/`pandas` anywhere. |
| 103, 175 | "Automated Remediation: Self-healing capabilities" | Does not exist. |
| 126 | Links `src/clarity/examples/msp_integration.clarity` | File does not exist (broken link). |
| 158 | "Memory Management: Advanced memory management for kernel and user space" (listed as implemented) | `extended_hal.py`, 13 lines, `def __init__(self): pass`. |
| 190, 192, 194 | "**fully functional** kernel self-update capability" / "with rollback capabilities" / "Automatically detects and recovers from failed updates" | `kernel_updater.py:141-147` — "we'll simulate a successful hot update" + `asyncio.sleep(1)`; four more stub sites at `:205`, `:253`, `:291`, `:351`. `:253-256` admits backups do not copy component files. Recovery code does not exist. |
| 285 | "a **functioning compiler** for the Clarity language" | Front-end only. No codegen module, no backend. `driver.py` prints tokens/AST/errors. README `:239` itself lists "Implement code generation for target platforms" as future work. |
| — | *Omission:* `clarityos-desktop/` is not mentioned anywhere in `README.md` | The only thing in the repository that boots is invisible in the document that describes the repository. |

**`src/clarityos/docs/CURRENT-STATUS.md:93-105`** — the worst single artifact: a 13-row table with
every row marked **✅ Complete**, against a legend (`IMPLEMENTATION_STATUS.md:6`) defining ✅ as
"Fully implemented and functional".

| Line | Row | Reality |
|---|---|---|
| 95 | Resource Agent — "Monitors and optimizes hardware resources dynamically" | `resource_agent.py:294-304` — "For now, return simulated values" with `random.uniform(0.8, 1.2)`. |
| 96 | Intent Agent — "Processes natural language into system actions" | `intent_agent.py:268-284` — "this would use an LLM or NLU system. This simplified version uses keyword matching"; `:283` "for demo purposes". |
| 97 | Boot System | Crashes at stage 2. |
| 98 | Hardware Interface | 45 simulation markers. |
| 99 | Memory Manager | Hardcodes 16 GB. |
| 100 | Process Isolation | `{"simulated": True}`. |
| 102 | Learning Framework | `strategies.py:318-322`, `:484-488` return literal `"placeholder"` dicts. |
| 104, 105 | Kernel Updater / Restart Manager | Five stub sites; `restart_manager.py:237` "Placeholder implementation". |
| 93, 94 | Message Bus / Agent Manager | **Accurate.** Two of thirteen. |

`CURRENT-STATUS.md:229` repeats "enabling direct hardware interaction". `CURRENT-STATUS.md:119`
*does* concede "Initially using hardware simulation for development and testing" — **contradicting
its own table 20 lines earlier.**

**Sibling docs contradict each other on the same components.**
`src/clarityos/docs/AI-OS-IMPLEMENTATION-PLAN.md:37-40` marks Memory Management ⬜ not done and
`:42-45` marks Process Isolation ⬜ not done, while `CURRENT-STATUS.md:99-100` marks both ✅ Complete
and `PROGRESS-SUMMARY.md:12-13` claims both implemented. Two of the three are wrong; the ⬜ one is
right.

**`src/clarityos/NETWORK-INTEGRATION.md`:**

| Line | Claim | Reality |
|---|---|---|
| 87 | "The network integration is now **fully implemented and ready for testing**." | `AttributeError` on the first call (§1.6). Not testable. Also unimportable — `aiofiles` is missing. |
| 13, 39-46 | "Safe Driver Manager ensures network drivers are secure and stable" | Delegates to `safety/security_manager.py`, 10 lines: `def apply_interface_policies(self, interface): pass`. Called at `ethernet_interface.py:51`. |
| 89-90 | "Load safe drivers for common network devices" | No driver implementations exist; `safe_driver_manager.py:78-147` returns a hardcoded table of driver *names*. |

**`src/clarityos/hardware/README.md`:**

| Line | Claim | Reality |
|---|---|---|
| 3 | "making the system bootable on actual hardware platforms" | False. |
| 66-73, 132 | "Extended HAL … Memory management / Interrupt handling / Device enumeration / Power state transitions" · "✅ Extended HAL with memory and interrupt management" | 13-line empty class. |
| 75-82, 133 | "Driver Framework … registry / lifecycle management / error handling and recovery" · "✅ Driver model framework" | `driver_model.py:28-38`, two `pass` placeholders docstringed "A placeholder for the…". |

**`src/clarityos/docs/HARDWARE_LEARNING_SUMMARY.md`:**

| Line | Claim | Reality |
|---|---|---|
| 84 | "now **fully functional and integrated** with ClarityOS" | `experimentation_framework.py` (773 ln) is orphaned — no importer. `:530` "In a real implementation, this would detect actual hardware". |
| 15-18 | "Documentation Ingestion: Text processing / Structured knowledge extraction" | `documentation_ingestion.py:44-45` "simple rule-based extraction"; `_convert_pdf_to_text` returns the string `"PDF content would be extracted here"` (`:315-319`); HTML likewise (`:321-325`). |
| 25-27 | "Safety Monitoring System" | `security_manager.py` is `pass`. |

**`PROJECT_ASSESSMENT.md`:**

| Line | Claim | Reality |
|---|---|---|
| 17-21 | "Significant foundational work has been completed: … Core OS components including boot system, hardware interface, and message bus" | Only the message bus. |
| 21 | "Working prototypes demonstrating core concepts" | The MSP prototype it means (cited again at `:109`, "Enhance the MSP monitoring prototype") is 22 lines of `return True`. |
| 29-33 | "The agent-based implementation **leveraging MCP servers** provides: Modular design / Scalable approach / Secure isolation / Learning capabilities" | **No MCP server exists in `src/`.** No `mcp` import, no FastMCP. This describes the code samples in `AI_Agent_Implementation_Plan.md:19-214` as though they had been built. |

**`MSP_INTEGRATION.md`:** `:9-11`, `:13-16`, `:18-21` claim connectors, ML monitoring, and
remediation — layers 1–3 of the five-layer design at `:30-36` are empty `__init__.py` files.
`:122-141` narrates three use cases in the present tense ("System automatically clears temporary
files", "Ticket is created") for code that does not exist.

**`src/clarityos/README.md`:** `:33-34` lists `ai_sched/` and `ai_mem/` as components; both are
README-only directories — and `kernel/README.md:33-43` is honest about this ("Design phase,
implementation not started"), so the two files contradict each other. `:87-91` "The Self-Learning
framework is now implemented … ✅ Improvement Generation" → literal `"placeholder"` dicts. `:119`
"✅ Basic framework implemented in boot.py" → `sleep()` + log lines. `:157-231` marks
"Foundation Phase (Completed ✅)" including "Boot process implementation ✅".

**`src/clarityos/docs/IMPLEMENTATION_STATUS.md`:** `:24-25` ✅ on kernel update and restart
management (stubs); `:101-105` "the Code Generation System can generate new code" (template
substitution; the learning→code path ends in placeholders). `:59-61` — ✅ on git operations, build
interface, and test execution — is **accurate**, and is the most honestly-labelled ✅ in the
repository. `:118` "Last updated: March 23, 2025" is stale: the two commits that added the only
genuinely bootable code (`a368791`, `a307ddb`) are recorded nowhere.

### 3.4 "How to run" instructions that do not work

| Doc:line | Command | Failure |
|---|---|---|
| `MSP_INTEGRATION.md:59` | `pip install -r requirements-msp.txt` | `:4` is `python>=3.7`; pip errors. |
| — | `pip install -r requirements.txt` | Same, plus `:22` `sklearn>=0.24.0` refuses to install. |
| `MSP_INTEGRATION.md:64-66` | `python connectwise_integration.py` | File does not exist. |
| `MSP_INTEGRATION.md:74-78` | `python dashboard.py` → localhost:5000 | Relative imports at `dashboard.py:23-24` → `ImportError: attempted relative import with no known parent package`. Even run correctly, every client shows `'No Devices'` (`:194-196`). |
| `MSP_INTEGRATION.md:62-67` | "This will create a config.yaml — edit with your credentials" | Nothing generates it; `config.py` only loads. Credentials go nowhere — `integration.py:9-10` ignores them. |
| `src/clarityos/README.md:62,344`; `kernel/README.md:153` | `python -m src.clarityos.boot` | Prints fake stage messages for ~2.4 s, then fails at HARDWARE_INIT. Also appends to `clarity_os.log` — a tracked file — at import time (`boot.py:29`). |
| `src/clarityos/README.md:349` | `python -m src.clarityos.boot_update_integration` | No `__main__` block; imports and exits silently. |
| — | `cargo build` in `clarity_os_kernel/` | `error[E0554]` — needs nightly (§1.5). No documented build path to a boot image at all. |

### 3.5 Docs that are already accurate — use these as the template

- **`clarityos-desktop/README.md`** — exemplary. `:12-18` distinguishes "verified in QEMU" /
  "in progress" / "**code written, untested**" / "not started". `:20-21` gives measured numbers.
  `:69-78` explicitly separates "the service started" from "a model is doing inference" and states
  that only the second counts. `:94-110` documents failures.
- **`src/clarityos/kernel/README.md:27-43`** — correctly marks `ai_init` "Partially implemented",
  `ai_mem`/`ai_sched` "Design phase, implementation not started".
- **`src/clarity/README.md:5-7`** — "This is an early-stage implementation".
- **`src/clarityos/docs/SELF_UPDATING_OS.md:97,164,281`** — openly says "simulated boot environment",
  "✅ Basic boot process **simulation**", "transform … from a simulated environment to a functioning
  AI operating system". This is the document `README.md:41` cites while dropping every one of those
  qualifiers.
- **`docs/implementation/ai-os-implementation-plan.md`**, **`practical-implementation-steps.md`**,
  **`docs/concepts/*`**, **`docs/msp-use-cases/*`**, **`FUTURE-WORK.md`** — correctly framed as
  plans; no false status claims.

---

## 4. Things that should not be in git

A root `.gitignore` **now exists and is correct** — but it was added by `a307ddb`, the
`clarityos-desktop` commit, and everything below was committed before it. Gitignore has no effect on
already-tracked files.

Of 362 tracked files:

| Kind | Count | Detail |
|---|---|---|
| `.pyc` under `__pycache__/` | **129** | More tracked bytecode than source (126 `.py`). 36% of the index. 27 `__pycache__` directories, all tracked. |
| Empty `.log` at repo root | 3 | `clarity_os.log`, `dashboard.log`, `prototype_os.log`, all 0 bytes. **`main.py:26` and `boot.py:29` open these as `logging.FileHandler` at import time**, so merely importing the package dirties the working tree. Observed during this audit. |
| `.broken` | 1 | `src/clarityos/agents/resource_manager/tests/test_resource_manager.py.broken`, 234 lines, `SyntaxError` on line 1. |

Two of the tracked `.pyc` files **have no corresponding source**, which proves the bytecode is stale
and was committed from a different machine:

- `src/clarity/__pycache__/test_driver.cpython-312-pytest-8.4.1.pyc` — no `src/clarity/test_driver.py`
  (yet `pytest.ini` still references that path)
- `src/clarity/tests/__pycache__/test_ctypes_import.cpython-312-pytest-8.4.1.pyc` — no source

Both are tagged `pytest-8.4.1` while the installed pytest is 8.3.5.

Also worth noting: running `python -c "import clarity.compiler.lexer"` during this audit marked 41
tracked `.pyc` files as modified — a routine import produces a 41-file diff. They were reverted with
`git checkout -- "*.pyc"`.

Nothing else problematic: no `target/`, no venvs, no `site-packages`. The Rust crate has its own
correct `.gitignore` (`/target`).

---

## 5. Recommended cleanup sequence

Ordered so that each step is safe on its own and the repository is never in a worse state than it
started.

**Step 0 — tag the current state.**
`git tag legacy-final a307ddb^` (i.e. `0fa53fd`, the last commit before `clarityos-desktop`). Nothing
below deletes history; this just makes the pre-desktop tree trivially recoverable and removes any
argument for keeping dead files "just in case".

**Step 1 — untrack the junk (one commit, no source changes).**

```bash
git rm -r --cached "**/__pycache__"                          # 129 .pyc
git rm --cached clarity_os.log dashboard.log prototype_os.log
git rm --cached src/clarityos/agents/resource_manager/tests/test_resource_manager.py.broken
```

Then change `main.py:26` and `boot.py:29` to log under a gitignored directory (or to stderr only) so
importing the package stops dirtying the tree. Verify: `git ls-files | grep -c pycache` → 0.

**Step 2 — fix the documentation before touching code.** This is the highest-value step and the
lowest-risk. Right now the README actively misleads anyone who opens the repository, including future
you.

1. Rewrite `README.md`. Lead with `clarityos-desktop/` — it is the project. Adopt that README's
   four-state vocabulary (verified / in progress / written-but-untested / not started). Remove the
   claims listed in §3.3. Relabel `src/clarity/` as a language front-end.
2. Add a one-line accuracy warning at the top of each status doc named in §2, pointing here. Do
   **not** edit their bodies — they are a record of what was believed, and that record has value.
3. Add a short "why this approach" note to `docs/implementation/ai-os-implementation-plan.md`
   recording that §6.1 was executed by `clarityos-desktop` and §6.2–6.3 were not.

**Step 3 — delete what is provably dead** (nothing imports it, nothing can run it):

```
src/clarityos/agents/update_system/          1,190 ln, zero references in src/
src/clarityos/boot_integration.py              399 ln, zero importers, crashes on import
src/clarityos/kernel/ai_mem/, ai_sched/        README-only
src/clarityos/user/ai_shell/                   README-only
check_imports.py, restart_clarityos.py         both non-functional
```

Do Step 3 before Step 4 — deleting `agents/update_system/` and `restart_clarityos.py` together
removes the trap where the restart script drives the dead updater.

**Step 4 — move the rest of the legacy tree under `legacy/`.** One `git mv`, one commit, one
`legacy/README.md` linking here. Contents per §2: `clarity_os_kernel/`, `hardware/`, `boot.py`,
`core/hardware_interface.py`, `core/memory_manager.py`, `core/process_isolation.py`, `prototype/`,
`learning/`, most of `development/`, `agents/` minus the manager, `kernel/`, `msp_integration/`, and
the dated status docs. Keeping them visible but clearly quarantined is better than deleting: they
are a genuine design corpus, and the interface taxonomy in `hardware/` is worth reading once before
rewriting anything against real Linux syscalls.

**Step 5 — extract the four keepers into a clean package.** `message_bus.py`,
`agent_manager.py` + `agent_base.py`, `system_monitor.py`, `environment_integration.py`, plus the
~60 salvageable lines from `hal.py:175-376`. While extracting:

- pick **one** import root and enforce it (§1.7) — the dual-identity bug must not survive the move;
- make `message_bus.start`/`stop` `async def`, or fix the call sites (`main.py:64`);
- fix `hal.py:286`'s `int("476.9G")` crash;
- rewrite `main.py` as a minimal, actually-running entry point.

Verify by running it. That is the bar the legacy tree never met.

**Step 6 — make the test suite mean something.** Fix `pytest.ini` (`testpaths`, `pythonpath`; drop
the dead `norecursedirs`). Either restore `test_syntax.py`'s 340 commented-out lines or delete the
file — do not leave 376 lines that collect zero tests. Delete the `assertTrue(True)` stub and
reconstruct the lost 234-line resource-manager suite from the `.broken` fragment (recoverable from
history before Step 1's `git rm --cached`, or from the file on disk) **if** the agent it tests
survives Step 4. Add tests for the extracted keepers. A green run of 24 tests that exercises five
real lines of the OS is worse than no suite, because it reads as coverage.

**Step 7 — fix packaging.** Rewrite `requirements.txt` so `pip install -r` works: drop
`python>=3.7`, `sklearn` → `scikit-learn`, remove the unused scientific stack, add `aiofiles` /
`aiohttp` / `psutil`. Consider deleting `requirements-msp.txt` alongside `msp_integration/`.

**What not to do:** do not try to repair `boot.py`, the `hardware/` tree, or the Rust kernel in
place. In each case the working version is a rewrite, not a patch — `boot.py`'s stages have no
implementations to fix, `hardware/`'s detection is constants rather than broken code, and the Rust
crate's dead end is architectural (an allocator that panics, on an obsolete bootloader generation,
with the frame allocator unconnected). The `clarityos-desktop` path already demonstrated that Linux
supplies all of it for free, which is precisely what
`docs/implementation/ai-os-implementation-plan.md:126` recommended in the first place.
