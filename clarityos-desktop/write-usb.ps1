<#
.SYNOPSIS
  Write the ClarityOS raw disk image to a USB stick. This DESTROYS the target disk.

.DESCRIPTION
  Run with no arguments to list the disks in this machine and see which ones are plausible
  USB targets. Nothing is written in that mode.

  To actually write, pass -DiskNumber explicitly. There is deliberately no auto-detection:
  the whole failure mode this script exists to prevent is "the tool guessed and the guess
  was your system drive".

  Layers of protection, in order:

    1. -DiskNumber is mandatory in the writing parameter set. No default, no guessing.
    2. Hard refusals that -Force cannot override: disk 0, the boot disk, the system disk,
       the disk holding %SystemDrive%, the disk holding this script or the image file, and
       any disk smaller than the image.
    3. Soft refusals that -Force overrides: a disk that is not removable/USB, and a disk
       larger than -MaxSizeGB (a 2 TB target is far more likely to be your backup drive
       than your USB stick).
    4. The image itself is checked for a GPT header before anything is touched, so a typo
       in -Image cannot silently write a text file over your partition table.
    5. A destruction summary lists every partition, volume, drive letter and label that is
       about to disappear, and you must type an exact phrase to proceed.

  Writing is done with a plain .NET FileStream against \\.\PhysicalDriveN. See
  docs/m4-real-hardware.md for why that rather than dd-for-windows.

.PARAMETER List
  List all disks with candidacy assessment and exit. This is the default when the script is
  run with no arguments.

.PARAMETER DiskNumber
  The physical disk number to overwrite, as shown in the -List output (and in Disk
  Management / diskpart "list disk"). Required. Everything on it is destroyed.

.PARAMETER Image
  Path to the raw image. Defaults to .\out\clarityos.raw, which the build produces when
  EXPORT_RAW=1.

.PARAMETER Force
  Override the soft refusals only: non-removable bus type, and the size ceiling. It does
  not override any of the hard refusals in layer 2 above.

.PARAMETER DryRun
  Run every check and print the destruction summary, then stop without asking for
  confirmation and without writing. Use this to see what would happen.

.PARAMETER Verify
  After writing, read the disk back and compare a SHA256 of the written region against the
  image. Roughly doubles the run time.

.PARAMETER MaxSizeGB
  Soft ceiling on target disk size. Default 256 GB. Above this, -Force is required.

.EXAMPLE
  .\write-usb.ps1
  List disks and work out which number your USB stick is.

.EXAMPLE
  .\write-usb.ps1 -DiskNumber 2 -DryRun
  Show exactly what would be destroyed, without touching anything.

.EXAMPLE
  .\write-usb.ps1 -DiskNumber 2 -Verify
  Write the image to physical disk 2 and verify it afterwards. Requires an elevated shell.
#>
[CmdletBinding(DefaultParameterSetName = 'List')]
param(
  [Parameter(ParameterSetName = 'List')]
  [switch] $List,

  [Parameter(ParameterSetName = 'Write', Mandatory = $true)]
  [ValidateRange(0, 63)]
  [int] $DiskNumber,

  [Parameter(ParameterSetName = 'Write')]
  [string] $Image = "$PSScriptRoot\out\clarityos.raw",

  [Parameter(ParameterSetName = 'Write')]
  [switch] $Force,

  [Parameter(ParameterSetName = 'Write')]
  [switch] $DryRun,

  [Parameter(ParameterSetName = 'Write')]
  [switch] $Verify,

  [Parameter(ParameterSetName = 'Write')]
  [ValidateRange(1, 65536)]
  [int] $MaxSizeGB = 256,

  [Parameter(ParameterSetName = 'Write')]
  [ValidateRange(1, 64)]
  [int] $ChunkMB = 4
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
function Say  { param([string]$m) Write-Host $m }
function Head { param([string]$m) Write-Host "`n$m" -ForegroundColor Cyan }
function Good { param([string]$m) Write-Host $m -ForegroundColor Green }
function Warn { param([string]$m) Write-Host "WARNING: $m" -ForegroundColor Yellow }
function Fail { param([string]$m) Write-Host "`nREFUSING: $m`n" -ForegroundColor Red; exit 1 }

function Format-Size {
  param([double] $Bytes)
  if ($Bytes -ge 1TB) { return ('{0:N2} TB' -f ($Bytes / 1TB)) }
  if ($Bytes -ge 1GB) { return ('{0:N2} GB' -f ($Bytes / 1GB)) }
  if ($Bytes -ge 1MB) { return ('{0:N1} MB' -f ($Bytes / 1MB)) }
  if ($Bytes -ge 1KB) { return ('{0:N0} KB' -f ($Bytes / 1KB)) }
  return ('{0:N0} B' -f $Bytes)
}

function Test-Admin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  $pr = New-Object Security.Principal.WindowsPrincipal($id)
  return $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ---------------------------------------------------------------------------
# Disk inventory
#
# Get-Disk knows about boot/system/offline/readonly flags and bus type; Win32_DiskDrive
# knows MediaType and the hardware serial. Neither alone is enough to judge "is this
# safe to destroy", so both are collected and joined on the disk number.
# ---------------------------------------------------------------------------
function Get-DiskInventory {
  $cim = @{}
  foreach ($d in Get-CimInstance Win32_DiskDrive) { $cim[[int]$d.Index] = $d }

  $rows = @()
  foreach ($disk in (Get-Disk | Sort-Object Number)) {
    $n   = [int]$disk.Number
    $drv = $null
    if ($cim.ContainsKey($n)) { $drv = $cim[$n] }

    $media = 'unknown'
    $iface = 'unknown'
    $serial = ''
    if ($null -ne $drv) {
      if ($drv.MediaType)      { $media  = [string]$drv.MediaType }
      if ($drv.InterfaceType)  { $iface  = [string]$drv.InterfaceType }
      if ($drv.SerialNumber)   { $serial = ([string]$drv.SerialNumber).Trim() }
    }

    # Volumes and drive letters living on this disk, for the destruction summary and for
    # the "does this disk host something load-bearing" checks.
    $vols = @()
    try {
      foreach ($p in (Get-Partition -DiskNumber $n -ErrorAction Stop)) {
        $v = $null
        try { $v = Get-Volume -Partition $p -ErrorAction Stop } catch { $v = $null }
        $letter = ''
        if ($p.DriveLetter -and $p.DriveLetter -ne [char]0) { $letter = [string]$p.DriveLetter }
        $label = ''; $fs = ''; $free = $null
        if ($null -ne $v) {
          if ($v.FileSystemLabel) { $label = [string]$v.FileSystemLabel }
          if ($v.FileSystem)      { $fs    = [string]$v.FileSystem }
          $free = $v.SizeRemaining
        }
        $vols += [pscustomobject]@{
          Partition = $p.PartitionNumber
          Letter    = $letter
          Label     = $label
          FileSystem= $fs
          Type      = [string]$p.Type
          Size      = [int64]$p.Size
          Free      = $free
        }
      }
    } catch {
      # Disks with no partition table have no partitions; that is not an error here.
    }

    $isRemovable = ($disk.BusType -in @('USB', 'SD', 'MMC')) -or ($media -like '*Removable*')

    $rows += [pscustomobject]@{
      Number       = $n
      Model        = [string]$disk.FriendlyName
      Serial       = $serial
      BusType      = [string]$disk.BusType
      MediaType    = $media
      Interface    = $iface
      Size         = [int64]$disk.Size
      SectorSize   = [int]$disk.LogicalSectorSize
      Partitions   = [string]$disk.PartitionStyle
      IsBoot       = [bool]$disk.IsBoot
      IsSystem     = [bool]$disk.IsSystem
      IsOffline    = [bool]$disk.IsOffline
      IsReadOnly   = [bool]$disk.IsReadOnly
      IsRemovable  = $isRemovable
      Volumes      = $vols
      Letters      = @($vols | Where-Object { $_.Letter } | ForEach-Object { $_.Letter })
    }
  }
  return $rows
}

function Get-DiskNumberForPath {
  # Which physical disk holds a given filesystem path? Used to refuse writing over the
  # disk that holds Windows, this script, or the image being written.
  param([string] $Path)
  try {
    $full = [System.IO.Path]::GetFullPath($Path)
    $root = [System.IO.Path]::GetPathRoot($full)          # e.g. "C:\"
    if (-not $root -or $root.Length -lt 2 -or $root[1] -ne ':') { return $null }
    $letter = $root.Substring(0, 1)
    $part = Get-Partition -DriveLetter $letter -ErrorAction Stop
    return [int]$part.DiskNumber
  } catch {
    return $null
  }
}

# ---------------------------------------------------------------------------
# List mode
# ---------------------------------------------------------------------------
function Show-DiskList {
  $inv = Get-DiskInventory

  Head 'Physical disks in this machine'
  Say ''
  Say ('  {0,-3} {1,-34} {2,-7} {3,-10} {4,-6} {5,-9} {6}' -f `
       '#', 'Model', 'Bus', 'Size', 'Part', 'Removable', 'Volumes')
  Say ('  ' + ('-' * 106))
  foreach ($d in $inv) {
    $volTxt = '(none)'
    if ($d.Volumes.Count -gt 0) {
      $bits = @()
      foreach ($v in $d.Volumes) {
        $b = ''
        if ($v.Letter) { $b = "$($v.Letter):" } else { $b = "p$($v.Partition)" }
        if ($v.Label)  { $b = "$b '$($v.Label)'" }
        $bits += $b
      }
      $volTxt = ($bits -join ', ')
    }
    $flags = @()
    if ($d.IsBoot)     { $flags += 'BOOT' }
    if ($d.IsSystem)   { $flags += 'SYSTEM' }
    if ($d.IsOffline)  { $flags += 'offline' }
    if ($d.IsReadOnly) { $flags += 'read-only' }
    if ($flags.Count -gt 0) { $volTxt = "$volTxt  [$($flags -join ' ')]" }

    $rem = 'no'
    if ($d.IsRemovable) { $rem = 'YES' }

    # Some controllers report no friendly name at all; do not let that abort the listing.
    $model = '(unnamed)'
    if ($d.Model) { $model = $d.Model.Substring(0, [Math]::Min(34, $d.Model.Length)) }

    $line = '  {0,-3} {1,-34} {2,-7} {3,-10} {4,-6} {5,-9} {6}' -f `
            $d.Number, $model, `
            $d.BusType, (Format-Size $d.Size), $d.Partitions, $rem, $volTxt

    $colour = 'Gray'
    if ($d.IsBoot -or $d.IsSystem -or $d.Number -eq 0) { $colour = 'Red' }
    elseif ($d.IsRemovable) { $colour = 'Green' }
    Write-Host $line -ForegroundColor $colour
  }

  $cands = @($inv | Where-Object { $_.IsRemovable -and -not $_.IsBoot -and -not $_.IsSystem -and $_.Number -ne 0 })

  Say ''
  if ($cands.Count -eq 0) {
    Warn 'No removable disk found. Plug the USB stick in, wait for Windows to enumerate it, and re-run.'
    Say  'A disk shown in red can never be written by this script.'
  } else {
    Head 'Plausible USB targets'
    foreach ($c in $cands) {
      Say ("  disk {0}   {1}   {2}   serial {3}" -f $c.Number, (Format-Size $c.Size), $c.Model, $c.Serial)
    }
    Say ''
    Say 'Confirm the identity from the model, size and serial above before continuing.'
    Say 'Unplug the stick, re-run this list, plug it back in and re-run again if unsure:'
    Say 'the number that appears and disappears is the right one.'
    Say ''
    Head 'Next step'
    foreach ($c in $cands) {
      Say "  .\write-usb.ps1 -DiskNumber $($c.Number) -DryRun     # check, destroy nothing"
      Say "  .\write-usb.ps1 -DiskNumber $($c.Number)             # write (elevated shell)"
      break
    }
  }
  Say ''
}

if ($PSCmdlet.ParameterSetName -eq 'List') {
  Show-DiskList
  exit 0
}

# ===========================================================================
# Write mode
# ===========================================================================

Head 'ClarityOS USB writer'

# --- The image ------------------------------------------------------------
if (-not (Test-Path -LiteralPath $Image -PathType Leaf)) {
  Say  ''
  Say  "Image not found: $Image"
  Say  ''
  Say  'The build only emits the raw image on request. From the project directory:'
  Say  '    EXPORT_RAW=1 STAGE=m1 ./make.sh          (or the equivalent docker run)'
  Fail 'no image to write'
}
$imgItem  = Get-Item -LiteralPath $Image
$imgPath  = $imgItem.FullName
$imgBytes = [int64]$imgItem.Length

if ($imgBytes -eq 0)     { Fail "image is zero bytes: $imgPath" }
if ($imgBytes -gt 128GB) { Fail "image is $(Format-Size $imgBytes); that is not a ClarityOS image" }

# Sanity-check that this really is a GPT disk image before we go anywhere near a physical
# drive. A protective MBR signature at 0x1FE and 'EFI PART' at the start of LBA 1.
$probe = New-Object byte[] 4096
$fsProbe = [System.IO.File]::OpenRead($imgPath)
try { $probeRead = $fsProbe.Read($probe, 0, $probe.Length) } finally { $fsProbe.Dispose() }

$looksGpt = $false
$hasClarity = $false
if ($probeRead -ge 1024) {
  $gptMagic = [System.Text.Encoding]::ASCII.GetString($probe, 512, 8)
  $mbrSig   = ($probe[510] -eq 0x55) -and ($probe[511] -eq 0xAA)
  $looksGpt = ($gptMagic -eq 'EFI PART') -and $mbrSig
  # GPT partition names are UTF-16LE; look for "CLARITY" in the entry array at LBA 2.
  $tail = [System.Text.Encoding]::Unicode.GetString($probe, 1024, $probeRead - 1024)
  $hasClarity = $tail.Contains('CLARITY')
}
if (-not $looksGpt) {
  Fail ("$imgPath does not begin with a protective MBR + GPT header. " +
        'This script only writes GPT disk images; check the -Image path.')
}
Say ("  image        : $imgPath")
Say ("  image size   : $(Format-Size $imgBytes)  ($imgBytes bytes)")
if ($hasClarity) { Say '  image check  : GPT header OK, CLARITY* partition labels found' }
else             { Warn 'GPT header is valid but no CLARITY* partition label was found. Right file?' }

# --- The target -----------------------------------------------------------
$inv    = Get-DiskInventory
$target = $inv | Where-Object { $_.Number -eq $DiskNumber }
if ($null -eq $target) {
  Say ''
  Show-DiskList
  Fail "there is no physical disk $DiskNumber on this machine"
}

Say ''
Say ("  target       : disk $($target.Number)  $($target.Model)")
Say ("  bus / media  : $($target.BusType) / $($target.MediaType)")
Say ("  serial       : $($target.Serial)")
Say ("  target size  : $(Format-Size $target.Size)  ($($target.Size) bytes)")
Say ("  sector size  : $($target.SectorSize) bytes")

# --- Hard refusals: -Force does not apply ---------------------------------
$sysDiskNum    = Get-DiskNumberForPath $env:SystemDrive
$scriptDiskNum = Get-DiskNumberForPath $PSScriptRoot
$imageDiskNum  = Get-DiskNumberForPath $imgPath

if ($target.Number -eq 0) {
  Fail 'disk 0. On essentially every machine this is the internal system disk.'
}
if ($target.IsBoot) {
  Fail "disk $DiskNumber is flagged by Windows as the BOOT disk."
}
if ($target.IsSystem) {
  Fail "disk $DiskNumber is flagged by Windows as the SYSTEM disk."
}
if ($null -ne $sysDiskNum -and $target.Number -eq $sysDiskNum) {
  Fail "disk $DiskNumber holds $env:SystemDrive (this Windows installation)."
}
if ($null -ne $scriptDiskNum -and $target.Number -eq $scriptDiskNum) {
  Fail "disk $DiskNumber holds this script ($PSScriptRoot). Writing it would destroy the project."
}
if ($null -ne $imageDiskNum -and $target.Number -eq $imageDiskNum) {
  Fail "disk $DiskNumber holds the image being written ($imgPath)."
}
if ($target.Size -lt $imgBytes) {
  Fail ("disk $DiskNumber is $(Format-Size $target.Size) but the image is " +
        "$(Format-Size $imgBytes). It will not fit.")
}
foreach ($v in $target.Volumes) {
  if ($v.Letter -and ($v.Letter + ':') -eq $env:SystemDrive) {
    Fail "disk $DiskNumber contains $env:SystemDrive."
  }
}

# --- Soft refusals: -Force overrides these --------------------------------
$softBlocks = @()
if (-not $target.IsRemovable) {
  $softBlocks += ("bus type is '$($target.BusType)' and media type is " +
                  "'$($target.MediaType)' -- this does not look like a removable USB device")
}
if ($target.Size -gt ($MaxSizeGB * 1GB)) {
  $softBlocks += ("disk is $(Format-Size $target.Size), above the ${MaxSizeGB} GB safety " +
                  'ceiling -- a disk this large is more likely an internal or backup drive ' +
                  'than a USB stick')
}
if ($softBlocks.Count -gt 0) {
  Say ''
  foreach ($b in $softBlocks) { Warn $b }
  if (-not $Force) {
    Say ''
    Say 'If this really is the disk you want, re-run with -Force. Read the reasons above first.'
    Fail "disk $DiskNumber failed the removable-media checks"
  }
  Warn '-Force given: proceeding despite the above. This is on you.'
}

# --- Elevation ------------------------------------------------------------
if (-not $DryRun -and -not (Test-Admin)) {
  Say ''
  Say 'Raw physical-disk access needs an elevated shell. Open PowerShell as Administrator'
  Say 'and re-run the same command, or from this window:'
  Say ''
  Say "    Start-Process powershell -Verb RunAs -ArgumentList '-NoExit','-File','$PSCommandPath','-DiskNumber','$DiskNumber'"
  Fail 'not running as Administrator'
}

# --- Destruction summary --------------------------------------------------
Head 'THIS WILL DESTROY EVERYTHING ON THE FOLLOWING DISK'
Say ''
Write-Host ("  Disk $($target.Number)   $($target.Model)   $(Format-Size $target.Size)   " +
            "bus=$($target.BusType)   serial=$($target.Serial)") -ForegroundColor Red
Say ''
if ($target.Volumes.Count -eq 0) {
  Say "  Partition table : $($target.Partitions) -- no partitions detected"
} else {
  Say "  Partition table : $($target.Partitions)"
  Say ''
  Say ('  {0,-4} {1,-7} {2,-22} {3,-8} {4,-11} {5}' -f 'Part', 'Letter', 'Label', 'FS', 'Size', 'Free')
  Say ('  ' + ('-' * 74))
  foreach ($v in $target.Volumes) {
    $letter = '-'
    if ($v.Letter) { $letter = "$($v.Letter):" }
    $label = '-'
    if ($v.Label) { $label = $v.Label }
    $fs = '-'
    if ($v.FileSystem) { $fs = $v.FileSystem }
    $free = '-'
    if ($null -ne $v.Free) { $free = Format-Size $v.Free }
    Write-Host ('  {0,-4} {1,-7} {2,-22} {3,-8} {4,-11} {5}' -f `
                $v.Partition, $letter, $label, $fs, (Format-Size $v.Size), $free) -ForegroundColor Red
  }
}
Say ''
Say '  Every partition, file and byte on that disk is overwritten. There is no undo,'
Say '  no recycle bin, and no partial recovery once writing starts.'
Say ''
Say ("  Replacing it with : $imgPath  ($(Format-Size $imgBytes))")

if ($DryRun) {
  Say ''
  Good '-DryRun: all checks passed. Nothing was written. Drop -DryRun to do it for real.'
  exit 0
}

# --- Typed confirmation ---------------------------------------------------
$phrase = "ERASE DISK $DiskNumber"
Say ''
Write-Host "  To proceed, type exactly:  $phrase" -ForegroundColor Yellow
Say         '  Anything else aborts.'
Say ''
$typed = Read-Host '  confirm'
if ($typed -cne $phrase) {
  Say ''
  Good 'Aborted. Nothing was written.'
  exit 1
}

# ---------------------------------------------------------------------------
# Dismount, then write
#
# Windows will not let a raw handle write to sectors that belong to a mounted volume, and
# it can also re-mount a volume mid-write and corrupt what has been written. So: clear the
# partition table (which removes the volumes), then take the disk offline (which stops the
# mount manager touching it), and only then open \\.\PhysicalDriveN.
# ---------------------------------------------------------------------------
Head 'Preparing the disk'

try {
  if ($target.IsReadOnly) {
    Say '  clearing the software read-only flag'
    Set-Disk -Number $DiskNumber -IsReadOnly $false
  }
  if ($target.IsOffline) {
    Say '  bringing the disk online so its partitions can be removed'
    Set-Disk -Number $DiskNumber -IsOffline $false
    Start-Sleep -Milliseconds 500
  }
  if ($target.Partitions -ne 'RAW') {
    Say '  removing existing partitions and volumes (Clear-Disk)'
    Clear-Disk -Number $DiskNumber -RemoveData -RemoveOEM -Confirm:$false
    Start-Sleep -Milliseconds 500
  }
  Say '  taking the disk offline for exclusive raw access'
  Set-Disk -Number $DiskNumber -IsOffline $true
  Start-Sleep -Milliseconds 500
} catch {
  Say ''
  Say "Could not prepare disk ${DiskNumber}: $($_.Exception.Message)"
  Say 'Close anything using the disk (Explorer windows, backup software, antivirus scans)'
  Say 'and try again. Nothing has been written.'
  Fail 'disk preparation failed'
}

$sector = $target.SectorSize
if ($sector -le 0) { $sector = 512 }
$chunk  = $ChunkMB * 1MB
if (($chunk % $sector) -ne 0) { Fail "chunk size $chunk is not a multiple of the $sector-byte sector" }

$devPath = "\\.\PhysicalDrive$DiskNumber"
Head "Writing $(Format-Size $imgBytes) to $devPath"
Say  '  Do not unplug the stick. Do not close this window.'
Say  ''

$src = $null
$dst = $null
$sw  = [System.Diagnostics.Stopwatch]::StartNew()
$written = [int64]0
$writeError = $null

try {
  $src = New-Object System.IO.FileStream(
    $imgPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read,
    [System.IO.FileShare]::Read, $chunk, [System.IO.FileOptions]::SequentialScan)

  # bufferSize 1 disables FileStream's own buffering. That matters: an unbuffered raw
  # device handle only accepts sector-aligned writes in sector-sized multiples, and a
  # buffering FileStream would happily issue a 137-byte write and fail.
  $dst = New-Object System.IO.FileStream(
    $devPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Write,
    [System.IO.FileShare]::ReadWrite, 1, [System.IO.FileOptions]::WriteThrough)

  $buf     = New-Object byte[] $chunk
  $lastTick = 0

  while ($written -lt $imgBytes) {
    $want = [int][Math]::Min([int64]$chunk, $imgBytes - $written)
    # Fill the buffer completely; a single Read is allowed to return short.
    $got = 0
    while ($got -lt $want) {
      $n = $src.Read($buf, $got, $want - $got)
      if ($n -le 0) { break }
      $got += $n
    }
    if ($got -le 0) { break }

    # Round the final short chunk up to a whole sector, zero-filling the tail. The image
    # is built in whole sectors so this normally rounds by 0, but never assume.
    $toWrite = $got
    if (($toWrite % $sector) -ne 0) {
      $pad = $sector - ($toWrite % $sector)
      for ($i = 0; $i -lt $pad; $i++) { $buf[$toWrite + $i] = 0 }
      $toWrite += $pad
    }

    $dst.Write($buf, 0, $toWrite)
    $written += $got

    if (($sw.ElapsedMilliseconds - $lastTick) -ge 1000) {
      $lastTick = $sw.ElapsedMilliseconds
      $pct  = [int](100 * $written / $imgBytes)
      $rate = 0
      if ($sw.Elapsed.TotalSeconds -gt 0) { $rate = $written / $sw.Elapsed.TotalSeconds }
      $etaSec = 0
      if ($rate -gt 0) { $etaSec = [int](($imgBytes - $written) / $rate) }
      Write-Progress -Activity "Writing to $devPath" `
        -Status ("$(Format-Size $written) of $(Format-Size $imgBytes)  @ $(Format-Size $rate)/s") `
        -PercentComplete $pct -SecondsRemaining $etaSec
    }
  }

  Write-Progress -Activity "Writing to $devPath" -Completed
  Say '  flushing to the device (this is where a slow stick makes you wait)'
  $dst.Flush($true)
} catch {
  $writeError = $_
} finally {
  if ($null -ne $dst) { try { $dst.Dispose() } catch { } }
  if ($null -ne $src) { try { $src.Dispose() } catch { } }
}
$sw.Stop()

if ($null -ne $writeError) {
  Say ''
  Say "Write failed after $(Format-Size $written): $($writeError.Exception.Message)"
  Say ''
  Say 'The disk is now in an indeterminate state and will not boot. Re-run the script to'
  Say 'try again. If it keeps failing at the same offset the stick is probably faulty.'
  try { Set-Disk -Number $DiskNumber -IsOffline $false -ErrorAction SilentlyContinue } catch { }
  Fail 'write incomplete'
}

if ($written -ne $imgBytes) {
  try { Set-Disk -Number $DiskNumber -IsOffline $false -ErrorAction SilentlyContinue } catch { }
  Fail "short write: $written of $imgBytes bytes"
}

$secs = [Math]::Max($sw.Elapsed.TotalSeconds, 0.001)
Good ("  wrote $(Format-Size $written) in $([int]$sw.Elapsed.TotalSeconds)s " +
      "($(Format-Size ($written / $secs))/s)")

# ---------------------------------------------------------------------------
# Optional read-back verification
# ---------------------------------------------------------------------------
if ($Verify) {
  Head 'Verifying'
  $vsw = [System.Diagnostics.Stopwatch]::StartNew()
  $shaA = [System.Security.Cryptography.SHA256]::Create()
  $shaB = [System.Security.Cryptography.SHA256]::Create()
  $ok = $false
  $rsrc = $null; $rdst = $null
  try {
    $rsrc = New-Object System.IO.FileStream(
      $imgPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read,
      [System.IO.FileShare]::Read, $chunk, [System.IO.FileOptions]::SequentialScan)
    $rdst = New-Object System.IO.FileStream(
      $devPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read,
      [System.IO.FileShare]::ReadWrite, 1, [System.IO.FileOptions]::None)

    $a = New-Object byte[] $chunk
    $b = New-Object byte[] $chunk
    $done = [int64]0
    while ($done -lt $imgBytes) {
      $want = [int][Math]::Min([int64]$chunk, $imgBytes - $done)
      $rounded = $want
      if (($rounded % $sector) -ne 0) { $rounded += $sector - ($rounded % $sector) }

      $ga = 0
      while ($ga -lt $want) { $n = $rsrc.Read($a, $ga, $want - $ga); if ($n -le 0) { break }; $ga += $n }
      $gb = 0
      while ($gb -lt $rounded) { $n = $rdst.Read($b, $gb, $rounded - $gb); if ($n -le 0) { break }; $gb += $n }
      if ($ga -lt $want -or $gb -lt $want) { throw "read short at offset $done" }

      $shaA.TransformBlock($a, 0, $want, $null, 0) | Out-Null
      $shaB.TransformBlock($b, 0, $want, $null, 0) | Out-Null
      $done += $want

      $pct = [int](100 * $done / $imgBytes)
      Write-Progress -Activity 'Verifying' -Status "$(Format-Size $done) of $(Format-Size $imgBytes)" -PercentComplete $pct
    }
    $shaA.TransformFinalBlock((New-Object byte[] 0), 0, 0) | Out-Null
    $shaB.TransformFinalBlock((New-Object byte[] 0), 0, 0) | Out-Null
    $hexA = ($shaA.Hash | ForEach-Object { $_.ToString('x2') }) -join ''
    $hexB = ($shaB.Hash | ForEach-Object { $_.ToString('x2') }) -join ''
    Write-Progress -Activity 'Verifying' -Completed
    Say "  image  sha256 $hexA"
    Say "  device sha256 $hexB"
    $ok = ($hexA -eq $hexB)
  } finally {
    if ($null -ne $rdst) { try { $rdst.Dispose() } catch { } }
    if ($null -ne $rsrc) { try { $rsrc.Dispose() } catch { } }
    $shaA.Dispose(); $shaB.Dispose()
    $vsw.Stop()
  }
  if ($ok) { Good "  verified OK in $([int]$vsw.Elapsed.TotalSeconds)s" }
  else {
    Say ''
    Say 'Read-back does NOT match the image. Do not trust this stick: rewrite it, and if it'
    Say 'fails again the flash is bad. Cheap USB sticks fail exactly like this.'
    try { Set-Disk -Number $DiskNumber -IsOffline $false -ErrorAction SilentlyContinue } catch { }
    Fail 'verification failed'
  }
}

# ---------------------------------------------------------------------------
# Bring the disk back online and hand over
# ---------------------------------------------------------------------------
Head 'Finishing'
try {
  Set-Disk -Number $DiskNumber -IsOffline $false
  Start-Sleep -Milliseconds 750
  Update-Disk -Number $DiskNumber -ErrorAction SilentlyContinue
  Say '  disk back online'
} catch {
  Warn "could not bring disk $DiskNumber back online: $($_.Exception.Message)"
  Say  '  The write itself succeeded. Unplugging and replugging the stick is enough.'
}

Say ''
Good 'Done.'
Say ''
Say 'Windows now sees a 256 MB FAT32 partition (CLARITYESP) and an ext4 partition it does'
Say 'not understand (CLARITYROOT). If Windows offers to format the second partition, say NO;'
Say 'that is the root filesystem and Windows simply cannot read ext4.'
Say ''
Say 'Eject the stick from the tray icon before unplugging it, then see'
Say 'docs/m4-real-hardware.md for the firmware settings the target laptop needs'
Say '(Secure Boot off, one-time boot menu, and what not to touch).'
Say ''
