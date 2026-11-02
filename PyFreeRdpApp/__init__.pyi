# coding=utf-8
"""
PyfreeRdpApp Module.
"""
from typing import List, Optional, Union
import keyboard

__author__: str
__version__: str
__email__: str
__status__: str
__credits__: List[str]
__copyright__: str
__maintainer__: str


def initializeLogging(log_folder: str, log_level: str = u'INFO'):
    """
    Initializes logging into this folder.
    """
    ...


class RDPApplication(object):
    """
    RDPApplication class.
    """

    def start(self):
        """
        Starts the rdp connection to server.
        :return:
        """
        ...

    def stop(self):
        """
        Stops the rdp connection to the server.
        :return:
        """
        ...

    def setPaused(self, paused: bool):
        """
        Pause/Resume RDP displays.
        :param paused: bool
        :return:
        """
        ...

    def setServer(self, hostname: str):
        """
        Sets the address of server which to connect to.
        :param hostname: (str | unicode) The server address, can be either hostname or ip.
        :return:
        """
        ...

    def setPort(self, port: int):
        """
        Sets the address of server which to connect to.
        :param port: (int) The port of the rdp service.
        :return:
        """
        ...

    def setUsername(self, username: str):
        """
        Sets the username of the account on the server which you want to connect.
        :param username: (str | unicode) The username, without a domain name.
            Example if the computer account name is FOO/BAR then use
            setUsername("BAR")
        :return:
        """
        ...

    def setPassword(self, password: str):
        """
        Sets the password of the account on the server which you want to connect.
        :param password: (str | unicode) The password.
        :return:
        """
        ...

    def setDomain(self, domain: str):
        """
        Sets the domain of the account on the server which you want to connect.
        :param domain: (str | unicode) Domain name of the username.
            Example if the computer account name is FOO/BAR then use
            setDomain("FOO")
        :return:
        """
        ...

    def setDisplaySize(self, width: int, height: int):
        """
        Sets the monitor size which will be used in screen transfer.
        :param width: (int) Width of the resulting display. Default=1920
        :param height: (int) Height of the resulting display. Default=1080
        :return:
        """
        ...

    def setAutoReconnect(self, enable: bool):
        """
        Sets if auto reconnect should be enabled when connection is lost.
        :param enable: (bool) If set to true AutoReconnect is enabled.
        :return:
        """
        ...

    def keyDown(self, scancode: int):
        """
        Presses a key on the remote keyboard.
        :param scancode: (int) Scancode of the key which is pressed.
        :return:
        """
        ...

    def keyUp(self, scancode: int):
        """
        Releases a key on the remote keyboard.
        :param scancode: (int) Scancode of the key which is released.
        :return:
        """
        ...

    def setBitsPerPixel(self, bpp: int):
        """
        Sets how many bits should be used for transferring the screen.
        Also sets the format of color to be:
           * BGR565 for 16 bits.
           * BGR888 for 24 bits.
           * ABGR8888 for 32 bits.
        :param bpp: (int) Number of bits. Options are 32, 24 (default) and 16.
        :return:
        """
        ...

    def hotkey(self, *scancodes: int, delay: int = 20):
        """
        Performs a hotkey with keys defined in scancodes.
        Keys are pressed down in order and released in reverse order.
        :param scancodes: (list[int] | int) Keys which should be pressed.
        :param delay: (int) Delay between two key events in milliseconds.
        :raises TypeError: No key given, unknown keyword argument or a noninteger delay.
        :raises ValueError: Negative or too large (above 2**32 - 1) delay, invalid key.
        :raises RuntimeError: The session is not connected.
        :return:
        """
        ...

    def typeText(self, text: str, typingDelay: int = 20):
        """
        Types supplied text via remote keyboard.
        :param text: (str | unicode) The text to be typed, can include Unicode characters.
        :param typingDelay: (int) Delay between typing two characters in milliseconds.
        :return:
        """
        ...

    def mouseMove(self, x: int, y: int):
        """
        Moves mouse on the remote machine to coordinates.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        ...

    def leftMouseUp(self, x: int, y: int):
        """
        Releases the left mouse button at specified coordinates on the remote machine.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        ...

    def leftMouseDown(self, x: int, y: int):
        """
        Presses the left mouse button at specified coordinates on the remote machine.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        ...

    def rightMouseUp(self, x: int, y: int):
        """
        Releases the right mouse button at specified coordinates on the remote machine.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        ...

    def rightMouseDown(self, x: int, y: int):
        """
        Presses the right mouse button at specified coordinates on the remote machine.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        ...

    def middleMouseUp(self, x: int, y: int):
        """
        Releases the middle mouse button at specified coordinates on the remote machine.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        ...

    def middleMouseDown(self, x: int, y: int):
        """
        Presses the middle mouse button at specified coordinates on the remote machine.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :return:
        """
        ...

    def mouseScroll(self, x: int, y: int, down: bool = True):
        """
        Scrolls the mouse on the remote machine on specified coordinates.
        :param x: (int) X coordinate of the location.
        :param y: (int) Y coordinate of the location.
        :param down: (bool) If True scrolls down otherwise scrolls up.
        :return:
        """
        ...

    def getDisplay(self, displayFormat=None):
        """
        Returns the current screen of the remote pc.
        Size of the display can be changed by `setDisplaySize`
        :param displayFormat: (str | unicode | None) Type of the returned screen, one of
            `numpy`  - numpy.ndarray (height, width, bpp/8) of BGR(A) pixels, ready for OpenCV,
            `pillow` - PIL.Image.Image in RGB or RGBA,
            `qimage` - QImage (needs ManyQt and a Qt binding),
            `bytes`  - raw BGR(A) pixels, tightly packed row after row,
            `tuple`  - (width, height, channels, bytes).
            None uses the format set by `setDisplayFormat` (`numpy` by default).
        :raises ValueError: Unknown display format.
        :raises ImportError: The library the format needs is not installed.
        :raises ConnectionError: The session is not connected.
        :return: The RDP screen.
        """
        ...

    def setDisplayFormat(self, displayFormat):
        """
        Sets the default type returned by `getDisplay`.
        :param displayFormat: (str | unicode) One of `numpy`, `pillow`, `qimage`, `bytes`, `tuple`.
        :raises ValueError: Unknown display format.
        :return:
        """
        ...

    def setClipboardListener(self, listener):
        """
        Registers a function called whenever the remote clipboard changes.
        It is called from the RDP thread with a dict {"text": bool, "files": bool}
        telling what the remote clipboard now offers; use `loadClipboard` from your
        own thread to fetch the content.
        :param listener: (callable | None) The function, or None to remove it.
        :return:
        """
        ...

    def getServer(self):
        """
        Returns the server set with `setServer`.
        :return: (str | unicode) The hostname or IP address.
        """
        ...

    def getPort(self):
        """
        Returns the port set with `setPort`.
        :return: (int) The port number.
        """
        ...

    def getUsername(self):
        """
        Returns the username set with `setUsername`.
        :return: (str | unicode) The username.
        """
        ...

    def getPassword(self):
        """
        Returns the password set with `setPassword`.
        :return: (str | unicode) The password.
        """
        ...

    def getDomain(self):
        """
        Returns the domain set with `setDomain`.
        :return: (str | unicode) The domain.
        """
        ...

    def getDisplaySize(self):
        """
        Returns the display size set with `setDisplaySize`; after a server-side resize, the current one.
        :return: (tuple[int, int]) (width, height).
        """
        ...

    def getDisplayWidth(self):
        """
        Returns the display width.
        :return: (int) Width in pixels.
        """
        ...

    def getDisplayHeight(self):
        """
        Returns the display height.
        :return: (int) Height in pixels.
        """
        ...

    def isAutoReconnect(self):
        """
        Returns whether automatic reconnection is enabled.
        :return: bool
        """
        ...

    def getBitsPerPixel(self):
        """
        Returns the color depth set with `setBitsPerPixel`.
        :return: (int) 32, 24 or 16.
        """
        ...

    def getGraphics(self):
        """
        Returns the graphics option set with `setGraphics`.
        :return: (str | unicode) e.g. `auto`, `AVC444`, `off`.
        """
        ...

    def getFreerdpCliArgs(self):
        """
        Returns the extra FreeRDP command line arguments.
        :return: (list[str]) The arguments.
        """
        ...

    def getDisplayFormat(self):
        """
        Returns the default type returned by `getDisplay`.
        :return: (str | unicode) `numpy`, `pillow`, `qimage`, `bytes` or `tuple`.
        """
        ...

    def isSound(self):
        """
        Returns whether the remote sound is played locally.
        :return: bool
        """
        ...

    def isMicrophone(self):
        """
        Returns whether the local microphone is redirected.
        :return: bool
        """
        ...

    def isCompressedAudio(self):
        """
        Returns whether compressed audio formats are allowed.
        :return: bool
        """
        ...

    def isGraphicsPipelineActive(self):
        """
        Returns whether the Graphics Pipeline (GFX) channel is active in the current session.
        :return: bool
        """
        ...

    def getLastError(self):
        """
        Returns the last connection error message, if any.
        :return: (str | unicode | None) The message.
        """
        ...

    def getSessionInfo(self):
        """
        Returns the status of the connection and information about the session: configuration,
        connection state, graphics/sound/clipboard/sharing status, FreeRDP version and frame counters,
        the negotiated RDP version and security protocol, and what FreeRDP received from the server
        while connecting (see `getServerInfo`; None before the first connection).
        :return: (dict) Keys: server, port, username, domain, width, height, bitsPerPixel, graphics,
            graphicsPipeline, sound, microphone, compressedAudio, clipboard, fileClipboard, sharedDirectories, running,
            ready, reconnecting, lastError, framesPublished, freerdpVersion, rdpVersion, securityProtocol, serverInfo.
        """
        ...

    def getServerInfo(self):
        """
        Returns what FreeRDP received from the server while connecting - no extra connection is made:
        the TLS certificate FreeRDP verified, decoded by FreeRDP's certificate API (subject, issuer,
        validity, signature algorithm, key type, SHA-256/SHA-1 fingerprints, alternative names, PEM), the NTLM challenge of its NLA exchange (Windows
        version, build and name, NetBIOS/DNS computer, domain and forest names, server clock), the
        Save Session Info data (logged-on user, domain, session id), and the negotiated RDP version
        and security protocol.
        :return: (dict | None) Keys: certificate {subject, issuer, commonName, selfSigned, notBefore,
            notAfter, daysLeft, expired, validity, signature, publicKey, sha256, sha1, email, upn,
            subjectAltNames, pem}, computer {osVersion, osName, osMajor, osMinor, osBuild, netbiosComputerName,
            netbiosDomainName, dnsComputerName, dnsDomainName, dnsTreeName, serverTime},
            logon {username, domain, sessionId, logonId}, rdpVersion, securityProtocol.
            None before the first connection.
        """
        ...

    def getDisconnectReason(self):
        """
        Returns why the last session ended or the last connection failed, as FreeRDP reports it:
        the server's reason (its Error Info, e.g. logged off, idle timeout, disconnected by an
        administrator) and FreeRDP's own last error.
        :return: (dict | None) Keys: phase (`connect` or `session`), byUser (bool: `stop` was called),
            message (str: the main cause, in words), serverCode (int), serverName (str), serverMessage (str),
            serverCategory (str), errorCode (int), errorName (str), errorMessage (str), errorCategory (str).
            None while connected or before the first connection.
        """
        ...

    def setDisconnectListener(self, listener):
        """
        Sets a function called when a session ends, or a connection fails, without `stop` being
        called. It runs on the RDP thread and receives the dict returned by `getDisconnectReason`.
        :param listener: (callable | None) listener(reason) or None to remove it.
        :return:
        """
        ...

    def setSound(self, enable, microphone=False, compressed=True):
        """
        Enables the remote sound: audio played on the remote machine is played
        locally (on by default). FreeRDP picks the platform's audio backend
        (WinMM on Windows, Core Audio on macOS, ALSA - which also reaches
        PulseAudio/PipeWire - on Linux, OpenSL ES on Android). Set it before `start`.
        :param enable: (bool) True to play the remote sound locally, False for silence.
        :param microphone: (bool) True to also redirect the local microphone.
        :param compressed: (bool) True (default) to allow compressed audio formats (AAC, ...),
            False for uncompressed PCM only (more bandwidth, no audio decoder involved).
        :return:
        """
        ...

    def setPointerListener(self, listener):
        """
        Registers a function called whenever the remote mouse pointer changes.
        It is called from the RDP thread as listener(state, data) with state one of
            `set`      - data is (width, height, hotX, hotY, pixels): pixels are
                         width*height*4 bytes of BGRA,
            `hidden`   - the pointer is hidden, data is None,
            `default`  - the system default pointer, data is None,
            `position` - the server moved the pointer, data is (x, y).
        :param listener: (callable | None) The function, or None to remove it.
        :return:
        """
        ...

    def getSharedDirectories(self):
        """
        Returns the folders shared with `loadSharedDirectory`.
        :return: (list[tuple]) (name, path) pairs.
        """
        ...

    def saveClipboard(self, preferredType: str, data: str, includeParent: bool = False):
        """
        Sets the remote clipboard to this preferred type.
        :param preferredType: (str | unicode) Value of either `text` or `file`.
        :param data: (str | unicode) String or path to either a dir or a file. Path is used when set to
                     file mode and string when texted.
        :param includeParent: (bool) Set to True if the parent of path be included while saving the clipboard.
        :return:
        """
        ...

    def loadClipboard(self, preferredType: str, dirPath: Optional[str], filePattern: Optional[str]):
        """
        Loads data from remote clipboard based by the preferred type.
        :param preferredType: (str | unicode) Value of either `text` or `file`.
        :param dirPath: (str | unicode) Path to a directory where the files from remote clipboard
                         will be downloaded. Only used with file mode.
        :param filePattern: (str | unicode) Download only files following this pattern. Only used with file mode.
        :return: Text from the server or Path which the files were downloaded to.
        """
        ...

    def loadSharedDirectory(self, dirPath: str, dirName: str = u''):
        """
        Loads folder as a shared directory.
        The folder appears on the remote machine as a redirected drive
        (in Explorer under "This PC" as "<dirName> on <client>"). A path to a
        file shares the folder that contains it. Several folders can be shared;
        each must be added before `start`, or the session has to be restarted
        for it to appear.
        :param dirPath: (str | unicode) Path to the directory.
        :param dirName: (str | unicode) Name of the directory, if left empty the system directory name will be used.
        :raises ValueError: The path does not exist.
        :return:
        """
        ...

    def isRunning(self) -> bool:
        """
        Used to check if the machine is running.
        :return: (bool) True if it's running. False otherwise.
        """
        ...

    @property
    def isReady(self) -> bool:
        """
        Used to check if the machine is ready for incoming instructions.
        :return: (bool) True if it readies. False otherwise.
        """
        ...

    @property
    def isReconnecting(self) -> bool:
        """
        Used to check if the machine is currently reconnecting.
        :return: (bool) True if it's reconnecting. False otherwise.
        """
        ...

    @property
    def isPaused(self) -> bool:
        """
        :return: bool
        """
        ...

    @property
    def isFileTransferFinished(self) -> bool:
        """
        Used to check if file transfer to remote machine has finished.
        :return: (bool) True if the transfer has finished. False otherwise.
        """
        ...

    @property
    def isFileClipboardEnabled(self) -> bool:
        """
        Used to check if file transfer is available.
        :return: (bool) True if it files can be transferred. False otherwise.
        """
        ...

    def setGraphics(self, graphicsOption: str):
        """
        Used to set graphics options according to FreeRDP specification.
        :param graphicsOption: (str | unicode) Which graphics option should be used.
        :return:
        """
        ...

    def setFreerdpCliArgs(self, cliArgs: Union[str, List[str]]):
        """
        Used to configure FreeRdp via its command-line options.
        Compatible args can be found at https://github.com/FreeRDP/FreeRDP/wiki/CommandLineInterface
        :param cliArgs: (str | unicode | list[str | unicode]) Arguments either as a string with spaces between arguments or a list of arguments.
        :return:
        """
        ...


class RDPClipboardError(Exception): ...
