# coding=utf-8
"""
Init the project.
"""
from os.path import dirname
from sys import path

if dirname(__file__) not in path:
    path.append(dirname(__file__))

try:
    from .metadata import __author__, __copyright__, __credits__, __email__, __maintainer__, __status__, __version__
    from .keyboard import INVALID, ESCAPE, KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6, KEY_7, KEY_8, KEY_9, KEY_0, \
        MINUS, EQUAL, DOUBLE_HYPHEN, BACKSPACE, TAB, KEY_Q, KEY_W, KEY_E, KEY_R, KEY_T, KEY_Y, KEY_U, KEY_I, KEY_O, \
        KEY_P, LEFT_SQ_BRACKET, RIGHT_SQ_BRACKET, ENTER, LEFT_CONTROL, KEY_A, KEY_S, KEY_D, KEY_F, KEY_G, KEY_H, \
        KEY_J, KEY_K, KEY_L, SEMICOLON, APOSTROF, GRAVE_ACCENT, LEFT_SHIFT, BACKSLASH, KEY_Z, KEY_X, KEY_C, KEY_V, \
        KEY_B, KEY_N, KEY_M, COMMA, PERIOD, SLASH, RIGHT_SHIFT, NUMPAD_ASTERISK, LEFT_ALT, SPACE_BAR, CAPS_LOCK, F1, \
        F2, F3, F4, F5, F6, F7, F8, F9, F10, NUM_LOCK, SCROLL_LOCK, NUMPAD_7, NUMPAD_8, NUMPAD_9, NUMPAD_MINUS, \
        NUMPAD_4, NUMPAD_5, NUMPAD_6, NUMPAD_PLUS, NUMPAD_1, NUMPAD_2, NUMPAD_3, NUMPAD_0, NUMPAD_DECIMAL, SYSREQ, \
        F11, F12, NUMPAD_ENTER, RIGHT_CONTROL, NUMPAD_DIVIDE, PRINT_SCREEN, RIGHT_ALT, PAUSE, HOME, UP, PAGE_UP, LEFT, \
        RIGHT, END, DOWN, PAGE_DOWN, INSERT, DELETE, LEFT_WINDOW, RIGHT_WINDOW, MENU, _makeKey
    from ._pyfreerdp import _PIXEL_FORMATS, _TYPED_AS_SCANCODE, _WHEEL_DOWN, _WHEEL_UP, _RECONNECT_ATTEMPTS, \
        DISPLAY_FORMATS, RDP_VERSIONS, _DISPLAY_FORMAT_ERROR, _guard, initializeLogging, _crashFile, _enableCrashLog, \
        _CRASH_MARKER, _parseWindowsCrashEvent, lastNativeCrash, _crashOfProcess, _markSession, RDPClipboardError, \
        _convertFrame, _waitFunction, _WakeEvent, _Call, RDPApplication
    from ._serverinfo import PROTOCOL_RDP, PROTOCOL_SSL, PROTOCOL_HYBRID, PROTOCOL_RDSTLS, PROTOCOL_HYBRID_EX, \
        PROTOCOL_RDSAAD, PROTOCOL_NAMES, AV_NAMES, AV_TIMESTAMP, WINDOWS_BUILDS, protocolNames, windowsName, \
        filetimeToDatetime, parseChallenge, DIGESTS, StreamHead, _peImport, _FREE, freerdpFree, _native, \
        parseUsername, describeCertificate, humanDuration
    from ._cliprdr import FILE_GROUP_DESCRIPTOR_W, LOCAL_FILE_FORMAT_ID, CHUNK, TIMEOUT, FILETIME_EPOCH, _fieldType, \
        encodeText, decodeText, buildFileList, parseFileList, collectFiles, Clipboard
except:
    from metadata import __author__, __copyright__, __credits__, __email__, __maintainer__, __status__, __version__
    from keyboard import INVALID, ESCAPE, KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6, KEY_7, KEY_8, KEY_9, KEY_0, \
        MINUS, EQUAL, DOUBLE_HYPHEN, BACKSPACE, TAB, KEY_Q, KEY_W, KEY_E, KEY_R, KEY_T, KEY_Y, KEY_U, KEY_I, KEY_O, \
        KEY_P, LEFT_SQ_BRACKET, RIGHT_SQ_BRACKET, ENTER, LEFT_CONTROL, KEY_A, KEY_S, KEY_D, KEY_F, KEY_G, KEY_H, \
        KEY_J, KEY_K, KEY_L, SEMICOLON, APOSTROF, GRAVE_ACCENT, LEFT_SHIFT, BACKSLASH, KEY_Z, KEY_X, KEY_C, KEY_V, \
        KEY_B, KEY_N, KEY_M, COMMA, PERIOD, SLASH, RIGHT_SHIFT, NUMPAD_ASTERISK, LEFT_ALT, SPACE_BAR, CAPS_LOCK, F1, \
        F2, F3, F4, F5, F6, F7, F8, F9, F10, NUM_LOCK, SCROLL_LOCK, NUMPAD_7, NUMPAD_8, NUMPAD_9, NUMPAD_MINUS, \
        NUMPAD_4, NUMPAD_5, NUMPAD_6, NUMPAD_PLUS, NUMPAD_1, NUMPAD_2, NUMPAD_3, NUMPAD_0, NUMPAD_DECIMAL, SYSREQ, \
        F11, F12, NUMPAD_ENTER, RIGHT_CONTROL, NUMPAD_DIVIDE, PRINT_SCREEN, RIGHT_ALT, PAUSE, HOME, UP, PAGE_UP, LEFT, \
        RIGHT, END, DOWN, PAGE_DOWN, INSERT, DELETE, LEFT_WINDOW, RIGHT_WINDOW, MENU, _makeKey
    from _pyfreerdp import _PIXEL_FORMATS, _TYPED_AS_SCANCODE, _WHEEL_DOWN, _WHEEL_UP, _RECONNECT_ATTEMPTS, \
        DISPLAY_FORMATS, RDP_VERSIONS, _DISPLAY_FORMAT_ERROR, _guard, initializeLogging, _crashFile, _enableCrashLog, \
        _CRASH_MARKER, _parseWindowsCrashEvent, lastNativeCrash, _crashOfProcess, _markSession, RDPClipboardError, \
        _convertFrame, _waitFunction, _WakeEvent, _Call, RDPApplication
    from _serverinfo import PROTOCOL_RDP, PROTOCOL_SSL, PROTOCOL_HYBRID, PROTOCOL_RDSTLS, PROTOCOL_HYBRID_EX, \
        PROTOCOL_RDSAAD, PROTOCOL_NAMES, AV_NAMES, AV_TIMESTAMP, WINDOWS_BUILDS, protocolNames, windowsName, \
        filetimeToDatetime, parseChallenge, DIGESTS, StreamHead, _peImport, _FREE, freerdpFree, _native, \
        parseUsername, describeCertificate, humanDuration
    from _cliprdr import FILE_GROUP_DESCRIPTOR_W, LOCAL_FILE_FORMAT_ID, CHUNK, TIMEOUT, FILETIME_EPOCH, _fieldType, \
        encodeText, decodeText, buildFileList, parseFileList, collectFiles, Clipboard

from importlib import import_module

try:
    from importlib.util import find_spec
except:
    from imp import find_module


    def find_spec(name):
        """
        Check whether a module can be found.
        :param name: str | unicode
        """
        try:
            return find_module(name)
        except:
            return None

# The Qt widget is optional (the [qt] extra) and heavy: it is imported on first use, so that
# `import PyFreeRdpApp` - and the console-only --screenshot / --info - never load Qt.
_WIDGET_NAMES = dict([(name, u'rdpwidget.rdpwidget') for name in (
    u'GRAPHICS_OPTIONS', u'BACKGROUND', u'FOREGROUND', u'frameToQimage', u'nativeToScancode', u'MIRRORED', u'IMAGES',
    u'ICON_SIZES', u'appIcon', u'localPaths', u'snapshotTree', u'qtExec', u'RDPWidget')] +
                     [(u'DisconnectDialog', u'rdpwidget.disconnectdialog')])  # type: dict


def __getattr__(name):
    """
    PEP 562: the widget names, imported on first use.
    :param name: (str | unicode) The attribute.
    :return: any
    """
    module = _WIDGET_NAMES.get(name)
    if module is None:
        raise AttributeError(u'Module {!r} has no attribute {!r}'.format(__name__, name))
    try:
        try:
            value = getattr(import_module(u'.' + module, __name__) if __package__ else import_module(module), name)
        except:
            value = getattr(import_module(module, __name__) if __package__ else import_module(module), name)
    except ImportError as exc:
        raise AttributeError(u'PyFreeRdpApp.{} needs Qt - pip install "PyFreeRdpApp[qt]" ({})'.format(name, exc))
    globals()[name] = value
    return value


__all__ = [u'__author__', u'__copyright__', u'__credits__', u'__email__', u'__maintainer__', u'__status__',
           u'__version__', u'INVALID', u'ESCAPE', u'KEY_1', u'KEY_2', u'KEY_3', u'KEY_4', u'KEY_5', u'KEY_6', u'KEY_7',
           u'KEY_8', u'KEY_9', u'KEY_0', u'MINUS', u'EQUAL', u'DOUBLE_HYPHEN', u'BACKSPACE', u'TAB', u'KEY_Q',
           u'KEY_W', u'KEY_E', u'KEY_R', u'KEY_T', u'KEY_Y', u'KEY_U', u'KEY_I', u'KEY_O', u'KEY_P',
           u'LEFT_SQ_BRACKET', u'RIGHT_SQ_BRACKET', u'ENTER', u'LEFT_CONTROL', u'KEY_A', u'KEY_S', u'KEY_D', u'KEY_F',
           u'KEY_G', u'KEY_H', u'KEY_J', u'KEY_K', u'KEY_L', u'SEMICOLON', u'APOSTROF', u'GRAVE_ACCENT', u'LEFT_SHIFT',
           u'BACKSLASH', u'KEY_Z', u'KEY_X', u'KEY_C', u'KEY_V', u'KEY_B', u'KEY_N', u'KEY_M', u'COMMA', u'PERIOD',
           u'SLASH', u'RIGHT_SHIFT', u'NUMPAD_ASTERISK', u'LEFT_ALT', u'SPACE_BAR', u'CAPS_LOCK', u'F1', u'F2', u'F3',
           u'F4', u'F5', u'F6', u'F7', u'F8', u'F9', u'F10', u'NUM_LOCK', u'SCROLL_LOCK', u'NUMPAD_7', u'NUMPAD_8',
           u'NUMPAD_9', u'NUMPAD_MINUS', u'NUMPAD_4', u'NUMPAD_5', u'NUMPAD_6', u'NUMPAD_PLUS', u'NUMPAD_1',
           u'NUMPAD_2', u'NUMPAD_3', u'NUMPAD_0', u'NUMPAD_DECIMAL', u'SYSREQ', u'F11', u'F12', u'NUMPAD_ENTER',
           u'RIGHT_CONTROL', u'NUMPAD_DIVIDE', u'PRINT_SCREEN', u'RIGHT_ALT', u'PAUSE', u'HOME', u'UP', u'PAGE_UP',
           u'LEFT', u'RIGHT', u'END', u'DOWN', u'PAGE_DOWN', u'INSERT', u'DELETE', u'LEFT_WINDOW', u'RIGHT_WINDOW',
           u'MENU', u'_makeKey', u'_PIXEL_FORMATS', u'_TYPED_AS_SCANCODE', u'_WHEEL_DOWN', u'_WHEEL_UP',
           u'_RECONNECT_ATTEMPTS', u'DISPLAY_FORMATS', u'RDP_VERSIONS', u'_DISPLAY_FORMAT_ERROR', u'_guard',
           u'initializeLogging', u'_crashFile', u'_enableCrashLog', u'_CRASH_MARKER', u'_parseWindowsCrashEvent',
           u'lastNativeCrash', u'_crashOfProcess', u'_markSession', u'RDPClipboardError', u'_convertFrame',
           u'_waitFunction', u'_WakeEvent', u'_Call', u'RDPApplication', u'PROTOCOL_RDP', u'PROTOCOL_SSL',
           u'PROTOCOL_HYBRID', u'PROTOCOL_RDSTLS', u'PROTOCOL_HYBRID_EX', u'PROTOCOL_RDSAAD', u'PROTOCOL_NAMES',
           u'AV_NAMES', u'AV_TIMESTAMP', u'WINDOWS_BUILDS', u'protocolNames', u'windowsName', u'filetimeToDatetime',
           u'parseChallenge', u'DIGESTS', u'StreamHead', u'_peImport', u'_FREE', u'freerdpFree', u'_native',
           u'parseUsername', u'describeCertificate', u'humanDuration', u'FILE_GROUP_DESCRIPTOR_W',
           u'LOCAL_FILE_FORMAT_ID', u'CHUNK', u'TIMEOUT', u'FILETIME_EPOCH', u'_fieldType', u'encodeText',
           u'decodeText', u'buildFileList', u'parseFileList', u'collectFiles', u'Clipboard']  # type: list[str]
if find_spec(u'ManyQt'):  # With Qt installed, `from PyFreeRdpApp import *` also offers the widget names.
    __all__.extend(_WIDGET_NAMES)  # The names only: nothing is imported here - the widget loads on first use.
