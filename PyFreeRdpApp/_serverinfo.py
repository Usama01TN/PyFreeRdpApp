# -*- coding: utf-8 -*-
"""
Decoders for what FreeRDP receives from an RDP server while it connects (RDPApplication collects
the raw data from FreeRDP itself - no extra connection is ever made):
  * the TLS certificate FreeRDP hands to VerifyX509Certificate (PEM), decoded with FreeRDP's own
    certificate API (freerdp_certificate_*),
  * the NTLM CHALLENGE of FreeRDP's own NLA exchange (MS-NLMP 2.2.1.2): the Windows version and
    build, the NetBIOS/DNS computer, domain and forest names and the server's clock,
  * the negotiated security protocol (MS-RDPBCGR 2.2.1.1.1).
"""
from ctypes import CDLL, CFUNCTYPE, POINTER, Structure, byref, c_char_p, c_int, c_size_t, c_void_p, cast, string_at
from datetime import datetime, timedelta, timezone
from pyfreerdpnative.winpr import custom_crypto
from struct import unpack, unpack_from
from sys import platform

# MS-RDPBCGR 2.2.1.1.1 requestedProtocols / selectedProtocol.
PROTOCOL_RDP = 0x00000000  # type: int
PROTOCOL_SSL = 0x00000001  # type: int
PROTOCOL_HYBRID = 0x00000002  # type: int
PROTOCOL_RDSTLS = 0x00000004  # type: int
PROTOCOL_HYBRID_EX = 0x00000008  # type: int
PROTOCOL_RDSAAD = 0x00000010  # type: int
PROTOCOL_NAMES = ((PROTOCOL_RDSAAD, u'Azure AD (RDSAAD)'), (PROTOCOL_HYBRID_EX, u'NLA with early user auth'),
                  (PROTOCOL_HYBRID, u'NLA (CredSSP)'), (PROTOCOL_RDSTLS, u'RDSTLS'), (PROTOCOL_SSL, u'TLS')
                  )  # type: tuple
# MS-NLMP 2.2.2.1 AV_PAIR identifiers.
AV_NAMES = {1: u'netbiosComputerName', 2: u'netbiosDomainName', 3: u'dnsComputerName', 4: u'dnsDomainName',
            5: u'dnsTreeName'}  # type: dict
AV_TIMESTAMP = 7  # type: int
# Windows builds -> names. Client and server editions share build numbers from Windows 10 on.
WINDOWS_BUILDS = (
    (26100, u'Windows Server 2025 / Windows 11 24H2'), (22631, u'Windows 11 23H2'), (22621, u'Windows 11 22H2'),
    (22000, u'Windows 11 21H2'), (20348, u'Windows Server 2022'), (19045, u'Windows 10 22H2'),
    (19044, u'Windows 10 21H2'), (19043, u'Windows 10 21H1'), (19042, u'Windows 10 20H2'),
    (19041, u'Windows 10 2004'), (18363, u'Windows 10 1909'), (18362, u'Windows 10 1903'),
    (17763, u'Windows Server 2019 / Windows 10 1809'), (17134, u'Windows 10 1803'), (16299, u'Windows 10 1709'),
    (15063, u'Windows 10 1703'), (14393, u'Windows Server 2016 / Windows 10 1607'), (10586, u'Windows 10 1511'),
    (10240, u'Windows 10 1507'), (9600, u'Windows Server 2012 R2 / Windows 8.1'),
    (9200, u'Windows Server 2012 / Windows 8'), (7601, u'Windows Server 2008 R2 SP1 / Windows 7 SP1'),
    (7600, u'Windows Server 2008 R2 / Windows 7'), (6002, u'Windows Server 2008 SP2 / Windows Vista SP2'),
)  # type: tuple


def protocolNames(protocols):
    """
    :param protocols: (int) A requestedProtocols/selectedProtocol bit field.
    :return: (str | unicode) e.g. `NLA (CredSSP)`, `TLS`, `standard RDP security`.
    """
    names = [name for bit, name in PROTOCOL_NAMES if protocols & bit]  # type: list
    return u' + '.join(names) if names else u'standard RDP security'


def windowsName(major, minor, build):
    """
    :param major: (int) Product major version.
    :param minor: (int) Product minor version.
    :param build: (int) Build number.
    :return: (str | unicode) e.g. `Windows Server 2022`.
    """
    if (major, minor) >= (6, 0):
        for number, name in WINDOWS_BUILDS:  # Newest first: the first build not above this one.
            if build >= number:
                return name
    return u'Windows {}.{}'.format(major, minor)


def filetimeToDatetime(value):
    """
    :param value: (int) 100 ns intervals since 1601-01-01 (UTC).
    :return: datetime
    """
    return datetime(1601, 1, 1) + timedelta(microseconds=value // 10)


def parseChallenge(data):
    """
    The useful fields of an NTLM CHALLENGE_MESSAGE found anywhere in data (MS-NLMP 2.2.1.2).
    :param data: (bytes) Typically the TSRequest that carries it.
    :return: dict | None
    """
    start = data.find(b'NTLMSSP\x00\x02\x00\x00\x00')  # type: int
    if start < 0:
        return None
    msg = data[start:]  # type: bytes
    info = {}  # type: dict
    if len(msg) >= 56:
        major, minor, build = unpack_from(u'<BBH', msg, 48)
        info.update(osMajor=major, osMinor=minor, osBuild=build,
                    osVersion=u'{}.{}.{}'.format(major, minor, build), osName=windowsName(major, minor, build))
    if len(msg) >= 48:
        length, _maxLength, offset = unpack_from(u'<HHI', msg, 40)
        pairs = msg[offset:offset + length]  # type: bytes
        position = 0  # type: int
        while position + 4 <= len(pairs):
            avId, avLength = unpack_from(u'<HH', pairs, position)
            value = pairs[position + 4:position + 4 + avLength]  # type: bytes
            position += 4 + avLength
            if avId == 0:
                break
            if avId in AV_NAMES:
                info[AV_NAMES[avId]] = value.decode(u'utf-16-le', u'replace')
            elif avId == AV_TIMESTAMP and avLength == 8:
                info[u'serverTime'] = filetimeToDatetime(unpack_from(u'<Q', value)[0]).strftime(
                    u'%Y-%m-%d %H:%M:%S UTC')
    return info


# WinPR digest identifiers -> names, e.g. WINPR_MD_SHA256 -> sha256.
DIGESTS = dict((getattr(custom_crypto, name), name[len(u'WINPR_MD_'):].lower())
               for name in dir(custom_crypto) if name.startswith(u'WINPR_MD_'))  # type: dict


class StreamHead(Structure):
    """
    The start of WinPR's wStream (winpr/stream.h) with size_t as size_t on every platform (the
    generated bindings use c_ulong, which is 32-bit on Windows).
    """
    _fields_ = [(u'buffer', c_void_p), (u'pointer', c_void_p), (u'length', c_size_t), (u'capacity', c_size_t)]


def _peImport(base, functionName):
    """
    The address a loaded Windows module calls for an imported function: read from the module's
    import address table in memory (what the loader bound it to). Every read is bounds-checked
    against the module's SizeOfImage: anything unexpected means (None, None), never a crash.
    :param base: (int) The module's base address (its HMODULE).
    :param functionName: (bytes) e.g. b'free'.
    :return: (tuple) (address, dll name) or (None, None) when the module does not import it.
    """
    limit = [0x1000]  # The headers, until SizeOfImage is known.

    def read(offset, size):
        """
        :param offset: (int) RVA.
        :param size: (int) Bytes.
        :return: bytes
        """
        if offset < 0 or size < 0 or offset + size > limit[0]:
            raise ValueError(u'outside the module')
        return string_at(base + offset, size)

    def name(offset):
        """
        :param offset: (int) RVA of a NUL-terminated ASCII name (at most 256 bytes).
        :return: bytes
        """
        raw = read(offset, min(256, limit[0] - offset))
        return raw.split(b'\0', 1)[0]

    try:
        if read(0, 2) != b'MZ':
            return None, None
        nt = unpack(u'<I', read(0x3C, 4))[0]  # type: int
        if read(nt, 4) != b'PE\0\0':
            return None, None
        optional = nt + 24  # type: int
        wide = unpack(u'<H', read(optional, 2))[0] == 0x20B  # PE32+ (64-bit), else PE32
        limit[0] = unpack(u'<I', read(optional + 56, 4))[0]  # SizeOfImage
        directories = optional + (112 if wide else 96)  # type: int
        imports, size = unpack(u'<II', read(directories + 8, 8))  # Entry 1 is IMPORT (entry 0 is EXPORT).
        if not imports or not size:
            return None, None
        thunkSize, ordinalFlag = (8, 1 << 63) if wide else (4, 1 << 31)
        descriptor = imports  # type: int
        while True:
            lookup, _stamp, _forwarder, nameRva, iat = unpack(u'<IIIII', read(descriptor, 20))
            if not (lookup or nameRva or iat):
                return None, None
            dll = name(nameRva).decode(u'ascii', u'replace')
            for index in range(65536):
                entry = unpack(u'<Q' if wide else u'<I', read((lookup or iat) + index * thunkSize, thunkSize))[0]
                if not entry:
                    break
                if not entry & ordinalFlag and name((entry & 0x7FFFFFFF) + 2) == functionName:
                    return unpack(u'<Q' if wide else u'<I', read(iat + index * thunkSize, thunkSize))[0], dll
            descriptor += 20
    except (ValueError, OSError):
        return None, None


_FREE = {}  # type: dict  # Resolved once per process.


def freerdpFree(api):
    """
    The free() FreeRDP's own code calls, for the strings it returns malloc()-ed. Never a guess: on
    Windows, FreeRDP may be built with the shared C runtime (ucrtbase) or with a private one inside
    its DLLs (/MT), and freeing with the wrong one is fatal - so the import table of FreeRDP's DLL
    says which. When the DLL has a private runtime (it imports no free), None: those few strings
    are then not freed (a few hundred bytes per connection) instead of risking the process.
    :param api: (pyfreerdpnative.FreeRDP) The loaded API.
    :return: callable | None
    """
    if u'free' in _FREE:
        return _FREE[u'free']
    free = None
    if platform == u'win32':
        from ctypes import WinDLL
        kernel32 = WinDLL(u'kernel32', use_last_error=True)
        module = c_void_p()
        # GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT
        if kernel32.GetModuleHandleExW(0x4 | 0x2, cast(api.freerdp_certificate_new_from_pem, c_void_p),
                                       byref(module)) and module.value:
            address, _dll = _peImport(module.value, b'free')
            if address:
                free = CFUNCTYPE(None, c_void_p)(address)
    else:
        free = CDLL(None).free  # Linux / macOS: FreeRDP allocates with the C library.
        free.argtypes = [c_void_p]
        free.restype = None
    _FREE[u'free'] = free
    return free


def _native(api, name, restype, *argtypes):
    """
    A FreeRDP function called through an explicit prototype: char* results stay raw pointers (so
    they can be freed), size_t is c_size_t on every platform.
    :param api: (pyfreerdpnative.FreeRDP) The loaded API.
    :param name: (str | unicode) The function name.
    :param restype: ctypes type
    :param argtypes: ctypes types
    :return: callable
    """
    return CFUNCTYPE(restype, *argtypes)(cast(getattr(api, name), c_void_p).value)


def parseUsername(username):
    """
    Split a username with FreeRDP's rule (freerdp_parse_username, used by its /u: option): at the
    first backslash, `DOMAIN\\user` -> (user, DOMAIN); `user@domain` stays whole - a UPN that CredSSP
    understands. Done here so logging in makes no native call that returns memory to free.
    :param username: (str | unicode) What was typed.
    :return: (tuple) (user, domain or None).
    """
    if not username or u'\\' not in username:
        return username, None
    domain, user = username.split(u'\\', 1)
    return user, domain


def describeCertificate(api, pem):
    """
    Decode a certificate with FreeRDP's own certificate API.
    :param api: (pyfreerdpnative.FreeRDP) The loaded API.
    :param pem: (str | unicode) The PEM FreeRDP passed to VerifyX509Certificate.
    :return: dict
    """
    free = freerdpFree(api)
    newFromPem = _native(api, u'freerdp_certificate_new_from_pem', c_void_p, c_char_p)
    certificate = newFromPem(pem.encode(u'ascii'))
    if not certificate:
        return {u'error': u'FreeRDP could not read the certificate'}

    def text(name, *args):
        """
        A char* result of freerdp_certificate_<name>(certificate, ...), freed after reading.
        :param name: str | unicode
        :param args: (tuple) (ctype, value) pairs.
        :return: str | unicode | None
        """
        fn = _native(api, u'freerdp_certificate_' + name, c_void_p, c_void_p, *[t for t, _v in args])
        pointer = fn(certificate, *[v for _t, v in args])
        if not pointer:
            return None
        try:
            return string_at(pointer).decode(u'utf-8', u'replace')
        finally:
            if free is not None:
                free(pointer)

    try:
        subject, issuer = text(u'get_subject'), text(u'get_issuer')
        info = {
            u'subject': subject,
            u'issuer': issuer,
            u'selfSigned': bool(subject) and subject == issuer,
            u'commonName': text(u'get_common_name', (POINTER(c_size_t), None)),
            u'notBefore': text(u'get_validity', (c_int, 1)),
            u'notAfter': text(u'get_validity', (c_int, 0)),
            u'sha256': (text(u'get_fingerprint_by_hash', (c_char_p, b'sha256')) or u'').upper() or None,
            u'sha1': (text(u'get_fingerprint_by_hash', (c_char_p, b'sha1')) or u'').upper() or None,
            u'email': text(u'get_email'),
            u'upn': text(u'get_upn'),
            u'signature': DIGESTS.get(_native(api, u'freerdp_certificate_get_signature_alg', c_int, c_void_p)(
                certificate)),
            u'publicKey': u'RSA' if _native(api, u'freerdp_certificate_is_rsa', c_int, c_void_p)(certificate)
            else u'not RSA (EC, ...)',
        }  # type: dict
        count, lengths = c_size_t(0), POINTER(c_size_t)()
        getNames = _native(api, u'freerdp_certificate_get_dns_names', POINTER(c_char_p), c_void_p,
                           POINTER(c_size_t), POINTER(POINTER(c_size_t)))
        names = getNames(certificate, byref(count), byref(lengths))
        if names:
            info[u'subjectAltNames'] = [names[i][:lengths[i]].decode(u'utf-8', u'replace') for i in range(count.value)]
            _native(api, u'freerdp_certificate_free_dns_names', None, c_size_t, POINTER(c_size_t),
                    POINTER(c_char_p))(count, lengths, names)
    finally:
        _native(api, u'freerdp_certificate_free', None, c_void_p)(certificate)
    try:
        expires = datetime.strptime(info[u'notAfter'], u'%b %d %H:%M:%S %Y %Z')
        remaining = expires - datetime.now(timezone.utc).replace(tzinfo=None)  # type: timedelta
        info[u'daysLeft'] = remaining.days
        info[u'expired'] = remaining.total_seconds() < 0
        info[u'validity'] = (u'EXPIRED {} ago' if info[u'expired'] else u'expires in {}').format(
            humanDuration(abs(remaining.total_seconds())))
    except (TypeError, ValueError):
        pass
    return info


def humanDuration(seconds):
    """
    :param seconds: (float) A duration.
    :return: (str | unicode) e.g. `3 days`, `1 day`, `5 hours`, `12 minutes`.
    """
    for unit, size in ((u'day', 86400), (u'hour', 3600), (u'minute', 60)):
        if seconds >= size:
            count = int(seconds // size)  # type: int
            return u'{} {}{}'.format(count, unit, u's' if count != 1 else u'')
    return u'less than a minute'
