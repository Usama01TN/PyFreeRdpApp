# coding=utf-8
"""
PyfreeRdpApp Module.
"""
from pyfreerdpnative.freerdp.settings_keys import FreeRDP_AudioCapture, FreeRDP_AudioPlayback, FreeRDP_ColorDepth, \
    FreeRDP_AutoReconnectionEnabled, FreeRDP_ClipboardFeatureMask, FreeRDP_DesktopHeight, FreeRDP_Username, \
    FreeRDP_DesktopWidth, FreeRDP_DeviceRedirection, FreeRDP_Domain, FreeRDP_GfxAVC444, FreeRDP_GfxAVC444v2, \
    FreeRDP_GfxH264, FreeRDP_GfxProgressive, FreeRDP_GfxProgressiveV2, FreeRDP_IgnoreCertificate, FreeRDP_NlaSecurity, \
    FreeRDP_Password, FreeRDP_RedirectClipboard, FreeRDP_RemoteFxCodec, FreeRDP_ServerHostname, FreeRDP_ServerPort, \
    FreeRDP_SoftwareGdi, FreeRDP_SupportGraphicsPipeline, FreeRDP_TcpAckTimeout, FreeRDP_TcpConnectTimeout, \
    FreeRDP_TlsSecurity, FreeRDP_RemoteApplicationMode, FreeRDP_RemoteApplicationProgram, FreeRDP_AadSecurity, \
    FreeRDP_ShellWorkingDirectory, FreeRDP_RemoteApplicationCmdLine, FreeRDP_AlternateShell, FreeRDP_AadAuthHelper, \
    FreeRDP_RemoteApplicationName, FreeRDP_MultitransportFlags
from pyfreerdpnative.freerdp.rail import RAIL_EXEC_ORDER, TS_RAIL_EXEC_FLAG_EXPAND_WORKINGDIRECTORY, \
    TS_RAIL_EXEC_FLAG_EXPAND_ARGUMENTS, RAIL_EXEC_E_HOOK_NOT_LOADED, RAIL_EXEC_E_DECODE_FAILED, \
    RAIL_EXEC_E_NOT_IN_ALLOWLIST, RAIL_EXEC_E_FILE_NOT_FOUND, RAIL_EXEC_E_FAIL, RAIL_EXEC_E_SESSION_LOCKED, \
    RAIL_EXEC_S_OK, RAIL_SVC_CHANNEL_NAME
from pyfreerdpnative.freerdp.settings_types import CLIPRDR_FLAG_LOCAL_TO_REMOTE, CLIPRDR_FLAG_LOCAL_TO_REMOTE_FILES, \
    CLIPRDR_FLAG_REMOTE_TO_LOCAL, CLIPRDR_FLAG_REMOTE_TO_LOCAL_FILES, TRANSPORT_TYPE_UDP_FECR, SOFTSYNC_TCP_TO_UDP, \
    TRANSPORT_TYPE_UDP_PREFERRED
from pyfreerdpnative.freerdp.input import KBD_FLAGS_EXTENDED, KBD_FLAGS_RELEASE, PTR_FLAGS_BUTTON1, PTR_FLAGS_BUTTON2, \
    PTR_FLAGS_BUTTON3, PTR_FLAGS_DOWN, PTR_FLAGS_MOVE, PTR_FLAGS_WHEEL, PTR_FLAGS_WHEEL_NEGATIVE
from pyfreerdpnative.freerdp.settings_keys import FreeRDP_RdpVersion, FreeRDP_SelectedProtocol, \
    FreeRDP_ExternalCertificateManagement
from pyfreerdpnative.freerdp.session import INFO_TYPE_LOGON, INFO_TYPE_LOGON_LONG, INFO_TYPE_LOGON_EXTENDED_INF, \
    logon_info, logon_info_ex
from pyfreerdpnative.freerdp.scancode import RDP_SCANCODE_BACKSPACE, RDP_SCANCODE_RETURN, RDP_SCANCODE_SPACE, \
    RDP_SCANCODE_TAB
from pyfreerdpnative.freerdp.client import RDP_CLIENT_ENTRY_POINTS_V1, RDP_CLIENT_INTERFACE_VERSION, rdpClientContext
from pyfreerdpnative.freerdp.codec.color import PIXEL_FORMAT_BGR16, PIXEL_FORMAT_BGR24, PIXEL_FORMAT_BGRA32
from pyfreerdpnative.freerdp.event import pChannelConnectedEventHandler, pChannelDisconnectedEventHandler
from pyfreerdpnative.freerdp.channels.cliprdr import CLIPRDR_SVC_CHANNEL_NAME
from pyfreerdpnative.freerdp.error import FREERDP_ERROR_CONNECT_LOGON_FAILURE
from pyfreerdpnative.freerdp.channels.rdpgfx import RDPGFX_DVC_CHANNEL_NAME
from pyfreerdpnative.freerdp.client.rdpgfx import RdpgfxClientContext
from pyfreerdpnative.freerdp.client.rail import RailClientContext
from pyfreerdpnative.freerdp.transport_io import rdpTransportIo
from pyfreerdpnative.freerdp.graphics import rdpPointer
from pyfreerdpnative.winpr.synch import WAIT_FAILED
from pyfreerdpnative.freerdp import settings_types
from pyfreerdpnative.winpr.wtypes import HANDLE
from pyfreerdpnative import load
from ctypes import c_char_p, c_char, memmove, c_ubyte, cast, c_void_p, c_uint32, c_int, sizeof, byref, addressof, \
    POINTER, string_at
from os.path import join, expanduser, abspath, isfile, dirname, isdir, basename, normpath, exists
from logging import getLogger, FileHandler, basicConfig, StreamHandler, INFO
from threading import Condition, Event, Lock, RLock, Thread, current_thread
from os import environ, remove, getcwd, getpid, makedirs
from datetime import datetime, timezone
from sys import platform, stderr, path
from subprocess import Popen, PIPE
from traceback import format_exc
from time import sleep, time
from re import search

try:
    from pyfreerdpnative.freerdp.settings_keys import FreeRDP_SupportMultitransportUdp
except:
    FreeRDP_SupportMultitransportUdp = None
try:
    from pyfreerdpnative.freerdp.settings_keys import FreeRDP_AadAuthUserAgent
except:  # Bindings older than FreeRDP 3.33: no Azure AD User-Agent (Azure AD sign-in needs 3.33).
    FreeRDP_AadAuthUserAgent = None
try:
    from pyfreerdpnative.freerdp.error import FREERDP_ERROR_CONNECT_NTLM_BLOCKED
except:
    # FreeRDP 3.33.0 additions, looked up so the bindings of 3.32 still work.
    FREERDP_ERROR_CONNECT_NTLM_BLOCKED = 0x0002001F  # type: int
if platform.lower() == u'win32':
    from ctypes import WinDLL  # Windows only: kernel32 for the event API.
else:
    WinDLL = None  # Linux / macOS: WinPR exports what is needed.
try:
    from time import monotonic
except:  # pragma: no cover - Python 2
    monotonic = time

if dirname(__file__) not in path:
    path.append(dirname(__file__))

try:
    from ._serverinfo import StreamHead, describeCertificate, parseChallenge, parseUsername, protocolNames
except:
    from _serverinfo import StreamHead, describeCertificate, parseChallenge, parseUsername, protocolNames
try:
    from ._cliprdr import Clipboard
except:
    from _cliprdr import Clipboard
try:
    from .keyboard import KEY_D, KEY_V, LEFT_CONTROL, LEFT_WINDOW
except:
    from keyboard import KEY_D, KEY_V, LEFT_CONTROL, LEFT_WINDOW
try:
    from subprocess import CREATE_NO_WINDOW
except:
    CREATE_NO_WINDOW = 0  # type: int
try:
    from faulthandler import enable, is_enabled
except:
    _fhEnabled = False  # type: bool


    def enable(*args, **kwargs):
        """
        Enable fault handler support when available.
        :param args: any
        :param kwargs: any
        :return:
        """
        if args and kwargs:
            pass
        global _fhEnabled
        _fhEnabled = True  # type: bool


    def is_enabled():
        """
        Return whether the compatibility flag is enabled.
        :return: bool
        """
        return _fhEnabled

_log = getLogger(u'PyFreeRdpApp')
TRANSPORTS = (u'default', u'udp', u'udp-preferred', u'tcp-only')  # type: tuple
# stop() keeps the connection this long after the last key/mouse event, so the server reads it before
# the close (a close with server updates unread is a TCP reset, which drops what the server had not read).
INPUT_LINGER = 0.5  # type: float
# Audio buffer target (ms) for FreeRDP's rdpsnd backends. FreeRDP reports the real playback latency to
# the server in each Wave Confirm, which the server uses for A/V sync; a short buffer keeps sound close
# to the picture. PulseAudio's own default is 100 ms. 0 = the backend's default.
DEFAULT_AUDIO_LATENCY = 50  # type: int
# RemoteApp (MS-RDPERP) Client Execute: the server expands %VARIABLES% in the arguments and folder.
RAIL_EXEC_FLAGS = TS_RAIL_EXEC_FLAG_EXPAND_WORKINGDIRECTORY | TS_RAIL_EXEC_FLAG_EXPAND_ARGUMENTS  # type: int
# Why the server refused a Client Execute (RAIL_EXEC_RESULT_ORDER.execResult).
RAIL_EXEC_ERRORS = {
    RAIL_EXEC_E_HOOK_NOT_LOADED: u'The server\'s RemoteApp component is not running',
    RAIL_EXEC_E_DECODE_FAILED: u'The server could not read the request',
    RAIL_EXEC_E_NOT_IN_ALLOWLIST: u'The server does not allow this program - publish it as a RemoteApp, or allow '
                                  u'unlisted programs (policy "Allow remote start of unlisted programs")',
    RAIL_EXEC_E_FILE_NOT_FOUND: u'the server did not find the program',
    RAIL_EXEC_E_FAIL: u'The server could not start it', RAIL_EXEC_E_SESSION_LOCKED: u'The session is locked',
}  # type: dict[int, str]
# (RDPController::start): 32 -> BGRA32, 24 -> BGR24, 16 -> BGR16
_PIXEL_FORMATS = {32: PIXEL_FORMAT_BGRA32, 24: PIXEL_FORMAT_BGR24, 16: PIXEL_FORMAT_BGR16}  # type: dict[int, int]
# (RDPController::pressKey(wchar_t)): these characters are typed as real keys,
# everything else as a Unicode keyboard event.
_TYPED_AS_SCANCODE = {
    u' ': RDP_SCANCODE_SPACE, u'\n': RDP_SCANCODE_RETURN, u'\b': RDP_SCANCODE_BACKSPACE, u'\t': RDP_SCANCODE_TAB
}  # type: dict[str, int]
# (RDPController::mouseScroll): 9-bit two's complement rotation.
_WHEEL_DOWN = PTR_FLAGS_WHEEL | PTR_FLAGS_WHEEL_NEGATIVE | 0x0088  # type: int
_WHEEL_UP = PTR_FLAGS_WHEEL | 0x0078  # type: int
_RECONNECT_ATTEMPTS = 5  # type: int
# getDisplay(displayFormat=...)
DISPLAY_FORMATS = (u'numpy', u'pillow', u'qimage', u'bytes', u'tuple')
RDP_VERSIONS = dict((getattr(settings_types, name), name[len(u'RDP_VERSION_'):].replace(
    u'_PLUS', u'+').replace(u'_', u'.')) for name in dir(settings_types) if name.startswith(
    u'RDP_VERSION_'))  # type: dict
_DISPLAY_FORMAT_ERROR = u'DisplayFormat must be one of: {}'.format(u', '.join(DISPLAY_FORMATS))


def _guard(default=None):
    """
    A FreeRDP callback must never let a Python exception reach C.
    """

    def decorate(method):
        def wrapper(self, *args):
            try:
                return method(self, *args)
            except:
                _log.error(u'Exception in %s:\n%s', method.__name__, format_exc())
                return default

        wrapper.__name__ = method.__name__
        return wrapper

    return decorate


def initializeLogging(logFolder, logLevel=u'INFO'):
    """
    Initializes logging into this folder.
    """
    import logging
    level = getattr(logging, str(logLevel).upper(), INFO)
    handlers = [StreamHandler(stderr)]
    if logFolder:
        try:
            if not isdir(logFolder):
                makedirs(logFolder)
            handlers.append(FileHandler(join(logFolder, u'pyfreerdpapp.log')))
        except OSError as exc:
            _log.warning(u'Could not open log folder %s: %s', logFolder, exc)
    basicConfig(level=level, handlers=handlers, format=u'%(asctime)s %(levelname)s %(name)s: %(message)s')
    _log.setLevel(level)
    _enableCrashLog(logFolder)


_crashFile = None


def _enableCrashLog(logFolder=None):
    """
    A native crash (0xC0000005 on Windows, SIGSEGV elsewhere) kills the
    process without a Python traceback. faulthandler catches it and writes the
    Python stack of EVERY thread - which callback or call was running - to
    stderr and, with a log folder, to pyfreerdpapp-crash.log.
    """
    global _crashFile
    if platform == u'win32' and not environ.get(u'PYFREERDPAPP_FAULTHANDLER'):
        # On Windows faulthandler also dumps exceptions that are then HANDLED
        # (e.g. "code 0x8001010d" from COM inside Qt's dialogs) - alarming
        # noise that looks like a crash. Native crashes are reported from the
        # Windows event log on the next start instead (lastNativeCrash), which
        # names the faulting module. Set PYFREERDPAPP_FAULTHANDLER=1 to opt in.
        return
    target = stderr
    if logFolder:
        try:
            _crashFile = open(join(logFolder, u'pyfreerdpapp-crash.log'), u'a')
            target = _crashFile
        except OSError:
            pass
    try:
        enable(file=target, all_threads=True)
    except (RuntimeError, ValueError, AttributeError):  # e.g. no usable stderr (pythonw).
        pass


_CRASH_MARKER = join(environ.get(u'TEMP') or environ.get(u'TMPDIR') or u'/tmp', u'pyfreerdpapp-session.running')


def _parseWindowsCrashEvent(text):
    """
    Pick the useful fields out of an Application Error event (ID 1000) as
    printed by `wevtutil qe ... /f:text`: which DLL faulted, where, and how.
    """
    fields = {}
    for key, pattern in ((u'application', r'Faulting application name:\s*([^,\r\n]+)'),
                         (u'module', r'Faulting module name:\s*([^,\r\n]+)'),
                         (u'module_version', r'Faulting module name:[^,]+,\s*version:\s*([^,\r\n]+)'),
                         (u'exception', r'Exception code:\s*(0x[0-9a-fA-F]+)'),
                         (u'offset', r'Fault offset:\s*(0x[0-9a-fA-F]+)'),
                         (u'module_path', r'Faulting module path:\s*([^\r\n]+)'), (u'time', r'Date:\s*([^\r\n]+)'),
                         (u'pid', r'Faulting process id:\s*(0x[0-9a-fA-F]+)')):
        m = search(pattern, text)
        if m:
            fields[key] = m.group(1).strip()
    return fields if u'module' in fields else None


def lastNativeCrash():
    """
    If the previous run died in native code, what Windows recorded about it:
    a dict with module, offset, exception, module_path, ... - else None.
    Windows logs every crash as an Application Error event (ID 1000); reading
    it after the fact needs no code running inside the crashing process.
    Only a crash of the very process that left the session marker (its process id), logged after
    that session started, is reported - and only once: an older crash in the log is not news.
    """
    if platform != u'win32' or not exists(_CRASH_MARKER):
        return None
    try:
        with open(_CRASH_MARKER) as fh:
            pid, started = (int(v) for v in fh.read().split())
    except (OSError, ValueError):
        pid, started = None, None
    _markSession(False)  # Consumed: reported (or not) once.
    if pid is None:
        return None
    try:
        proc = Popen(
            [u'wevtutil', u'qe', u'Application', u'/q:*[System[(EventID=1000)]]', u'/c:10', u'/rd:true', u'/f:text'],
            stdout=PIPE, stderr=PIPE, creationflags=CREATE_NO_WINDOW)  # type: Popen
        result = {}

        def communicate():
            """
            :return:
            """
            result[u'output'] = proc.communicate()  # type: tuple[str, str]

        thread = Thread(target=communicate)  # type: Thread
        thread.daemon = True
        thread.start()
        thread.join(15)
        if thread.is_alive():
            proc.kill()
            thread.join()
        stdout, _ = result.get(u'output', (u'', u''))  # type: bytes, int
        if not isinstance(stdout, type(u'')):
            stdout = stdout.decode(u'utf-8', u'replace')  # type: str
        out = stdout  # type: str
    except:
        return None
    return _crashOfProcess(out, pid, started)


def _crashOfProcess(events, pid, started):
    """
    The Application Error event of process `pid` logged after `started`, if any.
    :param events: (str | unicode) wevtutil qe ... /f:text output.
    :param pid: (int) The process that left the session marker.
    :param started: (int) When its session started (seconds since the epoch, UTC).
    :return: dict | None
    """
    for event in events.split(u'Event['):
        info = _parseWindowsCrashEvent(event)
        if not info or u'python' not in info.get(u'application', u'').lower():
            continue
        try:
            if int(info.get(u'pid', u'0'), 16) != pid:
                continue
            when = datetime.strptime(info.get(u'time', u'')[:19], u'%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if when.timestamp() >= started - 2:
            return info
    return None


def _markSession(active):
    """
    The session marker: present while a session runs, holding this process's id and start time, so
    that a native crash can be told apart from an old one (lastNativeCrash).
    :param active: (bool) True when a session starts, False when it ends.
    :return:
    """
    try:
        if active:
            with open(_CRASH_MARKER, u'w') as fh:
                fh.write(u'{} {}'.format(getpid(), int(time())))
        elif exists(_CRASH_MARKER):
            remove(_CRASH_MARKER)
    except OSError:
        pass


class RDPClipboardError(Exception):
    """
    Raised when a clipboard transfer cannot be completed.
    """


def _convertFrame(displayFormat, width, height, channels, data):
    """
    Tightly packed BGR(A) pixels -> the requested display type.
    """
    if displayFormat == u'bytes':
        return bytes(data)
    if displayFormat == u'tuple':
        return width, height, channels, bytes(data)
    if displayFormat == u'numpy':
        try:
            from numpy import frombuffer, uint8
        except:
            raise ImportError(u'getDisplay(\'numpy\') needs numpy: pip install numpy')
        return frombuffer(data, dtype=uint8).reshape(height, width, channels).copy()
    if displayFormat == u'pillow':
        try:
            from PIL.Image import frombuffer
        except:
            raise ImportError(u'getDisplay(\'pillow\') needs Pillow: pip install pillow')
        # Pillow reads BGR(A) directly through its raw decoder. 16 bpp is
        # FreeRDP's PIXEL_FORMAT_BGR16: blue in the HIGH bits, red in the low
        # ones (libfreerdp/codec/color.c), which Pillow calls 'RGB;16' - its 'BGR;16' would swap red and blue.
        mode, raw = {4: (u'RGBA', u'BGRA'), 3: (u'RGB', u'BGR'), 2: (u'RGB', u'RGB;16')}[channels]
        return frombuffer(mode, (width, height), bytes(data), u'raw', raw, 0, 1)
    if displayFormat == u'qimage':
        try:
            from PyFreeRdpApp.rdpwidget import frameToQimage
        except:
            raise ImportError(u'getDisplay("qimage") needs ManyQt and a Qt binding')
        image = frameToQimage((width, height, channels, bytes(data)))
        if image is None:
            raise ImportError(u'getDisplay("qimage") needs ManyQt and a Qt binding')
        return image
    raise ValueError(displayFormat)


def _waitFunction(api):
    """
    WaitForMultipleObjects for the event loop.
    On Linux/macOS WinPR implements and exports it. On Windows it is the
    Win32 API in kernel32.dll - WinPR declares its own copy only under
    `#ifndef _WIN32` - so no FreeRDP library exports it there, and it has to come from kernel32.
    """
    if api.has(u'WaitForMultipleObjects'):
        return api.WaitForMultipleObjects
    if platform.lower() == u'win32':
        kernel32 = WinDLL(u'kernel32', use_last_error=True)
        wait = kernel32.WaitForMultipleObjects
        wait.restype = c_uint32
        wait.argtypes = [c_uint32, POINTER(HANDLE), c_int, c_uint32]
        return wait
    raise OSError(u'WaitForMultipleObjects is not available on this platform')


class _WakeEvent(object):
    """
    A manual-reset event the event loop also waits on, so input queued from
    another thread is sent at once instead of at the next timeout. WinPR's
    on Linux/macOS, kernel32's on Windows (where WinPR exports none).
    """

    def __init__(self, api):
        if api.has(u'CreateEventA'):
            self._create, self._set = api.CreateEventA, api.SetEvent
            self._reset, self._close = api.ResetEvent, api.CloseHandle
        elif platform == u'win32':
            k32 = WinDLL(u'kernel32', use_last_error=True)
            self._create, self._set, self._reset, self._close = (
                k32.CreateEventA, k32.SetEvent, k32.ResetEvent, k32.CloseHandle)
            self._create.restype = HANDLE
            self._create.argtypes = [c_void_p, c_int, c_int, c_char_p]
            for fn in (self._set, self._reset, self._close):
                fn.restype = c_int
                fn.argtypes = [HANDLE]
        else:
            raise OSError(u'No event API on this platform')
        self.handle = self._create(None, True, False, None)

    def set(self):
        """
        :return:
        """
        if self.handle:
            self._set(self.handle)

    def reset(self):
        """
        :return:
        """
        if self.handle:
            self._reset(self.handle)

    def close(self):
        """
        :return:
        """
        if self.handle:
            self._close(self.handle)
            self.handle = None


class _Call(object):
    """
    A function to run on the RDP thread, with its result handed back.
    """

    def __init__(self, fn, waited=False):
        self.fn = fn
        self.waited = waited  # type: bool
        self.done = Event()  # type: Event
        self.result = None
        self.error = None

    def run(self):
        """
        :return:
        """
        try:
            self.result = self.fn()
        except BaseException as exc:
            self.error = exc
            if not self.waited:
                # a fire-and-forget call (_post): nobody will read .error, so
                # say it here - silently losing it hid a clipboard bug once
                _log.error(u'Call on the RDP thread failed:\n%s', format_exc())
        finally:
            self.done.set()


class RDPApplication(object):
    """
    RDPApplication class.
    """

    def __init__(self):
        self._api = load()
        self._wait = _waitFunction(self._api)
        self._ctx = None
        self._instance = None
        self._gdi = None
        self._thread = None
        self._refs = []  # C callbacks must outlive the session.
        self._queue = []  # _Call objects for the RDP thread.
        self._lastInputAt = 0.0  # type: float # monotonic time the last key/mouse event went out (stop() lingers)
        self._frameListener = None  # called on the RDP thread when a new frame is published
        self._startProgram = (u'', u'')  # (command line, working folder): the session's alternate shell
        self._remoteApp = None  # (program, arguments, working folder): a RemoteApp session
        self._rail = None  # POINTER(RailClientContext) while the RemoteApp channel is up
        self._railRefs = []  # the ctypes callbacks given to it
        self._execResults = []  # (execResult, rawResult) per Client Execute, in order
        self._execCondition = Condition()  # type: Condition
        self._queueLock = Lock()  # type: Lock
        self._host = u''  # type: str
        self._port = 3389  # type: int
        self._user = u''  # type: str
        self._password = u''  # type: str
        self._domain = u''  # type: str
        self._width = 1920  # type: int
        self._height = 1080  # type: int
        self._bpp = 24  # type: int
        self._autoReconnect = False
        self._graphics = u'auto'  # type: str # The Graphics Pipeline (/gfx) when the server has it.
        self._cliArgs = []
        self._drives = []  # [(name, path)]
        self._resetState()
        self._stop = False  # type: bool
        self._paused = False  # type: bool
        self._running = False  # type: bool
        self._error = None  # Last connection error message.
        self._displayFormat = u'numpy'  # type: str
        self._pointerListener = None
        self._sound = True  # type: bool # Play the remote audio locally.
        # real-time frames: the RDP thread copies only the rows a paint touched
        # into _fb, under _frameLock; readers never wait for the RDP thread.
        self._frameLock = Lock()  # type: Lock
        self._gdiLock = RLock()  # type: RLock # gdi_resize vs. reading GDI's buffer.
        self._fb = None  # bytearray, stride * height.
        self._fbView = None  # ctypes view of _fb for memmove.
        self._fbInfo = (0, 0, 0)  # Width, height, stride.
        self._frameGen = 0  # type: int # Bumped on every published change.
        self._dirty = None  # Union of changed rects since last _takeFrame.
        self._paintHooks = None
        self._gfx = None  # RdpgfxClientContext while the pipeline is up.
        self._wake = None
        self._microphone = False  # type: bool
        self._rdpVersion = None  # Negotiated RDP version, e.g. u'10.12'.
        self._securityProtocol = None  # Negotiated security, e.g. 'NLA (CredSSP)'.
        # What FreeRDP received from the server while connecting (getServerInfo).
        self._certificatePem = None  # the TLS certificate, from VerifyX509Certificate.
        self._certificateInfo = None  # ... Decoded once per connection.
        self._sentIdentity = (u'', u'')  # type: tuple[str, str] # (user, domain) as last sent to FreeRDP.
        self._challenge = None  # the NTLM CHALLENGE of the NLA exchange, decoded.
        self._logon = {}  # Save Session Info: user, domain, session id.
        self._ioSaved = None  # FreeRDP's own transport I/O table while ours is installed.
        self._disconnectReason = None  # Why the last session ended (getDisconnectReason).
        self._disconnectListener = None
        self._aad = False  # Azure AD (Entra ID) sign-in through a FreeRDP AAD helper.
        self._aadHelper = u'auto'  # type: str
        self._aadUserAgent = u''  # type: str
        self._aadResolved = None  # (helper path, environment) for the running session.
        self._aadSavedEnv = None  # What the helper's environment replaced, restored by stop()
        self._transport = u'default'  # type: str
        self._compressedAudio = True  # type: bool # False: PCM only (no audio decoder).
        self._audioLatency = DEFAULT_AUDIO_LATENCY  # type: int
        self._pointers = {}  # address of an rdpPointer -> decoded image.
        self._clipboard = Clipboard(self._post)  # type: Clipboard
        self.previousCrash = None

    def start(self):
        """
        Starts the rdp connection to server.
        :return: None
        """
        if not is_enabled():
            _enableCrashLog()
        crash = lastNativeCrash()
        if crash:
            _log.error(u'The previous session crashed in native code: %s+%s (exception %s, %s)',
                       crash.get(u'module'), crash.get(u'offset'), crash.get(u'exception'),
                       crash.get(u'module_path', u'?'))
        self.previousCrash = crash
        self._resolveAzureAD()
        _markSession(True)
        if self._running:
            return
        self._stop = False  # type: bool
        # self._paused = False  # type: bool
        self._error = None
        self._disconnectReason = None
        self._thread = Thread(target=self._run, name=u'rdp-session', daemon=True)
        self._running = True  # type: bool
        self._thread.start()
        deadline = time() + 30  # type: int
        while time() < deadline and self._running and not self._ready:
            sleep(0.05)
        if not self._ready:
            raise ConnectionError(self._error or u'The RDP session did not become ready')

    def stop(self):
        """
        Stops the rdp connection to the server.
        :return:
        """
        # Deliver what is still queued for the RDP thread (key presses, clicks) while the connection is
        # up: the calls run in order, so once this no-op ran, everything sent before stop() went out.
        # Otherwise they ran in the thread's cleanup, after the abort - and were lost.
        thread = self._thread
        if self._ready and thread and thread.is_alive() and thread is not current_thread():
            try:
                self._call(lambda: None, timeout=2.0)
            except:
                pass  # The RDP thread is stuck: stop anyway.
            # Sent is not yet read: closing with server updates still unread makes the socket close
            # with a TCP reset, and the server discards what it had not read - the last key presses.
            # Linger until INPUT_LINGER after the last input (only when there was any just now).
            linger = self._lastInputAt + INPUT_LINGER - monotonic()  # type: float
            if linger > 0:
                sleep(min(linger, INPUT_LINGER))
        self._stop = True  # type: bool
        # self._paused = False  # type: bool
        if self._ctx:
            self._api.freerdp_abort_connect_context(self._ctx)
        thread = self._thread
        if thread and thread.is_alive() and thread is not current_thread():
            thread.join(timeout=10)
        self._resetState()
        self._restoreAzureADEnvironment()
        _markSession(False)  # a clean stop: not a crash.

    def setPaused(self, paused):
        """
        Pause/Resume RDP displays.
        :param paused: bool
        :return:
        """
        self._paused = bool(paused)  # type: bool

    def setServer(self, hostname):
        """
        Sets the address of server which to connect to.
        :param hostname: (str | unicode) The server address, can be either hostname or ip.
        :return:
        """
        self._host = hostname  # type: str

    def setPort(self, port):
        """
        Sets the address of server which to connect to.
        :param port: (int) The port of the rdp service.
        :return:
        """
        self._port = int(port)  # type: int

    def setUsername(self, username):
        """
        Sets the username of the account on the server which you want to connect.
        :param username: (str | unicode) The username, without a domain name.
            Example if the computer account name is FOO/BAR then use
            setUsername("BAR")
        :return:
        """
        self._user = username  # type: str

    def setPassword(self, password):
        """
        Sets the password of the account on the server which you want to connect.
        :param password: (str | unicode) The password.
        :return:
        """
        self._password = password  # type: str

    def setDomain(self, domain):
        """
        Sets the domain of the account on the server which you want to connect.
        :param domain: (str | unicode) Domain name of the username.
            Example if the computer account name is FOO/BAR then use
            setDomain("FOO")
        :return:
        """
        self._domain = domain  # type: str

    def setDisplaySize(self, width, height):
        """
        Sets the monitor size which will be used in screen transfer.
        :param width: (int) Width of the resulting display. Default=1920
        :param height: (int) Height of the resulting display. Default=1080
        :return:
        """
        self._width, self._height = int(width), int(height)  # type: int, int

    def setAutoReconnect(self, enabled):
        """
        Sets if auto reconnect should be enabled when connection is lost.
        :param enabled: (bool) If set to true AutoReconnect is enabled.
        :return:
        """
        self._autoReconnect = bool(enabled)  # type: bool

    def keyDown(self, scancode):
        """
        Presses a key on the remote keyboard.
        :param scancode: (int) Scancode of the key which is pressed.
        :return:
        """
        self._post(lambda: self._sendScancode(int(scancode), True))

    def keyUp(self, scancode):
        """
        Releases a key on the remote keyboard.
        :param scancode: (int) Scancode of the key which is released.
        :return:
        """
        self._post(lambda: self._sendScancode(int(scancode), False))

    def setBitsPerPixel(self, bpp):
        """
        Sets how many bits should be used for transferring the screen.
        Also sets the format of color to be:
           * BGR565 for 16 bits.
           * BGR888 for 24 bits.
           * ABGR8888 for 32 bits.
        :param bpp: (int) Number of bits. Options are 32, 24 (default) and 16.
        :return:
        """
        bpp = int(bpp)  # type: int
        # Divisible by 8 and at least 16.
        if bpp % 8 or bpp <= 8 or bpp not in _PIXEL_FORMATS:
            raise ValueError(u'bpp has to be 32, 24 or 16')
        self._bpp = bpp  # type: int

    def hotkey(self, *scancodes, **kwargs):
        """
        Performs a hotkey with keys defined in scancodes.
        Keys are pressed down in order and released in reverse order.
        :param scancodes: (list[int] | int) Keys which should be pressed.
        :param delay: (int) Delay between two key events in milliseconds.
        :raises TypeError: No key given, unknown keyword argument or a noninteger delay.
        :raises ValueError: Negative or too large (above 2**32 - 1) delay, invalid key.
        :raises RuntimeError: The session is not connected.
        :return:
        """
        delay = kwargs.pop(u'delay', 20)  # type: int
        if kwargs:
            raise TypeError(u'Unexpected keyword argument(s): %s' % u', '.join(kwargs))
        if not scancodes:
            raise TypeError(u'At least one key to press is needed')
        if not isinstance(delay, int) or isinstance(delay, bool):
            raise TypeError(u'Delay must be an integer')
        if delay < 0 or delay > 2 ** 32 - 1:
            raise ValueError(u'Delay out of range')
        codes = []  # type: list[int | bool]
        for scancode in scancodes:
            if not isinstance(scancode, int) or isinstance(scancode, bool):
                raise ValueError(u'Invalid argument value. Keys need to be set as numeric values.')
            if scancode < 0 or scancode > 0xFFFF:
                raise ValueError(u'Invalid key 0x%X' % scancode)
            codes.append(scancode)
        if not self._ready:
            raise RuntimeError(self._error or u'The session is not connected')
        for scancode in codes:
            self.keyDown(scancode)
            sleep(delay / 1000.0)
        for scancode in reversed(codes):
            self.keyUp(scancode)
            sleep(delay / 1000.0)

    def typeText(self, text, typingDelay=20):
        """
        Types supplied text via remote keyboard.
        :param text: (str | unicode) The text to be typed, can include Unicode characters.
        :param typingDelay: (int) Delay between typing two characters in milliseconds.
        :return:
        """
        self._checkConnected()
        for char in text:
            if char in _TYPED_AS_SCANCODE:
                code = _TYPED_AS_SCANCODE[char]
                self._post(lambda c=code: self._sendScancode(c, True))
                sleep(typingDelay / 1000.0)
                self._post(lambda c=code: self._sendScancode(c, False))
            else:
                self._post(lambda ch=char: self._sendUnicode(ch, True))
                sleep(typingDelay / 1000.0)
                self._post(lambda ch=char: self._sendUnicode(ch, False))

    def mouseMove(self, x, y):
        """
        Moves mouse on the remote machine to coordinates.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        self._mouse(PTR_FLAGS_MOVE, x, y)

    def leftMouseUp(self, x, y):
        """
        Releases the left mouse button at specified coordinates on the remote machine.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        self._mouse(PTR_FLAGS_BUTTON1, x, y)

    def leftMouseDown(self, x, y):
        """
        Presses the left mouse button at specified coordinates on the remote machine.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        self._mouse(PTR_FLAGS_DOWN | PTR_FLAGS_BUTTON1, x, y)

    def rightMouseUp(self, x, y):
        """
        Releases the right mouse button at specified coordinates on the remote machine.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        self._mouse(PTR_FLAGS_BUTTON2, x, y)

    def rightMouseDown(self, x, y):
        """
        Presses the right mouse button at specified coordinates on the remote machine.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        self._mouse(PTR_FLAGS_DOWN | PTR_FLAGS_BUTTON2, x, y)

    def middleMouseUp(self, x, y):
        """
        Releases the middle mouse button at specified coordinates on the remote machine.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        self._mouse(PTR_FLAGS_BUTTON3, x, y)

    def middleMouseDown(self, x, y):
        """
        Presses the middle mouse button at specified coordinates on the remote machine.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        self._mouse(PTR_FLAGS_DOWN | PTR_FLAGS_BUTTON3, x, y)

    def mouseScroll(self, x, y, down=True):
        """
        Scrolls the mouse on the remote machine on specified coordinates.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :param down: (bool) If True scrolls down otherwise scrolls up.
        :return:
        """
        self._mouse(_WHEEL_DOWN if down else _WHEEL_UP, x, y)

    def getDisplay(self, displayFormat=None):
        """
        Returns the current screen of the remote pc.
        Size of the display can be changed by `setDisplaySize`
        :param displayFormat: (str | unicode | None) Type of the returned screen, one of
            `numpy`  - numpy.ndarray (height, width, bpp/8) of BGR(A) pixels, ready for OpenCV,
            `pillow` - PIL.Image.Image in RGB or RGBA,
            `qimage` - QImage (needs ManyQt and a Qt binding),
            `bytes`  - raw BGR(A) pixels, tightly packed row after row,
            `tuple`  - (width, height, channels, bytes).
            None uses the format set by `setDisplayFormat` (`numpy` by default).
        :raises ValueError: Unknown display format.
        :raises ImportError: The library the format needs is not installed.
        :raises ConnectionError: The session is not connected.
        :return: The RDP screen.
        """
        displayFormat = (displayFormat or self._displayFormat).lower()  # type: str
        if displayFormat not in DISPLAY_FORMATS:
            raise ValueError(_DISPLAY_FORMAT_ERROR)
        self._checkConnected()
        width, height, stride, data = self._snapshot()
        channels = self._bpp // 8  # type: int
        if stride != width * channels:  # Drop the row padding once, for every format.
            row = width * channels  # type: int
            data = b''.join(data[y * stride:y * stride + row] for y in range(height))
        return _convertFrame(displayFormat, width, height, channels, data)

    def setDisplayFormat(self, displayFormat):
        """
        Sets the default type returned by `getDisplay`.
        :param displayFormat: (str | unicode) One of `numpy`, `pillow`, `qimage`, `bytes`, `tuple`.
        :raises ValueError: Unknown display format.
        :return:
        """
        displayFormat = str(displayFormat).lower()  # type: str
        if displayFormat not in DISPLAY_FORMATS:
            raise ValueError(_DISPLAY_FORMAT_ERROR)
        self._displayFormat = displayFormat  # type: str

    def setClipboardListener(self, listener):
        """
        Registers a function called whenever the remote clipboard changes.
        It is called from the RDP thread with a dict {"text": bool, "files": bool}
        telling what the remote clipboard now offers; use `loadClipboard` from your
        own thread to fetch the content.
        :param listener: (callable | None) The function, or None to remove it.
        :return:
        """
        if listener is not None and not callable(listener):
            raise TypeError(u'Listener must be callable or None')
        self._clipboard.listener = listener

    def saveClipboard(self, preferredType, data, includeParent=False):
        """
        Sets the remote clipboard to this preferred type.
        :param preferredType: (str | unicode) Value of either `text` or `file`.
        :param data: (str | unicode) String or path to either a dir or a file. Path is used when set to
                     file mode and string when texted.
        :param includeParent: (bool) Set to True if the parent of path be included while saving the clipboard.
        :return:
        """
        self._checkClipboard(preferredType)
        if preferredType == u'text':
            if not hasattr(data, u'encode'):
                raise TypeError(u'Text mode needs a str')
            self._clipboard.saveText(data)
        else:
            if not (isinstance(data, (str, list, tuple)) or hasattr(data, u'encode')):
                raise TypeError(u'File mode needs a path or a list of paths')
            self._clipboardCall(self._clipboard.saveFiles, data, includeParent)
        sleep(0.1)  # Waits as well.

    def loadClipboard(self, preferredType, dirPath=None, filePattern=None):
        """
        Loads data from remote clipboard based by the preferred type.
        :param preferredType: (str | unicode) Value of either `text` or `file`.
        :param dirPath: (str | unicode) Path to a directory where the files from remote clipboard
                         will be downloaded. Only used with file mode.
        :param filePattern: (str | unicode) Download only files following this pattern. Only used with file mode.
        :return: Text from the server or Path which the files were downloaded to.
        """
        self._checkClipboard(preferredType)
        self._clipboard.waitForFormats(1.0)
        if preferredType == u'text':
            return self._clipboardCall(self._clipboard.loadText)
        return self._clipboardCall(self._clipboard.loadFiles, dirPath or getcwd(), filePattern)

    def loadSharedDirectory(self, dirPath, dirName=u''):
        """
        Loads folder as a shared directory.
        The folder appears on the remote machine as a redirected drive
        (in Explorer under "This PC" as "<dirName> on <client>"). A path to a
        file shares the folder that contains it. Several folders can be shared;
        each must be added before `start`, or the session has to be restarted
        for it to appear.
        :param dirPath: (str | unicode) Path to the directory.
        :param dirName: (str | unicode) Name of the directory, if left empty the system directory name will be used.
        :raises ValueError: The path does not exist.
        :return:
        """
        pth = abspath(expanduser(dirPath))  # type: str
        if isfile(pth):
            pth = dirname(pth)  # type: str
        if not isdir(pth):
            raise ValueError(u'No such directory: %s' % dirPath)
        name = dirName or basename(normpath(pth)) or pth.rstrip(u':\\/') or u'share'  # type: str
        if any(n == name or p == pth for n, p in self._drives):
            return
        self._drives.append((name, pth))
        if self._running:
            _log.warning(u'loadSharedDirectory(%s): restart the session (stop/start) for it to appear', name)

    def getSharedDirectories(self):
        """
        Returns the folders shared with `loadSharedDirectory`.
        :return: (list[tuple]) (name, path) pairs.
        """
        return list(self._drives)

    def getServer(self):
        """
        Returns the server set with `setServer`.
        :return: (str | unicode) The hostname or IP address.
        """
        return self._host

    def getPort(self):
        """
        Returns the port set with `setPort`.
        :return: (int) The port number.
        """
        return self._port

    def getUsername(self):
        """
        Returns the username set with `setUsername`.
        :return: (str | unicode) The username.
        """
        return self._user

    def getPassword(self):
        """
        Returns the password set with `setPassword`.
        :return: (str | unicode) The password.
        """
        return self._password

    def getDomain(self):
        """
        Returns the domain set with `setDomain`.
        :return: (str | unicode) The domain.
        """
        return self._domain

    def getDisplaySize(self):
        """
        Returns the display size set with `setDisplaySize`; after a server-side resize, the current one.
        :return: (tuple[int, int]) (width, height).
        """
        return self._width, self._height

    def getDisplayWidth(self):
        """
        Returns the display width.
        :return: (int) Width in pixels.
        """
        return self._width

    def getDisplayHeight(self):
        """
        Returns the display height.
        :return: (int) Height in pixels.
        """
        return self._height

    def isAutoReconnect(self):
        """
        Returns whether automatic reconnection is enabled.
        :return: bool
        """
        return self._autoReconnect

    def isPaused(self):
        """
        :return: bool
        """
        return self._paused

    def getBitsPerPixel(self):
        """
        Returns the color depth set with `setBitsPerPixel`.
        :return: (int) 32, 24 or 16.
        """
        return self._bpp

    def getGraphics(self):
        """
        Returns the graphics option set with `setGraphics`.
        :return: (str | unicode) e.g. `auto`, `AVC444`, `off`.
        """
        return self._graphics

    def getFreerdpCliArgs(self):
        """
        Returns the extra FreeRDP command line arguments.
        :return: (list[str]) The arguments.
        """
        return list(self._cliArgs)

    def getDisplayFormat(self):
        """
        Returns the default type returned by `getDisplay`.
        :return: (str | unicode) `numpy`, `pillow`, `qimage`, `bytes` or `tuple`.
        """
        return self._displayFormat

    def isSound(self):
        """
        Returns whether the remote sound is played locally.
        :return: bool
        """
        return self._sound

    def isMicrophone(self):
        """
        Returns whether the local microphone is redirected.
        :return: bool
        """
        return self._microphone

    def isCompressedAudio(self):
        """
        Returns whether compressed audio formats are allowed.
        :return: bool
        """
        return self._compressedAudio

    def isGraphicsPipelineActive(self):
        """
        Returns whether the Graphics Pipeline (GFX) channel is active in the current session.
        :return: bool
        """
        return bool(self._gfx)

    def getLastError(self):
        """
        Returns the last connection error message, if any.
        :return: (str | unicode | None) The message.
        """
        return self._error

    def getSessionInfo(self):
        """
        Returns the status of the connection and information about the session: configuration,
        connection state, graphics/sound/clipboard/sharing status, FreeRDP version and frame counters,
        the negotiated RDP version and security protocol, and what FreeRDP received from the server
        while connecting (see `getServerInfo`; None before the first connection).
        :return: (dict) Keys: server, port, username, domain, width, height, bitsPerPixel, graphics,
            graphicsPipeline, sound, microphone, compressedAudio, clipboard, fileClipboard, sharedDirectories, running,
            ready, reconnecting, lastError, framesPublished, freerdpVersion, rdpVersion, securityProtocol, serverInfo,
            azureAD, transport.
        """
        try:
            version = self._api.version()  # type: str
        except:
            version = u''  # type: str
        return {
            u'server': self._host,
            u'port': self._port,
            u'username': self._user,
            u'domain': self._domain,
            u'width': self._width,
            u'height': self._height,
            u'bitsPerPixel': self._bpp,
            u'graphics': self._graphics,
            u'graphicsPipeline': self.isGraphicsPipelineActive(),
            u'sound': self._sound,
            u'microphone': self._microphone,
            u'compressedAudio': self._compressedAudio,
            u'clipboard': bool(self._clipboard.ready),
            u'fileClipboard': self.isFileClipboardEnabled,
            u'sharedDirectories': self.getSharedDirectories(),
            u'running': self.isRunning,
            u'ready': self.isReady,
            u'reconnecting': self.isReconnecting,
            u'lastError': self._error,
            u'framesPublished': self._frameGen,
            u'freerdpVersion': version,
            u'rdpVersion': self._rdpVersion,
            u'securityProtocol': self._securityProtocol,
            u'serverInfo': self.getServerInfo(),
            u'azureAD': dict(self.getAzureAD(), helperPath=self._aadResolved[0] if self._aadResolved else None),
            u'transport': self._transport,
        }

    def getServerInfo(self):
        """
        Returns what FreeRDP received from the server while connecting - no extra connection is made:
        the TLS certificate FreeRDP verified, decoded by FreeRDP's certificate API (subject, issuer,
        validity, signature algorithm, key type, SHA-256/SHA-1 fingerprints, alternative names, PEM),
        the NTLM challenge of its NLA exchange (Windows version, build and name, NetBIOS/DNS computer,
        domain and forest names, server clock), the Save Session Info data (logged-on user, domain, session id),
        and the negotiated RDP version and security protocol.
        :return: (dict | None) Keys: certificate {subject, issuer, commonName, selfSigned, notBefore,
            notAfter, daysLeft, expired, validity, signature, publicKey, sha256, sha1, email, upn,
            subjectAltNames, pem}, computer {osVersion, osName, osMajor, osMinor, osBuild, netbiosComputerName,
            netbiosDomainName, dnsComputerName, dnsDomainName, dnsTreeName, serverTime},
            logon {username, domain, sessionId, logonId}, rdpVersion, securityProtocol.
            None before the first connection.
        """
        info = {}  # type: dict
        if self._certificatePem:
            if self._certificateInfo is None:  # Once per connection, not on every status refresh.
                try:
                    self._certificateInfo = describeCertificate(self._api, self._certificatePem)
                except Exception as exc:
                    self._certificateInfo = {u'error': u'{}'.format(exc)}
                self._certificateInfo[u'pem'] = self._certificatePem
            info[u'certificate'] = dict(self._certificateInfo)
        if self._challenge:
            info[u'computer'] = dict(self._challenge)
        if self._logon:
            info[u'logon'] = dict(self._logon)
        if self._rdpVersion:
            info.update(rdpVersion=self._rdpVersion, securityProtocol=self._securityProtocol)
        return info or None

    def getDisconnectReason(self):
        """
        Returns why the last session ended or the last connection failed, as FreeRDP reports it:
        the server's reason (its Error Info, e.g. logged off, idle timeout, disconnected by an
        administrator) and FreeRDP's own last error.
        :return: (dict | None) Keys: phase (`connect` or `session`), byUser (bool: `stop` was called),
            message (str: the main cause, in words), serverCode (int), serverName (str), serverMessage (str),
            serverCategory (str), errorCode (int), errorName (str), errorMessage (str), errorCategory (str).
            None while connected or before the first connection.
        """
        return dict(self._disconnectReason) if self._disconnectReason else None

    def setDisconnectListener(self, listener):
        """
        Sets a function called when a session ends, or a connection fails, without `stop` being
        called. It runs on the RDP thread and receives the dict returned by `getDisconnectReason`.
        :param listener: (callable | None) listener(reason) or None to remove it.
        :return:
        """
        self._disconnectListener = listener

    def _recordDisconnect(self, phase):
        """
        Keep why the session ended, from FreeRDP: the server's Error Info and FreeRDP's last error.
        Tell the listener unless `stop` ended it.
        :param phase: (str | unicode) `connect` or `session`.
        :return:
        """
        api = self._api

        def text(value):
            """
            :param value: (bytes | None) A static FreeRDP string.
            :return: str | unicode
            """
            return value.decode(u'utf-8', u'replace') if isinstance(value, bytes) else u''

        serverCode = int(api.freerdp_error_info(self._instance)) if self._instance else 0
        errorCode = int(api.freerdp_get_last_error(self._ctx)) if self._ctx else 0
        reason = {
            u'phase': phase, u'byUser': bool(self._stop),
            u'serverCode': serverCode, u'serverName': text(api.freerdp_get_error_info_name(serverCode)),
            u'serverMessage': text(api.freerdp_get_error_info_string(serverCode)),
            u'serverCategory': text(api.freerdp_get_error_info_category(serverCode)),
            u'errorCode': errorCode, u'errorName': text(api.freerdp_get_last_error_name(errorCode)),
            u'errorMessage': text(api.freerdp_get_last_error_string(errorCode)),
            u'errorCategory': text(api.freerdp_get_last_error_category(errorCode)),
        }
        if reason[u'byUser']:
            reason[u'message'] = u'You ended the session.'
        elif serverCode:  # The server said why (Error Info PDU).
            reason[u'message'] = reason[u'serverMessage'] or reason[u'serverName']
        elif errorCode:
            reason[u'message'] = self._error if phase == u'connect' and self._error else reason[u'errorMessage']
        else:
            reason[u'message'] = self._error or u'The connection was closed.'
        self._disconnectReason = reason
        _log.info(u'%s ended: %s', phase, reason[u'message'])
        listener = self._disconnectListener  # type: callable
        if listener is not None and not reason[u'byUser']:
            try:
                if callable(listener):
                    listener(dict(reason))
            except:
                _log.exception(u'Disconnect listener failed')

    def setAzureAD(self, enabled, helper=u'auto', userAgent=u''):
        """
        Signs in with Azure AD (Entra ID) instead of a password (RDS AAD: Azure / Entra joined hosts,
        Azure Virtual Desktop). The Microsoft login page opens in a FreeRDP AAD helper - a separate
        program shipped with pyfreerdpnative - and the session gets its access token from there.
        Set it before `start`.
        :param enabled: (bool) True to sign in with Azure AD.
        :param helper: (str | unicode) `auto` (the webview helper, else the Qt one), `webview` (the
            operating system's browser engine: WebKitGTK, WKWebView, Edge WebView2), `qt` (Qt
            WebEngine - from the system, PySide6-WebEngine or PyQt6-WebEngine), or the path to any
            program speaking FreeRDP's AAD helper protocol.
        :param userAgent: (str | unicode) User-Agent the login page sees (FreeRDP 3.33
            /azure:user-agent); empty for the browser's own.
        :return:
        """
        self._aad = bool(enabled)  # type: bool
        self._aadHelper = u'{}'.format(helper or u'auto')
        self._aadUserAgent = u'{}'.format(userAgent or u'')

    def getAzureAD(self):
        """
        Returns the Azure AD sign-in configuration.
        :return: (dict) Keys: enabled (bool), helper (str), userAgent (str).
        """
        return {u'enabled': self._aad, u'helper': self._aadHelper, u'userAgent': self._aadUserAgent}

    def setTransport(self, mode):
        """
        Chooses the transport (FreeRDP 3.33 client UDP multitransport, needs a FreeRDP built with
        WITH_RDPEUDP): `default` (FreeRDP's choice), `udp` (accept the server's UDP offer),
        `udp-preferred` (also carry the static channels over UDP) or `tcp-only` (decline UDP).
        Set it before `start`.
        :param mode: (str | unicode) One of default, udp, udp-preferred, tcp-only.
        :return:
        """
        mode = u'{}'.format(mode or u'default').lower()
        if mode not in TRANSPORTS:
            raise ValueError(u'Transport must be one of: {}'.format(u', '.join(TRANSPORTS)))
        self._transport = mode

    def getTransport(self):
        """
        Returns the transport set with `setTransport`.
        :return: (str | unicode) default, udp, udp-preferred or tcp-only.
        """
        return self._transport

    def _resolveAzureAD(self):
        """
        Find the AAD helper (pyfreerdpnative.aad) and give it its environment - the Qt helper needs
        to find a Qt WebEngine. On the calling thread, so a missing helper fails start() at once.
        FreeRDP starts the helper with this process's environment, while connecting.
        :return:
        """
        self._restoreAzureADEnvironment()  # A retry must not save our own values as the originals.
        self._aadResolved = None
        if not self._aad:
            return
        try:
            from pyfreerdpnative.aad import helper
        except:
            raise ConnectionError(u'Azure AD sign-in needs pyfreerdpnative with FreeRDP 3.33 (pyfreerdpnative.aad)')
        try:
            helperPath, env = helper(self._aadHelper)
        except LookupError as exc:
            raise ConnectionError(u'Azure AD sign-in: {}'.format(exc))
        if not self._api.has(u'client_helper_get_access_token'):
            raise ConnectionError(u'Azure AD sign-in: these FreeRDP libraries have no client_helper_get_access_token')
        self._aadSavedEnv = dict((k, environ.get(k)) for k in env)
        environ.update(env)
        self._aadResolved = (helperPath, env)
        _log.info(u'Azure AD sign-in through %s', helperPath)

    def _restoreAzureADEnvironment(self):
        """
        :return:
        """
        saved, self._aadSavedEnv = self._aadSavedEnv, None
        for key, value in (saved or {}).items():
            if value is None:
                environ.pop(key, None)
            else:
                environ[key] = value

    def _applyAzureADAndTransport(self, settings):
        """
        The settings /azure:auth-helper:, /azure:user-agent: and /multitransport: would set.
        :param settings: POINTER(rdpSettings)
        :return: None
        """
        if self._aadResolved:
            helperPath, _env = self._aadResolved
            strings = [(FreeRDP_AadAuthHelper, helperPath)]
            if FreeRDP_AadAuthUserAgent is not None:
                strings.append((FreeRDP_AadAuthUserAgent, self._aadUserAgent))
            self._writeSettings(settings, strings=tuple(strings), flags=((FreeRDP_AadSecurity, True),))
            # FreeRDP's own C implementation drives the helper: GetAccessToken is variadic, which a
            # Python callback cannot implement - the C function's address goes in instead.
            instance = self._instance.contents
            address = cast(self._api.client_helper_get_access_token, c_void_p).value
            instance.GetAccessToken = type(instance.GetAccessToken)(address)
        udpKey = FreeRDP_SupportMultitransportUdp
        if self._transport == u'default' or udpKey is None:
            return
        udp = self._transport != u'tcp-only'
        flags = []
        if udp:  # client/common/cmdline.c, /multitransport:udp[-preferred]
            value = TRANSPORT_TYPE_UDP_FECR | SOFTSYNC_TCP_TO_UDP
            if self._transport == u'udp-preferred':
                value |= TRANSPORT_TYPE_UDP_PREFERRED
            flags = [(FreeRDP_MultitransportFlags, value)]
        self._writeSettings(settings, flags=((udpKey, udp),), numbers=tuple(flags))

    def setSound(self, enabled, microphone=False, compressed=True):
        """
        Enables the remote sound: audio played on the remote machine is played
        locally (on by default). FreeRDP picks the platform's audio backend
        (WinMM on Windows, Core Audio on macOS, ALSA - which also reaches
        PulseAudio/PipeWire - on Linux, OpenSL ES on Android). Set it before `start`.
        :param enabled: (bool) True to play the remote sound locally, False for silence.
        :param microphone: (bool) True to also redirect the local microphone.
        :param compressed: (bool) True (default) to allow compressed audio formats (AAC, ...),
            False for uncompressed PCM only (more bandwidth, no audio decoder involved).
        :return:
        """
        self._sound = bool(enabled)  # type: bool
        self._microphone = bool(microphone)  # type: bool
        self._compressedAudio = bool(compressed)  # type: bool

    def setAudioLatency(self, milliseconds):
        """
        Sets the audio playback buffer target, in milliseconds (default 50; 0 = the audio backend's own
        default, 100 for PulseAudio/PipeWire). FreeRDP reports the real playback latency to the server in
        every Wave Confirm and the server synchronizes audio and video with it, so a short buffer keeps the
        sound with the picture; raise it on a jittery network if the sound stutters. Set it before `start`.
        :param milliseconds: (int) 0 to 2000.
        :raises ValueError: Out of range.
        :return:
        """
        milliseconds = int(milliseconds)
        if not 0 <= milliseconds <= 2000:
            raise ValueError(u'Audio latency must be 0 to 2000 ms')
        self._audioLatency = milliseconds  # type: int

    def getAudioLatency(self):
        """
        Returns the audio playback buffer target set with `setAudioLatency`.
        :return: (int) Milliseconds; 0 = the backend's default.
        """
        return self._audioLatency

    def setStartProgram(self, command, workingDir=u''):
        """
        Starts a program with the session, through the protocol (no keyboard, no clipboard): it is sent with
        the logon information and the server runs it instead of the desktop - the "alternate shell"
        (mstsc's "Start the following program on connection"). When it exits, the session ends. The server
        must allow it (policy "Start a program on connection"; Windows client editions may ignore it).
        Set it before `start`; an empty command turns it off.
        :param command: (str | unicode) The command line, e.g. `notepad` or `cmd /k ipconfig`.
        :param workingDir: (str | unicode) Its working folder (optional).
        :return:
        """
        self._startProgram = (u'{}'.format(command or u'').strip(), u'{}'.format(workingDir or u''))

    def getStartProgram(self):
        """
        Returns the program set with `setStartProgram`.
        :return: (tuple[str, str]) (command line, working folder); empty when none.
        """
        return self._startProgram

    def setRemoteApp(self, program, arguments=u'', workingDir=u''):
        """
        Connects as a RemoteApp session: the server runs the program and the session shows its windows,
        not a desktop. Programs are started through the RemoteApp channel (MS-RDPERP Client Execute) - no
        keyboard, no clipboard - and more can be started later with `runCommand`. The server must offer
        RemoteApp and allow the program (published, or "Allow remote start of unlisted programs"). Set it
        before `start`; an empty program turns it off.
        :param program: (str | unicode) The program, e.g. `notepad` or a full path.
        :param arguments: (str | unicode) Its command-line arguments (optional).
        :param workingDir: (str | unicode) Its working folder (optional; %VARIABLES% are expanded).
        :return:
        """
        program = u'{}'.format(program or u'').strip()
        self._remoteApp = (program, u'{}'.format(arguments or u''),
                           u'{}'.format(workingDir or u'')) if program else None

    def getRemoteApp(self):
        """
        Returns the RemoteApp set with `setRemoteApp`.
        :return: (tuple[str, str, str] | None) (program, arguments, working folder), or None.
        """
        return self._remoteApp

    def isRemoteApp(self):
        """
        :return: (bool) True while connected as a RemoteApp session with its channel up (`runCommand` works).
        """
        return bool(self._remoteApp and self._rail)

    def runCommand(self, program, arguments=u'', workingDir=u'', timeout=15.0):
        """
        Starts another program in a RemoteApp session through the protocol (Client Execute on the RemoteApp
        channel - no keyboard, no clipboard) and waits for the server's answer.
        :param program: (str | unicode) The program, e.g. `cmd` or a full path.
        :param arguments: (str | unicode) Its arguments (optional; %VARIABLES% are expanded).
        :param workingDir: (str | unicode) Its working folder (optional).
        :param timeout: (float | int) Seconds to wait for the server's answer.
        :raises ValueError: No program given.
        :raises RuntimeError: Not a RemoteApp session, or the server refused - with its reason (not
            allowed, not found, session locked...).
        :raises TimeoutError: The server did not answer.
        :return:
        """
        program = u'{}'.format(program or u'').strip()
        if not program:
            raise ValueError(u'Nothing to run')
        if not self.isRemoteApp():
            raise RuntimeError(u'Without keyboard or clipboard, RDP starts programs only through RemoteApp: connect '
                               u'with setRemoteApp (or start one program with the session: setStartProgram).')
        with self._execCondition:
            seen = len(self._execResults)
        texts = [x.encode(u'utf-8') for x in (program, u'{}'.format(workingDir or u''), u'{}'.format(arguments or u''))]

        def send():
            """
            :return: (int) The channel's status.
            """
            order = RAIL_EXEC_ORDER()
            order.flags = RAIL_EXEC_FLAGS
            order.RemoteApplicationProgram, order.RemoteApplicationWorkingDir, order.RemoteApplicationArguments = texts
            return self._rail.contents.ClientExecute(self._rail, byref(order))

        status = self._call(send)
        if status:
            raise RuntimeError(u'The RemoteApp channel did not send the request (error {})'.format(status))
        with self._execCondition:
            if not self._execCondition.wait_for(lambda: len(self._execResults) > seen, timeout):
                raise TimeoutError(u'The server did not answer within {:g} s'.format(timeout))
            result, raw = self._execResults[seen]
        if result != RAIL_EXEC_S_OK:
            raise RuntimeError(u'{} could not be started: {} (code {}, 0x{:08X})'.format(
                program, RAIL_EXEC_ERRORS.get(result, u'error'), result, raw))

    def _applyPrograms(self, settings):
        """
        The program to start, through the protocol: the alternate shell of a desktop session (sent with
        the logon information) and/or a RemoteApp session (FreeRDP then loads the rail channel).
        :param settings: POINTER(rdpSettings)
        :return:
        """
        shell, shellDir = self._startProgram
        if self._remoteApp:
            program, arguments, workingDir = self._remoteApp
            self._writeSettings(settings, flags=((FreeRDP_RemoteApplicationMode, True),),
                                strings=((FreeRDP_RemoteApplicationProgram, program),
                                         (FreeRDP_RemoteApplicationName, basename(program)),
                                         (FreeRDP_RemoteApplicationCmdLine, arguments),
                                         (FreeRDP_ShellWorkingDirectory, workingDir)))
        elif shell:
            self._writeSettings(
                settings, strings=((FreeRDP_AlternateShell, shell), (FreeRDP_ShellWorkingDirectory, shellDir)))

    def waitForRemoteApp(self, timeout=15.0):
        """
        Waits for the server's answer on the program of a RemoteApp session (`setRemoteApp`): it is
        started through the RemoteApp channel while the session comes up.
        :param timeout: (float | int) Seconds to wait.
        :raises RuntimeError: The server refused it - with its reason (not allowed, not found...).
        :raises TimeoutError: No answer (not a RemoteApp session, or a server without RemoteApp).
        :return:
        """
        with self._execCondition:
            if not self._execCondition.wait_for(lambda: bool(self._execResults), timeout):
                raise TimeoutError(u'The server did not start the RemoteApp within {:g} s'.format(timeout))
            result, raw = self._execResults[0]
        if result != RAIL_EXEC_S_OK:
            program = (self._remoteApp or (u'the program',))[0]
            raise RuntimeError(u'{} could not be started: {} (code {}, 0x{:08X})'.format(
                program, RAIL_EXEC_ERRORS.get(result, u'error'), result, raw))

    def _railHandshake(self, context, handshake):
        """
        RDP thread: the server's RemoteApp handshake. FreeRDP's own start sequence answers it - client
        information, system parameters, then Client Execute of the program set with setRemoteApp.
        :return: (int) Channel status.
        """
        return self._api.client_rail_server_start_cmd(context)

    def _railExecuteResult(self, context, result):
        """
        RDP thread: the server's verdict on a Client Execute.
        :return: (int) Channel status.
        """
        entry = (int(result.contents.execResult), int(result.contents.rawResult))
        with self._execCondition:
            self._execResults.append(entry)
            self._execCondition.notify_all()
        if entry[0] != RAIL_EXEC_S_OK:
            _log.warning(u'RemoteApp refused: %s (code %d)', RAIL_EXEC_ERRORS.get(entry[0], u'error'), entry[0])
        return 0

    def _attachRail(self, iface):
        """
        The RemoteApp channel is up: answer the handshake, collect execute results.
        :param iface: (int) The RailClientContext*.
        :return:
        """
        rail = cast(iface, POINTER(RailClientContext))
        contents = rail.contents
        handshake = type(contents.ServerHandshake)(self._railHandshake)
        handshakeEx = type(contents.ServerHandshakeEx)(lambda ctx, hs: self._railHandshake(ctx, hs))
        result = type(contents.ServerExecuteResult)(self._railExecuteResult)
        self._railRefs = [handshake, handshakeEx, result]
        contents.ServerHandshake, contents.ServerHandshakeEx, contents.ServerExecuteResult = self._railRefs
        # FreeRDP calls these handlers only while `custom` is set - its own clients put their context there.
        contents.custom = cast(self._ctx, c_void_p)
        self._rail = rail

    def uploadFiles(self, paths, toDesktop=True, timeout=600.0, progress=None):
        """
        Uploads files or folders into the remote session: they go on the remote clipboard and the session
        pastes them - on the desktop (Win+D, a click on it, Ctrl+V), or with toDesktop=False wherever the
        remote focus is (e.g. an open Explorer folder) - and the remote side downloads them through the
        clipboard channel. Blocks until every byte has arrived: run it on a worker thread in a GUI.
        :param paths: (str | unicode | list[str]) Files and/or folders.
        :param toDesktop: (bool) True: paste on the remote desktop; False: paste where the focus is.
        :param timeout: (float | int) Seconds the transfer may take once started.
        :param progress: (callable | None) progress(received, total) with byte counts, repeatedly.
        :raises FileNotFoundError: A path does not exist.
        :raises PermissionError: The server forbids file copy through the clipboard (its policy).
        :raises TimeoutError: Nothing was pasted, or the transfer did not finish in time.
        :return: (int) The bytes delivered.
        """
        paths = [paths] if hasattr(paths, u'encode') else list(paths)
        paths = [abspath(p) for p in paths]
        missing = [p for p in paths if not exists(p)]
        if not paths or missing:
            raise FileNotFoundError(u'No such file: {}'.format(u', '.join(missing) or u'(none given)'))
        deadline = monotonic() + 20
        while not self.isFileClipboardEnabled and monotonic() < deadline:
            sleep(0.2)
        if not self.isFileClipboardEnabled:
            raise PermissionError(u'The server does not allow copying files through the clipboard (its Remote '
                                  u'Desktop policy) - share the folder instead and copy from \\\\tsclient.')
        self.saveClipboard(u'file', paths if len(paths) > 1 else paths[0])
        received, total = self.getFileTransferProgress()
        if toDesktop:
            width, height = self.getDisplaySize()
            target = int(width * 0.6), int(height * 0.45)  # most likely empty; an icon there is only selected
            self.hotkey(LEFT_WINDOW, KEY_D)  # show the desktop - a toggle, so sent once only
            sleep(1.0)
        for attempt in (1, 2):
            if toDesktop:
                self.leftMouseDown(*target)
                self.leftMouseUp(*target)
                sleep(0.3)
            self.hotkey(LEFT_CONTROL, KEY_V)  # paste - the remote side downloads the files
            deadline = monotonic() + 15
            while monotonic() < deadline and not (self.getFileTransferProgress()[0] > 0 or
                                                  (total == 0 and self.isFileTransferFinished)):
                sleep(0.2)
            if self.getFileTransferProgress()[0] > 0 or (total == 0 and self.isFileTransferFinished):
                break
            # Nothing requested at all: no paste happened, so a retry cannot duplicate the files.
        else:
            raise TimeoutError(u'The remote side did not paste - is the session showing its desktop (not a '
                               u'logon, first-logon or permission screen)?')
        deadline = monotonic() + timeout
        while not self.isFileTransferFinished and monotonic() < deadline:
            if progress is not None:
                progress(*self.getFileTransferProgress())
            sleep(0.25)
        received, total = self.getFileTransferProgress()
        if progress is not None:
            progress(received, total)
        if not self.isFileTransferFinished:
            raise TimeoutError(u'Upload incomplete: {:,} of {:,} bytes after {:g} s'.format(received, total, timeout))
        return total

    def setFrameListener(self, listener):
        """
        Registers a function called whenever a new frame is published - the moment FreeRDP has
        finished painting it - so a viewer can show it at once instead of polling. It is called
        from the RDP thread as listener(), outside every lock: keep it short (e.g. emit a queued
        Qt signal) and fetch the frame from your own thread. None unregisters.
        :param listener: (callable | None) The function.
        :return:
        """
        self._frameListener = listener

    def setPointerListener(self, listener):
        """
        Registers a function called whenever the remote mouse pointer changes.
        It is called from the RDP thread as listener(state, data) with state one of
            `set`      - data is (width, height, hotX, hotY, pixels): pixels are
                         width*height*4 bytes of BGRA,
            `hidden`   - the pointer is hidden, data is None,
            `default`  - the system default pointer, data is None,
            `position` - the server moved the pointer, data is (x, y).
        :param listener: (callable | None) The function, or None to remove it.
        :return:
        """
        if listener is not None and not callable(listener):
            raise TypeError(u'Listener must be callable or None')
        self._pointerListener = listener

    @property
    def isRunning(self):
        """
        Used to check if the machine is running.
        :return: (bool) True if it's running. False otherwise.
        """
        return self._running

    @property
    def isReady(self):
        """
        Used to check if the machine is ready for incoming instructions.
        :return: (bool) True if it readies. False otherwise.
        """
        return self._ready

    @property
    def isReconnecting(self):
        """
        Used to check if the machine is currently reconnecting.
        :return: (bool) True if it's reconnecting. False otherwise.
        """
        return self._reconnecting

    @property
    def isFileTransferFinished(self):
        """
        Used to check if file transfer to remote machine has finished.
        :return: (bool) True if the transfer has finished. False otherwise.
        """
        return self._clipboard.uploadFinished()

    def getFileTransferProgress(self):
        """
        Returns how much of the files on the remote clipboard (`saveClipboard` in file mode) the remote
        side has received - it downloads them when they are pasted there.
        :return: (tuple[int, int]) (bytes received, bytes offered).
        """
        return self._clipboard.uploadProgress()

    @property
    def isFileClipboardEnabled(self):
        """
        Used to check if file transfer is available.
        :return: (bool) True if it files can be transferred. False otherwise.
        """
        return bool(self._ready and self._clipboard.ready and self._clipboard.fileClipboard)

    def setGraphics(self, graphicsOption):
        """
        Used to set graphics options according to FreeRDP specification.
        :param graphicsOption: (str | unicode) Which graphics option should be used.
        :return:
        """
        self._graphics = graphicsOption

    def setFreerdpCliArgs(self, cliArgs):
        """
        Used to configure FreeRdp via its command-line options.
        Compatible args can be found at https://github.com/FreeRDP/FreeRDP/wiki/CommandLineInterface
        :param cliArgs: (str | unicode | list[str | unicode]) Arguments either as a string with spaces between
                                                              arguments or a list of arguments.
        :return:
        """
        if hasattr(cliArgs, u'encode'):
            cliArgs = cliArgs.split()  # type: list[str]
        self._cliArgs = list(cliArgs)  # type: list[str]

    # ------------------------------------------------------------------ internals

    def _checkConnected(self):
        """
        :return:
        """
        if not self._ready:
            raise ConnectionError(self._error or u'The session is not connected')

    def _checkClipboard(self, preferredType=None):
        """
        The checks every clipboard call shares.
        :param preferredType: (str | unicode | None) `text` or `file`, validated when given.
        :return:
        """
        if preferredType is not None and preferredType not in (u'text', u'file'):
            raise ValueError(u'PreferredType must be \'text\' or \'file\'')
        self._checkConnected()
        if not self._clipboard.ready:
            raise RDPClipboardError(u'The clipboard channel is not available')
        if preferredType == u'file' and not self.isFileClipboardEnabled:
            raise RDPClipboardError(u'The server does not support file transfer over the clipboard')

    @staticmethod
    def _clipboardCall(fn, *args):
        """
        Run a clipboard transfer; I/O failures (timeouts included) become RDPClipboardError.
        :param fn: callable
        :param args: any
        :return: any
        """
        try:
            return fn(*args)
        except (OSError, IOError) as exc:
            raise RDPClipboardError(str(exc))

    def _resetState(self):
        """
        Not running, not connected, not reconnecting.
        :return:
        """
        self._running = False  # type: bool
        self._ready = False  # type: bool
        self._reconnecting = False  # type: bool

    def _wakeUp(self):
        """
        Wake the event loop at once (queued input/calls are sent without waiting for its timeout).
        :return:
        """
        wake = self._wake
        if wake is not None:
            wake.set()

    def _post(self, fn):
        """
        Queue fn for the RDP thread.
        """
        with self._queueLock:
            self._queue.append(_Call(fn))
        self._wakeUp()

    def _call(self, fn, timeout=10.0):
        """
        Run fn on the RDP thread and return its result.
        """
        call = _Call(fn, waited=True)
        with self._queueLock:
            self._queue.append(call)
        self._wakeUp()
        if not call.done.wait(timeout):
            raise ConnectionError(u'The RDP thread did not respond')
        if call.error is not None:
            raise call.error
        return call.result

    def _drain(self):
        with self._queueLock:
            calls, self._queue = self._queue, []
        for call in calls:
            call.run()

    def _run(self):
        """
        :return: None
        """
        api = self._api
        try:
            entry = RDP_CLIENT_ENTRY_POINTS_V1()  # type: RDP_CLIENT_ENTRY_POINTS_V1
            entry.Size = sizeof(entry)
            entry.Version = RDP_CLIENT_INTERFACE_VERSION
            # the client layer treats the context as an rdpClientContext
            # (requireRdpClientContext); a bare rdpContext is too small and
            # FreeRDP's client code would write past its end
            entry.ContextSize = sizeof(rdpClientContext)
            self._ctx = api.freerdp_client_context_new(byref(entry))
            if not self._ctx:
                self._error = u'freerdp_client_context_new failed'  # type: str
                return
            context = self._ctx.contents
            self._instance = context.instance
            instance = self._instance.contents
            instance.PostConnect = type(instance.PostConnect)(self._postConnect)
            instance.PostDisconnect = type(instance.PostDisconnect)(self._postDisconnect)
            self._refs += [instance.PostConnect, instance.PostDisconnect]
            instance.VerifyX509Certificate = type(instance.VerifyX509Certificate)(self._verifyX509Certificate)
            self._refs.append(instance.VerifyX509Certificate)
            self._applySettings(context.settings)
            self._hookNegotiation()
            self._subscribeChannels(context)
            if not api.freerdp_connect(self._instance):
                code = api.freerdp_get_last_error(self._ctx)
                message = api.freerdp_get_last_error_string(code)
                self._error = u'%s (0x%08X)' % (message.decode() if message else u'connect failed', code)
                if code == FREERDP_ERROR_CONNECT_NTLM_BLOCKED:
                    self._error += (u' - The server refuses NTLM sign-in (its policy, or a CredSSP security update'
                                    u' mismatch): sign in with Azure AD (setAzureAD / --azure-ad) or Kerberos.')
                if code == FREERDP_ERROR_CONNECT_LOGON_FAILURE:
                    self._error += u' - ' + self._explainLogonFailure()
                _log.error(u'Connect failed: %s', self._error)
                self._recordDisconnect(u'connect')
                return
            self._eventLoop()
            self._recordDisconnect(u'session')  # Before FreeRDP forgets why.
            api.freerdp_disconnect(self._instance)
        except Exception as exc:
            self._error = u'Session failed: %s: %s' % (type(exc).__name__, exc)
            _log.error(u'%s\n%s', self._error, format_exc())
            self._recordDisconnect(u'session')
        finally:
            self._ready = False  # type: bool
            self._drain()  # Release anyone waiting on a _call.
            gdi, self._gdi = self._gdi, None  # FreeRDP threads see "no GDI" from here on.
            if gdi and self._instance:
                try:
                    if self._gfx:
                        api.gdi_graphics_pipeline_uninit(gdi, self._gfx)
                        self._gfx = None
                    api.gdi_free(self._instance)
                except:
                    pass
            if self._ctx:
                api.freerdp_client_context_free(self._ctx)
            _markSession(False)  # Ended normally (a failed connection too): not a crash.
            self._ctx = self._instance = None
            self._clipboard.detach()
            self._resetState()

    def _applySettings(self, settings):
        # DOMAIN\user is split like FreeRDP's /u: does; an explicit domain wins.
        user, typedDomain = parseUsername(self._user)
        self._sentIdentity = (user, self._domain or typedDomain)  # For the logon-failure message.
        self._applyPrograms(settings)
        self._writeSettings(
            settings,
            strings=((FreeRDP_ServerHostname, self._host), (FreeRDP_Username, user),
                     (FreeRDP_Password, self._password), (FreeRDP_Domain, self._domain or typedDomain)),
            numbers=((FreeRDP_ServerPort, self._port), (FreeRDP_DesktopWidth, self._width),
                     (FreeRDP_DesktopHeight, self._height), (FreeRDP_ColorDepth, self._bpp),
                     (FreeRDP_TcpConnectTimeout, 30000), (FreeRDP_TcpAckTimeout, 30000)),
            flags=((FreeRDP_SoftwareGdi, True), (FreeRDP_IgnoreCertificate, True), (FreeRDP_NlaSecurity, True),
                   (FreeRDP_ExternalCertificateManagement, True), (FreeRDP_TlsSecurity, True),
                   (FreeRDP_AutoReconnectionEnabled, self._autoReconnect)))
        # clipboard (cliprdr): attached in _channelConnected. FreeRDP refuses every file-contents request unless the
        # feature mask allows files (channels/cliprdr/client/cliprdr_main.c), so state all four directions explicitly;
        # CLI arguments can still narrow it.
        self._writeSettings(
            settings, flags=((FreeRDP_RedirectClipboard, True),),
            numbers=((FreeRDP_ClipboardFeatureMask, CLIPRDR_FLAG_LOCAL_TO_REMOTE | CLIPRDR_FLAG_LOCAL_TO_REMOTE_FILES |
                      CLIPRDR_FLAG_REMOTE_TO_LOCAL | CLIPRDR_FLAG_REMOTE_TO_LOCAL_FILES),))
        self._addChannel(settings, u'static', [b'cliprdr'])
        # shared directories: one rdpdr 'drive' device per folder. NOT
        # FreeRDP_RedirectDrives - that means 'share every drive': without an
        # explicit drive device FreeRDP adds ('drive', "media", "*").
        if self._drives:
            self._writeSettings(settings, flags=((FreeRDP_DeviceRedirection, True),))
            for name, pth in self._drives:
                self._addChannel(settings, u'device', [b'drive', name.encode(), pth.encode()])
        # Sound, microphone and graphics are plain settings - exactly what
        # FreeRDP's add-in loader turns them into the rdpsnd / audin / rdpgfx channels (plus rdpdr and drdynvc) at
        # connect time (client/common/cmdline.c: freerdp_client_load_addins).
        # The command-line parser is used ONLY for arguments the caller passes explicitly with setFreerdpCliArgs.
        # Audio channels are registered here ("format:1" = PCM only, when
        # compressed audio is turned off). FreeRDP's add-in loader sees them
        # already present and only adds rdpdr, which rdpsnd needs.
        audioFormat = [] if self._compressedAudio else [b'format:1']
        # A short playback buffer: FreeRDP reports the real latency in each Wave Confirm, and the
        # server syncs audio and video with it - the smaller it is, the closer sound and picture are.
        playback = audioFormat + ([u'latency:{}'.format(self._audioLatency).encode()] if self._audioLatency else [])
        if self._sound:
            self._addChannel(settings, u'static', [b'rdpsnd'] + playback)
            self._addChannel(settings, u'dynamic', [b'rdpsnd'] + playback)
        if self._microphone:
            self._addChannel(settings, u'dynamic', [b'audin'] + audioFormat)
        self._writeSettings(
            settings, flags=((FreeRDP_AudioPlayback, self._sound), (FreeRDP_AudioCapture, self._microphone)))
        self._applyGraphics(settings)
        args = list(self._cliArgs)
        if args:
            self._parseCliArgs(settings, args)
        self._applyAzureADAndTransport(settings)

    def _writeSettings(self, settings, strings=(), numbers=(), flags=()):
        """
        Write FreeRDP settings from (key, value) pairs.
        :param settings: (POINTER(rdpSettings)) The session's settings.
        :param strings: (tuple) (key, str) pairs; empty strings are skipped.
        :param numbers: (tuple) (key, int) pairs, written as UINT32.
        :param flags: (tuple) (key, bool) pairs.
        :return:
        """
        api = self._api
        for key, value in strings:
            if value:
                api.freerdp_settings_set_string(settings, key, value.encode())
        for key, value in numbers:
            api.freerdp_settings_set_uint32(settings, key, int(value))
        for key, value in flags:
            api.freerdp_settings_set_bool(settings, key, bool(value))

    def _h264Available(self):
        """
        Whether this FreeRDP build can decode H.264 (no decoder -> NULL context).
        :return: bool
        """
        try:
            context = self._api.h264_context_new(False)
        except:
            return False
        if not context:
            return False
        self._api.h264_context_free(context)
        return True

    def _applyGraphics(self, settings):
        """
        setGraphics -> the Graphics Pipeline settings (what /gfx[:codec] sets).
        """
        option = u'off' if self._graphics is None else str(self._graphics).strip().lower()  # type: str
        if option in (u'off', u'none', u'legacy', u'false'):
            self._writeSettings(settings, flags=((FreeRDP_SupportGraphicsPipeline, False),))
            return
        h264 = self._h264Available()
        if option in (u'avc444', u'avc420') and not h264:
            _log.warning(u'setGraphics(%r): this build has no H.264 decoder; using the pipeline without it',
                         self._graphics)
        # (H.264, AVC444, progressive, RemoteFX). auto: everything this build can decode - H.264
        # (AVC444/AVC420) when a decoder is present, plus progressive and RemoteFX.
        auto = (h264, h264, True, True)
        wants = {
            u'auto': auto, u'on': auto, u'gfx': auto, u'': auto,
            u'avc444': (h264, h264, True, False), u'avc420': (h264, False, True, False),
            u'rfx': (False, False, False, True), u'progressive': (False, False, True, False),
        }.get(option)
        if wants is None:
            _log.warning(u'setGraphics(%r): unknown option; using auto', self._graphics)
            wants = auto
        useH264, avc444, progressive, rfx = wants
        self._writeSettings(settings, flags=(
            (FreeRDP_SupportGraphicsPipeline, True), (FreeRDP_GfxH264, useH264), (FreeRDP_GfxAVC444, avc444),
            (FreeRDP_GfxAVC444v2, avc444), (FreeRDP_GfxProgressive, progressive),
            (FreeRDP_GfxProgressiveV2, progressive), (FreeRDP_RemoteFxCodec, rfx)))

    def _addChannel(self, settings, kind, argv):
        array = (c_char_p * len(argv))(*argv)
        fn = {u'static': self._api.freerdp_client_add_static_channel,
              u'dynamic': self._api.freerdp_client_add_dynamic_channel,
              u'device': self._api.freerdp_client_add_device_channel}[kind]
        if not fn(settings, len(argv), array):
            _log.warning(u'Could not add %s channel %s', kind, argv[0].decode())

    def _parseCliArgs(self, settings, args):
        argvList = [b'pyfreerdpapp'] + [a.encode() if hasattr(a, u'encode') else a for a in args]
        argv = (c_char_p * len(argvList))(*argvList)
        rc = self._api.freerdp_client_settings_parse_command_line(settings, len(argvList), argv, False)
        if rc < 0:
            _log.warning(u'FreeRDP rejected the command-line arguments %s (code %d)', args, rc)

    def _subscribeChannels(self, context):
        self._onChannelConnected = pChannelConnectedEventHandler(self._channelConnected)
        self._onChannelDisconnected = pChannelDisconnectedEventHandler(self._channelDisconnected)
        self._refs += [self._onChannelConnected, self._onChannelDisconnected]
        self._api.PubSub_Subscribe(context.pubSub, b'ChannelConnected', self._onChannelConnected)
        self._api.PubSub_Subscribe(context.pubSub, b'ChannelDisconnected', self._onChannelDisconnected)

    @_guard()
    def _channelConnected(self, context, event):
        name, iface = event.contents.name, event.contents.pInterface
        if name == CLIPRDR_SVC_CHANNEL_NAME.encode() and iface:
            self._clipboard.attach(iface)
        elif name == RAIL_SVC_CHANNEL_NAME.encode() and iface:
            self._attachRail(iface)
        elif name == RDPGFX_DVC_CHANNEL_NAME.encode() and iface and self._gdi:
            # what xfreerdp/sdl-freerdp do: GFX surfaces render into the GDI.
            # pInterface is a void* (a plain int in Python); the function is
            # declared with an RdpgfxClientContext*, so cast it to that.
            gfx = cast(iface, POINTER(RdpgfxClientContext))
            if self._api.gdi_graphics_pipeline_init(self._gdi, gfx):
                self._gfx = gfx
                _log.info(u'Graphics pipeline active')

    @_guard()
    def _channelDisconnected(self, context, event):
        name = event.contents.name  # type: str
        if name == CLIPRDR_SVC_CHANNEL_NAME.encode():
            self._clipboard.detach()
        elif name == RAIL_SVC_CHANNEL_NAME.encode():
            self._rail = None
        elif name == RDPGFX_DVC_CHANNEL_NAME.encode() and self._gfx and self._gdi:
            self._api.gdi_graphics_pipeline_uninit(self._gdi, self._gfx)
            self._gfx = None

    @_guard(True)
    def _postConnect(self, instance):
        if not self._api.gdi_init(instance, _PIXEL_FORMATS[self._bpp]):
            self._error = u'gdi_init failed'  # type: bool
            return False
        self._gdi = self._ctx.contents.gdi
        self._registerPointer(instance.contents.context)
        self._registerPaint(instance.contents.context)
        self._registerDesktopResize(instance.contents.context)
        self._recordNegotiation()
        self._ready = True  # type: bool
        _log.info(u'Connected to %s:%d (%dx%d, %d bpp)', self._host, self._port, self._width, self._height, self._bpp)
        return True

    def _registerPaint(self, context):
        """
        Hook BeginPaint/EndPaint (legacy updates and the GFX pipeline both go
        through them). GDI registers none itself, so the dirty region it keeps
        must be reset here at the start of every paint.
        """
        update = context.contents.update.contents
        beginType = type(update.BeginPaint)
        endType = type(update.EndPaint)

        def detach(fn, fnType):
            # Reading a function-pointer field returns an object that SHARES
            # the struct's memory: keep it, and it turns into our own hook once
            # the field is overwritten (infinite recursion). Copy the address.
            address = cast(fn, c_void_p).value
            return fnType(address) if address else None

        previous = (detach(update.BeginPaint, beginType), detach(update.EndPaint, endType))

        def begin(ctx):
            if previous[0] and not previous[0](ctx):
                return False
            try:
                hwnd = self._gdiWindow()
                if hwnd is not None:
                    hwnd.invalid.contents.null = True
                    hwnd.ninvalid = 0
            except:
                _log.error(u'BeginPaint hook failed:\n%s', format_exc())
            return True

        def end(ctx):
            try:
                self._publishFrame()
            except:
                _log.error(u'Publishing a frame failed:\n%s', format_exc())
            return bool(previous[1](ctx)) if previous[1] else True

        self._paintHooks = (beginType(begin), endType(end))
        update.BeginPaint, update.EndPaint = self._paintHooks
        self._refs += list(self._paintHooks)

    def _explainLogonFailure(self):
        """
        Why the server may have refused the login, from what was sent and from the computer that
        answered (its NTLM challenge names it - FreeRDP received it during this attempt).
        :return: (str | unicode) An explanation for the error message.
        """
        user, domain = self._sentIdentity  # type: str, str
        sent = u'user {!r}{}'.format(user, u' in domain {!r}'.format(domain) if domain else u', no domain')
        server = self._challenge or {}  # type: dict
        computer = server.get(u'netbiosComputerName') or server.get(u'dnsComputerName')
        names = set(n.upper() for n in (server.get(u'netbiosComputerName'), server.get(u'netbiosDomainName'),
                                        server.get(u'dnsComputerName'), server.get(u'dnsDomainName')) if n)
        text = u'The server rejected the user name or password (sent: {}).'.format(sent)  # type: str
        if computer:
            text += u' The computer that answered is {!r}'.format(computer)  # type: str
            if server.get(u'netbiosDomainName') and server[u'netbiosDomainName'] != computer:
                text += u' in domain {!r}'.format(server[u'netbiosDomainName'])  # type: str
            text += u'.'
            if domain and domain.upper() not in names and domain != u'.':
                text += (u' The domain you sent is not this computer or its domain: for an account on this'
                         u' computer, type the user name alone (or {}\\{}).'.format(computer, user))  # type: str
                return text
        if domain:
            return text + u' For an account on the server itself, try the user name alone; check the password.'
        return text + u' For a domain account, type DOMAIN\\user; check the password.'

    def _recordNegotiation(self):
        """
        Keep what the connection negotiated, then read the server's published information once,
        in the background (it is a separate, credential-free handshake: never on the RDP thread).
        :return:
        """
        self._unhookNegotiation()
        self._registerSessionInfo()
        settings = self._ctx.contents.settings
        version = int(self._api.freerdp_settings_get_uint32(settings, FreeRDP_RdpVersion))  # type: int
        self._rdpVersion = RDP_VERSIONS.get(version, u'0x{:X}'.format(version))
        self._securityProtocol = protocolNames(int(self._api.freerdp_settings_get_uint32(
            settings, FreeRDP_SelectedProtocol)))

    @_guard(1)
    def _verifyX509Certificate(self, instance, data, length, hostname, port, flags):
        """
        FreeRDP passes the server's certificate (PEM) to the application (ExternalCertificateManagement).
        Keep it for getServerInfo, and accept it - as IgnoreCertificate did.
        :param instance: POINTER(freerdp)
        :param data: (POINTER(c_ubyte)) PEM.
        :param length: (int) Its length.
        :param hostname: bytes
        :param port: int
        :param flags: int
        :return: (int) 1: accepted.
        """
        self._certificatePem = string_at(data, int(length)).decode(u'ascii', u'replace')
        self._certificateInfo = None  # A new certificate: decode it again (once).
        return 1

    def _hookNegotiation(self):
        """
        Read the NTLM CHALLENGE of FreeRDP's own NLA exchange: wrap the transport's ReadPdu for the
        connection phase only (_unhookNegotiation restores FreeRDP's table in PostConnect, so normal
        traffic never goes through Python).
        :return: None
        """
        api = self._api
        self._challenge = None  # This attempt's server, not the previous one's.
        current = api.freerdp_get_io_callbacks(self._ctx)
        if not current:
            return
        self._ioSaved = rdpTransportIo.from_buffer_copy(current.contents)  # FreeRDP's table, to restore
        io = rdpTransportIo.from_buffer_copy(current.contents)
        readType = type(io.ReadPdu)
        original = readType(cast(io.ReadPdu, c_void_p).value)  # The address, not a view of the field.

        def readPdu(transport, stream):
            """
            :param transport: POINTER(rdpTransport)
            :param stream: POINTER(wStream)
            :return: int
            """
            rc = original(transport, stream)
            if rc > 0 and self._challenge is None:
                try:
                    st = cast(stream, POINTER(StreamHead)).contents  # size_t-correct on Windows too
                    start = st.buffer or 0
                    size = max(int(st.length), (st.pointer or 0) - start)
                    if start and 0 < size <= int(st.capacity):
                        self._challenge = parseChallenge(string_at(start, size))
                except:
                    pass
            return rc

        io.ReadPdu = readType(readPdu)
        self._ioHook = (io, io.ReadPdu, original)
        api.freerdp_set_io_callbacks(self._ctx, byref(io))

    def _unhookNegotiation(self):
        """
        :return:
        """
        if self._ioSaved is not None and self._ctx:
            self._api.freerdp_set_io_callbacks(self._ctx, byref(self._ioSaved))
        self._ioSaved = None

    def _registerSessionInfo(self):
        """
        Keep the Save Session Info data (logged-on user, domain, session id), then let FreeRDP's own
        handler run as before.
        :return:
        """
        update = self._ctx.contents.update.contents
        hookType = type(update.SaveSessionInfo)
        address = cast(update.SaveSessionInfo, c_void_p).value
        previous = hookType(address) if address else None

        def saveSessionInfo(context, infoType, data):
            """
            :param context: POINTER(rdpContext)
            :param infoType: int
            :param data: c_void_p
            :return: int
            """
            try:
                if data and infoType in (INFO_TYPE_LOGON, INFO_TYPE_LOGON_LONG):
                    logon = cast(data, POINTER(logon_info)).contents
                    self._logon.update(sessionId=int(logon.sessionId),
                                       username=(logon.username or b'').decode(u'utf-8', u'replace'),
                                       domain=(logon.domain or b'').decode(u'utf-8', u'replace'))
                elif data and infoType == INFO_TYPE_LOGON_EXTENDED_INF:
                    extended = cast(data, POINTER(logon_info_ex)).contents
                    if extended.haveCookie:
                        self._logon[u'logonId'] = int(extended.LogonId)
            except:
                pass
            return previous(context, infoType, data) if previous else 1

        self._sessionInfoHook = hookType(saveSessionInfo)
        update.SaveSessionInfo = self._sessionInfoHook
        self._refs.append(self._sessionInfoHook)

    def _registerDesktopResize(self, context):
        """
        update->DesktopResize is a CLIENT callback, and FreeRDP calls it with
        no NULL check when the Graphics Pipeline resets (libfreerdp/gdi/gfx.c,
        gdi_ResetGraphics: WINPR_ASSERT(update->DesktopResize) - compiled out
        in release builds - then update->DesktopResize(context)). Every GFX
        session sends Reset Graphics, so without it the process jumps to
        address 0. The legacy path calls it too (NULL-safely) when the server
        changes the desktop size. FreeRDP's own software-GDI clients resize
        the GDI here; so does this.
        """
        update = context.contents.update.contents
        resizeType = type(update.DesktopResize)
        self._desktopResizeHook = resizeType(self._desktopResize)
        update.DesktopResize = self._desktopResizeHook
        self._refs.append(self._desktopResizeHook)

    @_guard(False)
    def _desktopResize(self, context):
        api = self._api
        settings = self._ctx.contents.settings
        width = int(api.freerdp_settings_get_uint32(settings, FreeRDP_DesktopWidth))  # type: int
        height = int(api.freerdp_settings_get_uint32(settings, FreeRDP_DesktopHeight))  # type: int
        with self._gdiLock:
            if not self._gdi or width <= 0 or height <= 0:
                return False
            if not api.gdi_resize(self._gdi, width, height):
                _log.error(u'gdi_resize(%d, %d) failed', width, height)
                return False
            self._publishFrameLocked()  # viewers see the new size at once
        _log.info(u'Remote desktop resized to %dx%d', width, height)
        self._width, self._height = width, height
        return True

    def _publishFrame(self):
        with self._gdiLock:
            before = self._frameGen
            self._publishFrameLocked()
            published = self._frameGen != before
        listener = self._frameListener
        if published and listener is not None:  # outside the locks: a viewer never stalls FreeRDP
            try:
                listener()
            except Exception:
                _log.exception(u'Frame listener failed')

    def _publishFrameLocked(self):
        """
        Copy the rows this paint touched from GDI's buffer into _fb (one
        memmove of whole rows - no per-pixel work) and grow the dirty rect.
        Runs on the RDP thread, at the end of every paint.
        :return: None
        """
        gdiPtr = self._gdi
        if not gdiPtr:
            return
        gdi = gdiPtr.contents
        width, height, stride = int(gdi.width), int(gdi.height), int(gdi.stride)
        if width <= 0 or height <= 0 or stride < width or not gdi.primary_buffer:
            return
        hwnd = self._gdiWindow()
        if hwnd is None or not hwnd.invalid:
            return
        region = hwnd.invalid.contents
        resized = (width, height, stride) != self._fbInfo
        if region.null and not resized:
            return
        if resized:
            x, y, w, h = 0, 0, width, height
        else:
            x, y = max(0, int(region.x)), max(0, int(region.y))  # type: int, int
            w = min(width, int(region.x) + int(region.w)) - x  # type: int
            h = min(height, int(region.y) + int(region.h)) - y  # type: int
            if w <= 0 or h <= 0:
                return
        source = addressof(gdi.primary_buffer.contents)
        with self._frameLock:
            if resized:
                self._fbView = None
                self._fb = bytearray(stride * height)  # type: bytearray
                self._fbView = (c_char * len(self._fb)).from_buffer(self._fb)
                self._fbInfo = (width, height, stride)
                self._dirty = None
            offset = y * stride
            memmove(addressof(self._fbView) + offset, source + offset, h * stride)
            if self._dirty is None:
                self._dirty = (x, y, x + w, y + h)
            else:
                dx0, dy0, dx1, dy1 = self._dirty
                self._dirty = (min(dx0, x), min(dy0, y), max(dx1, x + w), max(dy1, y + h))
            self._frameGen += 1  # type: int

    def _gdiWindow(self):
        """
        gdi->primary->hdc->hwnd, or None if any link is NULL (never dereference NULL).
        """
        gdi = self._gdi
        if not gdi or not gdi.contents.primary:
            return None
        primary = gdi.contents.primary.contents
        return None if not primary.hdc or not primary.hdc.contents.hwnd else primary.hdc.contents.hwnd.contents

    def _takeFrame(self, lastGen):
        """
        For a viewer: everything that changed since generation `lastGen`, as
        (generation, width, height, channels, (x, y, w, h), packed BGR(A) rows
        of that rectangle) - or None when nothing changed.
        """
        with self._frameLock:
            if self._fb is None or self._frameGen == lastGen:
                return None
            width, height, stride = self._fbInfo
            channels = self._bpp // 8  # type: int
            if lastGen < 0 or self._dirty is None:
                x0, y0, x1, y1 = 0, 0, width, height  # type: int, int, int, int
            else:
                x0, y0, x1, y1 = self._dirty  # type: int, int, int, int
            self._dirty = None
            row = (x1 - x0) * channels  # type: int
            fb, start = self._fb, x0 * channels
            packed = b''.join(fb[y * stride + start:y * stride + start + row] for y in range(y0, y1))  # type: bytes
            return self._frameGen, width, height, channels, (x0, y0, x1 - x0, y1 - y0), packed

    def _registerPointer(self, context):
        """
        Install pointer callbacks so the remote cursor shape reaches setPointerListener.
        """
        proto = rdpPointer()  # type: rdpPointer
        proto.size = sizeof(rdpPointer)
        proto.New = type(proto.New)(self._pointerNew)
        proto.Free = type(proto.Free)(self._pointerFree)
        proto.Set = type(proto.Set)(self._pointerSet)
        proto.SetNull = type(proto.SetNull)(self._pointerSetNull)
        proto.SetDefault = type(proto.SetDefault)(self._pointerSetDefault)
        proto.SetPosition = type(proto.SetPosition)(self._pointerSetPosition)
        self._refs += [proto, proto.New, proto.Free, proto.Set, proto.SetNull, proto.SetDefault, proto.SetPosition]
        self._api.graphics_register_pointer(context.contents.graphics, byref(proto))

    def _notifyPointer(self, state, data):
        listener = self._pointerListener
        if listener is not None:
            listener(state, data)

    @_guard(True)
    def _pointerNew(self, context, pointer):
        p = pointer.contents
        width, height = int(p.width), int(p.height)
        if width <= 0 or height <= 0 or width > 512 or height > 512 or not self._gdi:
            return True
        image = (c_ubyte * (width * height * 4))()
        ok = self._api.freerdp_image_copy_from_pointer_data(
            image, PIXEL_FORMAT_BGRA32, width * 4, 0, 0, width, height,
            p.xorMaskData, p.lengthXorMask, p.andMaskData, p.lengthAndMask, p.xorBpp, byref(self._gdi.contents.palette))
        if ok:
            self._pointers[addressof(p)] = (width, height, int(p.xPos), int(p.yPos), bytes(image))
        return True

    @_guard()
    def _pointerFree(self, context, pointer):
        self._pointers.pop(addressof(pointer.contents), None)

    @_guard(True)
    def _pointerSet(self, context, pointer):
        shape = self._pointers.get(addressof(pointer.contents))
        if shape is not None:
            self._notifyPointer(u'set', shape)
        return True

    @_guard(True)
    def _pointerSetNull(self, context):
        self._notifyPointer(u'hidden', None)
        return True

    @_guard(True)
    def _pointerSetDefault(self, context):
        self._notifyPointer(u'default', None)
        return True

    @_guard(True)
    def _pointerSetPosition(self, context, x, y):
        self._notifyPointer(u'position', (int(x), int(y)))
        return True

    @_guard()
    def _postDisconnect(self, instance):
        self._ready = False  # type: bool

    def _eventLoop(self):
        api = self._api
        handles = (HANDLE * 64)()
        try:
            self._wake = _WakeEvent(api)
        except Exception as exc:  # no event API: fall back to polling
            _log.warning(u'input wake-up unavailable (%s); polling', exc)
            self._wake = None
        try:
            self._loop(api, handles)
        finally:
            wake, self._wake = self._wake, None
            if wake is not None:
                wake.close()

    def _loop(self, api, handles):
        while not self._stop:
            while self._paused:
                sleep(0.1)
                continue
            if self._wake is not None:
                self._wake.reset()
            self._drain()
            count = api.freerdp_get_event_handles(self._ctx, handles, 63)  # type: int
            if count == 0:
                break
            if self._wake is not None:
                handles[count] = self._wake.handle
                count += 1  # type: int
            if self._wait(count, handles, False, 100 if self._wake else 10) == WAIT_FAILED:
                break
            if api.freerdp_check_event_handles(self._ctx) and not api.freerdp_shall_disconnect_context(self._ctx):
                continue
            if self._stop or not self._autoReconnect or not self._reconnect():
                break

    def _reconnect(self):
        """
        setAutoReconnect: try to re-establish a dropped session.
        :return: bool
        """
        self._ready = False  # type: bool
        self._reconnecting = True  # type: bool
        try:
            for attempt in range(1, _RECONNECT_ATTEMPTS + 1):
                if self._stop:
                    return False
                _log.warning(u'connection lost; reconnecting (attempt %d of %d)', attempt, _RECONNECT_ATTEMPTS)
                self._hookNegotiation()
                if self._api.freerdp_reconnect(self._instance):
                    self._ready = True
                    return True
                sleep(min(2 ** attempt, 10))
            self._error = u'reconnection failed after %d attempts' % _RECONNECT_ATTEMPTS
            return False
        finally:
            self._reconnecting = False  # type: bool

    def _snapshot(self):
        """
        The latest published frame - read without waiting for the RDP thread.
        """
        with self._frameLock:
            if self._fb is None:
                raise ConnectionError(u'No display yet')
            width, height, stride = self._fbInfo
            return width, height, stride, bytes(self._fb)

    def _rdpInput(self):
        if self._ctx is None:
            return None
        rdpInput = self._ctx.contents.input
        return rdpInput if rdpInput else None

    def _keyboardTarget(self, down):
        """
        What every keyboard event needs: the session's input object and the press/release flags.
        :param down: (bool) True for a press.
        :return: (tuple) (rdpInput or None, flags)
        """
        return self._rdpInput(), (0 if down else KBD_FLAGS_RELEASE)

    def _sendScancode(self, scancode, down):
        rdpInput, flags = self._keyboardTarget(down)
        if rdpInput is None:
            return
        if scancode & 0x0100:
            flags |= KBD_FLAGS_EXTENDED
        self._api.freerdp_input_send_keyboard_event(rdpInput, flags, scancode & 0xFF)
        self._lastInputAt = monotonic()  # type: float

    def _sendUnicode(self, char, down):
        rdpInput, flags = self._keyboardTarget(down)
        if rdpInput is None:
            return
        # Characters outside the BMP travel as a UTF-16 surrogate pair.
        units = char.encode(u'utf-16-le')
        for i in range(0, len(units), 2):
            self._api.freerdp_input_send_unicode_keyboard_event(rdpInput, flags, units[i] | (units[i + 1] << 8))
        self._lastInputAt = monotonic()

    def _mouse(self, flags, x, y):
        self._checkConnected()
        x, y = int(x), int(y)  # type: int, int
        if not (0 <= x <= 0xFFFF and 0 <= y <= 0xFFFF):
            raise ValueError(u'Mouse coordinates out of range')

        def send():
            """
            :return:
            """
            rdpInput = self._rdpInput()
            if rdpInput is not None:
                self._api.freerdp_input_send_mouse_event(rdpInput, flags, x, y)
                self._lastInputAt = monotonic()  # type: float

        self._post(send)
