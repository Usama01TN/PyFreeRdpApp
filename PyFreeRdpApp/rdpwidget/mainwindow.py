# coding=utf-8
"""
RDPWidget demo window: a connection form beside the remote desktop.
"""
from ManyQt.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, \
    QComboBox, QCheckBox, QPushButton, QMessageBox
from ManyQt.QtCore import pyqtSlot
from os.path import dirname
from sys import path

if dirname(__file__) not in path:
    path.append(dirname(__file__))

try:
    from .rdpwidget import RDPWidget, GRAPHICS_OPTIONS
    from .disconnectdialog import DisconnectDialog
except:
    from rdpwidget import RDPWidget, GRAPHICS_OPTIONS
    from disconnectdialog import DisconnectDialog


class MainWindow(QMainWindow):
    """
    MainWindow class.
    """

    def __init__(self, *args, **kwargs):
        """
        :param args: any
        :param kwargs: any
        """
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle(self.tr(u'RDPWidget demo'))
        self.resize(1280, 760)
        self.__m_view = RDPWidget(displayWidth=1024, displayHeight=700, graphics=u'auto', sound=True,
                                  connected=self.onConnected, disconnected=self.onDisconnected,
                                  connectionLost=self.onConnectionLost, clipboardSent=self.onClipboardSent,
                                  screenshotSaved=self.onScreenshotSaved)  # type: RDPWidget
        panel = QWidget()  # type: QWidget
        panel.setFixedWidth(300)
        form = QFormLayout()  # type: QFormLayout
        self.__m_server = QLineEdit()  # type: QLineEdit
        self.__m_server.setPlaceholderText(self.tr(u'host or IP'))
        self.__m_server.textChanged.connect(self.__m_view.setServer)
        self.__m_port = QSpinBox()  # type: QSpinBox
        self.__m_port.setRange(1, 65535)
        self.__m_port.setValue(self.__m_view.port)
        self.__m_port.valueChanged.connect(self.__m_view.setPort)
        self.__m_user = QLineEdit()  # type: QLineEdit
        self.__m_user.textChanged.connect(self.__m_view.setUsername)
        self.__m_password = QLineEdit()  # type: QLineEdit
        self.__m_password.setEchoMode(QLineEdit.Password)
        self.__m_password.textChanged.connect(self.__m_view.setPassword)
        graphics = QComboBox()  # type: QComboBox
        graphics.addItems(list(GRAPHICS_OPTIONS))
        graphics.currentTextChanged.connect(self.__m_view.setGraphics)
        sound = QCheckBox(self.tr(u'Play remote sound'))  # type: QCheckBox
        sound.setChecked(self.__m_view.sound)
        sound.toggled.connect(self.__m_view.setSound)
        for label, field in ((self.tr(u'Server'), self.__m_server), (self.tr(u'Port'), self.__m_port),
                             (self.tr(u'User'), self.__m_user), (self.tr(u'Password'), self.__m_password),
                             (self.tr(u'Graphics'), graphics), (u'', sound)):
            form.addRow(label, field)
        buttons = QVBoxLayout()  # type: QVBoxLayout
        for text, slot in ((self.tr(u'Connect'), self.__m_view.connectToServer),
                           (self.tr(u'Disconnect'), self.__m_view.disconnectFromServer),
                           (self.tr(u'Screenshot...'), lambda: self.__m_view.takeScreenshot()),
                           (self.tr(u'Session info'), self.showSessionInfo)):
            button = QPushButton(text)  # type: QPushButton
            button.clicked.connect(slot)
            buttons.addWidget(button)
        column = QVBoxLayout(panel)  # type: QVBoxLayout
        column.addLayout(form)
        column.addLayout(buttons)
        column.addStretch(1)
        wdg = QWidget()  # type: QWidget
        layout = QHBoxLayout(wdg)  # type: QHBoxLayout
        layout.addWidget(panel)
        layout.addWidget(self.__m_view, 1)
        self.setCentralWidget(wdg)

    @pyqtSlot()
    def onConnected(self):
        """
        :return:
        """
        self.statusBar().showMessage(self.tr(u'Connected to {}').format(self.__m_view.server), 5000)

    @pyqtSlot()
    def onDisconnected(self):
        """
        :return:
        """
        self.statusBar().showMessage(self.tr(u'Disconnected'), 5000)

    @pyqtSlot(dict)
    def onConnectionLost(self, reason):
        """
        :param reason: (dict) Why the session ended or the connection failed.
        :return:
        """
        if DisconnectDialog.askReconnect(self, reason, self.__m_view.server):
            self.__m_view.connectToServer()

    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    def onClipboardSent(self, what):
        """
        :param what: str | unicode
        :return:
        """
        self.statusBar().showMessage(self.tr(u'On the remote clipboard: {}').format(what), 8000)

    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    def onScreenshotSaved(self, filePath):
        """
        :param filePath: str | unicode
        :return:
        """
        self.statusBar().showMessage(self.tr(u'Screenshot saved to {}').format(filePath), 5000)

    @pyqtSlot()
    def showSessionInfo(self):
        """
        :return:
        """
        info = self.__m_view.getSessionInfo()  # type: dict
        QMessageBox.information(
            self, self.tr(u'Session info'), u'\n'.join(u'{}: {}'.format(key, info[key]) for key in sorted(info)))
