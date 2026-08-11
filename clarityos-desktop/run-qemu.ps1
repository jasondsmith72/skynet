<#
.SYNOPSIS
  Boot a ClarityOS Desktop image in QEMU under UEFI with WHPX acceleration.

.DESCRIPTION
  Hyper-V is unavailable on Windows Home, but WSL2 leaves the Windows Hypervisor Platform
  enabled, so QEMU accelerates through WHPX. Firmware is OVMF (edk2), matching how the
  image boots on real UEFI desktop hardware.

.PARAMETER Mode
  log      Headless, no window. Serial is captured to a file and QEMU is stopped once the
           boot clearly succeeded or clearly failed. Use this for automated verification.
  gui      Opens a QEMU window. Serial still goes to the log file.
  console  -nographic: the VM's serial console takes over this terminal. Exit with Ctrl-A X.

.EXAMPLE
  .\run-qemu.ps1 -Mode log -TimeoutSec 90
  .\run-qemu.ps1 -Mode gui -MemoryGB 8
#>
[CmdletBinding()]
param(
  [ValidateSet('log', 'gui', 'console')] [string] $Mode = 'log',
  [string] $Image      = "$PSScriptRoot\out\clarityos.qcow2",
  [int]    $MemoryGB   = 6,
  [int]    $Cpus       = 4,
  [int]    $TimeoutSec = 120,
  [string] $SerialLog  = "$PSScriptRoot\out\serial.log",
  # Built UP from qemu64 rather than down from 'max', and this is load-bearing:
  #   * 'max' inherits VMX from the host. WHPX has no nested-virt support, so OVMF's
  #     PlatformPei writes IA32_FEATURE_CONTROL (MSR 0x3A), WHPX rejects the write, and
  #     every CPU dies with #GP before GRUB is ever reached. vmx=off does NOT help --
  #     WHPX rejects any write to that MSR, whatever the value.
  #   * qemu64 never advertises VMX, so OVMF never touches the MSR.
  #   * AVX2/FMA/F16C must then be added back explicitly: llama.cpp is compiled requiring
  #     them, and bare qemu64 exposes none, which would be SIGILL on first inference.
  [string] $CpuModel   = 'qemu64,+avx,+avx2,+f16c,+fma,+bmi1,+bmi2,+sse4.1,+sse4.2,+ssse3,+popcnt,+xsave,+xsaveopt,+aes',
  [switch] $NoAccel
)

$ErrorActionPreference = 'Stop'

$qemuDir = 'C:\Program Files\qemu'
$qemu    = Join-Path $qemuDir 'qemu-system-x86_64.exe'
$code    = Join-Path $qemuDir 'share\edk2-x86_64-code.fd'
$varsTpl = Join-Path $qemuDir 'share\edk2-i386-vars.fd'

foreach ($p in @($qemu, $code, $varsTpl)) {
  if (-not (Test-Path $p)) { throw "Missing required QEMU file: $p" }
}
if (-not (Test-Path $Image)) { throw "Image not found: $Image  (run the build first)" }

New-Item -ItemType Directory -Force -Path (Split-Path $SerialLog) | Out-Null

# Each run gets a private copy of the UEFI variable store, so a failed boot cannot leave
# stale NVRAM behind and every run starts from identical firmware state.
$vars = Join-Path $PSScriptRoot 'out\uefi-vars.fd'
Copy-Item $varsTpl $vars -Force

if (Test-Path $SerialLog) { Remove-Item $SerialLog -Force }

$qemuArgs = @(
  '-machine', 'q35'
  '-m',       "${MemoryGB}G"
  '-smp',     "$Cpus"

  # UEFI: read-only firmware code plus a writable variable store, the same split real
  # hardware uses.
  '-drive',   "if=pflash,format=raw,unit=0,readonly=on,file=$code"
  '-drive',   "if=pflash,format=raw,unit=1,file=$vars"

  # snapshot=on discards guest writes. Without it, the forced kill at the end of a run
  # leaves the ext4 dirty bit set and the next boot reports "recovery required" /
  # "Filesystems repaired" -- the test slowly degrades the image it is testing.
  '-drive',   "file=$Image,format=qcow2,if=none,id=disk0,snapshot=on"
  '-device',  'virtio-blk-pci,drive=disk0,bootindex=1'

  '-netdev',  'user,id=net0'
  '-device',  'virtio-net-pci,netdev=net0'

  '-device',  'virtio-vga'
  '-rtc',     'base=utc'
  '-no-reboot'
)

if (-not $NoAccel) {
  # WHPX also needs the in-kernel irqchip disabled.
  $qemuArgs += @('-accel', 'whpx,kernel-irqchip=off', '-cpu', $CpuModel)
} else {
  $qemuArgs += @('-accel', 'tcg', '-cpu', $CpuModel)
}

switch ($Mode) {
  'log'     { $qemuArgs += @('-display', 'none', '-serial', "file:$SerialLog") }
  'gui'     { $qemuArgs += @('-serial', "file:$SerialLog") }
  'console' { $qemuArgs += @('-nographic', '-serial', 'mon:stdio') }
}

Write-Host "QEMU  : $qemu"  -ForegroundColor Cyan
Write-Host "Image : $Image" -ForegroundColor Cyan
Write-Host "Accel : $(if ($NoAccel) { 'tcg (software, slow)' } else { 'whpx' })" -ForegroundColor Cyan
Write-Host "Mode  : $Mode"  -ForegroundColor Cyan
if ($Mode -ne 'console') { Write-Host "Serial: $SerialLog" -ForegroundColor Cyan }
Write-Host ''

if ($Mode -eq 'console') {
  & $qemu @qemuArgs
  exit $LASTEXITCODE
}

# Windows PowerShell 5.1's -ArgumentList array form does not quote elements containing
# spaces, which breaks every path under "C:\Program Files". Build one command line and
# quote each argument that needs it. Each -drive/-device value must stay a single argv
# element, so the quotes go around the whole comma-separated option string.
$argString = ($qemuArgs | ForEach-Object {
  if ($_ -match '\s') { '"' + $_ + '"' } else { $_ }
}) -join ' '

Write-Verbose "argv: $argString"
$proc = Start-Process -FilePath $qemu -ArgumentList $argString -PassThru -NoNewWindow

if ($Mode -eq 'gui') {
  Write-Host "QEMU running as PID $($proc.Id). Close the window to stop it." -ForegroundColor Green
  $proc.WaitForExit()
  exit $proc.ExitCode
}

# log mode: watch the serial log and stop as soon as the outcome is unambiguous.
#
# There are two different success markers because the stages end differently: an m0 image
# stops at a getty login prompt, while an m1 image replaces that getty with the chat REPL
# and therefore NEVER prints "login:". Checking only for "login:" made this verifier
# structurally incapable of passing on the project's flagship artifact -- a perfect m1 boot
# reported TIMEOUT.
$successMarkers = @{
  'REACHED CHAT PROMPT (m1)'  = 'you>'
  'REACHED LOGIN PROMPT (m0)' = 'login:'
}
# The #GP dump is the WHPX/OVMF firmware crash the $CpuModel default exists to avoid; it
# must be detectable, or a regression there looks like a plain timeout.
$failureMarkers = @{
  'KERNEL PANIC'            = 'Kernel panic'
  'ROOT MOUNT FAILED'       = 'Unable to mount root|Mounting root: failed'
  'EMERGENCY SHELL'         = 'Entering emergency|emergency recovery shell'
  'FIRMWARE #GP (CPU model)' = 'X64 Exception Type'
  'ILLEGAL INSTRUCTION'     = 'SIGILL|Illegal instruction'
  'GETTY RESPAWN LOOP'      = 'respawning too fast'
}

$deadline  = (Get-Date).AddSeconds($TimeoutSec)
$verdict   = 'TIMEOUT (no conclusive marker in serial log)'
$succeeded = $false
$readFailed = $true
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 3
  if ($proc.HasExited) { $verdict = "QEMU EXITED early (code $($proc.ExitCode))"; break }
  if (-not (Test-Path $SerialLog)) { continue }
  $txt = Get-Content $SerialLog -Raw -ErrorAction SilentlyContinue
  # Distinguish "log unreadable" from "marker not present yet". QEMU holds the chardev
  # file open, and if the share mode excludes readers this is $null every iteration --
  # which would otherwise be reported as an ordinary timeout with no hint of the cause.
  if ($null -eq $txt) { continue }
  $readFailed = $false

  $hit = $failureMarkers.GetEnumerator() | Where-Object { $txt -match $_.Value } | Select-Object -First 1
  if ($hit) { $verdict = $hit.Key; break }
  $hit = $successMarkers.GetEnumerator() | Where-Object { $txt -match $_.Value } | Select-Object -First 1
  if ($hit) { $verdict = $hit.Key; $succeeded = $true; break }
}

if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }

if ($readFailed -and -not $succeeded) {
  $verdict += ' -- NOTE: the serial log was never readable; the verdict is not evidence about the guest'
}

$color = if ($succeeded) { 'Green' } else { 'Yellow' }
Write-Host "`nVerdict: $verdict" -ForegroundColor $color
if (Test-Path $SerialLog) {
  Write-Host "Serial log: $((Get-Item $SerialLog).Length) bytes at $SerialLog"
}
# Exit non-zero on anything that is not a confirmed success, so this can gate automation.
exit $(if ($succeeded) { 0 } else { 1 })
