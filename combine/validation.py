"""Protocol field checks without network access or credential logging."""
import base64
import ipaddress
import json
from urllib.parse import parse_qs, unquote, urlsplit
from uuid import UUID

SS_CIPHERS = {
    'aes-128-ctr', 'aes-192-ctr', 'aes-256-ctr',
    'aes-128-cfb', 'aes-192-cfb', 'aes-256-cfb',
    'aes-128-gcm', 'aes-192-gcm', 'aes-256-gcm',
    'aes-128-ccm', 'aes-192-ccm', 'aes-256-ccm',
    'aes-128-gcm-siv', 'aes-256-gcm-siv',
    'chacha20-ietf', 'chacha20', 'xchacha20',
    'chacha20-ietf-poly1305', 'xchacha20-ietf-poly1305',
    'chacha8-ietf-poly1305', 'xchacha8-ietf-poly1305',
    '2022-blake3-aes-128-gcm', '2022-blake3-aes-256-gcm',
    '2022-blake3-chacha20-poly1305', 'lea-128-gcm', 'lea-192-gcm', 'lea-256-gcm',
    'rabbit128-poly1305', 'aegis-128l', 'aegis-256', 'aez-384', 'deoxys-ii-256-128',
    'rc4-md5', 'none',
}


def ss_credentials(method, password):
    if not isinstance(method, str) or method not in SS_CIPHERS or not text(password):
        return False
    if method.startswith('2022-'):
        size = 16 if method == '2022-blake3-aes-128-gcm' else 32
        try:
            return all(len(base64.b64decode(key, validate=True)) == size for key in password.split(':'))
        except ValueError:
            return False
    return True


def text(value):
    return isinstance(value, str) and bool(value.strip())


def integer(value, minimum=0, maximum=65535):
    return (isinstance(value, (int, str)) and not isinstance(value, bool)
            and str(value).isascii() and str(value).isdigit()
            and minimum <= int(value) <= maximum)


def uuid(value):
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
        return True
    except ValueError:
        return False


def host(value):
    if not text(value) or any(c.isspace() or ord(c) < 32 for c in value):
        return False
    if any(c in value for c in '/@?#'):
        return False
    if ':' in value:
        try:
            ipaddress.IPv6Address(value.strip('[]'))
        except ValueError:
            return False
    return True


def valid_proxy(proxy):
    kind = proxy['type']
    if not host(proxy['server']):
        return False
    required = {
        'ss': ('cipher', 'password'), 'ssr': ('cipher', 'password', 'protocol', 'obfs'),
        'trojan': ('password',), 'anytls': ('password',), 'snell': ('psk',),
    }.get(kind, ())
    if not all(text(proxy.get(key)) for key in required):
        return False
    if kind == 'ss' and not ss_credentials(proxy.get('cipher'), proxy.get('password')):
        return False
    if kind in ('vmess', 'vless') and not uuid(proxy.get('uuid')):
        return False
    if kind == 'vmess':
        if proxy.get('cipher', 'auto') not in ('auto', 'none', 'zero', 'aes-128-gcm', 'chacha20-poly1305'):
            return False
        if not integer(proxy.get('alterId', 0), maximum=2**31-1):
            return False
    if kind == 'tuic':
        if not text(proxy.get('token')) and not (uuid(proxy.get('uuid')) and text(proxy.get('password'))):
            return False
    if kind == 'hysteria':
        if not all(text(proxy.get(k)) or integer(proxy.get(k), minimum=1, maximum=2**63-1)
                   for k in ('up', 'down')):
            return False
    if kind == 'hysteria2' and 'password' in proxy and not text(proxy['password']):
        return False
    for key in ('tls', 'udp', 'skip-cert-verify', 'tfo'):
        if key in proxy and not isinstance(proxy[key], bool):
            return False
    for key in ('ws-opts', 'grpc-opts', 'h2-opts', 'http-opts', 'reality-opts', 'plugin-opts'):
        if key in proxy and not isinstance(proxy[key], dict):
            return False
    ws = proxy.get('ws-opts', {})
    if 'path' in ws and not isinstance(ws['path'], str):
        return False
    headers = ws.get('headers', {})
    if not isinstance(headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items()):
        return False
    if 'alpn' in proxy and (not isinstance(proxy['alpn'], list) or not all(text(v) for v in proxy['alpn'])):
        return False
    return True


def decode64(value):
    raw = value.encode('ascii')
    return base64.b64decode(raw + b'=' * (-len(raw) % 4), altchars=b'-_', validate=True).decode('utf-8')


def endpoint(parsed, default_port=None):
    port = parsed.port if parsed.port is not None else default_port
    return host(parsed.hostname) and integer(port, minimum=1)


def valid_uri(line):
    try:
        if any(c.isspace() or ord(c) < 32 for c in line):
            return False
        parsed = urlsplit(line)
        kind = parsed.scheme
        if kind == 'vmess' and '@' not in parsed.netloc:
            data = json.loads(decode64(line.split('://', 1)[1].split('#', 1)[0]))
            return (isinstance(data, dict) and host(data.get('add'))
                    and integer(data.get('port'), minimum=1) and uuid(data.get('id'))
                    and integer(data.get('aid', 0), maximum=2**31-1)
                    and data.get('scy', 'auto') in ('auto', 'none', 'zero', 'aes-128-gcm', 'chacha20-poly1305'))
        if kind == 'ssr':
            decoded = decode64(line.split('://', 1)[1])
            server, port, protocol, cipher, obfs, password = decoded.split('/?', 1)[0].rsplit(':', 5)
            return host(server) and integer(port, minimum=1) and all(text(v) for v in (protocol, cipher, obfs, decode64(password)))
        if kind == 'ss':
            body = line.split('://', 1)[1].split('#', 1)[0]
            if '@' not in body:
                parsed = urlsplit('ss://' + decode64(body))
            if not endpoint(parsed):
                return False
            if parsed.password is not None:
                method, password = unquote(parsed.username or ''), unquote(parsed.password)
            else:
                method, password = decode64(unquote(parsed.username or '')).split(':', 1)
            return ss_credentials(method, password)
        if kind in ('vmess', 'vless', 'trojan', 'hysteria', 'hysteria2', 'hy2', 'tuic'):
            if not endpoint(parsed, 443 if kind in ('hysteria2', 'hy2') else None):
                return False
            user = unquote(parsed.username or '')
            if kind in ('vmess', 'vless'):
                return uuid(user) and parsed.password is None
            if kind == 'tuic':
                return uuid(user) and text(unquote(parsed.password or ''))
            if kind == 'trojan':
                return text(user) and parsed.password is None
            if kind == 'hysteria':
                query = parse_qs(parsed.query)
                return all(integer(query.get(key, [None])[0], minimum=1, maximum=2**63-1) for key in ('upmbps', 'downmbps'))
            return True  # Hysteria2 allows an unauthenticated server.
        return False
    except (ValueError, TypeError, UnicodeError, AttributeError):
        return False
