# coding=utf-8
"""
Project main - a small RDP client.
    python -m PyFreeRdpApp [host] [user] [password] [port] [options]
Anything not given on the command line is asked for: in a connection dialog
when a Qt binding is available, otherwise on the terminal (the password
without echo). With Qt the session opens in a window; with --screenshot (or
without Qt) one frame is saved and the program exits.
"""
from sys import exit, platform, argv
from argparse import ArgumentParser
from os.path import dirname
from getpass import getpass
from time import sleep
from json import dumps
from sys import path
from os import walk

if dirname(__file__) not in path:
    path.append(dirname(__file__))

try:
    from ._pyfreerdp import DISPLAY_FORMATS, RDPApplication, initializeLogging
except:
    from _pyfreerdp import DISPLAY_FORMATS, RDPApplication, initializeLogging


def parseArgs(arv):
    """
    :param arv: any
    :return: Namespace
    """
    p = ArgumentParser(prog=u'python -m PyFreeRdpApp', description=u'Connect to an RDP server.')  # type: ArgumentParser
    p.add_argument(u'host', nargs=u'?', help=u'Server name or address.')
    p.add_argument(u'user', nargs=u'?', help=u'User name (without the domain).')
    p.add_argument(u'password', nargs=u'?', help=u'Password (asked for if omitted).')
    p.add_argument(u'port', nargs=u'?', type=int, help=u'Port (default 3389).')
    p.add_argument(u'-d', u'--domain', default=None, help=u'Domain.')
    p.add_argument(u'--size', default=u'1280x800', help=u'Desktop size, WIDTHxHEIGHT (default 1280x800).')
    p.add_argument(u'--bpp', type=int, default=32, choices=(16, 24, 32), help=u'Colour depth (default 32).')
    p.add_argument(u'--gfx', default=u'auto',
                   help=u'Graphics: auto (Graphics Pipeline, default), off, AVC444, AVC420, RFX, progressive.')
    p.add_argument(u'--share', action=u'append', default=[], metavar=u'DIR[=NAME]',
                   help=u'Redirect a local folder as a drive (repeatable).')
    p.add_argument(u'--no-sound', action=u'store_true', help=u'Do not play the remote sound locally.')
    p.add_argument(u'--microphone', action=u'store_true', help=u'Redirect the local microphone.')
    p.add_argument(u'--pcm-audio', action=u'store_true',
                   help=u'Uncompressed PCM audio only (more bandwidth, no audio decoder).')
    p.add_argument(u'--screenshot', metavar=u'FILE',
                   help=u'Console only: save the remote screen to FILE and exit (combines with --info).')
    p.add_argument(u'--info', action=u'store_true',
                   help=u'Console only: print the connection status and session information, then exit.')
    p.add_argument(u'--json', action=u'store_true', help=u'With --info: print the report as JSON.')
    p.add_argument(u'--format', default=u'pillow', choices=DISPLAY_FORMATS,
                   help=u'Display type used for --screenshot (default pillow).')
    p.add_argument(u'--no-gui', action=u'store_true', help=u'Never open a window or a dialog.')
    p.add_argument(u'--log', default=u'', metavar=u'DIR', help=u'Also write logs into DIR.')
    return p.parse_args(arv[1:])


def parseSize(text):
    """
    WIDTHxHEIGHT -> (width, height).
    :param text: (str | unicode) e.g. 1280x800.
    :return: tuple[int, int]
    :raises ValueError: Not WIDTHxHEIGHT.
    """
    width, height = (int(v) for v in u'{}'.format(text).lower().split(u'x'))  # type: int, int
    return width, height


def haveQt():
    """
    :return: bool
    """
    try:
        from ManyQt.QtWidgets import QApplication  # noqa: F401
        try:
            from .rdpwidget import RDPWidget
        except:
            from rdpwidget import RDPWidget
        return RDPWidget is not None
    except:
        return False


def needsInput(args):
    """
    Only an incomplete command line becomes interactive.
    :param args: any
    :return: bool
    """
    return not args.host or args.user is None or args.password is None


def askTerminal(args):
    """
    Fill the missing connection fields on the terminal.
    :param args: any
    """
    if not needsInput(args):
        args.port = args.port or 3389
        args.domain = args.domain or u''
        return args

    def ask(label, default=None):
        """
        :param label: str | unicode
        :param default: str | unicode | None
        :return: str | unicode
        """
        return input(u'%s%s: ' % (label, u' [%s]' % default if default else u'')).strip() or default

    while not args.host:
        args.host = ask(u'Server')
    if args.user is None:
        args.user = ask(u'User') or u''
    if args.password is None:
        args.password = getpass(u'Password: ')
    if args.port is None:
        port = ask(u'Port', u'3389')
        args.port = int(port) if str(port).isdigit() else 3389
    if args.domain is None:
        args.domain = ask(u'Domain (optional)') or u''
    return args


def askDialog(args):
    """
    Fill the missing connection fields in a Qt dialog. Returns None if canceled.
    """
    from ManyQt.QtWidgets import QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QWidget, \
        QHBoxLayout, QLineEdit, QListWidget, QPushButton, QSpinBox, QVBoxLayout
    dialog = QDialog()  # type: QDialog
    dialog.setWindowTitle(dialog.tr(u'PyFreeRdpApp - connect'))
    form = QFormLayout(dialog)  # type: QFormLayout
    host = QLineEdit(args.host or u'')  # type: QLineEdit
    user = QLineEdit(args.user or u'')  # type: QLineEdit
    user.setPlaceholderText(dialog.tr(u'user, or DOMAIN\\user'))
    password = QLineEdit(args.password or u'')  # type: QLineEdit
    password.setEchoMode(QLineEdit.Password)
    domain = QLineEdit(args.domain or u'')  # type: QLineEdit
    port = QSpinBox()  # type: QSpinBox
    port.setRange(1, 65535)
    port.setValue(args.port or 3389)
    width, height = parseSize(args.size)  # type: int, int
    size = QLineEdit(u'%dx%d' % (width, height))  # type: QLineEdit
    bpp = QComboBox()  # type: QComboBox
    bpp.addItems([u'32', u'24', u'16'])
    bpp.setCurrentText(str(args.bpp))
    graphics = QComboBox()  # type: QComboBox
    graphics.addItems([u'auto', u'AVC444', u'AVC420', u'progressive', u'RFX', u'off'])
    graphics.setCurrentText(args.gfx or u'auto')
    graphics.setToolTip(dialog.tr(u'auto = Graphics Pipeline with the best codec this build has (H.264 when '
                                  u'available); off = legacy bitmap updates'))
    sound = QCheckBox(dialog.tr(u'Play remote sound here'))  # type: QCheckBox
    sound.setChecked(not args.no_sound)
    microphone = QCheckBox(dialog.tr(u'Redirect my microphone'))  # type: QCheckBox
    microphone.setChecked(args.microphone)
    for label, field in ((u'Server', host), (u'User', user), (u'Password', password), (u'Domain', domain),
                         (u'Port', port), (u'Desktop size', size), (u'Colour depth', bpp),
                         (u'Graphics', graphics), (u'Sound', sound), (u'', microphone)):
        form.addRow(label, field)
    # Shared folders: redirected as drives ("<name> on <this pc>" remotely).
    shares = QListWidget()  # type: QListWidget
    shares.setToolTip(dialog.tr(u'Folders shown on the remote machine as drives'))
    shares.setMaximumHeight(90)
    for spec in args.share:
        shares.addItem(spec)
    add, remove = QPushButton(dialog.tr(u'Add...')), QPushButton(dialog.tr(u'Remove'))  # type: QPushButton, QPushButton

    def addShare():
        """
        :return:
        """
        pth = QFileDialog.getExistingDirectory(dialog, dialog.tr(u'Share a folder with the remote machine'))
        if pth:
            shares.addItem(pth)

    add.clicked.connect(addShare)
    remove.clicked.connect(lambda: [shares.takeItem(shares.row(i)) for i in shares.selectedItems()])
    buttonsBox = QWidget()  # type: QWidget
    column = QVBoxLayout(buttonsBox)  # type: QVBoxLayout
    column.setContentsMargins(0, 0, 0, 0)
    column.addWidget(add)
    column.addWidget(remove)
    column.addStretch(1)
    shareRow = QWidget()  # type: QWidget
    row = QHBoxLayout(shareRow)  # type: QHBoxLayout
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(shares, 1)
    row.addWidget(buttonsBox)
    form.addRow(dialog.tr(u'Shared folders'), shareRow)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # type: QDialogButtonBox
    buttons.button(QDialogButtonBox.Ok).setText(dialog.tr(u'Connect'))
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    okButton = buttons.button(QDialogButtonBox.Ok)  # type: QPushButton
    okButton.setEnabled(bool(host.text().strip()))
    host.textChanged.connect(lambda t: okButton.setEnabled(bool(t.strip())))
    # Focus the first empty field.
    for field in (host, user, password):
        if not field.text():
            field.setFocus()
            break
    try:
        from .rdpwidget import qtExec
    except:
        from rdpwidget import qtExec
    if not qtExec(dialog):
        return None
    args.host, args.user, args.password = host.text().strip(), user.text(), password.text()
    args.domain, args.port, args.size, args.bpp = domain.text(), port.value(), size.text(), int(bpp.currentText())
    args.gfx = graphics.currentText()
    args.no_sound = not sound.isChecked()
    args.microphone = microphone.isChecked()
    args.share = [shares.item(i).text() for i in range(shares.count())]
    return args


def buildApp(args):
    """
    :param args: any
    :return: RDPApplication
    """
    app = RDPApplication()  # type: RDPApplication
    app.setServer(args.host)
    app.setPort(args.port or 3389)
    app.setUsername(args.user or u'')
    app.setPassword(args.password or u'')
    if args.domain:
        app.setDomain(args.domain)
    try:
        width, height = parseSize(args.size)  # type: int, int
    except ValueError:
        exit(u'--size must look like 1280x800')
    app.setDisplaySize(width, height)
    app.setBitsPerPixel(args.bpp)
    app.setGraphics(args.gfx or u'auto')
    app.setSound(not args.no_sound, microphone=args.microphone, compressed=not args.pcm_audio)
    for spec in args.share:
        pth, _, name = spec.partition(u'=')  # type: str, str, str
        app.loadSharedDirectory(pth, name)
    return app


def saveScreenshot(app, pth, fmt):
    """
    Save the remote screen to path.
    :param app: (RDPApplication) A connected session.
    :param pth: (str | unicode) Target file.
    :param fmt: (str | unicode) The getDisplay() type used to write it: pillow, numpy, qimage, bytes or tuple.
    :return: (dict) {'path', 'width', 'height', 'format'}
    """
    frame = app.getDisplay(fmt)
    width, height = app.getDisplaySize()  # type: int, int
    if fmt == u'pillow':
        frame.save(pth)
        width, height = frame.size
    elif fmt == u'qimage':
        frame.save(pth)
        width, height = frame.width(), frame.height()  # type: int, int
    elif fmt == u'numpy':
        height, width = frame.shape[:2]  # type: int, int
        try:
            from cv2 import imwrite
            imwrite(pth, frame)
        except:
            from PIL.Image import fromarray
            fromarray(frame[..., 2::-1] if frame.shape[2] >= 3 else frame).save(pth)
    else:
        data = frame if fmt == u'bytes' else frame[3]
        with open(pth, u'wb') as fh:
            fh.write(data)
    print(u'screenshot: {} ({}x{}, {})'.format(pth, width, height, fmt))
    return {u'path': pth, u'width': width, u'height': height, u'format': fmt}


def isConsoleMode(args):
    """
    --screenshot and/or --info run in the console only: no Qt application, window or dialog.
    So does --no-gui, and any run without a Qt binding.
    :param args: argparse.Namespace
    :return: bool
    """
    return bool(args.screenshot or args.info or args.no_gui or not haveQt())


def runConsole(app, args):
    """
    The console-only run: take the screenshot and/or print the report.
    :param app: (RDPApplication) A connected session.
    :param args: argparse.Namespace
    :return: (int) The exit code.
    """
    sleep(2)  # Let the desktop paint and the channels (clipboard, graphics, sound) come up.
    shot = None
    if args.screenshot or not args.info:
        try:
            shot = saveScreenshot(app, args.screenshot or u'screenshot.png', args.format)
        except Exception as exc:
            print(u'screenshot failed: {}'.format(exc))
            return 3
    if args.info:
        info = app.getSessionInfo()
        if shot is not None:
            info[u'screenshot'] = shot
        print(dumps(info, indent=2, default=str) if args.json else formatSessionInfo(info))
    return 0


def describeSession(info):
    """
    The session in words - shared by the console report and the window's status bar.
    :param info: (dict) RDPApplication.getSessionInfo().
    :return: (dict) state, server, user, desktop, graphics, sound, clipboard, shared (all str).
    """
    if info.get(u'ready'):
        state = u'connected'  # type: str
    elif info.get(u'reconnecting'):
        state = u'reconnecting'  # type: str
    elif info.get(u'running'):
        state = u'connecting'  # type: str
    else:
        state = u'disconnected'  # type: str
    if not info.get(u'sound'):
        sound = u'off'  # type: str
    else:
        sound = u'on' + (u', compressed' if info.get(u'compressedAudio') else u'') + \
                (u', microphone' if info.get(u'microphone') else u'')
    if not info.get(u'clipboard'):
        clipboard = u'off'  # type: str
    elif info.get(u'fileClipboard'):
        clipboard = u'text + files'  # type: str
    else:
        clipboard = u'text (files: not offered by the server)'  # type: str
    domain = info.get(u'domain')  # type: str
    return {
        u'state': state,
        u'server': u'{}:{}'.format(info.get(u'server'), info.get(u'port')),
        u'user': u'{}{}'.format(domain + u'\\' if domain else u'', info.get(u'username')),
        u'desktop': u'{}x{}'.format(info.get(u'width'), info.get(u'height')),
        u'graphics': u'pipeline' if info.get(u'graphicsPipeline') else u'legacy updates',
        u'sound': sound,
        u'clipboard': clipboard,
        u'shared': u', '.join(name for name, _folder in info.get(u'sharedDirectories') or []) or u'none',
    }


def formatRows(rows, indent=u''):
    """
    An aligned two-column table; rows whose value is None are left out.
    :param rows: (tuple) (label, value) pairs.
    :param indent: (str | unicode) Put before every line.
    :return: str | unicode
    """
    rows = [(label, value) for label, value in rows if value is not None]
    width = max(len(label) for label, _value in rows) if rows else 0  # type: int
    return u'\n'.join(u'{}{}  {}'.format(indent, label.ljust(width), value) for label, value in rows)


def formatSessionInfo(info):
    """
    The session report shown by --info and the Session info dialog: the session, then what the
    server published about itself (remote computer, connection security, certificate).
    :param info: (dict) RDPApplication.getSessionInfo().
    :return: str | unicode
    """
    words = describeSession(info)  # type: dict
    folders = u', '.join(u'{} ({})'.format(name, folder) for name, folder in info.get(u'sharedDirectories') or [])
    report = [formatRows((
        (u'Status', words[u'state']),
        (u'Server', words[u'server']),
        (u'User', words[u'user']),
        (u'Desktop', u'{} at {} bpp'.format(words[u'desktop'], info.get(u'bitsPerPixel'))),
        (u'Graphics', u'{} ({})'.format(info.get(u'graphics'), words[u'graphics'])),
        (u'Sound', words[u'sound']),
        (u'Clipboard', words[u'clipboard']),
        (u'Shared folders', folders or u'none'),
        (u'Frames received', u'{}'.format(info.get(u'framesPublished'))),
        (u'FreeRDP', u'{}'.format(info.get(u'freerdpVersion'))),
        (u'Last error', u'{}'.format(info.get(u'lastError') or u'none')),
    ))]
    server = info.get(u'serverInfo')  # type: dict | None
    if not server:
        return u'\n'.join(report)
    computer = server.get(u'computer') or {}  # type: dict
    logon = server.get(u'logon') or {}  # type: dict
    cert = server.get(u'certificate') or {}  # type: dict

    def alsoDns(netbios, dns):
        """
        :param netbios: str | unicode | None
        :param dns: str | unicode | None
        :return: str | unicode | None
        """
        if not netbios and not dns:
            return None
        return u'{} (DNS: {})'.format(netbios, dns) if netbios and dns and dns != netbios else (netbios or dns)

    sections = (
        (u'Remote computer', (
            (u'Name', alsoDns(computer.get(u'netbiosComputerName'), computer.get(u'dnsComputerName'))),
            (u'Domain', alsoDns(computer.get(u'netbiosDomainName'), computer.get(u'dnsDomainName'))),
            (u'Forest', computer.get(u'dnsTreeName')),
            (u'OS', u'{} (version {})'.format(computer[u'osName'], computer[u'osVersion'])
            if computer.get(u'osVersion') else None), (u'Server time', computer.get(u'serverTime')),
        ), u'not published (the server does not use NLA)'),
        (u'Logon', (
            (u'User', u'{}\\{}'.format(logon[u'domain'], logon[u'username']) if logon.get(u'domain')
            else logon.get(u'username')), (u'Session ID', logon.get(u'sessionId'))), None),
        (u'Connection security', (
            (u'RDP version', server.get(u'rdpVersion') or info.get(u'rdpVersion')),
            (u'Security', server.get(u'securityProtocol') or info.get(u'securityProtocol')),
        ), None),
        (u'Certificate', (
            (u'Subject', cert.get(u'subject')),
            (u'Issuer', u'{}{}'.format(cert.get(u'issuer'), u' (self-signed)' if cert.get(u'selfSigned') else u'')
            if cert.get(u'issuer') else None), (u'Valid from', cert.get(u'notBefore')),
            (u'Valid until', u'{} ({})'.format(cert[u'notAfter'], cert.get(u'validity', u'?'))
            if cert.get(u'notAfter') else None),
            (u'Signature', cert.get(u'signature')),
            (u'Public key', cert.get(u'publicKey')),
            (u'Alt. names', u', '.join(cert[u'subjectAltNames']) if cert.get(u'subjectAltNames') else None),
            (u'SHA-256', cert.get(u'sha256')),
            (u'SHA-1', cert.get(u'sha1'))), u'none (no TLS)'),
    )
    for title, rows, empty in sections:
        body = formatRows(rows, u'  ')  # type: str
        if body or empty:
            report.append(u'\n{}\n{}'.format(title, body or u'  ' + empty))
    return u'\n'.join(report)


def MainWindow(app, args):
    """
    The session window (built lazily so the module imports without Qt).
    :param app: RDPApplication
    :param args: argparse.Namespace
    :return: QMainWindow
    """
    from ManyQt.QtWidgets import QLabel, QMainWindow, QToolBar, QMessageBox, QDialog, QPlainTextEdit, \
        QVBoxLayout, QDialogButtonBox
    from ManyQt.QtCore import QTimer, pyqtSlot
    from ManyQt.QtGui import QFont
    try:
        from .rdpwidget import DisconnectDialog, RDPWidget
    except:
        from rdpwidget import DisconnectDialog, RDPWidget

    class SessionInfoDialog(QDialog):
        """
        SessionInfoDialog class: the live status, connection and information report.
        """

        def __init__(self, *args, **kwargs):
            """
            :param view: (RDPWidget) The session to report on.
            :param args: any
            :param kwargs: any
            """
            view = kwargs.pop(u'view', None)  # type: RDPWidget | None
            super(SessionInfoDialog, self).__init__(*args, **kwargs)
            self.setWindowTitle(self.tr(u'Session info'))
            self.resize(560, 360)
            self.__m_view = view  # type: RDPWidget | None
            self.__m_text = QPlainTextEdit()  # type: QPlainTextEdit
            self.__m_text.setReadOnly(True)
            font = QFont(u'Monospace')  # type: QFont
            font.setStyleHint(QFont.TypeWriter)
            self.__m_text.setFont(font)
            buttons = QDialogButtonBox(QDialogButtonBox.Close)  # type: QDialogButtonBox
            buttons.rejected.connect(self.reject)
            layout = QVBoxLayout(self)  # type: QVBoxLayout
            layout.addWidget(self.__m_text)
            layout.addWidget(buttons)
            self.__m_timer = QTimer(self)  # type: QTimer
            self.__m_timer.timeout.connect(self.refresh)
            self.__m_timer.start(1000)
            self.refresh()

        @pyqtSlot()
        def refresh(self):
            """
            :return:
            """
            self.__m_text.setPlainText(formatSessionInfo(self.__m_view.getSessionInfo()))

    class SessionWindow(QMainWindow):
        """
        SessionWindow class: the remote desktop, a toolbar and a status bar.
        """

        def __init__(self, *args, **kwargs):
            """
            :param app: RDPApplication
            :param title: (str | unicode) Window title suffix.
            :param size: (tuple[int, int]) Initial desktop size.
            :param args: any
            :param kwargs: any
            """
            app = kwargs.pop(u'app', None)
            title = kwargs.pop(u'title', u'')  # type: str
            size = kwargs.pop(u'size', (1280, 800))  # type: tuple
            super(SessionWindow, self).__init__(*args, **kwargs)
            self.setWindowTitle(self.tr(u'PyFreeRdpApp - {}').format(title))
            self.resize(size[0], size[1] + 64)
            self.__m_app = app
            self.__m_view = RDPWidget(app, clipboardError=self.onClipboardError,
                                      filesDownloaded=self.onFilesDownloaded,
                                      screenshotSaved=self.onScreenshotSaved,
                                      clipboardSent=self.onClipboardSent,
                                      connectionLost=self.onConnectionLost)  # type: RDPWidget
            self.__m_asking = False  # type: bool
            self.__m_view.sessionRestarted.connect(self.onSessionRestarted)
            self.setCentralWidget(self.__m_view)
            self.__m_info = None  # type: SessionInfoDialog | None
            bar = QToolBar(self.tr(u'Session'))  # type: QToolBar
            bar.setMovable(False)
            self.addToolBar(bar)
            self.__m_share = bar.addAction(self.tr(u'Share folder...'))
            self.__m_share.setToolTip(self.tr(u'Redirect a local folder as a drive on the remote machine (reconnects)'))
            self.__m_share.triggered.connect(lambda: self.__m_view.shareFolder())
            self.__m_download = bar.addAction(self.tr(u'Download clipboard files...'))
            self.__m_download.setToolTip(self.tr(u'Save the files copied on the remote machine'))
            self.__m_download.triggered.connect(lambda: self.__m_view.downloadRemoteFiles())
            self.__m_send = bar.addAction(self.tr(u'Send clipboard'))
            self.__m_send.setToolTip(self.tr(u'Offer the local clipboard (text or copied files) to the remote machine'))
            self.__m_send.triggered.connect(self.__m_view.resendClipboard)
            bar.addSeparator()
            self.__m_shot = bar.addAction(self.tr(u'Screenshot...'))
            self.__m_shot.setToolTip(self.tr(u'Save the remote screen as an image'))
            self.__m_shot.triggered.connect(lambda: self.__m_view.takeScreenshot())
            info = bar.addAction(self.tr(u'Session info...'))
            info.setToolTip(self.tr(u'Status, connection and session information'))
            info.triggered.connect(self.showSessionInfo)
            self.__m_status = QLabel()  # type: QLabel
            self.statusBar().addPermanentWidget(self.__m_status, 1)
            crash = getattr(app, u'previousCrash', {})
            if crash:
                QTimer.singleShot(500, lambda: QMessageBox.warning(
                    self, self.tr(u'The previous session crashed'),
                    self.tr(u'Windows recorded where the previous run crashed:\n\nmodule: {}\noffset: {}\n'
                            u'exception: {}\npath: {}\n\nPlease send these lines (they are also in the log).').format(
                        crash.get(u'module'), crash.get(u'offset'), crash.get(u'exception'),
                        crash.get(u'module_path', u'?'))))
            self.__m_timer = QTimer(self)  # type: QTimer
            self.__m_timer.timeout.connect(self.refreshStatus)
            self.__m_timer.start(1000)
            self.refreshStatus()

        @pyqtSlot()
        def refreshStatus(self):
            """
            :return:
            """
            info = self.__m_view.getSessionInfo()  # type: dict
            if not info[u'ready']:
                self.__m_status.setText(self.tr(u'Reconnecting...') if info[u'reconnecting']
                                        else self.tr(u'Disconnected'))
                for action in (self.__m_share, self.__m_download, self.__m_send, self.__m_shot):
                    action.setEnabled(False)
                return
            words = describeSession(info)  # type: dict
            self.__m_status.setText(
                self.tr(u'Connected to {server}  ·  {desktop}  ·  Clipboard: {clipboard}  ·  '
                        u'Sound: {sound}  ·  Graphics: {graphics}  ·  Shared: {shared}').format(**words))
            for action in (self.__m_share, self.__m_send, self.__m_shot):
                action.setEnabled(True)
            self.__m_download.setEnabled(info[u'fileClipboard'] and self.__m_view.hasRemoteFiles())

        @pyqtSlot()
        def showSessionInfo(self):
            """
            :return:
            """
            if self.__m_info is None:
                self.__m_info = SessionInfoDialog(self, view=self.__m_view)  # type: SessionInfoDialog
            self.__m_info.refresh()
            self.__m_info.show()
            self.__m_info.raise_()

        @pyqtSlot(u'QString')
        def onFilesDownloaded(self, folder):
            """
            :param folder: str | unicode
            :return:
            """
            count = sum(len(files) for _root, _dirs, files in walk(folder))  # type: int
            self.statusBar().showMessage(self.tr(u'Files saved to {}').format(folder), 8000)
            QMessageBox.information(self, self.tr(u'Clipboard files'),
                                    self.tr(u'Saved to:\n{}\n\n{} file(s) in that folder.').format(folder, count))

        @pyqtSlot(u'QString')
        @pyqtSlot(str)
        def onClipboardError(self, message):
            """
            :param message: str | unicode
            :return:
            """
            self.statusBar().showMessage(self.tr(u'Clipboard: {}').format(message), 15000)
            QMessageBox.warning(self, self.tr(u'Clipboard'), message)

        @pyqtSlot(u'QString')
        @pyqtSlot(str)
        def onClipboardSent(self, what):
            """
            :param what: (str | unicode) What is now on the remote clipboard.
            :return:
            """
            self.statusBar().showMessage(self.tr(u'On the remote clipboard: {}').format(what), 10000)

        @pyqtSlot(dict)
        def onConnectionLost(self, reason):
            """
            The session ended (or a reconnection failed) without the user asking: say why, offer to
            reconnect. Cancel closes the window, like Windows' Remote Desktop client.
            :param reason: (dict) RDPApplication.getDisconnectReason().
            :return: None
            """
            if self.__m_asking:
                return
            self.__m_asking = True  # type: bool
            try:
                again = DisconnectDialog.askReconnect(self, reason, self.__m_view.server)  # type: bool
            finally:
                self.__m_asking = False  # type: bool
            if again:
                self.statusBar().showMessage(self.tr(u'Reconnecting...'))
                self.__m_view.connectToServer()
            else:
                self.close()

        @pyqtSlot(u'QString')
        @pyqtSlot(str)
        def onScreenshotSaved(self, filePath):
            """
            :param filePath: str | unicode
            :return:
            """
            self.statusBar().showMessage(self.tr(u'Screenshot saved to {}').format(filePath), 8000)

        @pyqtSlot(bool)
        def onSessionRestarted(self, ok):
            """
            :param ok: bool
            :return:
            """
            self.statusBar().showMessage(self.tr(u'Reconnected') if ok else self.tr(u'Reconnect failed'), 5000)

    return SessionWindow(app=app, title=args.host, size=parseSize(args.size))


def main(arv=None):
    """
    :param arv: (list[str] | None) Command line; sys.argv by default.
    :return: (int) The exit code: 0 ok, 1 canceled, 2 connection failed, 3 screenshot failed.
    """
    arv = list(argv if arv is None else arv)
    args = parseArgs(arv)
    initializeLogging(args.log)
    console = isConsoleMode(args)  # type: bool
    qApp = None
    if console:
        askTerminal(args)  # Asks only for what the command line lacks.
    else:
        from ManyQt.QtWidgets import QApplication
        try:
            from .rdpwidget import appIcon
        except:
            from rdpwidget import appIcon
        if platform == u'win32':  # The taskbar shows our icon, not Python's.
            try:
                from ctypes import windll
                if hasattr(windll.shell32, 'SetCurrentProcessExplicitAppUserModelID'):
                    windll.shell32.SetCurrentProcessExplicitAppUserModelID(u'PyFreeRdpApp')
            except:
                pass
        qApp = QApplication(arv)  # type: QApplication
        qApp.setWindowIcon(appIcon())  # Every window and dialog.
        if needsInput(args) and askDialog(args) is None:
            return 1
    rdpApp = buildApp(args)  # type: RDPApplication
    while True:
        try:
            rdpApp.start()
            break
        except ConnectionError as exc:
            print(u'could not connect: {}'.format(exc))
            if not console:
                try:
                    from .rdpwidget import DisconnectDialog
                except:
                    from rdpwidget import DisconnectDialog
                if DisconnectDialog.askReconnect(None, rdpApp.getDisconnectReason(), args.host):
                    continue  # Reconnect: try again.
            elif args.info:
                info = rdpApp.getSessionInfo()
                print(dumps(info, indent=2, default=str) if args.json else formatSessionInfo(info))
            return 2
    try:
        if console:
            return runConsole(rdpApp, args)
        window = MainWindow(rdpApp, args)  # type: MainWindow
        window.show()
        try:
            from .rdpwidget import qtExec
        except:
            from rdpwidget import qtExec
        return qtExec(qApp)
    finally:
        rdpApp.stop()


if __name__ == u'__main__':
    exit(main())
