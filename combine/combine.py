"""Fetch and validate subscriptions before replacing published outputs."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unicodedata

import yaml

if __package__ in (None, ''):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from combine.validation import valid_proxy, valid_uri

ROOT = Path(__file__).resolve().parent
SCHEMES = ('vmess://', 'vless://', 'ss://', 'ssr://', 'trojan://', 'hysteria://', 'hysteria2://', 'hy2://', 'tuic://')


def read_links(path):
    return [line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')]


def fetch_html(url):
    # Legacy callers receive text; the refresh pipeline keeps the full diagnostics.
    if __package__ in (None, ''):
        import sys
        sys.path.insert(0, str(ROOT.parent))
    from combine.download import fetch_subscription
    return fetch_subscription(url).content


def load_proxies(content, validate_protocols=True):
    if not content:
        return []
    try:
        config = yaml.safe_load(content)
    except yaml.YAMLError:
        return []
    if not isinstance(config, dict) or not isinstance(config.get('proxies'), list):
        return []
    result = []
    for proxy in config['proxies']:
        if not isinstance(proxy, dict):
            continue
        if not all(isinstance(proxy.get(key), str) and proxy[key].strip()
                   for key in ('name', 'type', 'server')):
            continue
        port = proxy.get('port')
        if isinstance(port, bool) or not str(port).isdigit() or not 1 <= int(port) <= 65535:
            continue
        proxy = copy.deepcopy(proxy)
        proxy['port'] = int(port)
        if validate_protocols and not valid_proxy(proxy):
            continue
        try:
            json.dumps(proxy, sort_keys=True, allow_nan=False, ensure_ascii=False).encode('utf-8')
        except (TypeError, ValueError, UnicodeError):
            continue
        result.append(proxy)
    return result


def merge_clash(configs, template=None, blacklist=None):
    if template is None:
        template = yaml.safe_load((ROOT / 'clash.config.template.yaml').read_text())
    template = copy.deepcopy(template)
    blocked = set(blacklist or [])
    entries = {}
    for content in configs:
        for proxy in load_proxies(content):
            if (proxy['server'], proxy['port']) in blocked:
                continue
            identity = {key: value for key, value in proxy.items() if key != 'name'}
            canonical = json.dumps(identity, sort_keys=True, ensure_ascii=False)
            label = ' '.join(proxy['name'].split())
            label = ''.join(char for char in label if unicodedata.category(char) != 'Cc')[:64] or 'node'
            entries.setdefault(canonical, set()).add(label)
    if not entries:
        raise ValueError('No valid Clash proxies; preserving previous output')
    proxies, names = [], set()
    for canonical in sorted(entries):
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        label = min(entries[canonical])
        length = 16
        name = f'{label} [{digest[:length]}]'
        while name in names and length < len(digest):
            length += 8
            name = f'{label} [{digest[:length]}]'
        if name in names:
            raise ValueError('Proxy name collision; preserving previous output')
        names.add(name)
        proxy = json.loads(canonical)
        proxy['name'] = name
        proxies.append(proxy)
    proxies.sort(key=lambda proxy: proxy['name'])
    template['proxies'] = proxies
    for group in template['proxy-groups']:
        if 'xxx' in group['proxies']:
            group['proxies'] = [name for name in group['proxies'] if name != 'xxx']
            group['proxies'].extend(proxy['name'] for proxy in proxies)
    return yaml.safe_dump(template, allow_unicode=True, sort_keys=False)


def load_v2ray(content, validate_protocols=True):
    if not content:
        return []
    content = content.strip()
    if not content.startswith(SCHEMES):
        try:
            encoded = ''.join(content.split()).encode('ascii')
            content = base64.b64decode(encoded + b'=' * (-len(encoded) % 4),
                                       altchars=b'-_', validate=True).decode('utf-8')
        except (ValueError, UnicodeError):
            return []
    return [line.strip() for line in content.splitlines()
            if line.strip().startswith(SCHEMES)
            and (valid_uri(line.strip()) if validate_protocols else
                 bool(line.strip().split('://', 1)[1]) and not any(c.isspace() for c in line.strip()))]


def merge_v2ray(configs):
    nodes = sorted({node for content in configs for node in load_v2ray(content)})
    if not nodes:
        raise ValueError('No recognized V2Ray URIs; preserving previous output')
    return base64.b64encode(('\n'.join(nodes) + '\n').encode()).decode() + '\n'


def atomic_write(path, content):
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     delete=False) as file:
        temporary = Path(file.name)
        file.write(content)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    # Keep the original script command working while using the shared refresh pipeline.
    if __package__ in (None, ''):
        import sys
        sys.path.insert(0, str(ROOT.parent))
    from combine.refresh import main as refresh_main
    return refresh_main()


if __name__ == '__main__':
    raise SystemExit(main())
