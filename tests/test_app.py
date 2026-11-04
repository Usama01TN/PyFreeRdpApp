# coding=utf-8
"""
PyFreerdpNative's library calls recorded instead of executed (no server).
"""
from ctypes import c_void_p, pointer, CFUNCTYPE, c_int, cast, create_string_buffer, addressof
from pytest import raises, importorskip, skip, fixture, mark
from subprocess import check_call, check_output, DEVNULL
from threading import Timer, current_thread, Thread
from struct import pack, pack_into
from os.path import getsize, join
from pyfreerdpnative import load
from os import urandom

try:
    from shutil import which
except:
    from distutils.spawn import find_executable as which


class Recorder(object):
    """
    Recorder class.
    """

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*args):
            """
            :param args: any
            :return: int
            """
            self.calls.append((name, args, current_thread().name))
            return 0 if name == u'freerdp_client_settings_parse_command_line' else 1

        return call


@fixture
def env(monkeypatch):
    """
    :param monkeypatch: MonkeyPatch
    :return:
    """
    rec = Recorder()  # type: Recorder
    from importlib import import_module
    mod = import_module(u'PyFreeRdpApp._pyfreerdp')
    # `from pyfreerdpnative import load` binds the name inside the module at
    # import time, so patch it there - patching pyfreerdpnative.load would only
    # affect the first test to import the module.
    monkeypatch.setattr(mod, u'load', lambda *a, **k: rec)
    app = mod.RDPApplication()
    return app, mod, rec


def connect(app):
    """
    Pretend the session is up, with a real rdpContext whose input is non-NULL.
    """
    from pyfreerdpnative.freerdp.freerdp import rdpContext
    app._ready = True
    app._ctx = pointer(rdpContext())
    app._ctx.contents.input = cast(c_void_p(0x1000), type(app._ctx.contents.input))


def drain_on_rdp_thread(app):
    t = Thread(target=app._drain, name=u'rdp-session')  # type: Thread
    t.start()
    t.join()


def sent(rec, prefix=u'freerdp_input_send_'):
    return [(n[len(prefix):], a[1], a[2], th) for n, a, th in rec.calls if n.startswith(prefix)]


def test_input_is_queued_to_the_rdp_thread(env):
    app, mod, rec = env
    connect(app)
    app.keyDown(0x1C)
    app.mouseMove(10, 20)
    assert not sent(rec), u'nothing may reach FreeRDP from the caller\'s thread'
    drain_on_rdp_thread(app)
    th_set = set()
    for item in sent(rec):
        th_set.add(item[-1])
    assert th_set == {u'rdp-session'}


def test_type_text_matches_pyfreerdp_205(env):
    app, mod, rec = env
    from pyfreerdpnative.freerdp.input import KBD_FLAGS_RELEASE
    connect(app)
    app.typeText(u'a b\n\U0001F600', typingDelay=0)
    drain_on_rdp_thread(app)
    events = [(k, bool(f & KBD_FLAGS_RELEASE), c) for k, f, c, _ in sent(rec)]
    assert events == [
        (u'unicode_keyboard_event', False, 0x61), (u'unicode_keyboard_event', True, 0x61),
        (u'keyboard_event', False, 0x39), (u'keyboard_event', True, 0x39),  # space
        (u'unicode_keyboard_event', False, 0x62), (u'unicode_keyboard_event', True, 0x62),
        (u'keyboard_event', False, 0x1C), (u'keyboard_event', True, 0x1C),  # \n -> Return
        (u'unicode_keyboard_event', False, 0xD83D), (u'unicode_keyboard_event', False, 0xDE00),
        (u'unicode_keyboard_event', True, 0xD83D), (u'unicode_keyboard_event', True, 0xDE00),
    ]


def test_scroll_and_extended_keys(env):
    app, mod, rec = env
    from pyfreerdpnative.freerdp.input import KBD_FLAGS_EXTENDED, PTR_FLAGS_WHEEL, PTR_FLAGS_WHEEL_NEGATIVE
    from PyFreeRdpApp.keyboard import RIGHT_CONTROL
    connect(app)
    app.mouseScroll(1, 2, down=True)
    app.mouseScroll(1, 2, down=False)
    app.keyDown(RIGHT_CONTROL)
    drain_on_rdp_thread(app)
    mouse = [f for k, f, c, _ in sent(rec) if k == u'mouse_event']
    assert mouse == [PTR_FLAGS_WHEEL | PTR_FLAGS_WHEEL_NEGATIVE | 0x88, PTR_FLAGS_WHEEL | 0x78]
    key = [(f, c) for k, f, c, _ in sent(rec) if k == u'keyboard_event'][0]
    assert key[1] == 0x1D and key[0] & KBD_FLAGS_EXTENDED


def test_settings_drives_graphics(env, tmp_path):
    app, mod, rec = env
    app.setBitsPerPixel(32)
    app.setGraphics(u'AVC444')
    app.loadSharedDirectory(str(tmp_path), u'Docs')
    app._applySettings(c_void_p(1))
    dev = [a for n, a, _ in rec.calls if n == u'freerdp_client_add_device_channel'][0]
    assert list(dev[2])[:3] == [b'drive', b'Docs', str(tmp_path).encode()]
    from pyfreerdpnative.freerdp.settings_keys import FreeRDP_SupportGraphicsPipeline
    bools = {a[1]: a[2] for n, a, _ in rec.calls if n == u'freerdp_settings_set_bool'}
    assert bools[FreeRDP_SupportGraphicsPipeline] is True  # setGraphics("AVC444")
    assert mod._PIXEL_FORMATS[32] == mod.PIXEL_FORMAT_BGRA32


def test_get_display_is_numpy_hwc(env):
    numpy = importorskip(u'numpy')
    app, mod, rec = env
    w, h, stride = 5, 3, 32
    raw = bytearray(stride * h)
    for y in range(h):
        for x in range(w):
            raw[y * stride + x * 4:y * stride + x * 4 + 4] = bytes([x, y, 200, 255])
    app._bpp = 32
    app._ready = True
    app._snapshot = lambda: (w, h, stride, bytes(raw))
    t = Timer(0.05, app._drain)
    t.start()
    img = app.getDisplay()
    assert img.shape == (3, 5, 4) and img.dtype == numpy.uint8
    assert list(img[2, 1]) == [1, 2, 200, 255]


def test_errors(env):
    app, mod, rec = env
    with raises(ConnectionError):
        app.typeText(u'x')
    with raises(ConnectionError):
        app.getDisplay()
    with raises(RuntimeError):  # documented in __init__.pyi
        app.hotkey(0x1C)
    with raises(TypeError):
        app.hotkey()
    with raises(ValueError):
        app.hotkey(u'wtf')
    with raises(ValueError):
        app.hotkey(0x1C, delay=-1)
    with raises(ValueError):
        app.setBitsPerPixel(8)


def test_clipboard_file_round_trip(tmp_path):
    from PyFreeRdpApp._cliprdr import collectFiles, buildFileList, Clipboard, decodeText, encodeText, FILECONTENTS_SIZE
    src = tmp_path / u'src'
    (src / u'sub').mkdir(parents=True)
    (src / u'a.txt').write_bytes(b'hello\n')
    (src / u'sub' / u'big.bin').write_bytes(urandom(150000))
    files = collectFiles(str(src), False)
    raw = buildFileList([e[:4] for e in files])
    assert len(raw) == 4 + 592 * len(files)
    cb = Clipboard(lambda fn: fn())  # type: Clipboard
    cb._serverFormats = {0xC0AA: b'FileGroupDescriptorW'}
    cb._formatData = lambda fid: raw

    def contents(index, flags, pos, size):
        full = files[index][4]
        if flags & FILECONTENTS_SIZE:
            return pack(u'<Q', getsize(full))
        with open(full, u'rb') as fh:
            fh.seek(pos)
            return fh.read(size)

    cb._fileContents = contents
    out = cb.loadFiles(str(tmp_path / u'dst'))
    for entry in files:
        name, isDir = entry[0], entry[1]
        if not isDir:
            with open(join(src, name), u'rb') as srcFile:
                with open(join(out, name), u'rb') as out_file:
                    assert srcFile.read() == out_file.read()
    assert decodeText(encodeText(u'x\ny')) == u'x\ny'


def test_package_exports():
    import PyFreeRdpApp as Pkg
    for n in (u'RDPApplication', u'RDPClipboardError', u'initializeLogging', u'keyboard'):
        assert hasattr(Pkg, n)


# --- getDisplay formats ----------------------------------------------------------

def _get(app, fmt):
    t = Timer(0.02, app._drain)  # type: Timer
    t.start()
    try:
        return app.getDisplay(fmt)
    finally:
        t.join()


@mark.parametrize(u'bpp', [32, 24])
def test_display_formats_agree(env, bpp):
    importorskip(u'numpy')
    importorskip(u'PIL')
    app, mod, rec = env
    ch = bpp // 8
    w, h, stride = 5, 3, 5 * ch + 12  # padded rows
    raw = bytearray(stride * h)
    for y in range(h):
        for x in range(w):
            raw[y * stride + x * ch:y * stride + x * ch + 3] = bytes([10 * x, 20 * y, 200])  # B G R
    app._bpp, app._ready = bpp, True
    app._snapshot = lambda: (w, h, stride, bytes(raw))
    npy = _get(app, u'numpy')
    assert npy.shape == (h, w, ch) and list(npy[2, 3][:3]) == [30, 40, 200]
    assert _get(app, u'pillow').getpixel((3, 2))[:3] == (200, 40, 30)
    assert len(_get(app, u'bytes')) == w * h * ch  # padding dropped
    assert _get(app, u'tuple')[:3] == (w, h, ch)
    with raises(ValueError):
        _get(app, u'gif')


def test_display_16bpp_is_freerdp_bgr16(env):
    """
    FreeRDP's BGR16 puts BLUE in the high bits (libfreerdp/codec/color.c).
    """
    importorskip(u'PIL')
    app, mod, rec = env
    r, g, b = 200, 40, 30
    word = (((b >> 3) & 0x1F) << 11) | (((g >> 2) & 0x3F) << 5) | ((r >> 3) & 0x1F)
    app._bpp, app._ready = 16, True
    app._snapshot = lambda: (1, 1, 2, pack(u'<H', word))
    pr, pg, pb = _get(app, u'pillow').getpixel((0, 0))
    assert pr > 190 and pb < 40, u'red and blue swapped'


def test_set_display_format(env):
    app, mod, rec = env
    app.setDisplayFormat(u'pillow')
    assert app._displayFormat == u'pillow'
    with raises(ValueError):
        app.setDisplayFormat(u'gif')


# --- __main__ prompts ---------------------------------------------------------------


def test_main_prompts_only_when_incomplete(monkeypatch):
    from PyFreeRdpApp import __main__ as main
    import builtins
    asked = []
    monkeypatch.setattr(builtins, u'input', lambda p=u'': (asked.append(p), u'x')[1])
    monkeypatch.setattr(main, u'getpass', lambda p=u'': (asked.append(p), u'pw')[1])
    a = main.askTerminal(main.parseArgs([u'prog', u'h', u'u', u'p', u'3390']))
    assert asked == [] and a.port == 3390
    a = main.askTerminal(main.parseArgs([u'prog']))
    assert a.host == u'x' and a.password == u'pw' and a.port == 3389


# --- found by the first live session ------------------------------------------------

def test_context_is_an_rdpclientcontext():
    """
    freerdp_client_context_new must be given room for an rdpClientContext:
    FreeRDP's client layer casts the context to it (requireRdpClientContext).
    A bare rdpContext (1024 bytes vs 3064) made it write past the allocation.
    """
    from PyFreeRdpApp._pyfreerdp import RDPApplication
    from inspect import getsource
    src = getsource(RDPApplication._run)
    assert u'sizeof(rdpClientContext)' in src and u'sizeof(rdpContext)' not in src


# --- clipboard mask, sharing, pointer ---------------------------------------------------

def test_clipboard_mask_and_no_redirect_all_drives(env, tmp_path):
    from pyfreerdpnative.freerdp.settings_keys import FreeRDP_ClipboardFeatureMask, FreeRDP_DeviceRedirection, \
        FreeRDP_RedirectDrives
    app, mod, rec = env
    (tmp_path / u'f.txt').write_text(u'x')
    app.loadSharedDirectory(str(tmp_path / u'f.txt'))  # a file shares its folder
    app.loadSharedDirectory(str(tmp_path))  # duplicate: ignored
    assert app.getSharedDirectories() == [(tmp_path.name, str(tmp_path))]
    app._applySettings(c_void_p(1))
    u32 = {a[1]: a[2] for n, a, _ in rec.calls if n == u'freerdp_settings_set_uint32'}
    bools = {a[1]: a[2] for n, a, _ in rec.calls if n == u'freerdp_settings_set_bool'}
    assert u32[FreeRDP_ClipboardFeatureMask] == 0x33  # all four directions, files included
    assert bools[FreeRDP_DeviceRedirection] is True
    assert FreeRDP_RedirectDrives not in bools  # would share EVERY drive


def test_pointer_states(env):
    from pyfreerdpnative.freerdp.graphics import rdpPointer
    from pyfreerdpnative.freerdp.gdi.gdi import rdpGdi
    app, mod, rec = env
    app._gdi = pointer(rdpGdi())
    seen = []
    app.setPointerListener(lambda state, data: seen.append((state, data if state != u'set' else data[:4])))
    p = rdpPointer()  # type: rdpPointer
    p.width, p.height, p.xPos, p.yPos, p.xorBpp = 32, 32, 4, 7, 32
    pp = pointer(p)  # type: pointer
    app._pointerNew(None, pp)
    app._pointerSet(None, pp)
    app._pointerSetNull(None)
    app._pointerSetDefault(None)
    app._pointerSetPosition(None, 10, 20)
    app._pointerFree(None, pp)
    assert seen == [(u'set', (32, 32, 4, 7)), (u'hidden', None), (u'default', None), (u'position', (10, 20))]
    assert app._pointers == {}
    decode = [a for n, a, _ in rec.calls if n == u'freerdp_image_copy_from_pointer_data'][0]
    assert decode[1] == mod.PIXEL_FORMAT_BGRA32 and decode[2] == 32 * 4


# --- regressions found live, this round ----------------------------------------------

def test_file_offer_reaches_freerdp():
    """
    A file offer once raised TypeError before ClientFormatList (a c_char_p field
    read as None was used as a cast target) and the error was swallowed.
    """
    from PyFreeRdpApp._cliprdr import Clipboard, LOCAL_FILE_FORMAT_ID
    cb = Clipboard(lambda fn: fn())
    cb._localText = u'x'
    cb._localFiles = [(u'a.txt', False, 1, 0, u'/nonexistent')]
    sentList = []

    class Ctx(object):
        """
        Ctx class.
        """

        class contents(object):
            """
            contents class.
            """

            @staticmethod
            def ClientFormatList(ctx, ref):
                fl = ref._obj
                sentList.append([(fl.formats[i].formatId, fl.formats[i].formatName) for i in range(fl.numFormats)])
                return 0

    cb._ctx = Ctx()
    cb._sendFormatList()
    assert sentList == [[(13, None), (LOCAL_FILE_FORMAT_ID, b'FileGroupDescriptorW')]]


def test_posted_call_errors_are_logged(env, caplog):
    app, mod, rec = env
    app._post(lambda: 1 / 0)
    with caplog.at_level(u'ERROR', logger=u'PyFreeRdpApp'):
        app._drain()
    assert u'ZeroDivisionError' in caplog.text


def test_paint_hook_chains_to_the_previous_one(env):
    """
    Reading a function-pointer field shares the struct's memory: chaining must copy the address.
    """
    from pyfreerdpnative.freerdp.freerdp import rdpContext
    from pyfreerdpnative.freerdp.update import rdpUpdate
    from pyfreerdpnative.freerdp.gdi.gdi import rdpGdi
    app, mod, rec = env
    update = rdpUpdate()
    calls = []
    original = type(update.EndPaint)(lambda ctx: calls.append(u'original') or 1)
    update.EndPaint = original
    ctx = rdpContext()
    ctx.update = pointer(update)
    app._gdi = pointer(rdpGdi())
    app._publishFrame = lambda: calls.append(u'publish')
    app._registerPaint(pointer(ctx))
    assert update.EndPaint(None) == 1  # no recursion
    assert calls == [u'publish', u'original']


def test_take_frame_returns_only_the_dirty_rect(env):
    app, mod, rec = env
    app._bpp = 32
    w, h, stride = 8, 4, 32
    app._fb = bytearray(bytes(range(256))[:stride * h] * 1)
    app._fbInfo = (w, h, stride)
    app._frameGen, app._dirty = 5, (2, 1, 5, 3)  # x0, y0, x1, y1
    gen, W, H, ch, rect, packed = app._takeFrame(4)
    assert (gen, W, H, ch, rect) == (5, 8, 4, 4, (2, 1, 3, 2))
    assert packed == bytes(app._fb[1 * 32 + 8:1 * 32 + 20]) + bytes(app._fb[2 * 32 + 8:2 * 32 + 20])
    assert app._takeFrame(5) is None  # nothing new


def test_sound_and_graphics_are_settings_not_cli_arguments(env):
    """
    Sound, microphone and graphics are plain settings;
    FreeRDP's add-in loader turns them into channels. The command-line parser -
    the one code path all the crashing options shared - is not called for them.
    """
    from pyfreerdpnative.freerdp.settings_keys import FreeRDP_AudioCapture, FreeRDP_GfxProgressive, FreeRDP_GfxH264, \
        FreeRDP_AudioPlayback, FreeRDP_SupportGraphicsPipeline
    app, mod, rec = env
    app._h264Available = lambda: True
    app.setSound(True, microphone=True)
    app.setGraphics(u'auto')
    app._applySettings(c_void_p(1))
    bools = {a[1]: a[2] for n, a, _ in rec.calls if n == u'freerdp_settings_set_bool'}
    assert bools[FreeRDP_AudioPlayback] is True and bools[FreeRDP_AudioCapture] is True
    # auto = the best this build decodes: H.264 when available, plus progressive
    assert bools[FreeRDP_SupportGraphicsPipeline] is True and bools[FreeRDP_GfxH264] is True
    assert bools[FreeRDP_GfxProgressive] is True
    assert not [n for n, a, _ in rec.calls if n == u'freerdp_client_settings_parse_command_line']
    if hasattr(rec.calls, u'clear'):
        rec.calls.clear()
    else:
        rec.calls = []
    app._h264Available = lambda: False  # a build without an H.264 decoder
    app.setSound(False)
    app.setGraphics(u'AVC444')
    app._applySettings(c_void_p(1))
    bools = {a[1]: a[2] for n, a, _ in rec.calls if n == u'freerdp_settings_set_bool'}
    assert bools[FreeRDP_AudioPlayback] is False
    assert bools[FreeRDP_GfxH264] is False and bools[FreeRDP_SupportGraphicsPipeline] is True
    if hasattr(rec.calls, u'clear'):
        rec.calls.clear()
    else:
        rec.calls = []
    app.setGraphics(u'off')
    app._applySettings(c_void_p(1))
    bools = {a[1]: a[2] for n, a, _ in rec.calls if n == u'freerdp_settings_set_bool'}
    assert bools[FreeRDP_SupportGraphicsPipeline] is False


def test_user_cli_arguments_still_reach_the_parser(env):
    app, mod, rec = env
    app.setFreerdpCliArgs(u'/rfx')
    app._applySettings(c_void_p(1))
    cli = [a for n, a, _ in rec.calls if n == u'freerdp_client_settings_parse_command_line']
    assert cli and list(cli[0][2])[:cli[0][1]] == [b'pyfreerdpapp', b'/rfx']


def test_publish_frame_tolerates_missing_gdi(env):
    app, mod, rec = env
    app._gdi = None
    app._publishFrame()  # no GDI (torn down): must not touch memory
    from pyfreerdpnative.freerdp.gdi.gdi import rdpGdi
    app._gdi = pointer(rdpGdi())  # GDI without primary/hdc/hwnd yet
    assert app._gdiWindow() is None
    app._publishFrame()


def test_gfx_interface_is_cast_for_the_typed_prototype(env):
    """
    ChannelConnected delivers pInterface as a void* (an int in Python), while
    gdi_graphics_pipeline_init is declared with an RdpgfxClientContext*. Use a
    stand-in carrying the REAL declared argtypes, so ctypes checks the call
    exactly as the real library does (a plain recorder would accept anything).
    """
    from pyfreerdpnative.freerdp.event import ChannelConnectedEventArgs
    from pyfreerdpnative.freerdp.gdi.gdi import rdpGdi
    from pyfreerdpnative import PROTOTYPES
    app, mod, rec = env
    restype, argtypes, _ = PROTOTYPES[u'gdi_graphics_pipeline_init']
    seen = []
    typed = CFUNCTYPE(c_int, *argtypes)(lambda gdi, gfx: seen.append(cast(gfx, c_void_p).value) or 1)
    rec.gdi_graphics_pipeline_init = typed
    app._gdi = pointer(rdpGdi())
    event = ChannelConnectedEventArgs()
    event.name = b'Microsoft::Windows::RDS::Graphics'
    event.pInterface = 0x7F001234
    app._channelConnected(None, pointer(event))
    assert seen == [0x7F001234] and app._gfx


def test_pcm_audio_option(env):
    """
    compressed=False pins rdpsnd/audin to PCM ("format:1"); the default allows compression.
    """
    app, mod, rec = env
    app.setSound(True, microphone=True, compressed=False)
    app._applySettings(c_void_p(1))
    channels = [(n.rsplit(u'_', 2)[-2], list(a[2])[:a[1]]) for n, a, _ in rec.calls
                if n in (u'freerdp_client_add_static_channel', u'freerdp_client_add_dynamic_channel')]
    assert (u'static', [b'rdpsnd', b'format:1', b'latency:50']) in channels
    assert (u'dynamic', [b'rdpsnd', b'format:1', b'latency:50']) in channels
    assert (u'dynamic', [b'audin', b'format:1']) in channels  # the playback buffer only
    if hasattr(rec.calls, u'clear'):
        rec.calls.clear()
    else:
        rec.calls = []
    app.setSound(True, compressed=True)
    app._applySettings(c_void_p(1))
    channels = [list(a[2])[:a[1]] for n, a, _ in rec.calls if n == u'freerdp_client_add_static_channel']
    assert [b'rdpsnd', b'latency:50'] in channels


def test_windows_crash_event_is_parsed():
    from PyFreeRdpApp._pyfreerdp import _parseWindowsCrashEvent
    text = (u'Faulting application name: python.exe, version: 3.13.0.1013, time stamp: 0x1\n'
            u'Faulting module name: example.dll, version: 1.2.3.4, time stamp: 0x0\n'
            u'Exception code: 0xc0000005\nFault offset: 0x00000000004a1b2c\n'
            u'Faulting module path: C:\\x\\example.dll\n')
    info = _parseWindowsCrashEvent(text)
    assert info[u'module'] == u'example.dll' and info[u'offset'] == u'0x00000000004a1b2c'
    assert info[u'exception'] == u'0xc0000005' and info[u'module_path'].endswith(u'example.dll')
    assert _parseWindowsCrashEvent(u'The service started.') is None


def test_desktop_resize_callback_is_registered_and_resizes(env):
    """
    THE crash: FreeRDP calls update->DesktopResize without a NULL check when the
    Graphics Pipeline resets (gfx.c: gdi_ResetGraphics). A client must set it.
    """
    from pyfreerdpnative.freerdp.freerdp import rdpContext
    from pyfreerdpnative.freerdp.gdi.gdi import rdpGdi
    from pyfreerdpnative.freerdp.update import rdpUpdate
    app, mod, rec = env
    update = rdpUpdate()
    ctx = rdpContext()
    ctx.update = pointer(update)
    assert not cast(update.DesktopResize, c_void_p).value  # NULL, as FreeRDP leaves it
    app._registerDesktopResize(pointer(ctx))
    assert cast(update.DesktopResize, c_void_p).value  # set
    app._ctx = pointer(ctx)
    app._gdi = pointer(rdpGdi())
    app._publishFrameLocked = lambda: None
    sizes = {u'w': 1024, u'h': 768}
    rec.freerdp_settings_get_uint32 = lambda s, key: sizes[u'w'] if key == mod.FreeRDP_DesktopWidth else sizes[u'h']
    resized = []
    rec.gdi_resize = lambda gdi, w, h: resized.append((w, h)) or 1
    assert update.DesktopResize(None) == 1  # called from C, like gfx.c
    assert resized == [(1024, 768)] and (app._width, app._height) == (1024, 768)


# --- getters, session info, the widget's Qt properties, the Designer plugin ------------

def test_application_getters_mirror_the_setters(env):
    app, mod, rec = env
    app.setServer(u'rdp.example.com')
    app.setPort(3390)
    app.setUsername(u'alice')
    app.setDomain(u'CORP')
    app.setDisplaySize(1024, 768)
    app.setBitsPerPixel(16)
    app.setGraphics(u'AVC444')
    app.setSound(True, microphone=True, compressed=False)
    app.setAutoReconnect(True)
    assert (app.getServer(), app.getPort(), app.getUsername(), app.getDomain()) == (u'rdp.example.com', 3390,
                                                                                    u'alice', u'CORP')
    assert app.getDisplaySize() == (1024, 768) and app.getBitsPerPixel() == 16 and app.getGraphics() == u'AVC444'
    assert app.isSound() and app.isMicrophone() and not app.isCompressedAudio() and app.isAutoReconnect()
    info = app.getSessionInfo()
    for key in (u'server', u'port', u'ready', u'running', u'graphicsPipeline', u'fileClipboard', u'freerdpVersion'):
        assert key in info
    assert info[u'server'] == u'rdp.example.com' and info[u'ready'] is False


_QAPP = []  # The QApplication must outlive every widget: keep a reference.


def _qt():
    importorskip(u'ManyQt')
    from ManyQt.QtWidgets import QApplication
    if not _QAPP:
        _QAPP.append(QApplication.instance() or QApplication([]))
    return _QAPP[0]


def test_widget_qt_properties_round_trip():
    _qt()
    from PyFreeRdpApp.rdpwidget import RDPWidget
    w = RDPWidget(designMode=True)
    for name, value in ((u'server', u'h'), (u'port', 3390), (u'graphics', u'RFX'), (u'sound', False),
                        (u'bitsPerPixel', 24), (u'sharedDirectories', [u'/a', u'/b']), (u'autoConnect', True)):
        w.setProperty(name, value)
        assert w.property(name) == value
    assert not w.running and not w.ready  # Designer: never connects


def test_widget_configures_the_session_it_creates(env):
    _qt()
    from PyFreeRdpApp.rdpwidget import RDPWidget
    app, mod, rec = env
    w = RDPWidget(server=u'rdp.example.com', port=3390, displayWidth=1024, displayHeight=768)
    w.setApplication(app, mirror=False)  # as getApplication() does for a session it creates
    w._applyTo(app)
    assert app.getServer() == u'rdp.example.com' and app.getPort() == 3390 and app.getDisplaySize() == (1024, 768)


def _designerWidget():
    """
    RDPWidget as Qt Designer sees it with the active binding: PyQt's plugin class (rdpwidgetplugin.py), or -
    PySide has no plugin class - what register_rdpwidget.py registers. Skips only when the binding has no
    QtDesigner module (importorskip gives the reason).
    :return: QDesignerCustomWidgetInterface
    """
    _qt()
    designer = importorskip(u'ManyQt.QtDesigner')
    from PyFreeRdpApp.rdpwidget import rdpwidgetplugin
    plugin = getattr(rdpwidgetplugin, u'RDPWidgetPlugin', None)
    if plugin is not None:  # PyQt
        return plugin()
    from PyFreeRdpApp.rdpwidget.register_rdpwidget import registerRDPWidget  # PySide
    assert registerRDPWidget()
    return [w for w in designer.QPyDesignerCustomWidgetCollection.instance().customWidgets()
            if w.name() == u'RDPWidget'][-1]


def test_designer_plugin():
    from xml.dom.minidom import parseString
    plugin = _designerWidget()
    assert plugin.name() == u'RDPWidget' and plugin.includeFile() == u'PyFreeRdpApp.rdpwidget'
    assert plugin.group() == u'PyFreeRdpApp' and plugin.toolTip() == u'Remote desktop (FreeRDP)'
    assert parseString(plugin.domXml()).getElementsByTagName(u'widget')[0].getAttribute(u'class') == u'RDPWidget'
    assert plugin.createWidget(None).isDesignMode()  # Designer's instances never connect


def test_compatibility_imports():
    _qt()
    try:
        from PyFreeRdpApp.rdpwidget import RDPWidget, frameToQimage
    except:
        RDPWidget = frameToQimage = None
    assert RDPWidget and callable(frameToQimage)


def test_session_report_format():
    from PyFreeRdpApp.__main__ import describeSession, formatSessionInfo
    text = formatSessionInfo({u'ready': True, u'server': u'h', u'port': 3389, u'username': u'u', u'domain': u'',
                              u'width': 800, u'height': 600, u'bitsPerPixel': 32, u'graphics': u'auto',
                              u'graphicsPipeline': True, u'sound': True, u'compressedAudio': True,
                              u'microphone': False, u'clipboard': True, u'fileClipboard': True,
                              u'sharedDirectories': [(u'Docs', u'/d')], u'framesPublished': 3,
                              u'freerdpVersion': u'3.32.2', u'lastError': None})
    assert u'connected' in text and u'(pipeline)' in text and u'Docs (/d)' in text
    words = describeSession({u'ready': True, u'sound': True, u'compressedAudio': True, u'clipboard': True,
                             u'fileClipboard': True, u'graphicsPipeline': True, u'sharedDirectories': []})
    # One vocabulary for the console report and the window's status bar.
    assert words[u'clipboard'] == u'text + files' and words[u'graphics'] == u'pipeline' and words[u'shared'] == u'none'


def test_widget_includes_its_session_and_writes_through(env):
    """
    RDPApplication is included by default; properties are written straight through.
    """
    _qt()
    from PyFreeRdpApp.rdpwidget import RDPWidget
    app, mod, rec = env  # env patches the FreeRDP loader for new sessions too
    w = RDPWidget()
    session = w.getApplication()
    assert isinstance(session, mod.RDPApplication)
    w.setServer(u'rdp.example.com')
    w.setPort(3390)
    w.setDisplayWidth(1024)
    w.setSound(False)
    assert session.getServer() == u'rdp.example.com' and session.getPort() == 3390
    assert session.getDisplayWidth() == 1024 and not session.isSound()
    assert w.getSessionInfo()[u'server'] == u'rdp.example.com'


def test_screenshot_and_info_are_console_only():
    from PyFreeRdpApp.__main__ import isConsoleMode, parseArgs
    for argv in ([u'p', u'h', u'u', u'pw', u'--screenshot', u'x.png'], [u'p', u'h', u'u', u'pw', u'--info'],
                 [u'p', u'h', u'u', u'pw', u'--info', u'--screenshot', u'x.png', u'--json']):
        assert isConsoleMode(parseArgs(argv))


def test_settings_are_written_from_tables(env):
    """One writer for every FreeRDP setting; empty strings are skipped."""
    from pyfreerdpnative.freerdp.settings_keys import FreeRDP_ServerHostname, FreeRDP_Domain
    app, mod, rec = env
    app.setServer(u'h')
    app._applySettings(c_void_p(1))
    strings = dict((a[1], a[2]) for n, a, _ in rec.calls if n == u'freerdp_settings_set_string')
    assert strings[FreeRDP_ServerHostname] == b'h' and FreeRDP_Domain not in strings


def test_session_info_fallback_never_reports_the_password():
    _qt()
    from PyFreeRdpApp.rdpwidget import RDPWidget
    w = RDPWidget(password=u'secret', designMode=True)  # type: RDPWidget
    w.setApplication.__self__  # The widget exists.
    info = w.getSessionInfo()
    assert u'password' not in info and u'secret' not in u'{}'.format(info)


# --- server information: certificate, OS version, names ------------------------------

def test_ntlm_challenge_parsing_against_impacket():
    """
    The CHALLENGE parser, checked against an independent MS-NLMP implementation.
    """
    ntlm = importorskip(u'impacket.ntlm')
    from PyFreeRdpApp._serverinfo import parseChallenge
    av = ntlm.AV_PAIRS()
    av[ntlm.NTLMSSP_AV_HOSTNAME] = u'WIN-SRV'.encode(u'utf-16-le')
    av[ntlm.NTLMSSP_AV_DNS_DOMAINNAME] = u'corp.example'.encode(u'utf-16-le')
    domain, target = u'CORP'.encode(u'utf-16-le'), av.getData()
    ch = ntlm.NTLMAuthChallenge()
    ch[u'flags'] = 0xE28A8215 | ntlm.NTLMSSP_NEGOTIATE_VERSION
    ch[u'challenge'] = b'\x11' * 8
    ch[u'domain_name'] = domain
    ch[u'domain_len'] = ch[u'domain_max_len'] = len(domain)
    ch[u'domain_offset'] = 56
    ch[u'TargetInfoFields'] = target
    ch[u'TargetInfoFields_len'] = ch[u'TargetInfoFields_max_len'] = len(target)
    ch[u'TargetInfoFields_offset'] = 56 + len(domain)
    ch[u'Version'] = b'\x0a\x00' + (17763).to_bytes(2, u'little') + b'\x00\x00\x00\x0f'
    ch[u'VersionLen'] = 8
    info = parseChallenge(b'\x30\x82prefix' + ch.getData())
    assert info[u'osVersion'] == u'10.0.17763' and info[u'osName'] == u'Windows Server 2019 / Windows 10 1809'
    assert info[u'netbiosComputerName'] == u'WIN-SRV' and info[u'dnsDomainName'] == u'corp.example'


def test_server_info_helpers():
    from PyFreeRdpApp._serverinfo import PROTOCOL_HYBRID, PROTOCOL_SSL, humanDuration, protocolNames, windowsName
    assert protocolNames(PROTOCOL_HYBRID | PROTOCOL_SSL) == u'NLA (CredSSP) + TLS'
    assert protocolNames(0) == u'standard RDP security'
    assert windowsName(10, 0, 20348) == u'Windows Server 2022'
    assert windowsName(6, 1, 7601).startswith(u'Windows Server 2008 R2')
    assert humanDuration(5 * 3600) == u'5 hours' and humanDuration(86400) == u'1 day'


def test_certificate_decoded_by_freerdp(tmp_path):
    """
    The PEM FreeRDP passes to VerifyX509Certificate, decoded by FreeRDP's API, as openssl reads it.
    """
    if not which(u'openssl'):
        skip(u'openssl not available')
    try:
        api = load()
    except:
        skip(u'FreeRDP libraries not available')
    key, crt = str(tmp_path / u'k.pem'), str(tmp_path / u'c.pem')
    check_call([u'openssl', u'req', u'-x509', u'-newkey', u'rsa:2048', u'-nodes', u'-keyout', key,
                u'-out', crt, u'-days', u'2', u'-subj', u'/CN=rdp.example', u'-addext',
                u'subjectAltName=DNS:rdp.example,DNS:alt.example'], stdout=DEVNULL, stderr=DEVNULL)
    from PyFreeRdpApp._serverinfo import describeCertificate
    info = describeCertificate(api, open(crt).read())
    fingerprint = check_output([u'openssl', u'x509', u'-in', crt, u'-noout', u'-fingerprint',
                                u'-sha256']).decode().strip().split(u'=', 1)[1]
    assert info[u'sha256'] == fingerprint and info[u'selfSigned'] and u'rdp.example' in info[u'subject']
    assert info[u'subjectAltNames'] == [u'rdp.example', u'alt.example'] and info[u'publicKey'] == u'RSA'
    assert not info[u'expired'] and info[u'validity'].startswith(u'expires in')


def test_server_info_uses_freerdp_only():
    """
    No temp files, no Python TLS/hash decoding: everything comes from FreeRDP.
    """
    import PyFreeRdpApp._serverinfo as serverinfo
    from inspect import getsource
    source = getsource(serverinfo)
    for forbidden in (u'tempfile', u'mkstemp', u'_test_decode_cert', u'import ssl', u'from ssl', u'hashlib',
                      u'create_connection', u'wrap_socket'):
        assert forbidden not in source, forbidden


def test_report_shows_computer_security_and_certificate():
    from PyFreeRdpApp.__main__ import formatSessionInfo
    server = {u'rdpVersion': u'10.12', u'securityProtocol': u'NLA (CredSSP)',
              u'computer': {u'netbiosComputerName': u'WIN-SRV', u'osName': u'Windows Server 2022',
                            u'osVersion': u'10.0.20348'},
              u'logon': {u'username': u'expert', u'domain': u'WIN-SRV', u'sessionId': 29},
              u'certificate': {u'subject': u'CN=WIN-SRV', u'issuer': u'CN=WIN-SRV', u'selfSigned': True,
                               u'notAfter': u'Jan 1 00:00:00 2030 GMT', u'validity': u'expires in 3 days',
                               u'sha256': u'AB:CD'}}
    text = formatSessionInfo({u'ready': True, u'server': u'h', u'port': 3389, u'serverInfo': server,
                              u'sharedDirectories': []})
    for expected in (u'Windows Server 2022 (version 10.0.20348)', u'RDP version  10.12', u'Security     NLA (CredSSP)',
                     u'WIN-SRV\\expert', u'Session ID  29', u'CN=WIN-SRV (self-signed)', u'expires in 3 days',
                     u'SHA-256'):
        assert expected in text, expected


def test_domain_backslash_user_is_split_like_freerdp():
    """
    FreeRDP's /u: rule, without any native call on the login path.
    """
    from PyFreeRdpApp._serverinfo import parseUsername
    assert parseUsername(u'WIN-SRV\\expert') == (u'expert', u'WIN-SRV')
    assert parseUsername(u'expert@corp.example') == (u'expert@corp.example', None)  # a UPN stays whole
    assert parseUsername(u'expert') == (u'expert', None)
    assert parseUsername(u'A\\b\\c') == (u'b\\c', u'A')  # the first backslash, like FreeRDP


def test_free_comes_from_the_module_that_allocated(tmp_path):
    """
    0xC0000409 in ucrtbase: FreeRDP's strings were freed with a guessed C runtime. The deallocator is
    now read from the import table of FreeRDP's own module; corrupt input never crashes.
    """
    from PyFreeRdpApp._serverinfo import _peImport
    garbage = create_string_buffer(b'MZ' + b'\xff' * 4094, 4096)
    assert _peImport(addressof(garbage), b'free') == (None, None)
    # A minimal PE32+ image importing free from api-ms-win-crt-heap-l1-1-0.dll.
    size = 0x3000
    image = bytearray(size)
    image[0:2] = b'MZ'
    pack_into(u'<I', image, 0x3C, 0x80)
    image[0x80:0x84] = b'PE\0\0'
    optional = 0x80 + 24
    pack_into(u'<H', image, optional, 0x20B)
    pack_into(u'<I', image, optional + 56, size)
    pack_into(u'<II', image, optional + 112 + 8, 0x1000, 40)  # IMPORT directory
    pack_into(u'<IIIII', image, 0x1000, 0x1100, 0, 0, 0x1200, 0x1180)  # one descriptor + terminator
    pack_into(u'<QQ', image, 0x1100, 0x1300, 0)  # lookup: hint/name at 0x1300
    pack_into(u'<QQ', image, 0x1180, 0x7FFE1234, 0)  # IAT: the bound address
    image[0x1200:0x1200 + 31] = b'api-ms-win-crt-heap-l1-1-0.dll\0'
    image[0x1302:0x1307] = b'free\0'
    buf = create_string_buffer(bytes(image), size)
    assert _peImport(addressof(buf), b'free') == (0x7FFE1234, u'api-ms-win-crt-heap-l1-1-0.dll')
    assert _peImport(addressof(buf), b'malloc') == (None, None)


def test_typed_domain_reaches_freerdp_settings(env, monkeypatch):
    from pyfreerdpnative.freerdp.settings_keys import FreeRDP_Username, FreeRDP_Domain
    app, mod, rec = env
    monkeypatch.setattr(mod, u'parseUsername', lambda name: (u'expert', u'WIN-SRV') if u'\\' in name else (name, None))
    app.setUsername(u'WIN-SRV\\expert')
    app._applySettings(c_void_p(1))
    strings = dict((a[1], a[2]) for n, a, _ in rec.calls if n == u'freerdp_settings_set_string')
    assert strings[FreeRDP_Username] == b'expert' and strings[FreeRDP_Domain] == b'WIN-SRV'


# --- drag & drop, Send clipboard, disconnection reasons -------------------------------

class _FakeSession(object):
    """
    Just enough of RDPApplication for the widget's clipboard paths.
    """

    def __init__(self, files=True):
        self.isReady, self.isRunning, self.isFileClipboardEnabled = True, True, files
        self.saved = []

    def saveClipboard(self, kind, data, includeParent=False):
        self.saved.append((kind, data))

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


def _widgetWith(session):
    from PyFreeRdpApp.rdpwidget import RDPWidget
    w = RDPWidget(designMode=True)
    w._RDPWidget__m_app = session  # the widget's session, without connecting
    w._RDPWidget__m_designMode = False
    w.isReady = lambda: True
    w.isFileClipboardEnabled = lambda: session.isFileClipboardEnabled
    return w


def _drop(widget, paths, proposed):
    from ManyQt.QtCore import QMimeData, QPointF, Qt, QUrl
    from ManyQt.QtGui import QDropEvent
    mime = QMimeData()  # type: QMimeData
    mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
    event = QDropEvent(
        QPointF(5, 5), Qt.CopyAction | Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)  # type: QDropEvent
    event.setDropAction(proposed)
    widget.dropEvent(event)
    return event


def _waitFor(predicate, seconds=3.0):
    from time import sleep, time
    end = time() + seconds
    while time() < end and not predicate():
        _QAPP[0].processEvents()
        sleep(0.01)
    return predicate()


# def test_drop_is_always_a_copy_and_reaches_the_session(tmp_path):
#     _qt()
#     from ManyQt.QtCore import Qt
#     source = tmp_path / u'a.txt'
#     source.write_text(u'x')
#     session = _FakeSession()
#     w = _widgetWith(session)
#     sentList = []
#     w.clipboardSent.connect(sentList.append)
#     event = _drop(w, [str(source)], Qt.MoveAction)  # a file manager proposing a MOVE
#     assert event.isAccepted() and event.dropAction() == Qt.CopyAction
#     assert _waitFor(lambda: session.saved and sentList)
#     assert session.saved == [(u'file', [str(source)])] and u'1 item' in sentList[0]


def test_drop_explains_when_the_server_refuses_files(tmp_path):
    _qt()
    from ManyQt.QtCore import Qt
    source = tmp_path / u'a.txt'
    source.write_text(u'x')
    session = _FakeSession(files=False)
    w = _widgetWith(session)
    errors = []
    w.clipboardError.connect(errors.append)
    _drop(w, [str(source)], Qt.CopyAction)
    assert session.saved == [] and errors and u'does not allow file transfer' in errors[0]


def test_send_clipboard_explains_an_empty_clipboard():
    _qt()
    from ManyQt.QtWidgets import QApplication
    QApplication.clipboard().clear()
    w = _widgetWith(_FakeSession())
    errors = []
    w.clipboardError.connect(errors.append)
    w.resendClipboard()
    assert errors and u'empty' in errors[0]


def test_disconnect_dialog_shows_the_cause():
    _qt()
    from PyFreeRdpApp.rdpwidget import DisconnectDialog
    d = DisconnectDialog(reason={u'phase': u'session', u'message': u'The user logged off.',
                                 u'serverCode': 0xC, u'serverName': u'ERRINFO_LOGOFF_BY_USER',
                                 u'serverMessage': u'The user logged off.'}, server=u'rdp.example')
    assert d.windowTitle() == u'Disconnected' and u'rdp.example' in d.text()
    assert d.informativeText() == u'The user logged off.' and u'ERRINFO_LOGOFF_BY_USER' in d.detailedText()
    assert [b.text() for b in d.buttons()][:2] == [u'Reconnect', u'Cancel']
    d.setReason({u'phase': u'connect', u'message': u'Logon failed.'})
    assert d.windowTitle() == u'Connection failed'


def test_disconnect_reason_prefers_the_servers_word(env):
    app, mod, rec = env
    calls = []
    app.setDisconnectListener(calls.append)
    app._instance = c_void_p(1)
    app._ctx = c_void_p(1)
    rec.freerdp_error_info = lambda instance: 0xC
    rec.freerdp_get_error_info_string = lambda code: b'The user logged off.'
    rec.freerdp_get_last_error = lambda ctx: 0x2000D
    rec.freerdp_get_last_error_string = lambda code: b'The connection transport layer failed.'
    app._recordDisconnect(u'session')
    assert calls and calls[0][u'message'] == u'The user logged off.' and not calls[0][u'byUser']
    app._stop = True  # stop(): recorded, but nobody is alarmed
    app._recordDisconnect(u'session')
    assert len(calls) == 1 and app.getDisconnectReason()[u'byUser']


def test_icon_ships_and_reaches_designer():
    """
    The project icon: every size present, loaded by appIcon(), shown by the Designer plugin.
    """
    _qt()
    from PyFreeRdpApp.rdpwidget.rdpwidget import ICON_SIZES, IMAGES
    from PyFreeRdpApp.rdpwidget import appIcon
    from os.path import exists, join
    for name in [u'pyfreerdpapp-{}.png'.format(s) for s in ICON_SIZES] + [u'pyfreerdpapp.svg', u'pyfreerdpapp.ico',
                                                                          u'pyfreerdpapp.icns']:
        assert exists(join(IMAGES, name)), name
    sizes = [s.width() for s in appIcon().availableSizes()]
    assert sizes == list(ICON_SIZES)
    plugin = _designerWidget()
    shown = [s.width() for s in plugin.icon().availableSizes()]
    # PyQt's plugin returns appIcon(); PySide registers an icon FILE - the .ico, every size up to 256.
    assert shown == list(ICON_SIZES) or (shown and set(shown) <= set(ICON_SIZES))


# --- the crash report is about this process, once; the logon failure names the server ------

_EVENT = (u'Event[0]\n  Date: {date}\n  Event ID: 1000\n  Description:\n'
          u'Faulting application name: python.exe, version: 3.13.0.1013, time stamp: 0x1\n'
          u'Faulting module name: ucrtbase.dll, version: 10.0.1, time stamp: 0x2\n'
          u'Exception code: 0xc0000409\nFault offset: 0x0000000000071208\n'
          u'Faulting process id: {pid}\nFaulting module path: C:\\Windows\\System32\\ucrtbase.dll\n')


def test_crash_report_is_only_this_processes_new_crash():
    from PyFreeRdpApp._pyfreerdp import _crashOfProcess
    from datetime import datetime, timezone
    started = int(datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc).timestamp())  # The session's start.
    later, earlier = u'2026-10-25T10:00:00.0000000Z', u'2026-10-20T10:00:00.0000000Z'
    assert _crashOfProcess(_EVENT.format(date=later, pid=u'0x5460'), 0x5460, started)  # This one.
    assert _crashOfProcess(_EVENT.format(date=later, pid=u'0x1234'), 0x5460, started) is None  # Another process.
    assert _crashOfProcess(_EVENT.format(date=earlier, pid=u'0x5460'), 0x5460, started) is None  # an older crash.


def test_failed_connection_leaves_no_crash_marker(env, monkeypatch, tmp_path):
    import PyFreeRdpApp._pyfreerdp as core
    monkeypatch.setattr(core, u'_CRASH_MARKER', str(tmp_path / u'marker'))
    core._markSession(True)
    assert (tmp_path / u'marker').exists()
    core._markSession(False)
    assert not (tmp_path / u'marker').exists()


def test_logon_failure_names_the_computer_that_answered(env):
    app, mod, rec = env
    app._challenge = {u'netbiosComputerName': u'WIN-NEW', u'netbiosDomainName': u'WIN-NEW'}
    app._sentIdentity = (u'expert', u'WIN-OLD')
    text = app._explainLogonFailure()
    assert u'\'WIN-NEW\'' in text and u'user name alone' in text and u'WIN-NEW\\expert' in text
    app._sentIdentity = (u'expert', u'WIN-NEW')  # right machine: then it is the password
    assert u'check the password' in app._explainLogonFailure()
    app._challenge = None  # no challenge seen: still says what was sent
    assert u'user \'expert\' in domain \'WIN-NEW\'' in app._explainLogonFailure()



# --- FreeRDP 3: Azure AD sign-in through an AAD helper, UDP multitransport, lazy Qt -------------

def test_transport_flags_match_freerdp_cmdline(env):
    """
    setTransport writes what /multitransport:<mode> writes (client/common/cmdline.c).
    """
    try:
        from pyfreerdpnative.freerdp.settings_keys import FreeRDP_SupportMultitransportUdp, FreeRDP_MultitransportFlags
    except:
        skip(u'Needs the FreeRDP 3.33 bindings')
    from pyfreerdpnative.freerdp.settings_types import TRANSPORT_TYPE_UDP_FECR, SOFTSYNC_TCP_TO_UDP, \
        TRANSPORT_TYPE_UDP_PREFERRED
    app, mod, rec = env
    expected = {u'udp': (True, TRANSPORT_TYPE_UDP_FECR | SOFTSYNC_TCP_TO_UDP),
                u'udp-preferred': (True, TRANSPORT_TYPE_UDP_FECR | SOFTSYNC_TCP_TO_UDP | TRANSPORT_TYPE_UDP_PREFERRED),
                u'tcp-only': (False, None), u'default': (None, None)}
    for mode, (udp, flags) in expected.items():
        rec.calls[:] = []
        app.setTransport(mode)
        app._applySettings(c_void_p(1))
        bools = dict((a[1], a[2]) for n, a, _ in rec.calls if n == u'freerdp_settings_set_bool')
        numbers = dict((a[1], a[2]) for n, a, _ in rec.calls if n == u'freerdp_settings_set_uint32')
        assert bools.get(FreeRDP_SupportMultitransportUdp) == udp, mode
        assert numbers.get(FreeRDP_MultitransportFlags) == flags, mode
    with raises(ValueError):
        app.setTransport(u'carrier-pigeon')


def test_azure_ad_settings_and_freerdps_token_function(env, monkeypatch):
    """
    The helper path/user agent reach FreeRDP; GetAccessToken is FreeRDP's own C function.
    """
    aad = importorskip(u'pyfreerdpnative.aad')  # first: the names below need the FreeRDP 3.33 bindings
    from pyfreerdpnative.freerdp.settings_keys import FreeRDP_AadAuthHelper, FreeRDP_AadAuthUserAgent, \
        FreeRDP_AadSecurity
    from pyfreerdpnative.freerdp.freerdp import freerdp
    from os import environ
    app, mod, rec = env
    monkeypatch.setattr(
        aad, u'helper', lambda kind: (u'/opt/helpers/freerdp-qt-aad-helper', {u'PYFREERDPAPP_TEST_QT': u'qt-lib-dir'}))
    tokenFunction = CFUNCTYPE(c_int)(lambda: 0)
    rec.client_helper_get_access_token = tokenFunction
    instance = freerdp()
    app._instance = pointer(instance)
    app.setAzureAD(True, helper=u'qt', userAgent=u'UA/1.0')
    environ.pop(u'PYFREERDPAPP_TEST_QT', None)
    app._resolveAzureAD()
    assert environ[u'PYFREERDPAPP_TEST_QT'] == u'qt-lib-dir'
    app._applySettings(c_void_p(1))
    strings = dict((a[1], a[2]) for n, a, _ in rec.calls if n == u'freerdp_settings_set_string')
    bools = dict((a[1], a[2]) for n, a, _ in rec.calls if n == u'freerdp_settings_set_bool')
    assert strings[FreeRDP_AadAuthHelper] == b'/opt/helpers/freerdp-qt-aad-helper'
    assert strings[FreeRDP_AadAuthUserAgent] == b'UA/1.0' and bools[FreeRDP_AadSecurity] is True
    assert cast(instance.GetAccessToken, c_void_p).value == cast(tokenFunction, c_void_p).value
    app._resolveAzureAD()  # a retry must not save our own value as the original.
    app._restoreAzureADEnvironment()
    assert u'PYFREERDPAPP_TEST_QT' not in environ
    assert app.getSessionInfo()[u'azureAD'][u'enabled'] is True


def test_missing_aad_helper_fails_start_with_the_reason(env, monkeypatch):
    aad = importorskip(u'pyfreerdpnative.aad')
    app, mod, rec = env

    def noHelper(kind):
        raise LookupError(u'the webview helper is not part of this FreeRDP build')

    monkeypatch.setattr(aad, u'helper', noHelper)
    app.setServer(u'h')
    app.setAzureAD(True)
    with raises(ConnectionError) as info:
        app.start()
    assert u'not part of this FreeRDP build' in str(info.value)


# Run in a fresh interpreter: which Qt modules does import the package ADD, and who imported them?
_QT_IMPORT_PROBE = u'''
import sys, traceback
import linecache, tokenize  # Python 3.13+ imports tokenize lazily, at the first stack format: load it first
QT = ("ManyQt", "PyQt", "PySide")
before = set(m for m in sys.modules if m.startswith(QT))  # loaded at startup (sitecustomize, .pth): not ours
chain = []
busy = []

class Spy(object):
    def find_spec(self, name, path=None, target=None):
        # Only Qt names; and never re-entered: formatting a stack can import modules itself.
        if busy or chain or not name.startswith(QT):
            return None
        busy.append(True)
        try:
            self.record(name)
        finally:
            busy.pop()
        return None  # let the real finders import it

    def record(self, name):
        stack = traceback.format_stack()[:-2]
        # Only the import machinery innermost to THIS lookup tells what it is: importlib.util.find_spec only
        # looks (loads nothing); anything else imports. (An outer import - the package's own - is always there.)
        last = max(i for i, f in enumerate(stack) if "importlib" not in f)
        # "<frozen importlib.util>" (Python 3.11+) or ".../importlib/util.py"
        lookup = any("importlib" in f and "util" in f for f in stack[last + 1:])
        if not lookup:  # the first real Qt import: who made it
            chain.extend(f for f in stack if "importlib" not in f)

sys.meta_path.insert(0, Spy())
import PyFreeRdpApp, PyFreeRdpApp.__main__
print(sorted(m for m in sys.modules if m.startswith(QT) and m not in before))
print("".join(chain[-8:]))
'''


def test_import_loads_no_qt():
    """
    The widget is imported on first use: the package and console mode never load Qt themselves. What the
    interpreter loads before (a site customize or .pth startup hook) is the environment's, not the package's;
    on failure, the message shows which file and line imported Qt.
    """
    import sys
    out = check_output([sys.executable, u'-c', _QT_IMPORT_PROBE]).decode(u'utf-8', u'replace')
    added, _, chain = out.partition(u'\n')
    assert added.strip() == u'[]', u'importing PyFreeRdpApp loaded {} - imported from:\n{}'.format(added.strip(), chain)


def test_azure_ad_needs_no_password():
    import PyFreeRdpApp.__main__ as main
    assert not main.needsInput(main.parseArgs([u'p', u'host.example', u'--azure-ad']))
    assert main.needsInput(main.parseArgs([u'p', u'host.example']))


# --- stop() keeps the last input; --upload puts a file on the remote desktop ------------------------

def test_stop_delivers_queued_input_then_lingers(env, monkeypatch):
    """
    Input sent just before stop() used to vanish: it ran after the abort, and a close with server
    updates unread is a TCP reset that drops what the server had not read yet.
    """
    from threading import Thread
    from time import sleep
    app, mod, rec = env

    def rdpThread():
        """
        :return:
        """
        while not app._stop:
            app._drain()
            sleep(0.005)

    thread = Thread(target=rdpThread)  # type: Thread
    thread.daemon = True
    thread.start()
    app._thread, app._ready = thread, True
    sentList = []
    app._post(lambda: (sentList.append(u'key'), setattr(app, u'_lastInputAt', mod.monotonic())))
    slept = []
    monkeypatch.setattr(mod, u'sleep', lambda seconds: slept.append(seconds))
    app.stop()
    assert sentList == [u'key']  # Delivered while the connection was up
    assert slept and 0 < slept[0] <= mod.INPUT_LINGER  # and given time to be read.


def test_audio_latency_reaches_the_playback_channel(env):
    """
    A short rdpsnd buffer keeps sound with the picture (FreeRDP reports the real latency to the server).
    """
    app, mod, rec = env
    for latency, expected in ((50, [b'rdpsnd', b'latency:50']), (120, [b'rdpsnd', b'latency:120']), (0, [b'rdpsnd'])):
        rec.calls[:] = []
        app.setAudioLatency(latency)
        app.setSound(True)
        app._applySettings(c_void_p(1))
        channels = [list(a[2])[:a[1]] for n, a, _ in rec.calls if n == u'freerdp_client_add_static_channel']
        assert expected in channels, latency  # 0: the backend's own default
    with raises(ValueError):
        app.setAudioLatency(5000)


class _Clock(object):
    """
    A fast clock for the blocking session helpers: sleep() advances time instead of waiting.
    """

    def __init__(self):
        self.now = 0.0  # type: float

    def sleep(self, seconds):
        """
        :param seconds: float | int
        :return:
        """
        self.now += max(seconds, 0.01)  # type: float

    def monotonic(self):
        """
        :return: float | int
        """
        return self.now


def _scriptedSession(env, monkeypatch, fileClipboard=True, pastes=True, size=1000):
    """
    A real RDPApplication whose input is recorded; Ctrl+V makes the remote side 'download'.
    """
    from PyFreeRdpApp.keyboard import KEY_V
    app, mod, rec = env
    clock = _Clock()
    monkeypatch.setattr(mod, u'sleep', clock.sleep)
    monkeypatch.setattr(mod, u'monotonic', clock.monotonic)
    state = {u'served': 0, u'events': []}
    cls = type(app)
    monkeypatch.setattr(cls, u'isFileClipboardEnabled', property(lambda self: fileClipboard))
    monkeypatch.setattr(cls, u'isFileTransferFinished', property(lambda self: state[u'served'] >= size))
    monkeypatch.setattr(app, u'getFileTransferProgress', lambda: (state[u'served'], size))
    monkeypatch.setattr(app, u'getDisplaySize', lambda: (800, 600))
    monkeypatch.setattr(app, u'saveClipboard', lambda kind, data, *a: state[u'events'].append((u'clipboard', data)))
    monkeypatch.setattr(app, u'leftMouseDown', lambda x, y: state[u'events'].append((u'down', x, y)))
    monkeypatch.setattr(app, u'leftMouseUp', lambda x, y: state[u'events'].append((u'up', x, y)))
    monkeypatch.setattr(app, u'typeText', lambda text, typingDelay=20: state[u'events'].append((u'type', text)))
    monkeypatch.setattr(app, u'_checkConnected', lambda: None)

    def hotkey(*codes, **kw):
        state[u'events'].append((u'hotkey', codes))
        if KEY_V in codes and pastes:
            state[u'served'] = size

    monkeypatch.setattr(app, u'hotkey', hotkey)
    return app, state


def test_upload_files_pastes_on_the_remote_desktop(env, monkeypatch, tmp_path):
    from PyFreeRdpApp.keyboard import LEFT_WINDOW, KEY_D, LEFT_CONTROL, KEY_V
    app, state = _scriptedSession(env, monkeypatch)
    first, second = tmp_path / u'a.zip', tmp_path / u'b.txt'
    first.write_bytes(b'x' * 10)
    second.write_bytes(b'y')
    seen = []
    assert app.uploadFiles([str(first), str(second)], progress=lambda r, t: seen.append((r, t))) == 1000
    kinds = [e[0] for e in state[u'events']]
    assert kinds == [u'clipboard', u'hotkey', u'down', u'up', u'hotkey']
    assert state[u'events'][0][1] == [str(first), str(second)]  # several files at once
    assert state[u'events'][1] == (u'hotkey', (LEFT_WINDOW, KEY_D))
    assert state[u'events'][4] == (u'hotkey', (LEFT_CONTROL, KEY_V))
    assert seen[-1] == (1000, 1000)


def test_upload_files_retries_without_toggling_the_desktop_back(env, monkeypatch, tmp_path):
    """
    Win+D is a toggle: a retry repeats only the click and Ctrl+V; nothing pasted -> TimeoutError.
    """
    from PyFreeRdpApp.keyboard import LEFT_WINDOW, KEY_D
    app, state = _scriptedSession(env, monkeypatch, pastes=False)
    target = tmp_path / u'a.zip'
    target.write_bytes(b'x')
    with raises(TimeoutError):
        app.uploadFiles(str(target))
    hotkeys = [e[1] for e in state[u'events'] if e[0] == u'hotkey']
    assert hotkeys.count((LEFT_WINDOW, KEY_D)) == 1 and len(hotkeys) == 3


def test_upload_files_errors(env, monkeypatch, tmp_path):
    app, state = _scriptedSession(env, monkeypatch, fileClipboard=False)
    target = tmp_path / u'a.zip'
    target.write_bytes(b'x')
    with raises(PermissionError):
        app.uploadFiles(str(target))
    with raises(FileNotFoundError):
        app.uploadFiles(str(tmp_path / u'missing.zip'))


def test_console_upload_exit_codes(monkeypatch, tmp_path):
    import PyFreeRdpApp.__main__ as main
    monkeypatch.setattr(main, u'sleep', lambda s: None)
    target = tmp_path / u'a.zip'
    target.write_bytes(b'x')

    class App(object):
        """
        App class.
        """

        def __init__(self, outcome):
            self.outcome = outcome

        def uploadFiles(self, paths, timeout=0, progress=None):
            """
            :param paths: list[str | unicode]
            :param timeout: int
            :param progress: callable | None
            :return: int
            """
            if self.outcome == u'incomplete':
                progress(5, 10)
            if isinstance(self.outcome, type):
                raise self.outcome(u'x')
            if self.outcome == u'incomplete':
                raise TimeoutError(u'incomplete')
            return 10

    args = main.parseArgs([u'p', u'h', u'u', u'pw', u'--upload', str(target), u'--upload-wait', u'0'])
    assert main.uploadToDesktop(App(None), args) == 0
    assert main.uploadToDesktop(App(PermissionError), args) == 4
    assert main.uploadToDesktop(App(TimeoutError), args) == 5  # nothing pasted.
    assert main.uploadToDesktop(App(u'incomplete'), args) == 6  # started, not finished.
    missing = main.parseArgs([u'p', u'h', u'u', u'pw', u'--upload', str(tmp_path / u'no.zip')])
    assert main.uploadToDesktop(App(None), missing) == 2


def test_widget_reports_uploads(env, monkeypatch, tmp_path):
    from ManyQt.QtWidgets import QApplication
    from time import sleep
    QApplication.instance() or QApplication([])
    from PyFreeRdpApp import RDPWidget
    app, state = _scriptedSession(env, monkeypatch)
    monkeypatch.setattr(type(app), u'isReady', property(lambda self: True))
    widget = RDPWidget()
    widget._RDPWidget__m_app = app
    results = []
    widget.uploadFinished.connect(lambda ok, message: results.append(ok))
    target = tmp_path / u'a.zip'
    target.write_bytes(b'x')
    widget.uploadFiles([str(target)])
    for _ in range(200):
        QApplication.processEvents()
        if results:
            break
        sleep(0.01)
    assert results == [True]


class _FakeRail(object):
    """
    A RemoteApp channel: records Client Execute orders; the 'server' answers through the app's handler.
    """

    def __init__(self, app, verdicts):
        self.app, self.verdicts, self.orders = app, list(verdicts), []
        outer = self

        class Contents(object):
            """
            Contents class.
            """

            @staticmethod
            def ClientExecute(rail, order):
                o = order._obj
                outer.orders.append((o.flags, o.RemoteApplicationProgram, o.RemoteApplicationArguments,
                                     o.RemoteApplicationWorkingDir))
                verdict = outer.verdicts.pop(0)

                class Result(object):
                    """
                    Result class.
                    """
                    contents = type(u'R', (), {u'execResult': verdict, u'rawResult': 0x80070005 if verdict else 0})

                outer.app._railExecuteResult(None, Result)
                return 0

        self.contents = Contents()  # type: Contents


def test_run_command_goes_over_the_remoteapp_channel(env, monkeypatch):
    """
    No keyboard, no clipboard: a Client Execute order, and the server's verdict.
    """
    from pyfreerdpnative.freerdp.rail import RAIL_EXEC_S_OK, RAIL_EXEC_E_NOT_IN_ALLOWLIST
    app, mod, rec = env
    monkeypatch.setattr(app, u'_call', lambda fn, timeout=10.0: fn())
    with raises(RuntimeError):  # a desktop session: RDP has no protocol way
        app.runCommand(u'notepad')
    app.setRemoteApp(u'notepad')
    app._rail = _FakeRail(app, [RAIL_EXEC_S_OK, RAIL_EXEC_E_NOT_IN_ALLOWLIST])
    app.runCommand(u'cmd', u'/k ipconfig', u'%USERPROFILE%')
    assert app._rail.orders[0] == (mod.RAIL_EXEC_FLAGS, b'cmd', b'/k ipconfig', b'%USERPROFILE%')
    assert mod.RAIL_EXEC_FLAGS == 0x0009  # expand arguments and working folder
    with raises(RuntimeError) as info:
        app.runCommand(u'blocked.exe')
    assert u'does not allow this program' in str(info.value)
    with raises(ValueError):
        app.runCommand(u'  ')


def test_wait_for_remoteapp_reports_the_server_answer(env):
    from pyfreerdpnative.freerdp.rail import RAIL_EXEC_E_FILE_NOT_FOUND, RAIL_EXEC_S_OK
    app, mod, rec = env
    app.setRemoteApp(u'notepad')
    app._execResults.append((RAIL_EXEC_E_FILE_NOT_FOUND, 2))
    with raises(RuntimeError) as info:
        app.waitForRemoteApp(timeout=0.1)
    assert u'did not find the program' in str(info.value)
    app._execResults[:] = [(RAIL_EXEC_S_OK, 0)]
    app.waitForRemoteApp(timeout=0.1)


def test_program_settings(env):
    """
    Alternate shell: sent with the logon. RemoteApp: FreeRDP then loads the rail channel.
    """
    from pyfreerdpnative.freerdp.settings_keys import FreeRDP_AlternateShell, FreeRDP_ShellWorkingDirectory, \
        FreeRDP_RemoteApplicationMode, FreeRDP_RemoteApplicationProgram, FreeRDP_RemoteApplicationCmdLine
    app, mod, rec = env
    app.setStartProgram(u'cmd /k echo hi', u'C:\\Temp')
    app._applySettings(c_void_p(1))
    strings = dict((a[1], a[2]) for n, a, _ in rec.calls if n == u'freerdp_settings_set_string')
    assert strings[FreeRDP_AlternateShell] == b'cmd /k echo hi' and strings[
        FreeRDP_ShellWorkingDirectory] == b'C:\\Temp'
    rec.calls[:] = []
    app.setRemoteApp(u'notepad', u'C:\\notes.txt', u'%USERPROFILE%')
    app._applySettings(c_void_p(1))
    strings = dict((a[1], a[2]) for n, a, _ in rec.calls if n == u'freerdp_settings_set_string')
    flags = dict((a[1], a[2]) for n, a, _ in rec.calls if n == u'freerdp_settings_set_bool')
    assert flags[FreeRDP_RemoteApplicationMode] is True
    assert strings[FreeRDP_RemoteApplicationProgram] == b'notepad'
    assert strings[FreeRDP_RemoteApplicationCmdLine] == b'C:\\notes.txt'
    assert FreeRDP_AlternateShell not in strings  # RemoteApp wins


def test_console_program_options(env, monkeypatch):
    import PyFreeRdpApp.__main__ as main
    app, mod, rec = env
    monkeypatch.setattr(main, u'RDPApplication', lambda: app)  # the fake FreeRDP: no libraries needed
    args = main.parseArgs(
        [u'p', u'h', u'u', u'pw', u'--app', u'notepad', u'--app-args', u'a.txt', u'--workdir', u'C:\\'])
    assert main.buildApp(args).getRemoteApp() == (u'notepad', u'a.txt', u'C:\\')
    args = main.parseArgs([u'p', u'h', u'u', u'pw', u'--shell', u'cmd'])
    assert main.buildApp(args).getStartProgram() == (u'cmd', u'')
    assert main.parseArgs([u'p', u'h']).audio_latency == 50

    class Refused(object):
        """
        Refused class.
        """

        def waitForRemoteApp(self):
            """
            :return:
            """
            raise RuntimeError(u'refused')

    assert main.reportRemoteApp(Refused(), main.parseArgs([u'p', u'h', u'--app', u'x'])) == 7


def test_widget_runs_over_the_protocol(env, monkeypatch):
    from ManyQt.QtWidgets import QApplication
    from time import sleep
    QApplication.instance() or QApplication([])
    from PyFreeRdpApp import RDPWidget
    app, mod, rec = env
    monkeypatch.setattr(type(app), u'isReady', property(lambda self: True))
    sentList = []
    monkeypatch.setattr(app, u'runCommand', lambda program, arguments=u'', workingDir=u'': sentList.append(
        (program, arguments, workingDir)))
    widget = RDPWidget()
    widget._RDPWidget__m_app = app
    results = []
    widget.commandFinished.connect(lambda ok, message: results.append((ok, message)))
    widget.runCommand(u'cmd', u'/k ipconfig', u'C:\\Temp')
    for _ in range(200):
        QApplication.processEvents()
        if results:
            break
        sleep(0.01)
    assert sentList == [(u'cmd', u'/k ipconfig', u'C:\\Temp')] and results == [(True, u'cmd /k ipconfig')]


def test_frames_are_presented_when_published_coalesced(env):
    """
    The RDP thread asks the GUI for a present once per burst, not once per paint.
    """
    from ManyQt.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from PyFreeRdpApp import RDPWidget
    widget = RDPWidget()  # type: RDPWidget
    emitted = []
    widget._frameReady.connect(lambda: emitted.append(1))
    from threading import Thread
    worker = Thread(target=lambda: [widget._frameAvailable() for _ in range(5)])  # Like the RDP thread.
    worker.start()
    worker.join()  # Five paints published before the GUI thread runs.
    QApplication.processEvents()
    assert len(emitted) == 1


def test_upload_is_console_only():
    import PyFreeRdpApp.__main__ as main
    assert main.isConsoleMode(main.parseArgs([u'p', u'host', u'u', u'pw', u'--upload', u'C:\\usama.zip']))



def test_session_window_builds_with_run_after_connecting(env, monkeypatch):
    """
    The session window builds with a program to start (it once crashed on that path),
    and has the Upload files / Run program buttons.
    """
    from ManyQt.QtWidgets import QApplication, QMessageBox, QToolBar
    QApplication.instance() or QApplication([])
    import PyFreeRdpApp.__main__ as main
    app, mod, rec = env
    monkeypatch.setattr(QMessageBox, u'warning', staticmethod(lambda *a, **k: 0))
    args = main.parseArgs([u'p', u'h', u'u', u'pw', u'--app', u'notepad', u'--upload-wait', u'0'])
    window = main.MainWindow(app, args)
    names = [a.text() for a in window.findChildren(QToolBar)[0].actions()]
    assert u'Upload files...' in names and u'Run program...' in names
