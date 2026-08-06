#!/usr/bin/env python3
"""End-to-end test for ClarityOS Desktop stage m1.

Boots the image in QEMU with the guest's serial console on a TCP socket, waits for the
machine to load the model, then actually sends a prompt and captures the reply. This is
the difference between "the service started" and "a model is doing inference on this
hardware" -- only the second one is the milestone.

    python test-m1.py [--timeout 600] [--gui]
"""
from __future__ import annotations

import argparse
import pathlib
import re
import socket
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).parent
QEMU_DIR = pathlib.Path(r"C:\Program Files\qemu")
QEMU = QEMU_DIR / "qemu-system-x86_64.exe"
CODE_FD = QEMU_DIR / "share" / "edk2-x86_64-code.fd"
VARS_TPL = QEMU_DIR / "share" / "edk2-i386-vars.fd"

# qemu64 plus explicit AVX2: 'max' would advertise VMX, and WHPX rejects the
# IA32_FEATURE_CONTROL write OVMF then performs, killing the boot with #GP before GRUB.
CPU = ("qemu64,+avx,+avx2,+f16c,+fma,+bmi1,+bmi2,+sse4.1,+sse4.2,"
       "+ssse3,+popcnt,+xsave,+xsaveopt,+aes")

PROMPT = "Name three colors, comma separated, nothing else."


def free_port() -> int:
    """Grab a port the OS says is free, rather than hoping a fixed one is.

    A leftover QEMU from a previous run holding the port produces a guest that looks
    wedged for the entire timeout, which is a miserable thing to debug.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Serial:
    """Reader thread over the guest's serial console."""

    def __init__(self, sock: socket.socket, mirror: pathlib.Path):
        self.sock = sock
        self.buf = ""
        self.lock = threading.Lock()
        self.mirror = mirror.open("w", encoding="utf-8", errors="replace")
        self.alive = True
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        while self.alive:
            try:
                chunk = self.sock.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            text = chunk.decode("utf-8", "replace")
            with self.lock:
                self.buf += text
            self.mirror.write(text)
            self.mirror.flush()

    def wait_for(self, pattern: str, timeout: float, label: str = "",
                 proc: subprocess.Popen | None = None) -> str | None:
        """Block until `pattern` appears in the stream. Returns the matched text.

        Takes the QEMU handle so a dead VM is reported as such instead of masquerading
        as a slow one for the full timeout.
        """
        rx = re.compile(pattern)
        start = time.time()
        last_len = 0
        stalled_since = time.time()
        while time.time() - start < timeout:
            with self.lock:
                snapshot = self.buf
            m = rx.search(snapshot)
            if m:
                print(f"  [{time.time() - start:6.1f}s] MATCH {label or pattern}")
                return m.group(0)
            if proc is not None and proc.poll() is not None:
                print(f"  [{time.time() - start:6.1f}s] QEMU EXITED (code {proc.returncode}) "
                      f"while waiting for {label or pattern}")
                return None
            if len(snapshot) > last_len:
                if len(snapshot) > last_len + 2000:
                    print(f"  [{time.time() - start:6.1f}s] ...{len(snapshot)} bytes of console output")
                last_len = len(snapshot)
                stalled_since = time.time()
            elif time.time() - stalled_since > 90:
                print(f"  [{time.time() - start:6.1f}s] console silent for 90s "
                      f"({len(snapshot)} bytes) -- guest appears wedged")
                stalled_since = time.time()
            time.sleep(0.5)
        print(f"  [{timeout:6.1f}s] TIMEOUT waiting for {label or pattern}")
        return None

    def send(self, line: str):
        self.sock.sendall((line + "\n").encode())

    def tail(self, n: int = 2500) -> str:
        with self.lock:
            return self.buf[-n:]

    def close(self):
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass
        self.mirror.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=str(HERE / "out" / "clarityos.qcow2"))
    ap.add_argument("--timeout", type=int, default=600, help="model load budget, seconds")
    ap.add_argument("--memory", default="6G")
    ap.add_argument("--cpus", default="4")
    ap.add_argument("--gui", action="store_true", help="also show the QEMU window")
    args = ap.parse_args()

    for p in (QEMU, CODE_FD, VARS_TPL):
        if not pathlib.Path(p).exists():
            print(f"FAIL: missing {p}")
            return 2
    if not pathlib.Path(args.image).exists():
        print(f"FAIL: image not found: {args.image}")
        return 2

    out = HERE / "out"
    out.mkdir(exist_ok=True)
    varsfd = out / "uefi-vars-test.fd"
    varsfd.write_bytes(pathlib.Path(VARS_TPL).read_bytes())
    logfile = out / "m1-test-serial.log"
    qemu_err = out / "m1-test-qemu-stderr.log"
    port = free_port()

    qemu_args = [
        str(QEMU),
        "-machine", "q35",
        "-accel", "whpx,kernel-irqchip=off",
        "-cpu", CPU,
        "-m", args.memory,
        "-smp", args.cpus,
        "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={CODE_FD}",
        "-drive", f"if=pflash,format=raw,unit=1,file={varsfd}",
        "-drive", f"file={args.image},format=qcow2,if=none,id=disk0",
        "-device", "virtio-blk-pci,drive=disk0,bootindex=1",
        "-netdev", "user,id=net0",
        "-device", "virtio-net-pci,netdev=net0",
        "-device", "virtio-vga",
        "-rtc", "base=utc",
        "-no-reboot",
        # wait=on makes QEMU block until we attach, so no early output is lost.
        "-serial", f"tcp:127.0.0.1:{PORT},server=on,wait=on",
    ]
    if not args.gui:
        qemu_args += ["-display", "none"]

    print(f"Launching QEMU (serial on tcp/{PORT}, log -> {logfile.name})")
    proc = subprocess.Popen(qemu_args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    sock = None
    for _ in range(40):
        try:
            sock = socket.create_connection(("127.0.0.1", PORT), timeout=3)
            break
        except OSError:
            if proc.poll() is not None:
                err = proc.stderr.read().decode("utf-8", "replace")
                print(f"FAIL: QEMU exited before serial was reachable\n{err[-2000:]}")
                return 2
            time.sleep(0.5)
    if sock is None:
        proc.kill()
        print("FAIL: could not attach to the guest serial port")
        return 2

    ser = Serial(sock, logfile)
    results: dict[str, bool] = {}

    try:
        print("\n--- boot ---")
        results["GRUB loaded"]      = bool(ser.wait_for(r"GNU GRUB", 90, "GRUB", proc))
        results["kernel booted"]    = bool(ser.wait_for(r"Linux version", 120, "kernel", proc))
        results["root mounted"]     = bool(ser.wait_for(r"Remounting root filesystem", 180, "root fs", proc))

        print("\n--- AI ---")
        results["llama-server up"]  = bool(ser.wait_for(r"Starting llama-server", 180, "llama-server", proc))
        results["chat autostarted"] = bool(ser.wait_for(r"the AI is the shell", 180, "chat banner", proc))
        # Anchored on the .gguf filename: a loose 'model:' also matches kernel boot text
        # such as "Memory model:", which reports a pass before the model has loaded at all.
        results["model loaded"]     = bool(ser.wait_for(r"model:\s+\S+\.gguf", args.timeout, "model ready", proc))
        got_prompt                  = bool(ser.wait_for(r"you>", 180, "input prompt", proc))
        results["prompt ready"]     = got_prompt

        if got_prompt:
            print(f"\n--- inference ---\n  sending: {PROMPT!r}")
            ser.send(PROMPT)
            results["model replied"] = bool(ser.wait_for(r"ai>\s*\S", 420, "model reply", proc))
            time.sleep(25)  # let the token stream finish
            print("\n--- transcript tail ---")
            for line in ser.tail(1600).splitlines()[-22:]:
                print("    " + line)
        else:
            results["model replied"] = False
    finally:
        ser.close()
        if proc.poll() is None:
            proc.kill()
        print(f"\nFull serial log: {logfile}")

    print("\n=================== RESULTS ===================")
    width = max(len(k) for k in results)
    for k, v in results.items():
        print(f"  {k.ljust(width)}  {'PASS' if v else 'FAIL'}")
    ok = all(results.values())
    print("===============================================")
    print("M1 VERIFIED: a model is doing inference on this machine." if ok
          else "M1 NOT verified -- see the serial log above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
