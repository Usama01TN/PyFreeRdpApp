# -*- coding: utf-8 -*-
"""
DisconnectDialog: why a remote session ended (or a connection failed), with Reconnect and Cancel.
The reason is RDPApplication.getDisconnectReason() / RDPWidget.connectionLost: FreeRDP's own report
(the server's Error Info and FreeRDP's last error).
"""
from ManyQt.QtCore import pyqtSlot, pyqtProperty
from ManyQt.QtWidgets import QMessageBox
from os.path import dirname
from sys import path

if dirname(__file__) not in path:
    path.append(dirname(__file__))

try:
    from .rdpwidget import qtExec
except:
    from rdpwidget import qtExec


class DisconnectDialog(QMessageBox):
    """
    DisconnectDialog class: the cause of a disconnection, Reconnect (default) and Cancel.
    """

    def __init__(self, *args, **kwargs):
        """
        :param reason: (dict | None) RDPApplication.getDisconnectReason().
        :param server: (str | unicode) The server, shown in the text.
        :param args: any
        :param kwargs: any
        """
        reason = kwargs.pop(u'reason', None)  # type: dict | None
        server = kwargs.pop(u'server', u'')  # type: str
        super(DisconnectDialog, self).__init__(*args, **kwargs)
        self.__m_reason = dict(reason or {})  # type: dict
        self.__m_server = u'{}'.format(server)  # type: str
        self.setIcon(QMessageBox.Warning)
        self.__m_reconnect = self.addButton(self.tr(u'Reconnect'), QMessageBox.AcceptRole)
        self.__m_cancel = self.addButton(QMessageBox.Cancel)
        self.setDefaultButton(self.__m_reconnect)
        self.setEscapeButton(self.__m_cancel)
        self._refresh()

    # ---------- Helpers ----------

    def _refresh(self):
        """
        :return:
        """
        reason = self.__m_reason  # type: dict
        connecting = reason.get(u'phase') == u'connect'  # type: bool
        self.setWindowTitle(self.tr(u'Connection failed') if connecting else self.tr(u'Disconnected'))
        target = u' {}'.format(self.__m_server) if self.__m_server else u''  # type: str
        self.setText(self.tr(u'Could not connect to the remote computer{}.').format(target) if connecting
                     else self.tr(u'The remote session{} has ended.').format(target))
        self.setInformativeText(reason.get(u'message') or self.tr(u'The connection was closed.'))
        details = []  # type: list[str]
        if reason.get(u'serverCode'):
            details.append(self.tr(u'Server reason: {} (0x{:08X})\n  {}').format(
                reason.get(u'serverName'), reason[u'serverCode'], reason.get(u'serverMessage')))
        if reason.get(u'errorCode'):
            details.append(self.tr(u'FreeRDP error: {} (0x{:08X})\n  {}').format(
                reason.get(u'errorName'), reason[u'errorCode'], reason.get(u'errorMessage')))
        self.setDetailedText(u'\n\n'.join(details))

    # ---------- Public API ----------

    def getReason(self):
        """
        :return: dict
        """
        return dict(self.__m_reason)

    def setReason(self, reason):
        """
        :param reason: (dict | None) RDPApplication.getDisconnectReason().
        :return:
        """
        self.__m_reason = dict(reason or {})
        self._refresh()

    def getServer(self):
        """
        :return: str | unicode
        """
        return self.__m_server

    @pyqtSlot(u'QString')
    @pyqtSlot(str)
    def setServer(self, server):
        """
        :param server: str | unicode | QString
        :return:
        """
        self.__m_server = u'{}'.format(server)  # type: str
        self._refresh()

    def isReconnectChosen(self):
        """
        :return: (bool) True when the dialog was closed with Reconnect.
        """
        return self.clickedButton() is self.__m_reconnect

    @staticmethod
    def askReconnect(parent, reason, server=u''):
        """
        Show the dialog and wait for the answer.
        :param parent: (QWidget | None) The dialog's parent.
        :param reason: (dict | None) RDPApplication.getDisconnectReason().
        :param server: (str | unicode | QString) The server, shown in the text.
        :return: (bool) True: reconnect; False: cancel.
        """
        dialog = DisconnectDialog(parent, reason=reason, server=server)  # type: DisconnectDialog
        qtExec(dialog)
        return dialog.isReconnectChosen()

    # ---------- Properties ----------

    reason = pyqtProperty(dict, fget=getReason, fset=setReason)  # type: pyqtProperty
    server = pyqtProperty(u'QString', fget=getServer, fset=setServer)  # type: pyqtProperty
