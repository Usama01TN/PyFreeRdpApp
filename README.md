# PyFreeRdpApp

<p align="center">
  <img src="assets/banner.png" alt="PyFreeRdpApp - remote desktop for Python: FreeRDP 3 underneath, Qt on top." width="100%">
</p>

A high-level RDP client for Python, built on
[pyfreerdpnative](https://github.com/Usama01TN/PyFreeRdpNative) (FreeRDP 3).
It wraps the low-level ctypes bindings in a small, task-oriented
`RDPApplication` class and an optional Qt widget.

![screenshot](screenshot.png)

## Install:

```bash
pip install pyfreerdpnative --find-links https://github.com/Usama01TN/PyFreeRdpNative/releases/expanded_assets/freerdp-libs-3.32.2
pip install .            # this package
pip install numpy pillow # getDisplay() as an array / image
pip install ManyQt       # optional, for the GUI
```

## Usage:

```python
from PyFreeRdpApp.keyboard import LEFT_CONTROL, KEY_A
from PyFreeRdpApp import RDPApplication, keyboard

app = RDPApplication()  # type: RDPApplication
app.setServer('10.0.0.5')
app.setUsername('alice')
app.setPassword('secret')
app.setDisplaySize(1280, 800)
app.start()
# Wait until ready, then drive it.
while not app.isReady:
    pass
app.typeText('Hello')
app.hotkey(LEFT_CONTROL, KEY_A)     # Ctrl+A
frame = app.getDisplay()                              # numpy (h, w, bpp/8), BGR(A)
app.stop()
```

A window, if a Qt binding is installed:

```bash
python -m PyFreeRdpApp                       # asks for everything in a dialog
python -m PyFreeRdpApp 10.0.0.5 alice        # asks only for the password
python -m PyFreeRdpApp 10.0.0.5 alice secret --size 1920x1080 --share ~/Documents=Docs
python -m PyFreeRdpApp 10.0.0.5 alice secret --screenshot desk.png
```

Anything missing from the command line is asked for: in a dialog with Qt, on
the terminal without it (the password without echo). Without Qt, or with
`--screenshot`, it saves one frame and exits. `--help` lists every option.

### The window (`RDPWidget`):

Mouse, wheel and keyboard go to the remote machine (Tab included). The
clipboard works both ways: copy text on either side and paste on the other;
copy files in your file manager - or drag them onto the window - and paste
them remotely (when the server allows file transfer). Files copied remotely
are saved with **Shift + right-click → Download remote clipboard files...** or
`RDPWidget.downloadRemoteFiles(dir)`; a plain right-click goes to the remote
machine. The cursor follows the remote one (I-beam over text, resize arrows,
hidden in video players...). **Shift + right-click → Share a local folder...**
redirects a folder as a drive and reconnects.

## API:

`RDPApplication` behaviour on FreeRDP 3 (see `__init__.pyi` for the full signatures):

- **connection:** `setServer`, `setPort`, `setUsername`, `setPassword`,
  `setDomain`, `setDisplaySize`, `setBitsPerPixel` (16/24/32),
  `setAutoReconnect`, `setGraphics` (passed to FreeRDP as `/gfx:<option>`),
  `setFreerdpCliArgs` (parsed by FreeRDP's own command-line parser)
- **lifecycle:** `setPaused`, `start` (blocks until ready; raises `ConnectionError` on
  failure), `stop`; properties `isRunning`, `isReady`, `isReconnecting`, `isPaused`
- **keyboard:** `keyDown`, `keyUp`, `hotkey`, `typeText` - scancodes from the
  `keyboard` module. `typeText` sends space, newline, backspace and tab as real
  keys and everything else as Unicode (non-BMP characters as surrogate pairs)
- **mouse:** `mouseMove`, `{left,right,middle}Mouse{Down,Up}`, `mouseScroll`
- **screen:** `getDisplay(displayFormat=None)` returns the screen as
  `numpy` (array `(height, width, bpp/8)` of BGR(A) pixels, ready for OpenCV),
  `pillow` (RGB/RGBA image), `qimage`, `bytes` (packed BGR(A)) or `tuple`
  `(width, height, channels, bytes)`; `setDisplayFormat` changes the default
  (`numpy`)
- **clipboard listener:** `setClipboardListener(fn)` is told when the remote
  clipboard changes
- **clipboard:** `saveClipboard` / `loadClipboard` in `text` mode
  (`CF_UNICODETEXT`) and `file` mode (`FileGroupDescriptorW` + file contents
  streams, with `includeParent` and `filePattern`); `isFileClipboardEnabled`,
  `isFileTransferFinished`
- **folders:** `loadSharedDirectory` redirects a local folder as a drive
  ("Shared on <client>" in the remote Explorer); a file path shares its
  folder; several folders allowed; call before `start` (or restart);
  `getSharedDirectories` lists them. Only the folders you share are exposed -
  never the whole disk
- **pointer:** `setPointerListener(fn)` reports the remote cursor shape
  (`set` with BGRA pixels and hotspot, `hidden`, `default`, `position`)

Every input event is queued and sent from the RDP session thread, never from
the caller's thread - FreeRDP's transport is not safe for concurrent writes.
Methods raise `ConnectionError` when the session is not connected (`hotkey`
raises `RuntimeError`, as documented in the stub).

## The widget: `PyFreeRdpApp.rdpwidget`

`RDPWidget` is configurable entirely through Qt properties (getter, `@pyqtSlot`
setter and `pyqtProperty` for each): `server`, `port`, `username`, `password`,
`domain`, `displayWidth`, `displayHeight`, `bitsPerPixel`, `graphics`, `sound`,
`microphone`, `compressedAudio`, `autoReconnect`, `sharedDirectories`,
`freerdpCliArgs`, `fps`, `syncClipboard`, `autoConnect`, plus the read-only
`ready` and `running`. Every `RDPWidget` includes its `RDPApplication`: one is
created with the widget (`getApplication()` returns it), and the properties are
written straight through to it. Pass your own (`RDPWidget(app)`) to reuse a
session; the widget then mirrors its configuration.

```python
from PyFreeRdpApp.rdpwidget import RDPWidget

view = RDPWidget(server=u'10.0.0.5', username=u'alice', password=u'secret', autoConnect=True,
                 connected=lambda: print(u'connected'), screenshotSaved=print)
view.show()
view.takeScreenshot(u'desk.png')       # or with no path: asks for one
print(view.getSessionInfo())             # status, connection and session information
```

Signals: `connected`, `disconnected`, `connectionFailed(str)`, `sessionRestarted(bool)`,
`remoteClipboardChanged(dict)`, `filesDownloaded(str)`, `clipboardError(str)`,
`screenshotSaved(str)`. Demo: `python PyFreeRdpApp/rdpwidget/main.py`.

### Clipboard, drag & drop, disconnections:

* **Drag & drop** files or folders onto the widget, or use **Send
  clipboard**: they go on the remote clipboard - paste them in the remote
  session (Ctrl+V). A drop is always a *copy* (the sources stay where they
  are). The status bar says what was sent; a message says why nothing could
  be (not connected, empty clipboard, or a server whose policy disables file
  transfer - text still works there). Signals: `clipboardSent(str)`,
  `clipboardError(str)`; method: `sendFiles(paths)`.
* **Disconnections**: when the session ends without you asking, or a
  connection fails, a dialog shows the cause as FreeRDP reports it - the
  server's reason (logged off, idle timeout, disconnected by an
  administrator, ...) or FreeRDP's error - with **Reconnect** and **Cancel**
  (details under *Show Details*). `RDPApplication.getDisconnectReason()`,
  `setDisconnectListener(fn)`, `RDPWidget.connectionLost(dict)` and
  `rdpwidget.DisconnectDialog` expose the same information.

### Icon and banner:

The icon ships in `PyFreeRdpApp/rdpwidget/images/` (PNG 16-512 px, SVG, ICO for Windows, ICNS for
macOS); `PyFreeRdpApp.rdpwidget.appIcon()` returns it as a `QIcon` with every size. The window,
its dialogs and the Qt Designer plugin use it. The banner is in `assets/` (`banner.png` 1280x640 -
GitHub's social preview size - `banner@2x.png` and `banner.svg`). Both are generated by
`python tools/make_artwork.py`.

### Releasing

Pushing a tag `vX.Y.Z` tests, builds and publishes a release (PyPI or TestPyPI, and a GitHub
Release) - see [docs/RELEASING.md](docs/RELEASING.md) for the one-time setup and the steps.

### Qt Designer:

* **PyQt5 / PyQt6** (`pyqt5-tools designer`): set `PYQTDESIGNERPATH` to the
  `PyFreeRdpApp/rdpwidget` folder and make `PyFreeRdpApp` importable
  (`PYTHONPATH`). `RDPWidget` appears in the *PyFreeRdpApp* group; every
  connection option is editable in the property editor. `pyuic5` generates
  `from PyFreeRdpApp.rdpwidget import RDPWidget`.
* **PySide6** (`pyside6-designer`): set `PYSIDE_DESIGNER_PLUGINS` to the same
  folder; `register_rdpwidget.py` registers the widget.

Inside Designer the widget never connects (it shows its configuration); the
session starts at run time with `connectToServer()` or `autoConnect`.

### Screenshot and session report in the console

`--screenshot` and `--info` run in the console only - no window, no dialog
(missing credentials are asked in the terminal) - and they combine:

```bash
python -m PyFreeRdpApp 10.0.0.5 alice secret --screenshot desk.png         # screenshot only
python -m PyFreeRdpApp 10.0.0.5 alice secret --info                        # status/connection/info only
python -m PyFreeRdpApp 10.0.0.5 alice secret --screenshot desk.png --info  # both
python -m PyFreeRdpApp 10.0.0.5 alice secret --info --json                 # stdout is pure JSON
```

Exit codes: 0 ok, 1 cancelled, 2 connection failed (the report still prints
with `--info`), 3 screenshot failed.

The report (console, JSON and the window's **Session info...**) also shows
what FreeRDP received from the server while connecting
(`RDPApplication.getServerInfo()`) - no extra connection is made:

* **Remote computer** - Windows version and build (e.g. *Windows Server 2022,
  10.0.20348*), NetBIOS/DNS computer and domain names, forest, server time:
  from the NTLM challenge of FreeRDP's own NLA exchange (servers using NLA).
* **Logon** - the logged-on user (domain\\user) and session ID, from the
  server's Save Session Info.
* **Connection security** - the negotiated RDP version (e.g. 10.12) and
  security protocol, from FreeRDP's settings.
* **Certificate** - the certificate FreeRDP verified (VerifyX509Certificate),
  decoded by FreeRDP's own certificate API: subject, issuer (self-signed or
  not), validity with the time left, signature algorithm, key type,
  alternative names, SHA-256 and SHA-1 fingerprints, PEM. No temporary files.

The window has **Screenshot...** and **Session info...** in its toolbar.

### Performance:

Frames are published by the RDP thread at the end of each paint: only the
rows the server changed are copied (one `memmove`), and viewers take just the
changed rectangle - typically a few KB instead of the whole screen. Input
wakes the session thread at once (sub-millisecond latency) instead of waiting
for the next poll. The Graphics Pipeline (`/gfx`, H.264 on the media
editions) is on by default; `setGraphics("off")` returns to legacy updates.

### Sound:

The remote sound plays locally by default (`setSound(False)` to mute,
`setSound(True, microphone=True)` to redirect the microphone as well), using
the platform's audio backend.

### Troubleshooting:

* **The program exits with 0xC0000005 / a segmentation fault.** On the next
  start (Windows) the app reads what Windows recorded about the crash - the
  faulting DLL, offset and exception code - logs it, and shows it once.
  Python-level stacks of every thread also go to stderr and to
  `pyfreerdpapp-crash.log` (with `--log DIR`).
* **Audio bandwidth.** `--pcm-audio` (`setSound(True, compressed=False)`)
  keeps the audio uncompressed - no audio decoder involved.
* **Clipboard files do not download.** The status bar says whether the server
  allows file transfer ("Clipboard: text + files"); Windows hosts can block it
  by policy while text still works. Every download step is logged
  (`PyFreeRdpApp.clipboard`), and the window reports the exact reason.
* **Black or frozen screen with the Graphics Pipeline.** Use `--gfx off`
  (`setGraphics("off")`) to fall back to legacy updates.

## Support:

If PyFreeRdpApp is useful to you, feel free to support its development:

<p>
  <a href="https://ba9chich.com/fr/IninouUsama"><img src="https://img.shields.io/badge/ba9chich-Support%20me-E4002B?style=for-the-badge" alt="Support me on ba9chich"></a>
  <a href="https://ko-fi.com/usamatn"><img src="https://img.shields.io/badge/Ko--fi-Buy%20me%20a%20coffee-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white" alt="Buy me a coffee on Ko-fi"></a>
</p>

- **ba9chich:** [ba9chich.com/fr/IninouUsama](https://ba9chich.com/fr/IninouUsama)
- **Ko-fi:** [ko-fi.com/usamatn](https://ko-fi.com/usamatn)

Thank you :)

## License:

Apache-2.0. FreeRDP is Apache-2.0.
