# -*- coding: utf-8 -*-
"""
RDPWidget: a QWidget that shows a remote desktop (RDPApplication) and drives it.
Features:
  * real-time display: only the rectangle the server changed is copied and repainted;
  * mouse, wheel and keyboard forwarding (Tab included), remote cursor shapes;
  * two-way clipboard: text automatically, files from the file manager or by drag & drop,
    remote files with downloadRemoteFiles();
  * shared folders redirected as drives (shareFolder());
  * screenshots (takeScreenshot()) and session information (getSessionInfo());
  * every connection option is a Qt property, so the widget is configurable in Qt Designer
    (see rdpwidgetplugin.py) without connecting there.
"""
from ManyQt.QtCore import Qt, QTimer, QSize, QRectF, pyqtSignal, pyqtSlot, pyqtProperty
from ManyQt.QtGui import QCursor, QIcon, QImage, QPainter, QPixmap, QColor, QFont
from ManyQt.QtWidgets import QApplication, QFileDialog, QMenu, QWidget
from os.path import join, exists, dirname, basename, normpath
from sys import platform, path
from logging import getLogger
from threading import Thread
from os import walk

if dirname(dirname(dirname(__file__))) not in path:
    path.append(dirname(dirname(dirname(__file__))))

try:
    from .._pyfreerdp import RDPApplication
except:
    from PyFreeRdpApp._pyfreerdp import RDPApplication

_log = getLogger(u'PyFreeRdpApp.widget')
GRAPHICS_OPTIONS = (u'auto', u'AVC444', u'AVC420', u'progressive', u'RFX', u'off')  # type: tuple
BACKGROUND = QColor(u'#101418')  # type: QColor
FOREGROUND = QColor(u'#9AA4AE')  # type: QColor


def frameToQimage(frame):
    """
    RDPApplication.getDisplay() -> QImage.
    getDisplay() returns a NumPy array (height, width, bpp/8) of BGR(A) pixels;
    without NumPy a (width, height, channels, bytes) tuple. Both are accepted here.
    :param frame: (numpy.ndarray | tuple | None) The frame.
    :return: QImage | None
    """
    if frame is None:
        return None
    if isinstance(frame, tuple):
        width, height, channels, data = frame
        stride = len(data) // height if height else 0  # type: int
    else:
        height, width, channels = frame.shape
        data = frame.tobytes()  # type: bytes
        stride = width * channels  # type: int
    if channels == 4:
        fmt = QImage.Format_ARGB32  # BGRA in memory == ARGB32 on little-endian.
    elif channels == 3:
        fmt = getattr(QImage, u'Format_BGR888', None)
        if fmt is None:  # Qt < 5.14: RGB888 + swap.
            return QImage(data, width, height, stride, QImage.Format_RGB888).rgbSwapped()
    else:
        # FreeRDP's BGR16 has blue in the high bits; Qt's RGB16 expects red there.
        return QImage(data, width, height, stride, QImage.Format_RGB16).rgbSwapped()
    return QImage(data, width, height, stride, fmt).copy()


def nativeToScancode(api, nativeScancode, nativeVirtualKey):
    """
    A Qt key event's native codes -> RDP scancode (0x100 = extended), or None.
    Windows reports hardware scancodes; Linux reports evdev + 8 (X11 and Wayland alike);
    macOS reports Carbon virtual keys. WinPR maps the last two.
    :param api: (pyfreerdpnative.FreeRDP) The loaded FreeRDP API.
    :param nativeScancode: (int) QKeyEvent.nativeScanCode().
    :param nativeVirtualKey: (int) QKeyEvent.nativeVirtualKey().
    :return: int | None
    """
    if platform == u'win32':
        code = nativeScancode & 0xFF  # type: int
        if not code:
            return None
        return code | (0x100 if nativeScancode & 0x100 else 0)
    from pyfreerdpnative.winpr.input import WINPR_KBD_TYPE_IBM_ENHANCED, WINPR_KEYCODE_TYPE_APPLE, \
        WINPR_KEYCODE_TYPE_EVDEV
    if platform == u'darwin':
        vk = api.GetVirtualKeyCodeFromKeycode(nativeVirtualKey, WINPR_KEYCODE_TYPE_APPLE)  # type: int
    else:
        if nativeScancode <= 8:
            return None
        vk = api.GetVirtualKeyCodeFromKeycode(nativeScancode - 8, WINPR_KEYCODE_TYPE_EVDEV)  # type: int
    if not vk:
        return None
    return api.GetVirtualScanCodeFromVirtualKeyCode(vk, WINPR_KBD_TYPE_IBM_ENHANCED) or None


# Properties the widget and its RDPApplication share 1:1: (name, getter prefix). Both sides have
# <prefix><Name>() and set<Name>(), so one table drives both directions (see _readFrom / _applyTo).
MIRRORED = ((u'Server', u'get'), (u'Port', u'get'), (u'Username', u'get'), (u'Password', u'get'), (u'Domain', u'get'),
            (u'BitsPerPixel', u'get'), (u'Graphics', u'get'), (u'AutoReconnect', u'is'), (u'Paused', u'is')
            )  # type: tuple
IMAGES = join(dirname(__file__), u'images')  # type: str
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512)  # type: tuple


def appIcon():
    """
    The PyFreeRdpApp icon, with every size drawn for it (Qt picks the sharpest one for each place:
    title bar, taskbar, Qt Designer's widget box, ...).
    :return: QIcon
    """
    icon = QIcon()  # type: QIcon
    for size in ICON_SIZES:
        icon.addFile(join(IMAGES, u'pyfreerdpapp-{}.png'.format(size)), QSize(size, size))
    return icon


def qtExec(obj, *args):
    """
    exec_() (Qt 4/5) or exec() (Qt 6), whichever the binding has.
    :param obj: (QApplication | QDialog | QMenu) The object to run.
    :param args: any
    :return: any
    """
    return obj.exec_(*args) if hasattr(obj, u'exec_') else obj.exec(*args)


def localPaths(mimeData):
    """
    The existing local files and folders in a clipboard or drag & drop QMimeData.
    :param mimeData: QMimeData | None
    :return: list[str | unicode | QString] | QStringList
    """
    if mimeData is None or not mimeData.hasUrls():
        return []
    paths = [url.toLocalFile() for url in mimeData.urls() if url.isLocalFile()]  # type: list
    return [p for p in paths if p and exists(p)]


def snapshotTree(pth):
    """
    The set of files under path (to report what a download actually wrote).
    :param pth: (str | unicode | QString) A directory.
    :return: set
    """
    found = set()  # type: set
    for root, _dirs, files in walk(pth or u'.'):
        for name in files:
            found.add(join(root, name))
    return found


class RDPWidget(QWidget):
    """
    RDPWidget class: shows an RDPApplication session and forwards input, clipboard and folders.
    Every RDPWidget includes its RDPApplication: one is created with the widget (or pass your own:
    RDPWidget(app) / app=...). The widget's properties are written straight through to it, so the
    session always reflects the widget; call connectToServer() (or set autoConnect) to connect.
    Shift + right-click opens the session menu (a plain right-click goes to the remote machine).
    """
    # Session.
    connected = pyqtSignal()  # type: pyqtSignal
    disconnected = pyqtSignal()  # type: pyqtSignal
    connectionFailed = pyqtSignal(u'QString')  # type: pyqtSignal
    sessionRestarted = pyqtSignal(bool)  # type: pyqtSignal
    # Clipboard.
    remoteClipboardChanged = pyqtSignal(dict)  # type: pyqtSignal
    filesDownloaded = pyqtSignal(u'QString')  # type: pyqtSignal
    clipboardError = pyqtSignal(u'QString')  # type: pyqtSignal
    # Screenshots.
    screenshotSaved = pyqtSignal(u'QString')  # type: pyqtSignal
    # What was put on the remote clipboard, e.g. u'2 files - paste them in the remote session (Ctrl+V)'.
    clipboardSent = pyqtSignal(u'QString')  # type: pyqtSignal
    # The session ended, or a connection failed, without disconnectFromServer(): FreeRDP's reason
    # (RDPApplication.getDisconnectReason()).
    connectionLost = pyqtSignal(dict)  # type: pyqtSignal
    # Internal: hops from the RDP / worker threads to the GUI thread.
    _remoteText = pyqtSignal(u'QString')  # type: pyqtSignal
    _pointer = pyqtSignal(u'QString', object)  # type: pyqtSignal
    _startFinished = pyqtSignal(bool, u'QString')  # type: pyqtSignal
    _stopFinished = pyqtSignal()  # type: pyqtSignal
    _lost = pyqtSignal(dict)  # type: pyqtSignal

    def __init__(self, *args, **kwargs):
        """
        :param app: (RDPApplication | None) An existing session; may also be the first positional argument.
        :param server: (str | unicode | QString) Hostname or IP address.
        :param port: (int) Port, 3389 by default.
        :param username: (str | unicode | QString) Username, without the domain.
        :param password: (str | unicode | QString) Password.
        :param domain: (str | unicode | QString) Domain.
        :param displayWidth: (int) Remote desktop width.
        :param displayHeight: (int) Remote desktop height.
        :param bitsPerPixel: (int) 32, 24 or 16.
        :param graphics: (str | unicode | QString) One of GRAPHICS_OPTIONS.
        :param sound: (bool) Play the remote sound locally.
        :param microphone: (bool) Redirect the local microphone.
        :param compressedAudio: (bool) Allow compressed audio formats.
        :param autoReconnect: (bool) Reconnect automatically after a network failure.
        :param sharedDirectories: (list[str | unicode | QString] | QStringList) Local folders redirected as drives.
        :param freerdpCliArgs: (str | unicode | QString) Extra FreeRDP command line arguments.
        :param fps: (int) Display refresh rate.
        :param syncClipboard: (bool) Synchronize the clipboards.
        :param autoConnect: (bool) Connect when the widget is first shown.
        :param designMode: (bool) Created by Qt Designer: never connects, paints a placeholder.
        :param connected: callable | None
        :param disconnected: callable | None
        :param connectionFailed: callable | None
        :param filesDownloaded: callable | None
        :param clipboardError: callable | None
        :param screenshotSaved: callable | None
        :param clipboardSent: callable | None
        :param connectionLost: callable | None
        :param args: any
        :param kwargs: any
        """
        app = kwargs.pop(u'app', None)  # type: object | None
        server = kwargs.pop(u'server', u'')  # type: str
        port = kwargs.pop(u'port', 3389)  # type: int
        username = kwargs.pop(u'username', u'')  # type: str
        password = kwargs.pop(u'password', u'')  # type: str
        domain = kwargs.pop(u'domain', u'')  # type: str
        displayWidth = kwargs.pop(u'displayWidth', 1280)  # type: int
        displayHeight = kwargs.pop(u'displayHeight', 800)  # type: int
        bitsPerPixel = kwargs.pop(u'bitsPerPixel', 32)  # type: int
        graphics = kwargs.pop(u'graphics', u'auto')  # type: str
        sound = kwargs.pop(u'sound', True)  # type: bool
        microphone = kwargs.pop(u'microphone', False)  # type: bool
        compressedAudio = kwargs.pop(u'compressedAudio', True)  # type: bool
        autoReconnect = kwargs.pop(u'autoReconnect', False)  # type: bool
        sharedDirectories = kwargs.pop(u'sharedDirectories', [])  # type: list
        freerdpCliArgs = kwargs.pop(u'freerdpCliArgs', u'')  # type: str
        fps = kwargs.pop(u'fps', 60)  # type: int
        syncClipboard = kwargs.pop(u'syncClipboard', True)  # type: bool
        autoConnect = kwargs.pop(u'autoConnect', False)  # type: bool
        paused = kwargs.pop(u'paused', False)  # type: bool
        designMode = kwargs.pop(u'designMode', False)  # type: bool
        callbacks = dict((name, kwargs.pop(name, None)) for name in (
            u'connected', u'disconnected', u'connectionFailed', u'filesDownloaded', u'clipboardError',
            u'screenshotSaved', u'clipboardSent', u'connectionLost'))  # type: dict
        # Backwards compatible RDPWidget(app, parent=None): the app may come first, positionally.
        subArgs = []  # type: list
        for arg in args:
            if app is None and arg is not None and not isinstance(arg, QWidget) and hasattr(arg, u'setServer'):
                app = arg
            else:
                subArgs.append(arg)
        super(RDPWidget, self).__init__(*subArgs, **kwargs)
        # Options.
        self.__m_server = u'{}'.format(server)  # type: str
        self.__m_port = max(1, min(65535, int(port)))  # type: int
        self.__m_username = u'{}'.format(username)  # type: str
        self.__m_password = u'{}'.format(password)  # type: str
        self.__m_domain = u'{}'.format(domain)  # type: str
        self.__m_displayWidth = max(200, int(displayWidth))  # type: int
        self.__m_displayHeight = max(200, int(displayHeight))  # type: int
        self.__m_bitsPerPixel = int(bitsPerPixel) if int(bitsPerPixel) in (16, 24, 32) else 32  # type: int
        self.__m_graphics = u'{}'.format(graphics)  # type: str
        self.__m_sound = bool(sound)  # type: bool
        self.__m_microphone = bool(microphone)  # type: bool
        self.__m_compressedAudio = bool(compressedAudio)  # type: bool
        self.__m_autoReconnect = bool(autoReconnect)  # type: bool
        self.__m_sharedDirectories = [u'{}'.format(d) for d in sharedDirectories]  # type: list
        self.__m_freerdpCliArgs = u'{}'.format(freerdpCliArgs)  # type: str
        self.__m_fps = max(1, min(240, int(fps)))  # type: int
        self.__m_syncClipboard = bool(syncClipboard)  # type: bool
        self.__m_autoConnect = bool(autoConnect)  # type: bool
        self.__m_paused = bool(paused)  # type: bool
        self.__m_designMode = bool(designMode) or self.isInsideDesigner()  # type: bool
        for name, callback in callbacks.items():
            if callable(callback):
                getattr(self, name).connect(callback)
        # Session state.
        self.__m_app = None  # type: RDPApplication | None
        self.__m_appError = u''  # type: str
        self.__m_mirroring = False  # type: bool
        self.__m_pendingLost = None  # type: dict | None
        self.__m_busy = False  # type: bool
        self.__m_shown = False  # type: bool
        self.__m_image = None  # type: QImage | None
        self.__m_generation = -1  # type: int
        self.__m_remoteHasFiles = False  # type: bool
        self.__m_lastSynced = None  # type: str | None
        self.__m_cursors = {}  # type: dict
        # Widget flags.
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(not self.__m_designMode)
        # Signals from other threads.
        self._pointer.connect(self._applyPointer)
        self._remoteText.connect(self._setLocalText)
        self._startFinished.connect(self._onStartFinished)
        self._stopFinished.connect(self._onStopFinished)
        self._lost.connect(self._onConnectionLost)
        self.remoteClipboardChanged.connect(self._onRemoteClipboard)
        # Timing.
        self.__m_timer = QTimer(self)  # type: QTimer
        self.__m_timer.timeout.connect(self._refresh)
        self.__m_pushTimer = QTimer(self)  # type: QTimer
        self.__m_pushTimer.timeout.connect(self._pushInitialClipboard)
        if not self.__m_designMode:
            QApplication.clipboard().dataChanged.connect(self._onLocalClipboard)
        # The session: the given one (its configuration fills the properties), else a new one
        # configured from the properties. In Qt Designer it exists too, but never connects.
        if app is not None:
            self.setApplication(app)
        else:
            try:
                self.setApplication(RDPApplication(), mirror=False)
            except Exception as exc:  # FreeRDP libraries not loadable: report it at connect time.
                self.__m_appError = u'{}'.format(exc)

    # ---------- Helpers ----------

    @staticmethod
    def isInsideDesigner():
        """
        True when the widget lives in Qt Designer (PyQt passes designMode, PySide6 does not).
        :return: bool
        """
        instance = QApplication.instance()  # type: QApplication
        return bool(instance is not None and u'designer' in u'{}'.format(instance.applicationName()).lower())

    @staticmethod
    def _safe(fn, *args):
        """
        Run an input call; a session that just dropped must not raise into Qt.
        :param fn: callable
        :param args: any
        :return:
        """
        try:
            fn(*args)
        except (ConnectionError, RuntimeError, ValueError):
            pass

    def _remoteXY(self, pos):
        """
        :param pos: QPoint
        :return: tuple[int, int]
        """
        if self.__m_image is None or self.__m_image.isNull():
            return 0, 0
        sx = self.__m_image.width() / float(max(1, self.width()))  # type: float
        sy = self.__m_image.height() / float(max(1, self.height()))  # type: float
        return int(pos.x() * sx), int(pos.y() * sy)

    def _attach(self, app):
        """
        Route the session's pointer and clipboard events to this widget.
        :param app: RDPApplication
        :return:
        """
        app.setPointerListener(lambda state, data: self._pointer.emit(state, data))
        app.setDisconnectListener(lambda reason: self._lost.emit(reason))
        if self.__m_syncClipboard:
            app.setClipboardListener(lambda content: self.remoteClipboardChanged.emit(content))
        else:
            app.setClipboardListener(None)
        self.__m_timer.start(max(1, int(1000 / float(self.__m_fps))))
        if self.__m_syncClipboard:
            self.__m_pushTimer.start(500)

    def _readFrom(self, app):
        """
        Mirror an existing session's configuration in the widget's properties.
        :param app: RDPApplication
        :return:
        """
        self.__m_mirroring = True  # type: bool # The values come from the session: do not write them back.
        try:
            for name, prefix in MIRRORED:
                getattr(self, u'set' + name)(getattr(app, prefix + name)())
            self.setDisplayWidth(app.getDisplayWidth())
            self.setDisplayHeight(app.getDisplayHeight())
            self.setSound(app.isSound())
            self.setMicrophone(app.isMicrophone())
            self.setCompressedAudio(app.isCompressedAudio())
            self.setSharedDirectories([folder for _name, folder in app.getSharedDirectories()])
            self.setFreerdpCliArgs(u' '.join(app.getFreerdpCliArgs()))
        finally:
            self.__m_mirroring = False  # type: bool

    def _sync(self):
        """
        Write the properties through to the session, so it always reflects the widget.
        Skipped while connected: the server-side values (e.g. a resized desktop) must not be overwritten.
        :return: None
        """
        app = self.__m_app  # type: RDPApplication | None
        if app is None or app.isRunning or self.__m_mirroring:
            return
        try:
            self._applyTo(app, folders=False)
        except:
            pass

    def _applyTo(self, app, folders=True):
        """
        Push the widget's properties into the session.
        :param app: RDPApplication
        :param folders: (bool) Also register the shared folders (only when connecting: it cannot be undone).
        :return:
        """
        for name, prefix in MIRRORED:
            getattr(app, u'set' + name)(getattr(self, prefix + name)())
        app.setDisplaySize(self.__m_displayWidth, self.__m_displayHeight)
        app.setSound(self.__m_sound, microphone=self.__m_microphone, compressed=self.__m_compressedAudio)
        app.setFreerdpCliArgs(self.__m_freerdpCliArgs)
        if folders:
            for folder in self.__m_sharedDirectories:
                if exists(folder):
                    app.loadSharedDirectory(folder)

    def _background(self, fn, *args, **kwargs):
        """
        Run fn(*args) on a daemon thread. A failure is reported through clipboardError (or only
        logged, when quiet); a success through the done callback.
        :param fn: callable
        :param errorPrefix: (str | unicode | QString) Put before the error message.
        :param done: (callable | None) Called after fn succeeded.
        :param quiet: (bool) True: background work nobody asked for - log failures, do not report them.
        :param args: any
        :param kwargs: any
        :return:
        """
        errorPrefix = kwargs.pop(u'errorPrefix', u'')  # type: str
        done = kwargs.pop(u'done', None)  # type: callable | None
        quiet = kwargs.pop(u'quiet', False)  # type: bool

        def run():
            """
            :return:
            """
            try:
                fn(*args)
            except Exception as exc:
                if quiet:
                    _log.info(u'%s%s', errorPrefix, exc)
                else:
                    self.clipboardError.emit(u'{}{}'.format(errorPrefix, exc))
                return
            if callable(done):
                done()

        Thread(target=run, daemon=True).start()

    def _askFolder(self, folder, title):
        """
        The given folder, or one chosen in a dialog.
        :param folder: (str | unicode | QString) A folder, or empty to ask.
        :param title: (str | unicode | QString) The dialog title.
        :return: (str | unicode | QString) The folder, or empty when cancelled.
        """
        return folder or QFileDialog.getExistingDirectory(self, title)

    def _mouseButton(self, e, down):
        """
        Send a button press or release to the session.
        :param e: QMouseEvent
        :param down: bool
        :return: None
        """
        if not self.isReady():
            return
        app = self.__m_app  # type: RDPApplication | None
        names = {Qt.LeftButton: u'left', Qt.RightButton: u'right', Qt.MiddleButton: u'middle'}  # type: dict
        name = names.get(e.button())  # type: str | None
        if name:
            self._safe(getattr(app, u'{}Mouse{}'.format(name, u'Down' if down else u'Up')), *self._remoteXY(e.pos()))

    # ---------- Public API: session ----------

    def getApplication(self):
        """
        The RDPApplication included in the widget.
        :return: RDPApplication | None (None only when the FreeRDP libraries could not be loaded).
        """
        return self.__m_app

    def setApplication(self, app, mirror=True):
        """
        Use an existing RDPApplication.
        :param app: RDPApplication
        :param mirror: (bool) True: the widget's properties take the session's configuration.
        :return:
        """
        self.__m_app = app  # type: RDPApplication
        self.__m_image = None  # type: QImage | None
        self.__m_generation = -1  # type: int
        if mirror:
            self._readFrom(app)
        else:
            self._sync()
        if not self.__m_designMode:
            self._attach(app)
        self.update()

    def isReady(self):
        """
        :return: (bool) True while connected.
        """
        return bool(self.__m_app is not None and self.__m_app.isReady)

    def isRunning(self):
        """
        :return: (bool) True while the session thread runs (connecting, connected or reconnecting).
        """
        return bool(self.__m_app is not None and self.__m_app.isRunning)

    def isReconnecting(self):
        """
        :return: bool
        """
        return bool(self.__m_app is not None and self.__m_app.isReconnecting)

    def isFileClipboardEnabled(self):
        """
        :return: (bool) True when the server allows file transfer over the clipboard.
        """
        return bool(self.__m_app is not None and self.__m_app.isFileClipboardEnabled)

    def hasRemoteFiles(self):
        """
        :return: (bool) True when the remote clipboard currently holds files.
        """
        return self.__m_remoteHasFiles

    def getSessionInfo(self):
        """
        :return: (dict) RDPApplication.getSessionInfo(), or the configured values when not connected.
        """
        if self.__m_app is not None:
            return self.__m_app.getSessionInfo()
        # No session (FreeRDP not loadable): the configuration, in RDPApplication.getSessionInfo()'s shape.
        info = dict(((name[0].lower() + name[1:]), getattr(self, prefix + name)()) for name, prefix in MIRRORED
                    if name not in (u'Password', u'AutoReconnect'))  # Never report the password.
        info.update(dict.fromkeys((u'graphicsPipeline', u'clipboard', u'fileClipboard', u'running', u'ready',
                                   u'reconnecting'), False))
        info.update(width=self.__m_displayWidth, height=self.__m_displayHeight, sound=self.__m_sound,
                    microphone=self.__m_microphone, compressedAudio=self.__m_compressedAudio,
                    sharedDirectories=[(basename(normpath(d)), d) for d in self.__m_sharedDirectories],
                    lastError=self.__m_appError or None, framesPublished=0, freerdpVersion=None)
        return info

    @pyqtSlot()
    def connectToServer(self):
        """
        Connect with the current properties (in the background; see connected / connectionFailed).
        :return: None
        """
        if self.__m_designMode or self.__m_busy or self.isReady():
            return
        app = self.__m_app  # type: RDPApplication | None
        if app is None:
            self.connectionFailed.emit(self.tr(self.__m_appError or u'the FreeRDP libraries could not be loaded'))
            return
        try:
            self._applyTo(app)
        except Exception as exc:
            self.connectionFailed.emit(u'{}'.format(exc))
            return
        self.__m_busy = True  # type: bool

        def start():
            """
            :return:
            """
            try:
                if app.isRunning:  # A session that is ending (e.g. right after connectionLost): let it finish.
                    app.stop()
                app.start()
                self._startFinished.emit(True, u'')
            except Exception as exc:
                self._startFinished.emit(False, u'{}'.format(exc))

        self._background(start)
        self.update()

    @pyqtSlot()
    def disconnectFromServer(self):
        """
        Close the session (in the background; see disconnected).
        :return: None
        """
        app = self.__m_app  # type: RDPApplication | None
        if app is None or not app.isRunning:
            return

        def stop():
            """
            :return:
            """
            app.stop()
            self._stopFinished.emit()

        self._background(stop)

    # ---------- Public API: screenshots ----------

    def grabDisplay(self):
        """
        The remote screen at full resolution.
        :return: (QImage) A copy; a null image when nothing was received yet.
        """
        return QImage(self.__m_image) if self.__m_image is not None else QImage()

    @pyqtSlot()
    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    def takeScreenshot(self, pth=u''):
        """
        Save the remote screen as an image (format from the extension: png, jpg, bmp, ...).
        Asks for a file name when none is given.
        :param pth: (str | unicode | QString) Target file.
        :return: (str | unicode | QString) The saved file, or an empty string.
        """
        image = self.grabDisplay()  # type: QImage
        if image.isNull():
            self.clipboardError.emit(self.tr(u'No remote screen to save yet'))
            return u''
        if not pth:
            pth = QFileDialog.getSaveFileName(
                self, self.tr(u'Save screenshot'), u'screenshot.png', self.tr(u'Images (*.png *.jpg *.bmp)'))
            pth = pth[0] if isinstance(pth, tuple) else pth  # type: str
            if not pth:
                return u''
        if not image.save(pth):
            self.clipboardError.emit(self.tr(u'Could not write {}').format(pth))
            return u''
        self.screenshotSaved.emit(pth)
        return pth

    # ---------- Public API: clipboard and folders ----------

    @pyqtSlot()
    def sendLocalClipboard(self):
        """
        Offer the local clipboard (files, else text) to the remote machine; clipboardSent says what was
        sent, clipboardError why nothing could be.
        :return:
        """
        self._offerLocalClipboard(True)

    @pyqtSlot()
    def resendClipboard(self):
        """
        Offer the local clipboard again, even if it was already sent.
        :return:
        """
        self.__m_lastSynced = None
        self._offerLocalClipboard(True)

    @pyqtSlot(list)
    @pyqtSlot(u'QStringList')
    def sendFiles(self, paths):
        """
        Put local files and folders on the remote clipboard, ready to paste in the remote session.
        :param paths: (list[str | unicode | QString] | QStringList) Files and folders.
        :return:
        """
        self._offerFiles([p for p in paths if p and exists(p)], True)

    def _refuse(self, message, explain):
        """
        Nothing could be sent: tell the user when they asked, else only log it.
        :param message: str | unicode | QString
        :param explain: (bool) True when the user asked (button, drop).
        :return: (bool) False.
        """
        self.clipboardError.emit(message) if explain else _log.info(self.tr(u'Clipboard not sent: %s'), message)
        return False

    def _offerLocalClipboard(self, explain):
        """
        :param explain: (bool) True when the user asked: every refusal is reported.
        :return: (bool) True when something is being sent.
        """
        if not self.isReady():
            return self._refuse(self.tr(u'not connected'), explain)
        mime = QApplication.clipboard().mimeData()
        paths = localPaths(mime)  # type: list[str]
        if paths:
            return self._offerFiles(paths, explain)
        text = mime.text() if mime is not None and mime.hasText() else u''  # type: str
        if not text:
            return self._refuse(self.tr(u'the local clipboard is empty - copy some text or files first'), explain)
        if text == self.__m_lastSynced and not explain:
            return False  # Already there (or just received from the remote side): no echo.
        self.__m_lastSynced = text
        self._background(self.__m_app.saveClipboard, u'text', text, quiet=not explain,
                         done=lambda: self.clipboardSent.emit(
                             self.tr(u'text ({} characters) - paste it in the remote session').format(len(text))))
        return True

    def _offerFiles(self, paths, explain):
        """
        :param paths: (list[str | unicode | QString] | QStringList) Existing local files and folders.
        :param explain: (bool) True when the user asked: every refusal is reported.
        :return: (bool) True when the files are being sent.
        """
        if not paths:
            return self._refuse(self.tr(u'no local files to send'), explain)
        if not self.isReady():
            return self._refuse(self.tr(u'not connected'), explain)
        if not self.isFileClipboardEnabled():
            return self._refuse(self.tr(u'this server does not allow file transfer over the clipboard (its '
                                        u'administrator or policy disabled it) - text copy still works'), explain)
        count = len(paths)  # type: int
        self._background(self.__m_app.saveClipboard, u'file', paths, quiet=not explain,
                         done=lambda: self.clipboardSent.emit(
                             self.tr(u'{} {} - paste in the remote session (Ctrl+V)').format(
                                 count, self.tr(u'item') if count == 1 else self.tr(u'items'))))
        return True

    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    @pyqtSlot()
    def downloadRemoteFiles(self, dirPath=u'', filePattern=None):
        """
        Save the files on the remote clipboard; asks for a folder if none is given.
        :param dirPath: (str | unicode | QString) Target directory.
        :param filePattern: (str | unicode | None) Only files matching this pattern (e.g. *.txt).
        :return: None
        """
        app = self.__m_app  # type: RDPApplication
        if app is None:
            return
        dirPath = self._askFolder(dirPath, self.tr(u'Save remote clipboard files to'))  # type: str
        if not dirPath:
            return

        def work():
            """
            :return: None
            """
            if not app.isFileClipboardEnabled:
                self.clipboardError.emit(self.tr(u'The server does not allow file transfer over the clipboard '
                                                 u'(check the RDP host\'s clipboard/drive redirection policy)'))
                return
            before = snapshotTree(dirPath)  # type: set
            out = app.loadClipboard(u'file', dirPath, filePattern)
            if not out:
                self.clipboardError.emit(
                    self.tr(u'The remote clipboard holds no files - copy them on the remote machine first'))
                return
            if not sorted(snapshotTree(out) - before) and filePattern:
                self.clipboardError.emit(self.tr(u'No remote file matched {!r}').format(filePattern))
                return
            self.filesDownloaded.emit(out)

        self._background(work, errorPrefix=self.tr(u'download failed: '))

    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    @pyqtSlot()
    def shareFolder(self, dirPath=u'', dirName=u''):
        """
        Redirect a local folder as a drive on the remote machine. Asks for the folder if none is given;
        a running session reconnects so the drive appears.
        :param dirPath: (str | unicode | QString) The folder.
        :param dirName: (str | unicode | QString) The drive name; the folder's name when empty.
        :return: None
        """
        dirPath = self._askFolder(dirPath, self.tr(u'Share a local folder with the remote machine'))  # type: str
        if not dirPath:
            return
        if dirPath not in self.__m_sharedDirectories:
            self.__m_sharedDirectories.append(dirPath)
        app = self.__m_app
        if app is None:
            return
        try:
            app.loadSharedDirectory(dirPath, dirName)
        except ValueError as exc:
            self.clipboardError.emit(u'{}'.format(exc))
            return
        if not app.isRunning:
            return

        def restart():
            """
            :return:
            """
            try:
                app.stop()
                app.start()
            finally:
                self.sessionRestarted.emit(app.isReady)

        self._background(restart, errorPrefix=self.tr(u'Reconnect failed: '))

    # ---------- Public API: properties ----------

    def getServer(self):
        """
        :return: str | unicode | QString
        """
        return self.__m_server

    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    def setServer(self, server):
        """
        :param server: str | unicode | QString
        :return:
        """
        self.__m_server = u'{}'.format(server)  # type: str
        self.update()
        self._sync()

    def getPort(self):
        """
        :return: int
        """
        return self.__m_port

    @pyqtSlot(int)
    def setPort(self, port):
        """
        :param port: int
        :return:
        """
        self.__m_port = max(1, min(65535, int(port)))  # type: int
        self._sync()

    def getUsername(self):
        """
        :return: str | unicode | QString
        """
        return self.__m_username

    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    def setUsername(self, username):
        """
        :param username: str | unicode | QString
        :return:
        """
        self.__m_username = u'{}'.format(username)  # type: str
        self._sync()

    def getPassword(self):
        """
        :return: str | unicode | QString
        """
        return self.__m_password

    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    def setPassword(self, password):
        """
        :param password: str | unicode | QString
        :return:
        """
        self.__m_password = u'{}'.format(password)  # type: str
        self._sync()

    def getDomain(self):
        """
        :return: str | unicode | QString
        """
        return self.__m_domain

    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    def setDomain(self, domain):
        """
        :param domain: str | unicode | QString
        :return:
        """
        self.__m_domain = u'{}'.format(domain)  # type: str
        self._sync()

    def getDisplayWidth(self):
        """
        :return: int
        """
        return self.__m_displayWidth

    @pyqtSlot(int)
    def setDisplayWidth(self, width):
        """
        :param width: int
        :return:
        """
        self.__m_displayWidth = max(200, int(width))  # type: int
        self.updateGeometry()
        self._sync()

    def getDisplayHeight(self):
        """
        :return: int
        """
        return self.__m_displayHeight

    @pyqtSlot(int)
    def setDisplayHeight(self, height):
        """
        :param height: int
        :return:
        """
        self.__m_displayHeight = max(200, int(height))  # type: int
        self.updateGeometry()
        self._sync()

    def getBitsPerPixel(self):
        """
        :return: int
        """
        return self.__m_bitsPerPixel

    @pyqtSlot(int)
    def setBitsPerPixel(self, bitsPerPixel):
        """
        :param bitsPerPixel: (int) 32, 24 or 16.
        :return:
        """
        if int(bitsPerPixel) in (16, 24, 32):
            self.__m_bitsPerPixel = int(bitsPerPixel)  # type: int
        self._sync()

    def getGraphics(self):
        """
        :return: str | unicode | QString
        """
        return self.__m_graphics

    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    def setGraphics(self, graphics):
        """
        :param graphics: (str | unicode | QString) One of GRAPHICS_OPTIONS.
        :return:
        """
        self.__m_graphics = u'{}'.format(graphics)  # type: str
        self._sync()

    def isSound(self):
        """
        :return: bool
        """
        return self.__m_sound

    @pyqtSlot(bool)
    @pyqtSlot(int)
    def setSound(self, sound):
        """
        :param sound: bool
        :return:
        """
        self.__m_sound = bool(sound)  # type: bool
        self._sync()

    def isMicrophone(self):
        """
        :return: bool
        """
        return self.__m_microphone

    @pyqtSlot(bool)
    @pyqtSlot(int)
    def setMicrophone(self, microphone):
        """
        :param microphone: bool
        :return:
        """
        self.__m_microphone = bool(microphone)  # type: bool
        self._sync()

    def isCompressedAudio(self):
        """
        :return: bool
        """
        return self.__m_compressedAudio

    @pyqtSlot(bool)
    @pyqtSlot(int)
    def setCompressedAudio(self, compressedAudio):
        """
        :param compressedAudio: bool
        :return:
        """
        self.__m_compressedAudio = bool(compressedAudio)  # type: bool
        self._sync()

    def isAutoReconnect(self):
        """
        :return: bool
        """
        return self.__m_autoReconnect

    @pyqtSlot(bool)
    @pyqtSlot(int)
    def setAutoReconnect(self, autoReconnect):
        """
        :param autoReconnect: bool
        :return:
        """
        self.__m_autoReconnect = bool(autoReconnect)  # type: bool
        self._sync()

    def getSharedDirectories(self):
        """
        :return: list[str | unicode | QString] | QStringList
        """
        return list(self.__m_sharedDirectories)

    @pyqtSlot(list)
    @pyqtSlot(u'QStringList')
    def setSharedDirectories(self, sharedDirectories):
        """
        :param sharedDirectories: (list[str | unicode | QString] | QStringList)
                                Local folders redirected as drives at the next connection.
        :return:
        """
        self.__m_sharedDirectories = [u'{}'.format(d) for d in sharedDirectories]  # type: list[str]

    def getFreerdpCliArgs(self):
        """
        :return: str | unicode
        """
        return self.__m_freerdpCliArgs

    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    def setFreerdpCliArgs(self, freerdpCliArgs):
        """
        :param freerdpCliArgs: (str | unicode | QString) Extra FreeRDP command line arguments.
        :return:
        """
        self.__m_freerdpCliArgs = u'{}'.format(freerdpCliArgs)  # type: str
        self._sync()

    def getFps(self):
        """
        :return: int
        """
        return self.__m_fps

    @pyqtSlot(int)
    def setFps(self, fps):
        """
        :param fps: (int) Display refresh rate, 1 to 240.
        :return:
        """
        self.__m_fps = max(1, min(240, int(fps)))  # type: int
        if self.__m_timer.isActive():
            self.__m_timer.start(max(1, int(1000 / float(self.__m_fps))))

    def isSyncClipboard(self):
        """
        :return: bool
        """
        return self.__m_syncClipboard

    @pyqtSlot(bool)
    @pyqtSlot(int)
    def setSyncClipboard(self, syncClipboard):
        """
        :param syncClipboard: bool
        :return:
        """
        self.__m_syncClipboard = bool(syncClipboard)  # type: bool
        if self.__m_app is not None:
            self._attach(self.__m_app)

    def isAutoConnect(self):
        """
        :return: bool
        """
        return self.__m_autoConnect

    @pyqtSlot(bool)
    @pyqtSlot(int)
    def setAutoConnect(self, autoConnect):
        """
        :param autoConnect: (bool) Connect when the widget is first shown.
        :return:
        """
        self.__m_autoConnect = bool(autoConnect)  # type: bool

    def isPaused(self):
        """
        :return: bool
        """
        return self.__m_paused

    @pyqtSlot(bool)
    @pyqtSlot(int)
    def setPaused(self, paused):
        """
        Pause/Resume RDP displays.
        :param paused: bool
        :return:
        """
        self.__m_paused = bool(paused)  # type: bool
        if hasattr(self.__m_app, 'setPaused'):
            self.__m_app.setPaused(self.__m_paused)

    def isDesignMode(self):
        """
        :return: (bool) True when created by Qt Designer.
        """
        return self.__m_designMode

    # ---------- Session callbacks (GUI thread) ----------

    @pyqtSlot(bool, u'QString')
    def _onStartFinished(self, ok, message):
        """
        :param ok: bool
        :param message: str | unicode
        :return:
        """
        self.__m_busy = False  # type: bool
        pending, self.__m_pendingLost = self.__m_pendingLost, None
        if ok:
            self._readFrom(self.__m_app)
            self.connected.emit()
        else:
            self.connectionFailed.emit(message)
            if pending is not None:
                self.connectionLost.emit(pending)  # Now a new attempt can start.
        self.update()

    @pyqtSlot(dict)
    def _onConnectionLost(self, reason):
        """
        :param reason: (dict) RDPApplication.getDisconnectReason().
        :return: None
        """
        if self.__m_busy:  # A connect attempt is still finishing: report once it has (see _onStartFinished).
            self.__m_pendingLost = reason
            return
        self.connectionLost.emit(reason)
        self.update()

    @pyqtSlot()
    def _onStopFinished(self):
        """
        :return:
        """
        self.disconnected.emit()
        self.update()

    # ---------- Display ----------

    @pyqtSlot()
    def _refresh(self):
        """
        Real-time path: take only what changed since the last frame (a rectangle of packed rows,
        copied by the RDP thread as it painted), blit it into the backing image, repaint that area.
        :return: None
        """
        app = self.__m_app  # type: RDPApplication | None
        if app is None or not app.isReady:
            return
        change = app._takeFrame(self.__m_generation)
        if change is None:
            return
        generation, width, height, channels, (x, y, w, h), packed = change
        if self.__m_image is None or self.__m_image.width() != width or self.__m_image.height() != height:
            self.__m_image = QImage(width, height, QImage.Format_RGB32)  # type: QImage
            self.__m_image.fill(Qt.black)
        patch = frameToQimage((w, h, channels, packed))  # type: QImage | None
        if patch is None:
            return
        painter = QPainter(self.__m_image)  # type: QPainter
        painter.drawImage(x, y, patch)
        painter.end()
        self.__m_generation = generation  # type: int
        sx = self.width() / float(width)  # type: float
        sy = self.height() / float(height)  # type: float
        self.update(int(x * sx) - 1, int(y * sy) - 1, int(w * sx) + 3, int(h * sy) + 3)

    @pyqtSlot(u'QString', object)
    def _applyPointer(self, state, data):
        """
        :param state: (str | unicode | QString) set, hidden, default or position.
        :param data: (tuple | None) (width, height, hotX, hotY, BGRA pixels) for set.
        :return:
        """
        if state == u'hidden':
            self.setCursor(Qt.BlankCursor)
        elif state == u'default':
            self.unsetCursor()
        elif state == u'set':
            width, height, hotX, hotY, pixels = data
            key = (width, height, hotX, hotY, hash(pixels))  # type: tuple
            cursor = self.__m_cursors.get(key)  # type: QCursor | None
            if cursor is None:
                image = QImage(pixels, width, height, width * 4, QImage.Format_ARGB32).copy()  # type: QImage
                cursor = QCursor(QPixmap.fromImage(image), hotX, hotY)  # type: QCursor
                if len(self.__m_cursors) > 64:
                    self.__m_cursors.clear()
                self.__m_cursors[key] = cursor  # type: QCursor
            self.setCursor(cursor)

    # ---------- Clipboard (GUI thread) ----------

    @pyqtSlot(dict)
    def _onRemoteClipboard(self, content):
        """
        :param content: (dict) {'text': bool, 'files': bool}
        :return:
        """
        self.__m_remoteHasFiles = bool(content.get(u'files'))  # type: bool
        if content.get(u'text') and self.__m_syncClipboard:
            self._background(self._fetchRemoteText, quiet=True)

    def _fetchRemoteText(self):
        """
        :return:
        """
        text = self.__m_app.loadClipboard(u'text')  # type: str
        if text:
            self._remoteText.emit(text)

    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    def _setLocalText(self, text):
        """
        :param text: str | unicode | QString
        :return: None
        """
        if text == self.__m_lastSynced:
            return
        # The coming dataChanged carries this text: _offerLocalClipboard skips it.
        self.__m_lastSynced = text  # type: str
        QApplication.clipboard().setText(text)

    @pyqtSlot()
    def _onLocalClipboard(self):
        """
        :return:
        """
        if self.__m_syncClipboard:
            self._offerLocalClipboard(False)

    @pyqtSlot()
    def _pushInitialClipboard(self):
        """
        :return:
        """
        if self.isReady():
            self.__m_pushTimer.stop()
            self._offerLocalClipboard(False)

    def _contextMenu(self, globalPos):
        """
        :param globalPos: QPoint
        :return:
        """
        menu = QMenu(self)  # type: QMenu
        download = menu.addAction(self.tr(u'Download remote clipboard files...'))
        download.setEnabled(self.__m_remoteHasFiles and self.isFileClipboardEnabled())
        download.triggered.connect(lambda: self.downloadRemoteFiles())
        send = menu.addAction(self.tr(u'Send local clipboard to remote'))
        send.triggered.connect(self.resendClipboard)
        menu.addSeparator()
        share = menu.addAction(self.tr(u'Share a local folder... (reconnects)'))
        share.triggered.connect(lambda: self.shareFolder())
        screenshot = menu.addAction(self.tr(u'Save screenshot...'))
        screenshot.triggered.connect(lambda: self.takeScreenshot())
        if self.__m_sharedDirectories:
            info = menu.addAction(self.tr(u'Shared: {}').format(u', '.join(self.__m_sharedDirectories)))
            info.setEnabled(False)
        qtExec(menu, globalPos)

    # ---------- Qt overrides ----------

    def sizeHint(self):
        """
        :return: QSize
        """
        return QSize(min(1024, self.__m_displayWidth), min(768, self.__m_displayHeight))

    def minimumSizeHint(self):
        """
        :return: QSize
        """
        return QSize(160, 120)

    def showEvent(self, e):
        """
        :param e: QShowEvent
        :return:
        """
        super(RDPWidget, self).showEvent(e)
        if not self.__m_shown:
            self.__m_shown = True  # type: bool
            if self.__m_autoConnect and not self.__m_designMode and self.__m_server:
                QTimer.singleShot(0, self.connectToServer)

    def closeEvent(self, e):
        """
        :param e: QCloseEvent
        :return:
        """
        self.__m_timer.stop()
        self.__m_pushTimer.stop()
        super(RDPWidget, self).closeEvent(e)

    def mouseMoveEvent(self, e):
        """
        :param e: QMouseEvent
        :return:
        """
        if self.isReady():
            self._safe(self.__m_app.mouseMove, *self._remoteXY(e.pos()))
        super(RDPWidget, self).mouseMoveEvent(e)

    def mousePressEvent(self, e):
        """
        :param e: QMouseEvent
        :return: None
        """
        if e.button() == Qt.RightButton and e.modifiers() & Qt.ShiftModifier:
            self._contextMenu(e.globalPos())
            return
        self._mouseButton(e, True)
        self.setFocus()

    def mouseReleaseEvent(self, e):
        """
        :param e: QMouseEvent
        :return: None
        """
        if e.button() == Qt.RightButton and e.modifiers() & Qt.ShiftModifier:
            return
        self._mouseButton(e, False)

    def wheelEvent(self, e):
        """
        :param e: QWheelEvent
        :return:
        """
        if self.isReady():
            x, y = self._remoteXY(e.position().toPoint() if hasattr(e, u'position') else e.pos())  # type: int, int
            self._safe(self.__m_app.mouseScroll, x, y, e.angleDelta().y() < 0)

    def _key(self, e, down):
        """
        :param e: QKeyEvent
        :param down: bool
        :return: None
        """
        if not self.isReady() or (e.isAutoRepeat() and not down):
            return
        app = self.__m_app
        code = nativeToScancode(app._api, int(e.nativeScanCode()), int(e.nativeVirtualKey()))
        if code is not None:
            self._safe(app.keyDown if down else app.keyUp, code)
        elif down and e.text() and ord(e.text()[0]) >= 32:
            self._safe(app.typeText, e.text(), 0)  # Unmapped: send the character.
        e.accept()

    def keyPressEvent(self, e):
        """
        :param e: QKeyEvent
        :return:
        """
        self._key(e, True)

    def keyReleaseEvent(self, e):
        """
        :param e: QKeyEvent
        :return:
        """
        self._key(e, False)

    def focusNextPrevChild(self, nextChild):
        """
        :param nextChild: bool
        :return: (bool) False: Tab goes to the remote machine.
        """
        return False

    def dragEnterEvent(self, e):
        """
        :param e: QDragEnterEvent
        :return:
        """
        self._acceptFileDrag(e)

    def dragMoveEvent(self, e):
        """
        :param e: QDragMoveEvent
        :return:
        """
        self._acceptFileDrag(e)

    @staticmethod
    def _acceptFileDrag(e):
        """
        Accept local files as a COPY - a proposed move would make the file manager delete the sources.
        Accepted even when the server refuses files, so the drop can say why.
        :param e: QDragEnterEvent | QDragMoveEvent
        :return:
        """
        if localPaths(e.mimeData()):
            e.setDropAction(Qt.CopyAction)
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        """
        :param e: QDropEvent
        :return: None
        """
        paths = localPaths(e.mimeData())  # type: list[str]
        if not paths:
            e.ignore()
            return
        e.setDropAction(Qt.CopyAction)  # Never a move: the sources stay where they are.
        e.accept()
        self._offerFiles(paths, True)

    # ---------- Painting ----------

    def paintEvent(self, e):
        """
        :param e: QPaintEvent
        :return: None
        """
        painter = QPainter(self)  # type: QPainter
        image = self.__m_image  # type: QImage | None
        if image is not None and not image.isNull() and not self.__m_designMode:
            if image.width() == self.width() and image.height() == self.height():
                painter.drawImage(e.rect(), image, e.rect())  # 1:1, no scaling.
            else:
                painter.drawImage(self.rect(), image)  # Scaled, clipped to the update.
            return
        self._paintPlaceholder(painter)

    def _paintPlaceholder(self, painter):
        """
        What Qt Designer (and a widget that is not connected yet) shows.
        :param painter: QPainter
        :return:
        """
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), BACKGROUND)
        rect = QRectF(self.rect()).adjusted(12, 12, -12, -12)  # type: QRectF
        painter.setPen(FOREGROUND)
        font = QFont(self.font())  # type: QFont
        font.setPointSizeF(max(8.0, font.pointSizeF() * 1.4))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter, self._placeholderText())

    def _placeholderText(self):
        """
        :return: str | unicode | QString
        """
        target = u'{}:{}'.format(self.__m_server or u'<server>', self.__m_port)  # type: str
        if self.__m_designMode:
            return u'RDPWidget\n{}\n{}x{} - {} bpp - {}'.format(
                target, self.__m_displayWidth, self.__m_displayHeight, self.__m_bitsPerPixel, self.__m_graphics)
        if self.__m_busy:
            return self.tr(u'Connecting to {}...').format(target)
        return self.tr(u'Reconnecting to {}...' if self.isReconnecting() else u'Not connected\n{}').format(target)

    # ---------- Properties ----------

    server = pyqtProperty(u'QString', fget=getServer, fset=setServer)  # type: pyqtProperty
    port = pyqtProperty(int, fget=getPort, fset=setPort)  # type: pyqtProperty
    username = pyqtProperty(u'QString', fget=getUsername, fset=setUsername)  # type: pyqtProperty
    password = pyqtProperty(u'QString', fget=getPassword, fset=setPassword)  # type: pyqtProperty
    domain = pyqtProperty(u'QString', fget=getDomain, fset=setDomain)  # type: pyqtProperty
    displayWidth = pyqtProperty(int, fget=getDisplayWidth, fset=setDisplayWidth)  # type: pyqtProperty
    displayHeight = pyqtProperty(int, fget=getDisplayHeight, fset=setDisplayHeight)  # type: pyqtProperty
    bitsPerPixel = pyqtProperty(int, fget=getBitsPerPixel, fset=setBitsPerPixel)  # type: pyqtProperty
    graphics = pyqtProperty(u'QString', fget=getGraphics, fset=setGraphics)  # type: pyqtProperty
    sound = pyqtProperty(bool, fget=isSound, fset=setSound)  # type: pyqtProperty
    microphone = pyqtProperty(bool, fget=isMicrophone, fset=setMicrophone)  # type: pyqtProperty
    compressedAudio = pyqtProperty(bool, fget=isCompressedAudio, fset=setCompressedAudio)  # type: pyqtProperty
    autoReconnect = pyqtProperty(bool, fget=isAutoReconnect, fset=setAutoReconnect)  # type: pyqtProperty
    sharedDirectories = pyqtProperty(
        u'QStringList', fget=getSharedDirectories, fset=setSharedDirectories)  # type: pyqtProperty
    freerdpCliArgs = pyqtProperty(u'QString', fget=getFreerdpCliArgs, fset=setFreerdpCliArgs)  # type: pyqtProperty
    fps = pyqtProperty(int, fget=getFps, fset=setFps)  # type: pyqtProperty
    syncClipboard = pyqtProperty(bool, fget=isSyncClipboard, fset=setSyncClipboard)  # type: pyqtProperty
    autoConnect = pyqtProperty(bool, fget=isAutoConnect, fset=setAutoConnect)  # type: pyqtProperty
    paused = pyqtProperty(bool, fget=isPaused, fset=setPaused)  # type: pyqtProperty
    application = pyqtProperty(object, fget=getApplication, fset=setApplication, designable=False)  # type: pyqtProperty
    ready = pyqtProperty(bool, fget=isReady)  # type: pyqtProperty
    running = pyqtProperty(bool, fget=isRunning)  # type: pyqtProperty
