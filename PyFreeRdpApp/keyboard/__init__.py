# coding=utf-8
"""
Keyboard module.
"""


def _makeKey(code, extended=False, isPause=False):
    """
    :param code: int | hex
    :param extended: bool
    :param isPause: bool
    :return: int | hex
    """
    return (0x0100 if extended else 0x0000) | code


INVALID = _makeKey(0x00)  # type: int
ESCAPE = _makeKey(0x01)  # type: int
KEY_1 = _makeKey(0x02)  # type: int
KEY_2 = _makeKey(0x03)  # type: int
KEY_3 = _makeKey(0x04)  # type: int
KEY_4 = _makeKey(0x05)  # type: int
KEY_5 = _makeKey(0x06)  # type: int
KEY_6 = _makeKey(0x07)  # type: int
KEY_7 = _makeKey(0x08)  # type: int
KEY_8 = _makeKey(0x09)  # type: int
KEY_9 = _makeKey(0x0A)  # type: int
KEY_0 = _makeKey(0x0B)  # type: int
MINUS = _makeKey(0x0C)  # type: int
EQUAL = _makeKey(0x0D)  # type: int
DOUBLE_HYPHEN = _makeKey(0x0D)  # type: int
BACKSPACE = _makeKey(0x0E)  # type: int
TAB = _makeKey(0x0F)  # type: int
KEY_Q = _makeKey(0x10)  # type: int
KEY_W = _makeKey(0x11)  # type: int
KEY_E = _makeKey(0x12)  # type: int
KEY_R = _makeKey(0x13)  # type: int
KEY_T = _makeKey(0x14)  # type: int
KEY_Y = _makeKey(0x15)  # type: int
KEY_U = _makeKey(0x16)  # type: int
KEY_I = _makeKey(0x17)  # type: int
KEY_O = _makeKey(0x18)  # type: int
KEY_P = _makeKey(0x19)  # type: int
LEFT_SQ_BRACKET = _makeKey(0x1A)  # type: int
RIGHT_SQ_BRACKET = _makeKey(0x1B)  # type: int
ENTER = _makeKey(0x1C)  # type: int
LEFT_CONTROL = _makeKey(0x1D)  # type: int
KEY_A = _makeKey(0x1E)  # type: int
KEY_S = _makeKey(0x1F)  # type: int
KEY_D = _makeKey(0x20)  # type: int
KEY_F = _makeKey(0x21)  # type: int
KEY_G = _makeKey(0x22)  # type: int
KEY_H = _makeKey(0x23)  # type: int
KEY_J = _makeKey(0x24)  # type: int
KEY_K = _makeKey(0x25)  # type: int
KEY_L = _makeKey(0x26)  # type: int
SEMICOLON = _makeKey(0x27)  # type: int
APOSTROF = _makeKey(0x28)  # type: int
GRAVE_ACCENT = _makeKey(0x29)  # type: int
LEFT_SHIFT = _makeKey(0x2A)  # type: int
BACKSLASH = _makeKey(0x2B)  # type: int
KEY_Z = _makeKey(0x2C)  # type: int
KEY_X = _makeKey(0x2D)  # type: int
KEY_C = _makeKey(0x2E)  # type: int
KEY_V = _makeKey(0x2F)  # type: int
KEY_B = _makeKey(0x30)  # type: int
KEY_N = _makeKey(0x31)  # type: int
KEY_M = _makeKey(0x32)  # type: int
COMMA = _makeKey(0x33)  # type: int
PERIOD = _makeKey(0x34)  # type: int
SLASH = _makeKey(0x35)  # type: int
RIGHT_SHIFT = _makeKey(0x36)  # type: int
NUMPAD_ASTERISK = _makeKey(0x37)  # type: int
LEFT_ALT = _makeKey(0x38)  # type: int
SPACE_BAR = _makeKey(0x39)  # type: int
CAPS_LOCK = _makeKey(0x3A)  # type: int
F1 = _makeKey(0x3B)  # type: int
F2 = _makeKey(0x3C)  # type: int
F3 = _makeKey(0x3D)  # type: int
F4 = _makeKey(0x3E)  # type: int
F5 = _makeKey(0x3F)  # type: int
F6 = _makeKey(0x40)  # type: int
F7 = _makeKey(0x41)  # type: int
F8 = _makeKey(0x42)  # type: int
F9 = _makeKey(0x43)  # type: int
F10 = _makeKey(0x44)  # type: int
NUM_LOCK = _makeKey(0x45)  # type: int
SCROLL_LOCK = _makeKey(0x46)  # type: int
NUMPAD_7 = _makeKey(0x47)  # type: int
NUMPAD_8 = _makeKey(0x48)  # type: int
NUMPAD_9 = _makeKey(0x49)  # type: int
NUMPAD_MINUS = _makeKey(0x4A)  # type: int
NUMPAD_4 = _makeKey(0x4B)  # type: int
NUMPAD_5 = _makeKey(0x4C)  # type: int
NUMPAD_6 = _makeKey(0x4D)  # type: int
NUMPAD_PLUS = _makeKey(0x4E)  # type: int
NUMPAD_1 = _makeKey(0x4F)  # type: int
NUMPAD_2 = _makeKey(0x50)  # type: int
NUMPAD_3 = _makeKey(0x51)  # type: int
NUMPAD_0 = _makeKey(0x52)  # type: int
NUMPAD_DECIMAL = _makeKey(0x53)  # type: int
SYSREQ = _makeKey(0x54)  # type: int
F11 = _makeKey(0x57)  # type: int
F12 = _makeKey(0x58)  # type: int
NUMPAD_ENTER = _makeKey(0x1C, True)  # type: int
RIGHT_CONTROL = _makeKey(0x1D, True)  # type: int
NUMPAD_DIVIDE = _makeKey(0x35, True)  # type: int
PRINT_SCREEN = _makeKey(0x37, True)  # type: int
RIGHT_ALT = _makeKey(0x38, True)  # type: int
PAUSE = _makeKey(0x46, True, True)  # type: int
HOME = _makeKey(0x47, True)  # type: int
UP = _makeKey(0x48, True)  # type: int
PAGE_UP = _makeKey(0x49, True)  # type: int
LEFT = _makeKey(0x4B, True)  # type: int
RIGHT = _makeKey(0x4D, True)  # type: int
END = _makeKey(0x4F, True)  # type: int
DOWN = _makeKey(0x50, True)  # type: int
PAGE_DOWN = _makeKey(0x51, True)  # type: int
INSERT = _makeKey(0x52, True)  # type: int
DELETE = _makeKey(0x53, True)  # type: int
LEFT_WINDOW = _makeKey(0x5B, True)  # type: int
RIGHT_WINDOW = _makeKey(0x5C, True)  # type: int
MENU = _makeKey(0x5D, True)  # type: int
