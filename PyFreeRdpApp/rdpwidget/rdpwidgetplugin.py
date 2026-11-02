# -*- coding: utf-8 -*-
"""
Qt Designer plugin for RDPWidget (PyQt4 / PyQt5 / PyQt6 through ManyQt).
Install: point PYQTDESIGNERPATH at this folder (the folder that contains this file), make sure
PyFreeRdpApp is importable (PYTHONPATH), and start Qt Designer (e.g. pyqt5-tools designer).
RDPWidget then appears in the "PyFreeRdpApp" group of the widget box; all its connection options
are editable in the property editor. pyuic generates `from PyFreeRdpApp.rdpwidget import RDPWidget`.
"""
from ManyQt.QtDesigner import QPyDesignerCustomWidgetPlugin
from os.path import dirname
from sys import path

if dirname(__file__) not in path:
    path.append(dirname(__file__))
if dirname(dirname(dirname(__file__))) not in path:
    path.append(dirname(dirname(dirname(__file__))))

try:
    from .rdpwidget import RDPWidget, appIcon
except:
    from rdpwidget import RDPWidget, appIcon

DOM_XML = u'''<ui language="c++" displayname="RDPWidget">
 <widget class="RDPWidget" name="rdpWidget">
  <property name="geometry">
   <rect><x>0</x><y>0</y><width>640</width><height>400</height></rect>
  </property>
  <property name="toolTip"><string>Remote desktop (FreeRDP)</string></property>
  <property name="server"><string></string></property>
  <property name="port"><number>3389</number></property>
  <property name="graphics"><string>auto</string></property>
 </widget>
</ui>
'''  # type: str


class RDPWidgetPlugin(QPyDesignerCustomWidgetPlugin):
    """
    RDPWidgetPlugin class: exposes RDPWidget to Qt Designer.
    """

    def __init__(self, *args, **kwargs):
        """
        :param args: any
        :param kwargs: any
        """
        super(RDPWidgetPlugin, self).__init__(*args, **kwargs)
        self.__m_initialized = False  # type: bool

    def initialize(self, core):
        """
        :param core: QDesignerFormEditorInterface
        :return:
        """
        if not self.__m_initialized:
            self.__m_initialized = True  # type: bool

    def isInitialized(self):
        """
        :return: bool
        """
        return self.__m_initialized

    def createWidget(self, parent):
        """
        Designer instances never connect: they only show and edit the configuration.
        :param parent: QWidget
        :return: RDPWidget
        """
        return RDPWidget(parent, designMode=True)

    def name(self):
        """
        :return: str | unicode
        """
        return u'RDPWidget'

    def group(self):
        """
        :return: str | unicode
        """
        return u'PyFreeRdpApp'

    def icon(self):
        """
        :return: QIcon
        """
        return appIcon()  # The PyFreeRdpApp icon (images/), every size.

    def toolTip(self):
        """
        :return: str | unicode
        """
        return u'Remote desktop (FreeRDP)'

    def whatsThis(self):
        """
        :return: str | unicode
        """
        return (u'Shows an RDP session and forwards mouse, keyboard, clipboard (text and files), '
                u'shared folders and sound. Configure the connection in the property editor; '
                u'call connectToServer() at run time, or set autoConnect.')

    def isContainer(self):
        """
        :return: bool
        """
        return False

    def domXml(self):
        """
        :return: str | unicode
        """
        return DOM_XML

    def includeFile(self):
        """
        :return: (str | unicode) The Python module pyuic imports RDPWidget from.
        """
        return u'PyFreeRdpApp.rdpwidget'
