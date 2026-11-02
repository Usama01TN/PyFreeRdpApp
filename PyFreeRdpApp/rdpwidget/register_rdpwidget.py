# -*- coding: utf-8 -*-
"""
Qt Designer registration of RDPWidget for PySide6 (through ManyQt).
Install: point PYSIDE_DESIGNER_PLUGINS at this folder, make sure PyFreeRdpApp is importable
(PYTHONPATH), and start `pyside6-designer`. PySide6 runs every register*.py file it finds there.
"""
from os.path import dirname
from sys import path

if dirname(__file__) not in path:
    path.append(dirname(__file__))
if dirname(dirname(dirname(__file__))) not in path:
    path.append(dirname(dirname(dirname(__file__))))

try:
    from .rdpwidgetplugin import DOM_XML
    from .rdpwidget import RDPWidget
except:
    from rdpwidgetplugin import DOM_XML
    from rdpwidget import RDPWidget

try:
    from ManyQt.QtDesigner import QPyDesignerCustomWidgetCollection
except:  # Not PySide6: the PyQt plugin (rdpwidgetplugin.py) is used instead.
    QPyDesignerCustomWidgetCollection = None


def registerRDPWidget():
    """
    Register RDPWidget with PySide6's Qt Designer.
    :return: (bool) True when registered.
    """
    if QPyDesignerCustomWidgetCollection is None:
        return False
    QPyDesignerCustomWidgetCollection.registerCustomWidget(
        RDPWidget, module=u'PyFreeRdpApp.rdpwidget', tool_tip=u'Remote desktop (FreeRDP)', xml=DOM_XML,
        group=u'PyFreeRdpApp', container=False)
    return True


registerRDPWidget()
