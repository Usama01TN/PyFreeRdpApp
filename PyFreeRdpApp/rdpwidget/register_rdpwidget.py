# -*- coding: utf-8 -*-
"""
Qt Designer registration of RDPWidget for PySide6 (through ManyQt).
Install: point PYSIDE_DESIGNER_PLUGINS at this folder, make sure PyFreeRdpApp is importable
(PYTHONPATH), and start `pyside6-designer`. PySide6 runs every register*.py file it finds there.
"""
from os.path import dirname, join
from sys import path

if dirname(__file__) not in path:
    path.append(dirname(__file__))
if dirname(dirname(dirname(__file__))) not in path:
    path.append(dirname(dirname(dirname(__file__))))

try:
    from .rdpwidgetplugin import DOM_XML, GROUP, INCLUDE, TOOL_TIP
    from .rdpwidget import RDPWidget as _RDPWidget, IMAGES
except:
    from rdpwidgetplugin import DOM_XML, GROUP, INCLUDE, TOOL_TIP
    from rdpwidget import RDPWidget as _RDPWidget, IMAGES

try:
    from ManyQt.QtDesigner import QPyDesignerCustomWidgetCollection
except:  # Not PySide6: the PyQt plugin (rdpwidgetplugin.py) is used instead.
    QPyDesignerCustomWidgetCollection = None


class RDPWidget(_RDPWidget):
    """
    RDPWidget as Designer creates it: in design mode, so it never connects - as with the PyQt plugin. Its
    name is the one .ui files use; the generated code imports the real RDPWidget (INCLUDE).
    """

    def __init__(self, parent=None):
        """
        :param parent: QWidget | None
        """
        super(RDPWidget, self).__init__(parent, designMode=True)


def registerRDPWidget():
    """
    Register RDPWidget with PySide6's Qt Designer.
    :return: (bool) True when registered.
    """
    if QPyDesignerCustomWidgetCollection is None:
        return False
    QPyDesignerCustomWidgetCollection.registerCustomWidget(
        RDPWidget, module=INCLUDE, tool_tip=TOOL_TIP, xml=DOM_XML, group=GROUP, container=False,
        icon=join(IMAGES, u'pyfreerdpapp.ico'))  # PySide takes an icon file: the .ico has every size up to 256.
    return True


registerRDPWidget()
