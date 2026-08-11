# M2 — graphics stack: what to add, and the evidence for it

Target: the machine boots and displays `http://127.0.0.1:7000/` as a fullscreen rendering
surface with no browser chrome.

Everything below was verified by running Alpine 3.21 containers against the v3.21
main+community CDN repositories. Versions resolved on 2026-08-06 from index
`v3.21.7-186-g60f8d914baf`:

| Package | Version |
|---|---|
| `cage` | 0.2.0-r0 |
| `cog` | 0.18.3-r1 |
| `wpewebkit` | 2.40.5-r2 |
| `libwpebackend-fdo` | 1.14.2-r1 |
| `libwpe` | 1.14.2-r0 |
| `wlroots` (pulled by cage) | 0.18.1-r2 |
| `seatd` / `libseat` | 0.9.1-r0 |
| `eudev` | 3.2.14-r5 |
| `udev-init-scripts` / `-openrc` | 35-r1 |
| `mesa-dri-gallium` | 24.2.8-r0 |
| `font-dejavu` | 2.37-r5 |
| `bubblewrap` | 0.11.0-r0 |
| `xdg-dbus-proxy` | 0.1.6-r0 |

**Headline result: the whole stack was run end to end and screenshotted.** `cage` +
`cog -P wl` loaded `build/files/clarity-shell.py`'s page from `http://127.0.0.1:7000/` and
rendered it fullscreen, dark, with legible text and a focused input — captured with `grim`
at 1280x720. `cog` logged `<http://127.0.0.1:7000/> Loaded successfully.` This was on
wlroots' **headless** backend with the **pixman** renderer (Docker has no `/dev/dri`), which
is the same software-rendering path QEMU's virgl-less virtio-gpu forces — but see
[Unresolved](#unresolved--must-be-confirmed-on-the-first-real-boot) for what the headless
backend does *not* prove.

---

## 1. Package list

Add to `PKGS` in `build/build.sh` for `STAGE = m2` (all of these are explicit choices; every
other library arrives as a transitive dependency):

```sh
[ "$STAGE" = "m2" ] && PKGS+=(
  # device manager: wlroots enumerates DRM and input through libudev
  eudev eudev-openrc udev-init-scripts udev-init-scripts-openrc
  # seat/session management: mandatory, see 4
  seatd seatd-openrc
  # compositor + rendering engine
  cage cog
  # software GL for the virgl-less virtio-gpu
  mesa-dri-gallium
  # WPE WebKit will not render a single glyph without a font
  font-dejavu
  # WPE WebKit's web-process sandbox
  bubblewrap xdg-dbus-proxy
)
```

Measured closure, `apk --root` into a clean root with the m1 package list plus the above:

* **285 packages total**, of which **188 are new** relative to m1.
* Rootfs grows **240 MB → 770 MB** (measured with `du -sh`, `/var/cache/apk` emptied,
  excluding the model and the llama binaries).
* With the ~1.1 GB GGUF model and llama binaries that is **~1.9 GB**, so the existing
  `ROOT_MIB=6144` still fits comfortably. Add an `m2)` case to the `case "$STAGE"` block;
  6144 is sufficient, 8192 gives M3 headroom.

`cog` needs no separate platform-plugin package. `apk info -R cog` shows a direct
`so:libWPEBackend-fdo-1.0.so.1` dependency, so `libwpebackend-fdo` is pulled automatically,
and the platform plug-ins ship inside `cog` itself:

```
$ apk info -L cog
usr/bin/cog
usr/bin/cogctl
usr/lib/libcogcore.so.9
usr/lib/cog/modules/libcogplatform-drm.so
usr/lib/cog/modules/libcogplatform-headless.so
usr/lib/cog/modules/libcogplatform-wl.so
```

Notes on the transitive closure, so nothing below is a surprise:

* `xkeyboard-config` and `libxkbcommon` arrive with cage — no action needed (verified
  present in a `cog cage`-only root).
* `wpewebkit` drags in the GStreamer media stack (`gst-plugins-base`, `gst-plugins-bad`) and,
  through it, `gtk+3.0`, `librsvg`, `directfb`, `pango`, `libx11` and friends. Ugly, but they
  are hard dependencies of the Alpine packages; nothing here is optional without rebuilding
  wpewebkit.
* `dbus` (the daemon) arrives as a dependency of `xdg-dbus-proxy`; `dbus-openrc` comes with
  it. `at-spi2-core` and `dbus-libs` arrive with wpewebkit.
* `libelogind` arrives too. It is only the library — no elogind daemon — but it matters
  because libseat will *try* the logind backend. See section 4.
* `xwayland` is **not** needed. cage 0.2.0 is built with XWayland support and logs
  `Cannot find Xwayland binary "/usr/bin/Xwayland"` / `Cannot create XWayland server` at
  startup, but it **continues and works normally** — verified: the successful screenshot run
  produced exactly those two errors in cage's log. Do not install `xwayland` chasing them.

---

## 2. cog platform decision: `-P wl`

**Decision: `cog -P wl`.** There is no `fdo` platform plug-in in cog 0.18, and `wl` is the
correct choice when nested inside another Wayland compositor.

Evidence, from `cog` 0.18.3-r1 in a container:

```
$ cog -P fdo http://127.0.0.1:7000/
(cog): Cog-Core-WARNING **: Platform module name 'fdo' is deprecated, please use 'wl' instead.
```

`fdo` is accepted only as a deprecated alias that is rewritten to `wl` — and the module
listing above confirms only `drm`, `headless` and `wl` exist on disk. So:

* `-P fdo` — works, but only via a deprecation alias. Do not use.
* `-P drm` — cog would take the DRM device itself. That is the *alternative* to cage, not a
  companion to it: two DRM masters cannot coexist. Wrong for this design.
* `-P headless` — renders to no output at all.
* `-P wl` — connects to `$WAYLAND_DISPLAY`, i.e. cage. **Correct.**

`cog --help` in 0.18.3 confirms the flag spelling: `-P, --platform=NAME` and
`-O, --platform-params=PARAMS`. The binary is `/usr/bin/cog` (plus `cogctl`, unused here).
There is no `--kiosk` or `--fullscreen` flag and none is needed: cage fullscreens its single
client unconditionally.

Note the *auto-detection* failure mode, because it is misleading. If `XDG_RUNTIME_DIR` is
unset, cog cannot init the wl platform and then falls back to libwpe's default backend,
producing a red herring:

```
error: XDG_RUNTIME_DIR is invalid or not set in the environment.
Cog-Core-WARNING **: cog_modules_get_preferred: preferred module 'wl' not supported
Cog-WARNING **: Cannot create platform: Could not find a usable platform module
wpe: could not load the impl library. Is there any backend installed?:
     Error loading shared library libWPEBackend-default.so: No such file or directory
```

`libWPEBackend-default.so` genuinely does not exist in Alpine (`libwpebackend-fdo` ships
only `libWPEBackend-fdo-1.0.so{,.1,.1.9.4}`) — but installing something to provide it is not
the fix. The fix is `XDG_RUNTIME_DIR`. Once the wl platform initialises, that message
disappears.

---

## 3. mdev → udev

wlroots links `libudev.so.1` (from `eudev-libs`) and `libinput.so.10`, and eudev's libudev
resolves devices out of the database that **udevd** writes under `/run/udev`. Busybox `mdev`
does not populate it, so with mdev wlroots enumerates zero DRM devices and zero input
devices. `eudev` + `udevd` is required, not merely preferable.

The runlevel changes are taken verbatim from Alpine's own `/usr/sbin/setup-devd` (function
`enable_udev`, with `disable_mdev` above it), which is the authoritative source:

```sh
enable_udev () {
	apk add --quiet eudev udev-init-scripts udev-init-scripts-openrc
	rc-update add --quiet udev sysinit
	rc-update add --quiet udev-trigger sysinit
	rc-update add --quiet udev-settle sysinit
	rc-update add --quiet udev-postmount default
	...
}
disable_mdev () {
	rc-update delete --quiet --quiet hwdrivers sysinit || :
	rc-update delete --quiet --quiet mdev sysinit || :
}
```

Note that `hwdrivers` goes away **with** mdev. It is mdev's coldplug/modprobe helper;
`udev-trigger` does that job under udev.

### Diff against what `build/build.sh` does today

Today (line ~126):

```sh
for s in devfs dmesg mdev hwdrivers cgroups; do add_svc sysinit "$s"; done
for s in modules sysctl hostname bootmisc syslog networking; do add_svc boot "$s"; done
for s in mount-ro killprocs savecache;               do add_svc shutdown "$s"; done
```

For m2:

```
  sysinit:  devfs dmesg cgroups                    (unchanged)
          - mdev                                    REMOVE
          - hwdrivers                               REMOVE  (mdev's coldplug helper)
          + sysfs                                   ADD     (see below)
          + udev                                    ADD
          + udev-trigger                            ADD
          + udev-settle                             ADD
  boot:     modules sysctl hostname bootmisc syslog networking   (unchanged)
  default:  llama-server                            (unchanged)
          + udev-postmount                          ADD
          + clarity-shell                           ADD
          + clarity-ui                              ADD
  shutdown: mount-ro killprocs savecache            (unchanged)
```

Concretely:

```sh
-for s in devfs dmesg mdev hwdrivers cgroups; do add_svc sysinit "$s"; done
+if [ "$STAGE" = "m2" ]; then
+  for s in devfs sysfs dmesg cgroups udev udev-trigger udev-settle; do add_svc sysinit "$s"; done
+else
+  for s in devfs dmesg mdev hwdrivers cgroups; do add_svc sysinit "$s"; done
+fi
```

`sysfs` is an addition beyond what `setup-devd` does, because `build.sh` builds its
runlevels from scratch rather than inheriting Alpine's defaults, and `/etc/init.d/udev`
declares `depend() { need sysfs dev-mount; ... }`. `devfs` provides `dev-mount`; nothing in
the current sysinit list provides `sysfs`. OpenRC would probably pull it in on demand, but
relying on that is a fragile way to boot a display.

Package split gotcha, worth stating because it will otherwise cost a build cycle:

```
$ apk info -L udev-init-scripts        # 35-r1
udev-init-scripts-35-r1 contains:      <- nothing. Zero files.
$ apk info -L udev-init-scripts-openrc
etc/init.d/udev  etc/init.d/udev-settle  etc/init.d/udev-trigger  (+ conf.d)
$ apk info -L eudev-openrc
etc/init.d/udev-postmount
```

`eudev` depends on `udev-init-scripts`, which is an empty meta-package. **The init scripts
only exist if you install `udev-init-scripts-openrc`, and `udev-postmount` only exists if you
install `eudev-openrc`.** `build.sh`'s `add_svc` silently skips missing init scripts
(`step "(skip: no init script for $2)"`), so getting this wrong produces a boot that looks
clean and has no udev.

Kernel side is already fine (checked `/boot/config-6.12.98-0-lts` from `linux-lts`):
`CONFIG_DEVTMPFS=y`, `CONFIG_DEVTMPFS_MOUNT=y`, `CONFIG_DRM_VIRTIO_GPU=m`,
`CONFIG_INPUT_EVDEV=m`, `CONFIG_DRM_FBDEV_EMULATION=y`, `CONFIG_VT=y`, `CONFIG_USER_NS=y`.
`virtio-gpu.ko` is already in the initramfs (`mkinitfs` feature `virtio` includes
`kernel/drivers/gpu/drm/virtio`, and `kms` includes all of `kernel/drivers/gpu`), which
matches the `[drm] features: -virgl` line already in the boot log. `evdev.ko` is *not* in
the initramfs — it is coldplugged by `udev-trigger`, which is exactly why udev is needed.

---

## 4. seatd is mandatory, not optional

`libseat.so.1` in Alpine 3.21 is built with the **seatd, logind and noop** backends only:

```
$ strings /usr/lib/libseat.so.1 | grep backend/
../libseat/backend/logind.c
../libseat/backend/noop.c
../libseat/backend/seatd.c
```

There is no `builtin.c`. The builtin backend is the one that lets a root process do its own
DRM/VT management without a daemon — **it is not compiled in**, so "just run cage as root" is
not an option on this image. `seatd` must be running.

From `libseat/libseat.c` (0.9.1 source), backends are tried in order **seatd → logind →
noop**, so seatd wins by default. The `LIBSEAT_BACKEND=seatd` in `clarity-ui.initd` is
belt-and-braces: `libelogind.so.0` is present on this image and the `noop` backend
"succeeds" while providing no device access, which would present as a black screen with no
useful error. Naming the backend makes a failure loud.

Service: `seatd-openrc` provides `/etc/init.d/seatd`, which runs `seatd -g seat`. The `seat`
group is created by the `seatd` package itself (verified: `seat:x:102:` appears in
`/etc/group` of a fresh root that has seatd installed). cage runs as root, so group
membership is moot. Put `seatd` in the **`default`** runlevel — or rely on
`need seatd` from `clarity-ui`; adding it explicitly is clearer.

---

## 5. Required runtime environment

All set in `build/files/clarity-ui.initd`.

| Variable | Value | Why |
|---|---|---|
| `XDG_RUNTIME_DIR` | `/run/user/0` | **Mandatory.** cog aborts: `error: XDG_RUNTIME_DIR is invalid or not set in the environment.` Nothing else creates it (no elogind, no PAM) — the init script does, mode 0700. |
| `HOME` | `/root` | fontconfig and WebKit caches. |
| `XDG_SESSION_TYPE` | `wayland` | Hygiene; not observed to be load-bearing. |
| `LIBSEAT_BACKEND` | `seatd` | See section 4. |
| `WLR_RENDERER` | `pixman` | No hardware GL under QEMU. pixman is wlroots' CPU compositor: DRM dumb buffers, no EGL in the compositor at all. Verified as an accepted value — `strings libwlroots-0.18.so` yields exactly `auto`, `gles2`, `vulkan`, `pixman`, and `wlr_pixman_renderer_create` is present. This is the renderer the successful screenshot run used. |
| `WLR_RENDERER_ALLOW_SOFTWARE` | `1` | Inert with pixman; required if anyone switches to `gles2`/`auto`, where wlroots otherwise refuses: `Software rendering detected, please use the WLR_RENDERER_ALLOW_SOFTWARE environment variable to proceed`. |
| `LIBGL_ALWAYS_SOFTWARE` | `1` | cog's web process needs EGL regardless of the compositor's renderer. Forces Mesa to llvmpipe/`kms_swrast` rather than hunting for a hardware driver on the virtio-gpu node. Part of the verified working configuration. |

`mesa-dri-gallium` is the package that supplies the software path: it ships
`swrast_dri.so` and `kms_swrast_dri.so` (plus `virtio_gpu_dri.so`, which is inert without
virgl). `mesa-egl`, `mesa-gbm`, `mesa-gl`, `mesa-gles` and `llvm19-libs` come in
transitively.

**Do not set these in production** — they are headless-test-only and were used only because
Docker has no `/dev/dri`:

* `WLR_BACKENDS=headless` — leave unset so wlroots selects the DRM backend.
* `WLR_LIBINPUT_NO_DEVICES=1` — leave unset; you want real input devices.

### The bubblewrap sandbox

WPE WebKit 2.40.5 hard-codes `/usr/bin/bwrap` and `/usr/bin/xdg-dbus-proxy` (both appear as
literal strings in `libWPEWebKit-2.0.so.1`) and **aborts** if bwrap is absent:

```
** (cog): ERROR **: Failed to start dbus proxy: Failed to spawn child process
                    */usr/bin/bwrap* (No such file or directory)
```

Hence `bubblewrap` and `xdg-dbus-proxy` in the package list. `WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS`
also exists in the library and does work (the successful screenshot run used it, because
Docker blocks user namespaces); `clarity-ui.initd` exposes it as `clarity_sandbox=no` in
`/etc/conf.d/clarity-ui` and warns when used. Default is sandbox **on**.

`Could not determine the accessibility bus address` is printed on every start and is
harmless — it appeared in the run that rendered correctly.

---

## 6. VT ownership and the tty1 getty

`cage` 0.2.0 has **no option to select a VT**. Its complete option set is:

```
 -d	 Don't draw client side decorations, when possible
 -h	 Display this help message
 -m extend / -m last	 output layout
 -s	 Allow VT switching
 -v	 Show the version number and exit
```

The VT is chosen by **seatd**, not by cage, and seatd picks whichever VT is *currently
active* — from `seatd/seat.c` 0.9.1:

```c
static void seat_update_vt(struct seat *seat) {
	int tty0fd = terminal_open(0);          /* /dev/tty0 */
	seat->cur_vt = terminal_current_vt(tty0fd);   /* ioctl VT_GETSTATE -> st.v_active */
}
...
	client->session = seat->cur_vt;
```

It is *not* derived from the client's controlling terminal, which matters because an OpenRC
service has none. On activation seatd then does `terminal_set_keyboard(ttyfd, false)` (K_OFF)
and `terminal_set_graphics(ttyfd, true)` (KD_GRAPHICS) on that VT.

Consequences and the chosen approach:

* Left alone, cage lands on **VT 1** — the same VT as `build.sh`'s
  `tty1::respawn:/sbin/getty --noclear -n -l /bin/login 38400 tty1`. seatd's K_OFF/KD_GRAPHICS
  means the getty cannot actually paint or steal keystrokes while cage is active, so this is
  survivable — but it is a shared-resource race with nothing gained.
* `clarity-ui.initd` therefore runs `chvt 2` in `start_pre` before launching cage, so seatd
  binds cage to **VT 2**. `chvt` is a busybox applet, present in the image. This *keeps* tty1
  usable for debugging: with cage's `-s` not passed, VT switching from the UI is disabled,
  but `chvt 1` over the serial console still gets you the login prompt.
* `stop_post` does `chvt 1` so a failed UI leaves a usable console.
* Recommended `build.sh` change: keep the tty1 getty (it is now on a different VT than the
  UI) and optionally add a `tty2` getty **only if** `clarity_vt` is changed away from 2.
  Do not put a getty on whatever VT `clarity_vt` names.

Kernel messages: `console=tty0 console=ttyS0,115200` already makes `/dev/console` the serial
port (last `console=` wins), and printk to the framebuffer console is suppressed while cage
holds KD_GRAPHICS. No change needed.

---

## 7. Fonts

**A font package is mandatory.** Installing `cog cage` alone yields `fontconfig`, `freetype`,
`harfbuzz` and `harfbuzz-icu` but **zero font files** (`find /usr/share/fonts -type f`
returns nothing). Verified by moving `/usr/share/fonts` aside and re-running the exact
configuration that had just rendered correctly: cog never even reached `Load started` — its
log stopped after the Wayland output warning, and the screenshot was byte-for-byte the size
of a blank frame.

`font-dejavu` (2.37-r5) is sufficient — it is what the successful screenshots used, and
`clarity-shell.py`'s CSS already names `"DejaVu Sans"` and `"DejaVu Sans Mono"`. Add
`font-dejavu-sans-mono-nerd` or a CJK font only if the generated surfaces need them.

---

## 8. Service wiring summary

New files (this change adds only these two init scripts; `build.sh` must install them and
`add_svc default`):

* `build/files/clarity-shell.initd` — `need localmount llama-server`; runs
  `/opt/clarity/bin/clarity-shell`, `command_background=true`, log to
  `/var/log/clarity-shell.log`.
* `build/files/clarity-ui.initd` — `need localmount seatd udev clarity-shell`,
  `after llama-server modules`, `use dbus`; runs
  `cage -d -- cog -P wl --bg-color=#0d1117 http://127.0.0.1:7000/`.

`clarity-ui`'s `start_pre` polls `http://127.0.0.1:7000/health` (up to 90 s) before starting
cage. This is not belt-and-braces: **cog fetches its URL exactly once and does not retry**,
so starting it before clarity-shell is listening leaves a permanent WebKit error page on the
screen. `need clarity-shell` is not sufficient on its own, because OpenRC considers a
`command_background=true` service started as soon as `start-stop-daemon` returns.

Both scripts syntax-check clean under busybox `ash` (`sh -n`), and `chvt`, `wget`, `sleep`
and `checkpath` were all confirmed resolvable on the PATH that `openrc-run` sets
(`/usr/libexec/rc/bin:/bin:/sbin:/usr/bin:/usr/sbin` — note `checkpath` lives at
`/usr/libexec/rc/bin/checkpath`, not `/sbin`). `checkpath` does not create missing parent
directories, which is why `/run/user` is created before `/run/user/0`.

---

## Unresolved — must be confirmed on the first real boot

These are the things I could **not** verify in Docker. Each is a plausible first-boot
failure; none is a guess dressed up as a fact.

1. **The DRM backend itself.** Docker has no `/dev/dri`, so every successful run used
   `WLR_BACKENDS=headless`. That proves cage↔cog↔wpewebkit↔fontconfig↔pixman, but it does
   **not** prove wlroots can mode-set on QEMU's virtio-gpu, nor that the pixman renderer can
   allocate DRM dumb buffers on that device. With `WLR_RENDERER` unset and no DRM device,
   wlroots logged `drmGetDevices2 failed: No such file or directory` — on real hardware that
   error should not appear. If the DRM+pixman combination fails, the documented fallback is
   `WLR_RENDERER=gles2` (with `WLR_RENDERER_ALLOW_SOFTWARE=1` and `LIBGL_ALWAYS_SOFTWARE=1`,
   both already set), which routes through GBM + `kms_swrast_dri.so`.

2. **Whether the WPE bubblewrap sandbox works on the target.** Docker Desktop's WSL2 kernel
   refuses user namespaces (`bwrap: Creating new namespace failed: Operation not permitted`,
   and even `docker exec --privileged` gave `likely because the kernel does not allow
   non-privileged user namespaces`), so the sandbox path is untested. `CONFIG_USER_NS=y` in
   Alpine's `linux-lts` 6.12.98, and cog runs as root with full capabilities, so it should
   work — but "should" is the operative word. **If the UI comes up blank with
   `bwrap: Creating new namespace failed` in `/var/log/clarity-ui.log`, set
   `clarity_sandbox=no` in `/etc/conf.d/clarity-ui`** — that exact configuration is verified
   to render.

3. **Whether `chvt 2` behaves as intended at boot.** The seatd source proves *which* VT gets
   bound (the active one) and `chvt` is present, but VT switching cannot be exercised in a
   container. If cage ends up on VT 1 anyway, the fallback is to delete the tty1 getty line
   from the generated `/etc/inittab` and accept VT 1 for the UI.

4. **Input.** No input devices existed in the container (`WLR_LIBINPUT_NO_DEVICES=1` was set
   throughout), so keyboard and pointer are entirely unverified. This depends on
   `udev-trigger` coldplugging `evdev.ko` and on `libinput-udev`'s rules (that package is
   pulled in transitively). This is the single most likely thing to be silently broken —
   check `udevadm info /dev/input/event0` and cage's log on first boot.

5. **`-P wl` vs. letting cog auto-detect.** `-P wl` is verified working. Auto-detection under
   a live cage was not tested; the explicit flag is used precisely so it does not matter.

6. **Whether `dbus` needs its own runlevel entry.** `dbus-openrc` is installed, and
   `clarity-ui` declares `use dbus` (soft), but the a11y-bus warning is benign and the
   sandbox's dbus proxy is spawned by WebKit rather than requiring a system bus. Not adding
   `dbus` to a runlevel; revisit only if the sandbox complains about the bus specifically
   rather than about bwrap.

7. **Cursor and output naming.** Untested: whether a visible cursor appears, what resolution
   QEMU's virtio-gpu advertises, and whether cage's `-m extend` default does anything
   surprising with a single output.
