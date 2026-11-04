# coding=utf-8
"""
Clipboard redirection (MS-RDPECLIP) for RDPApplication: text and files.
All channel traffic runs on the RDP thread (the cliprdr callbacks are called there, and
the Client* calls are made there through RDPApplication's command queue);
the public load/save calls wait on threading events.
Formats:
    CF_UNICODETEXT          text, UTF-16LE, CRLF line endings.
    FileGroupDescriptorW    a registered format: UINT32 count + FILEDESCRIPTORW[]
                            followed by FILECONTENTS requests for the bytes.
"""
from pyfreerdpnative.freerdp.channels.cliprdr import CB_CAPS_VERSION_2, CB_CAPSTYPE_GENERAL, CB_FORMAT_LIST, \
    CB_FILECLIP_NO_FILE_PATHS, CB_FORMAT_LIST_RESPONSE, CB_RESPONSE_FAIL, CB_RESPONSE_OK, CB_STREAM_FILECLIP_ENABLED, \
    CB_USE_LONG_FORMAT_NAMES, CLIPRDR_CAPABILITIES, CLIPRDR_CAPABILITY_SET, CLIPRDR_FILE_CONTENTS_REQUEST, \
    CLIPRDR_FILE_CONTENTS_RESPONSE, CLIPRDR_FORMAT, CLIPRDR_FORMAT_DATA_REQUEST, CLIPRDR_FORMAT_DATA_RESPONSE, \
    CLIPRDR_FORMAT_LIST, CLIPRDR_FORMAT_LIST_RESPONSE, CLIPRDR_GENERAL_CAPABILITY_SET, FILECONTENTS_RANGE, \
    FILECONTENTS_SIZE
from pyfreerdpnative.winpr.shell import FD_ATTRIBUTES, FD_FILESIZE, FD_WRITESTIME, FILEDESCRIPTORW
from pyfreerdpnative.winpr.file import FILE_ATTRIBUTE_DIRECTORY, FILE_ATTRIBUTE_NORMAL
from pyfreerdpnative.freerdp.client.cliprdr import CliprdrClientContext
from pyfreerdpnative.winpr.user import CF_UNICODETEXT
from ctypes import c_ubyte, cast, POINTER, string_at, c_char_p, byref, pointer, sizeof
from os.path import basename, abspath, isdir, isfile, relpath, join, dirname
from struct import pack, unpack, unpack_from
from os import walk, stat, getcwd, makedirs
from threading import Event, RLock
from traceback import format_exc
from logging import getLogger
from fnmatch import fnmatch

_log = getLogger(u'PyFreeRdpApp.clipboard')
FILE_GROUP_DESCRIPTOR_W = b'FileGroupDescriptorW'  # type: bytes
LOCAL_FILE_FORMAT_ID = 0xC0BC  # type: int # any id >= 0xC000 for a registered format.
CHUNK = 64 * 1024  # type: int
TIMEOUT = 30.0  # type: float
FILETIME_EPOCH = 116444736000000000  # type: int # 1601 -> 1970, in 100 ns units.


def _fieldType(structure, name):
    """
    The declared ctypes type of struct field (reading a field may convert it).
    """
    for field in structure._fields_:
        if field[0] == name:
            return field[1]
    raise KeyError(name)


def encodeText(text):
    """
    :param text: str | unicode
    :return: bytes
    """
    return text.replace(u'\r\n', u'\n').replace(u'\n', u'\r\n').encode(u'utf-16-le') + b'\x00\x00'


def decodeText(raw):
    """
    :param raw: bytes
    :return: str | unicode
    """
    return raw.decode(u'utf-16-le', u'replace').split(u'\x00', 1)[0].replace(u'\r\n', u'\n')


def buildFileList(entries):
    """
    entries: [(relative_name, isDir, size, mtime)] -> CLIPRDR_FILELIST bytes.
    """
    out = [pack(u'<I', len(entries))]
    for name, isDir, size, mtime in entries:
        fd = FILEDESCRIPTORW()  # type: FILEDESCRIPTORW
        fd.dwFlags = FD_ATTRIBUTES | FD_FILESIZE | FD_WRITESTIME
        fd.dwFileAttributes = FILE_ATTRIBUTE_DIRECTORY if isDir else FILE_ATTRIBUTE_NORMAL
        size = 0 if isDir else int(size)  # type: int
        fd.nFileSizeHigh, fd.nFileSizeLow = size >> 32, size & 0xFFFFFFFF
        ft = FILETIME_EPOCH + int(mtime * 10000000)  # type: int
        fd.ftLastWriteTime.dwLowDateTime, fd.ftLastWriteTime.dwHighDateTime = ft & 0xFFFFFFFF, ft >> 32
        wName = name.replace(u'/', u'\\')[:259]  # type: str
        for i, ch in enumerate(wName):
            fd.cFileName[i] = ord(ch)
        out.append(bytes(memoryview(fd).cast(u'B')))
    return b''.join(out)


def parseFileList(raw):
    """
    CLIPRDR_FILELIST bytes -> [(relative_name, isDir, size)].
    """
    if len(raw) < 4:
        return []
    count = unpack_from(u'<I', raw, 0)[0]
    sizeFd = sizeof(FILEDESCRIPTORW)
    entries = []
    for i in range(count):
        off = 4 + i * sizeFd
        if off + sizeFd > len(raw):
            break
        fd = FILEDESCRIPTORW.from_buffer_copy(raw[off:off + sizeFd])
        name = u''.join(chr(c) for c in fd.cFileName if c).replace(u'\\', u'/')  # type: str
        isDir = bool(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)  # type: bool
        size = (fd.nFileSizeHigh << 32) | fd.nFileSizeLow
        entries.append((name, isDir, size))
    return entries


def collectFiles(paths, includeParent):
    """
    Files and/or directories on disk -> [(relative_name, isDir, size, mtime, absolute_path)].
    `paths` is one path or a list of them; with several, each keeps its own name.
    """
    if isinstance(paths, (list, tuple)):
        out = []
        for p in paths:
            out += collectFiles(p, includeParent or isdir(p) and len(paths) > 1)
        return out
    path = abspath(paths)  # type: str
    if isfile(path):
        st = stat(path)
        return [(basename(path), False, st.st_size, st.st_mtime, path)]
    if not isdir(path):
        raise FileNotFoundError(path)
    base = dirname(path) if includeParent else path
    out = []
    if includeParent:
        st = stat(path)
        out.append((basename(path), True, 0, st.st_mtime, path))
    for root, dirs, files in walk(path):
        dirs.sort()
        for d in dirs:
            full = join(root, d)  # type: str
            out.append((relpath(full, base), True, 0, stat(full).st_mtime, full))
        for f in sorted(files):
            full = join(root, f)  # type: str
            st = stat(full)
            out.append((relpath(full, base), False, st.st_size, st.st_mtime, full))
    return out


class Clipboard(object):
    """
    The client side of the cliprdr channel.
    """

    def __init__(self, runOnRdpThread):
        self._run = runOnRdpThread  # callable(fn) -> executes fn on the RDP thread.
        self._ctx = None  # POINTER(CliprdrClientContext)
        self._refs = []
        self.ready = False  # type: bool
        self.fileClipboard = False  # type: bool # Server supports file streams.
        self._serverFormats = {}  # id -> name (bytes) or None.
        self._formatsChanged = Event()  # type: Event
        self._localText = None
        self._localFiles = []  # for uploads
        self._served = {}  # listIndex -> bytes served.
        self._uploadStarted = False  # type: bool
        self._pending = None  # (kind, Event, [result])
        self._stream = 0  # type: int
        self.listener = None  # called (RDP thread) with {"text": bool, "files": bool}
        self._requestLock = RLock()  # type: RLock

    # --- channel attach (RDP thread) -----------------------------------------------
    def attach(self, iface):
        """
        :param iface: CliprdrClientContext
        :return:
        """
        self._ctx = cast(iface, POINTER(CliprdrClientContext))
        c = self._ctx.contents
        fields = dict((f[0], f[1]) for f in CliprdrClientContext._fields_)
        for name, fn in ((u'MonitorReady', self._monitorReady),
                         (u'ServerCapabilities', self._serverCapabilities),
                         (u'ServerFormatList', self._serverFormatList),
                         (u'ServerFormatListResponse', self._serverFormatListResponse),
                         (u'ServerFormatDataRequest', self._serverFormatDataRequest),
                         (u'ServerFormatDataResponse', self._serverFormatDataResponse),
                         (u'ServerFileContentsRequest', self._serverFileContentsRequest),
                         (u'ServerFileContentsResponse', self._serverFileContentsResponse)):
            cb = fields[name](self._safe(fn))
            self._refs.append(cb)
            setattr(c, name, cb)

    def detach(self):
        """
        :return:
        """
        self._ctx = None
        self.ready = False  # type: bool

    @staticmethod
    def _safe(fn):
        def wrapper(*args):
            """
            :param args: any
            :return: int
            """
            try:
                rc = fn(*args)
                return 0 if rc is None else rc
            except:
                getLogger(u'PyFreeRdpApp').error(u'cliprdr: %s', format_exc())
                return 0

        return wrapper

    # --- Outgoing PDUs (RDP thread) ---------------------------------------------------
    def _sendCapabilities(self):
        general = CLIPRDR_GENERAL_CAPABILITY_SET()  # type: CLIPRDR_GENERAL_CAPABILITY_SET
        general.capabilitySetType = CB_CAPSTYPE_GENERAL
        general.capabilitySetLength = 12
        general.version = CB_CAPS_VERSION_2
        general.generalFlags = CB_USE_LONG_FORMAT_NAMES | CB_STREAM_FILECLIP_ENABLED | CB_FILECLIP_NO_FILE_PATHS
        caps = CLIPRDR_CAPABILITIES()  # type: CLIPRDR_CAPABILITIES
        caps.cCapabilitiesSets = 1
        caps.capabilitySets = cast(pointer(general), POINTER(CLIPRDR_CAPABILITY_SET))
        self._keep = general
        return self._ctx.contents.ClientCapabilities(self._ctx, byref(caps))

    def _sendFormatList(self):
        formats = []
        if self._localText is not None:
            formats.append((CF_UNICODETEXT, None))
        if self._localFiles:
            formats.append((LOCAL_FILE_FORMAT_ID, FILE_GROUP_DESCRIPTOR_W))
        arr = (CLIPRDR_FORMAT * max(1, len(formats)))()
        names = []
        for i, (fid, name) in enumerate(formats):
            arr[i].formatId = fid
            if name:
                # a c_char_p field: reading it yields bytes/None, so never use
                # type(field) as a cast target - assign the bytes directly
                names.append(name)
                arr[i].formatName = name
        fl = CLIPRDR_FORMAT_LIST()  # type: CLIPRDR_FORMAT_LIST
        fl.common.msgType = CB_FORMAT_LIST
        fl.numFormats = len(formats)
        fl.formats = cast(arr, POINTER(CLIPRDR_FORMAT)) if formats else None
        self._keep_fl = (arr, names)
        return self._ctx.contents.ClientFormatList(self._ctx, byref(fl))

    @staticmethod
    def _fillResponse(resp, field, payload):
        """
        Fill a response PDU: OK + data, or FAIL when payload is None.
        :param resp: (CLIPRDR_FORMAT_DATA_RESPONSE | CLIPRDR_FILE_CONTENTS_RESPONSE) The PDU.
        :param field: (str | unicode) The pointer field that receives the data.
        :param payload: (bytes | None) The data.
        :return: (c_ubyte array | None) The buffer, to keep alive until the PDU is sent.
        """
        if payload is None:
            resp.common.msgFlags = CB_RESPONSE_FAIL
            return None
        buf = (c_ubyte * max(1, len(payload))).from_buffer_copy(payload or b'\0')
        resp.common.msgFlags = CB_RESPONSE_OK
        resp.common.dataLen = len(payload)
        setattr(resp, field, cast(buf, _fieldType(type(resp), field)))
        return buf

    @staticmethod
    def _responsePayload(common, ptr, length):
        """
        The data of a response PDU, or None when the peer answered FAIL.
        :param common: CLIPRDR_HEADER
        :param ptr: (POINTER(c_ubyte)) The data field.
        :param length: (int) Its length.
        :return: bytes | None
        """
        return None if common.msgFlags & CB_RESPONSE_FAIL or not ptr else string_at(ptr, int(length))

    def _dataResponse(self, payload):
        resp = CLIPRDR_FORMAT_DATA_RESPONSE()  # type: CLIPRDR_FORMAT_DATA_RESPONSE
        self._keep_resp = self._fillResponse(resp, u'requestedFormatData', payload)
        return self._ctx.contents.ClientFormatDataResponse(self._ctx, byref(resp))

    # --- callbacks from the server (RDP thread) ----------------------------------------
    def _monitorReady(self, ctx, ready):
        self._sendCapabilities()
        self._sendFormatList()
        self.ready = True  # type: bool

    def _serverCapabilities(self, ctx, caps):
        # FreeRDP calls this once per general capability set, with
        # capabilitySets pointing straight at a CLIPRDR_GENERAL_CAPABILITY_SET
        # (channels/cliprdr/client/cliprdr_main.c)
        c = caps.contents
        if not c.capabilitySets:
            return
        general = cast(c.capabilitySets, POINTER(CLIPRDR_GENERAL_CAPABILITY_SET)).contents
        if general.capabilitySetType == CB_CAPSTYPE_GENERAL:
            self.fileClipboard = bool(general.generalFlags & CB_STREAM_FILECLIP_ENABLED)

    def _serverFormatList(self, ctx, fl):
        f = fl.contents
        formats = {}
        for i in range(int(f.numFormats)):
            fmt = f.formats[i]
            name = cast(fmt.formatName, c_char_p).value if fmt.formatName else None
            formats[int(fmt.formatId)] = name
        self._serverFormats = formats
        self._formatsChanged.set()
        if self.listener is not None:
            try:
                if callable(self.listener):
                    self.listener(self.remoteContent())
            except:
                pass
        resp = CLIPRDR_FORMAT_LIST_RESPONSE()  # type: CLIPRDR_FORMAT_LIST_RESPONSE
        resp.common.msgType = CB_FORMAT_LIST_RESPONSE
        resp.common.msgFlags = CB_RESPONSE_OK
        self._ctx.contents.ClientFormatListResponse(self._ctx, byref(resp))

    @staticmethod
    def _serverFormatListResponse(ctx, resp):
        return 0

    def _serverFormatDataRequest(self, ctx, req):
        fid = int(req.contents.requestedFormatId)  # type: int
        if fid == CF_UNICODETEXT and self._localText is not None:
            return self._dataResponse(encodeText(self._localText))
        if fid == LOCAL_FILE_FORMAT_ID and self._localFiles:
            self._uploadStarted = True  # type: bool
            return self._dataResponse(buildFileList([e[:4] for e in self._localFiles]))
        return self._dataResponse(None)

    def _serverFormatDataResponse(self, ctx, resp):
        r = resp.contents
        self._complete(u'data', self._responsePayload(r.common, r.requestedFormatData, r.common.dataLen))

    def _serverFileContentsRequest(self, ctx, req):
        r = req.contents
        resp = CLIPRDR_FILE_CONTENTS_RESPONSE()  # type: CLIPRDR_FILE_CONTENTS_RESPONSE
        resp.streamId = r.streamId
        idx = int(r.listIndex)
        payload = None
        if 0 <= idx < len(self._localFiles):
            name, isDir, size, mtime, full = self._localFiles[idx]
            if r.dwFlags & FILECONTENTS_SIZE:
                payload = pack(u'<Q', 0 if isDir else size)
                if isDir or size == 0:
                    self._served[idx] = size
            elif r.dwFlags & FILECONTENTS_RANGE and not isDir:
                pos = (int(r.nPositionHigh) << 32) | int(r.nPositionLow)
                with open(full, u'rb') as fh:
                    fh.seek(pos)
                    payload = fh.read(int(r.cbRequested))
                self._served[idx] = max(self._served.get(idx, 0), pos + len(payload))
        self._keep_fc = self._fillResponse(resp, u'requestedData', payload)
        if payload is not None:
            resp.cbRequested = len(payload)
        return self._ctx.contents.ClientFileContentsResponse(self._ctx, byref(resp))

    def _serverFileContentsResponse(self, ctx, resp):
        r = resp.contents
        self._complete(u'contents', self._responsePayload(r.common, r.requestedData, r.cbRequested))

    # --- request/response plumbing --------------------------------------------------
    def _expect(self, kind):
        ev = Event()  # type: Event
        self._pending = (kind, ev, [None])
        return ev

    def _complete(self, kind, value):
        p = self._pending
        if p and p[0] == kind:
            p[2][0] = value
            p[1].set()

    def _request(self, kind, send):
        with self._requestLock:
            return self._requestLocked(kind, send)

    def _requestLocked(self, kind, send):
        ev = self._expect(kind)
        self._run(send)
        if not ev.wait(TIMEOUT):
            self._pending = None
            raise TimeoutError(u'No clipboard response from the server within %ds' % TIMEOUT)
        value = self._pending[2][0]
        self._pending = None
        return value

    def _formatData(self, formatId):
        def send():
            """
            :return:
            """
            req = CLIPRDR_FORMAT_DATA_REQUEST()  # type: CLIPRDR_FORMAT_DATA_REQUEST
            req.requestedFormatId = formatId
            self._ctx.contents.ClientFormatDataRequest(self._ctx, byref(req))

        return self._request(u'data', send)

    def _fileContents(self, index, flags, position, size):
        self._stream += 1
        stream = self._stream

        def send():
            """
            :return:
            """
            req = CLIPRDR_FILE_CONTENTS_REQUEST()  # type: CLIPRDR_FILE_CONTENTS_REQUEST
            req.streamId = stream
            req.listIndex = index
            req.dwFlags = flags
            req.nPositionLow, req.nPositionHigh = position & 0xFFFFFFFF, position >> 32
            req.cbRequested = size
            req.haveClipDataId = 0
            self._ctx.contents.ClientFileContentsRequest(self._ctx, byref(req))

        return self._request(u'contents', send)

    def _serverFileFormatId(self):
        for fid, name in self._serverFormats.items():
            if name and name.rstrip(b'\0') == FILE_GROUP_DESCRIPTOR_W:
                return fid
        return None

    def remoteContent(self):
        """
        What the server's clipboard currently offers.
        """
        return {u'text': CF_UNICODETEXT in self._serverFormats, u'files': self._serverFileFormatId() is not None}

    # --- public API (user thread) ------------------------------------------------------
    def saveText(self, text):
        """
        :param text: str | unicode
        :return:
        """
        self._localText = text  # type: str
        self._localFiles = []
        self._run(self._sendFormatList)

    def loadText(self):
        """
        :return: str | unicode | None
        """
        if CF_UNICODETEXT not in self._serverFormats:
            return None
        raw = self._formatData(CF_UNICODETEXT)
        return None if raw is None else decodeText(raw)

    def saveFiles(self, paths, includeParent=False):
        """
        :param paths: list[str | unicode]
        :param includeParent: bool
        :return:
        """
        self._localFiles = collectFiles(paths, includeParent)
        self._localText = None
        self._served = {}
        self._uploadStarted = False  # type: bool
        self._run(self._sendFormatList)

    def uploadProgress(self):
        """
        :return: (tuple[int, int]) (bytes the remote side has received, bytes offered) of the files
            on the remote clipboard.
        """
        files = [(i, size) for i, (name, isDir, size, mtime, full) in enumerate(self._localFiles)
                 if not isDir and size]
        return sum(min(self._served.get(i, 0), size) for i, size in files), sum(size for i, size in files)

    def uploadFinished(self):
        """
        :return: bool
        """
        if not self._localFiles:
            return True
        for i, (name, isDir, size, mtime, full) in enumerate(self._localFiles):
            if not isDir and size and self._served.get(i, 0) < size:
                return False
        return True

    def loadFiles(self, dirPath, pattern=None):
        """
        :param dirPath: str | unicode
        :param pattern: str | unicode
        :return: str | unicode | None
        """
        with self._requestLock:
            return self._loadFiles(dirPath, pattern)

    def _loadFiles(self, dirPath, pattern=None):
        fid = self._serverFileFormatId()
        if fid is None:
            _log.info(u'Download: the remote clipboard offers no files (formats: %s)',
                      sorted(self._serverFormats.values(), key=str))
            return None
        _log.info(u'Download: requesting the file list (format 0x%04X)', fid)
        raw = self._formatData(fid)
        if raw is None:
            _log.warning(u'download: the server refused the file list (policy may block clipboard files)')
            return None
        entries = parseFileList(raw)
        _log.info(u'Download: %d entr%s: %s', len(entries), u'y' if len(entries) == 1 else u'ies',
                  u', '.join(e[0] for e in entries[:10]))
        dirPath = abspath(dirPath or getcwd())  # type: str
        if not isdir(dirPath):
            makedirs(dirPath)
        for index, (name, isDir, size) in enumerate(entries):
            target = join(dirPath, *[p for p in name.split(u'/') if p not in (u'', u'.', u'..')])
            if isDir:
                if not isdir(target):
                    makedirs(target)
                continue
            if pattern and not fnmatch(basename(name), pattern):
                continue
            parent = dirname(target)  # type: str
            if parent and not isdir(parent):
                makedirs(parent)
            if not size:
                sz = self._fileContents(index, FILECONTENTS_SIZE, 0, 8)
                size = unpack(u'<Q', sz[:8])[0] if sz and len(sz) >= 8 else 0
            _log.info(u'Download: %s (%d bytes) -> %s', name, size, target)
            with open(target, u'wb') as out:
                pos = 0  # type: int
                while pos < size:
                    chunk = self._fileContents(index, FILECONTENTS_RANGE, pos, min(CHUNK, size - pos))  # type: int
                    if not chunk:
                        raise IOError(u'Server stopped sending %s at byte %d of %d' % (name, pos, size))
                    out.write(chunk)
                    pos += len(chunk)  # type: int
        return dirPath

    def waitForFormats(self, timeout=2.0):
        """
        Give a just-announced server format list a moment to arrive.
        :param timeout: float | int
        :return: dict
        """
        self._formatsChanged.wait(timeout)
        return dict(self._serverFormats)
