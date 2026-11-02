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

    try:
        from .rdpwidget.rdpwidget import GRAPHICS_OPTIONS, BACKGROUND, FOREGROUND, frameToQimage, nativeToScancode, \
            MIRRORED, IMAGES, ICON_SIZES, appIcon, localPaths, snapshotTree, qtExec, RDPWidget
        from .rdpwidget.disconnectdialog import DisconnectDialog
    except:
        pass
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

    try:
        from rdpwidget.rdpwidget import GRAPHICS_OPTIONS, BACKGROUND, FOREGROUND, frameToQimage, nativeToScancode, \
            MIRRORED, IMAGES, ICON_SIZES, appIcon, localPaths, snapshotTree, qtExec, RDPWidget
        from rdpwidget.disconnectdialog import DisconnectDialog
    except:
        pass

__all__ = ['__author__', '__copyright__', '__credits__', '__email__', '__maintainer__', '__status__', '__version__',
           'INVALID', 'ESCAPE', 'KEY_1', 'KEY_2', 'KEY_3', 'KEY_4', 'KEY_5', 'KEY_6', 'KEY_7', 'KEY_8', 'KEY_9',
           'KEY_0', 'MINUS', 'EQUAL', 'DOUBLE_HYPHEN', 'BACKSPACE', 'TAB', 'KEY_Q', 'KEY_W', 'KEY_E', 'KEY_R', 'KEY_T',
           'KEY_Y', 'KEY_U', 'KEY_I', 'KEY_O', 'KEY_P', 'LEFT_SQ_BRACKET', 'RIGHT_SQ_BRACKET', 'ENTER', 'LEFT_CONTROL',
           'KEY_A', 'KEY_S', 'KEY_D', 'KEY_F', 'KEY_G', 'KEY_H', 'KEY_J', 'KEY_K', 'KEY_L', 'SEMICOLON', 'APOSTROF',
           'GRAVE_ACCENT', 'LEFT_SHIFT', 'BACKSLASH', 'KEY_Z', 'KEY_X', 'KEY_C', 'KEY_V', 'KEY_B', 'KEY_N', 'KEY_M',
           'COMMA', 'PERIOD', 'SLASH', 'RIGHT_SHIFT', 'NUMPAD_ASTERISK', 'LEFT_ALT', 'SPACE_BAR', 'CAPS_LOCK', 'F1',
           'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'NUM_LOCK', 'SCROLL_LOCK', 'NUMPAD_7', 'NUMPAD_8',
           'NUMPAD_9', 'NUMPAD_MINUS', 'NUMPAD_4', 'NUMPAD_5', 'NUMPAD_6', 'NUMPAD_PLUS', 'NUMPAD_1', 'NUMPAD_2',
           'NUMPAD_3', 'NUMPAD_0', 'NUMPAD_DECIMAL', 'SYSREQ', 'F11', 'F12', 'NUMPAD_ENTER', 'RIGHT_CONTROL',
           'NUMPAD_DIVIDE', 'PRINT_SCREEN', 'RIGHT_ALT', 'PAUSE', 'HOME', 'UP', 'PAGE_UP', 'LEFT', 'RIGHT', 'END',
           'DOWN', 'PAGE_DOWN', 'INSERT', 'DELETE', 'LEFT_WINDOW', 'RIGHT_WINDOW', 'MENU', '_makeKey', '_PIXEL_FORMATS',
           '_TYPED_AS_SCANCODE', '_WHEEL_DOWN', '_WHEEL_UP', '_RECONNECT_ATTEMPTS', 'DISPLAY_FORMATS', 'RDP_VERSIONS',
           '_DISPLAY_FORMAT_ERROR', '_guard', 'initializeLogging', '_crashFile', '_enableCrashLog', '_CRASH_MARKER',
           '_parseWindowsCrashEvent', 'lastNativeCrash', '_crashOfProcess', '_markSession', 'RDPClipboardError',
           '_convertFrame', '_waitFunction', '_WakeEvent', '_Call', 'RDPApplication', 'PROTOCOL_RDP', 'PROTOCOL_SSL',
           'PROTOCOL_HYBRID', 'PROTOCOL_RDSTLS', 'PROTOCOL_HYBRID_EX', 'PROTOCOL_RDSAAD', 'PROTOCOL_NAMES', 'AV_NAMES',
           'AV_TIMESTAMP', 'WINDOWS_BUILDS', 'protocolNames', 'windowsName', 'filetimeToDatetime', 'parseChallenge',
           'DIGESTS', 'StreamHead', '_peImport', '_FREE', 'freerdpFree', '_native', 'parseUsername',
           'describeCertificate', 'humanDuration', 'FILE_GROUP_DESCRIPTOR_W', 'LOCAL_FILE_FORMAT_ID', 'CHUNK',
           'TIMEOUT', 'FILETIME_EPOCH', '_fieldType', 'encodeText', 'decodeText', 'buildFileList', 'parseFileList',
           'collectFiles', 'Clipboard', 'GRAPHICS_OPTIONS', 'BACKGROUND', 'FOREGROUND', 'frameToQimage',
           'nativeToScancode', 'MIRRORED', 'IMAGES', 'ICON_SIZES', 'appIcon', 'localPaths', 'snapshotTree', 'qtExec',
           'RDPWidget', 'DisconnectDialog']  # type: list[str]
