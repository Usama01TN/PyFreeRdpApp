# coding=utf-8
"""
RDPWidget package: the widget, its Qt Designer plugins and a demo (python main.py).
"""
from os.path import dirname
from sys import path

if dirname(__file__) not in path:
    path.append(dirname(__file__))

try:
    from .rdpwidget import RDPWidget, frameToQimage, nativeToScancode, snapshotTree, localPaths, qtExec, appIcon, \
        GRAPHICS_OPTIONS, BACKGROUND, FOREGROUND, IMAGES, MIRRORED, ICON_SIZES
    from .disconnectdialog import DisconnectDialog
except:
    from rdpwidget import RDPWidget, frameToQimage, nativeToScancode, snapshotTree, localPaths, qtExec, appIcon, \
        GRAPHICS_OPTIONS, BACKGROUND, FOREGROUND, IMAGES, MIRRORED, ICON_SIZES
    from disconnectdialog import DisconnectDialog

__all__ = [u'RDPWidget', u'DisconnectDialog', u'frameToQimage', u'nativeToScancode', u'snapshotTree', u'appIcon',
           u'GRAPHICS_OPTIONS', u'BACKGROUND', u'FOREGROUND', u'IMAGES', u'MIRRORED', u'ICON_SIZES', u'qtExec',
           u'localPaths']  # type: list[str]
