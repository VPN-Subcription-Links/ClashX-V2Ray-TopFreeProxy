"""Source registry and generated subscription links; no network access on import."""
import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DOCUMENTS = {
    'README.md': 'clash', 'clash中文版.md': 'clash',
    'v2ray.md': 'v2ray', 'v2ray中文版.md': 'v2ray',
}
START = '<!-- subscriptions:start -->'
END = '<!-- subscriptions:end -->'
ARCHIVE = '<!-- Archived Reference:'
URL_PATTERN = re.compile(r'https?://[^\s<>]+')


def load_sources(path=None):
    sources = json.loads((path or ROOT / 'sources.json').read_text(encoding='utf-8'))
    if not isinstance(sources, list):
        raise ValueError('Source registry must be a list')
    seen = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError('Every source must be an object')
        identifier = source.get('id', '')
        if not isinstance(identifier, str) or not re.fullmatch(r'[a-z0-9-]+', identifier) or identifier in seen:
            raise ValueError('Source IDs must be unique lowercase identifiers')
        seen.add(identifier)
        if not isinstance(source.get('name'), str) or not source['name'].strip():
            raise ValueError(f'{identifier}: missing source name')
        if not isinstance(source.get('enabled'), bool):
            raise ValueError(f'{identifier}: enabled must be a boolean')
        formats = source.get('formats')
        if not isinstance(formats, dict) or not formats or set(formats) - {'clash', 'v2ray'}:
            raise ValueError(f'{identifier}: invalid formats')
        for kind, feed in formats.items():
            if not isinstance(feed, dict):
                raise ValueError(f'{identifier}/{kind}: invalid feed')
            if 'enabled' in feed and not isinstance(feed['enabled'], bool):
                raise ValueError(f'{identifier}/{kind}: enabled must be a boolean')
            for key in ('url', 'date_pattern'):
                if key not in feed and key == 'date_pattern':
                    continue
                url = feed.get(key)
                if not isinstance(url, str):
                    raise ValueError(f'{identifier}/{kind}: missing URL')
                try:
                    parsed = urlsplit(url.format(year='2026', month='01', date='20260101'))
                except (KeyError, ValueError) as exc:
                    raise ValueError(f'{identifier}/{kind}: invalid URL pattern') from exc
                if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                    raise ValueError(f'{identifier}/{kind}: URL must use HTTPS without credentials')
    return sources


def active_formats(source):
    return [kind for kind, feed in source['formats'].items()
            if source['enabled'] and feed.get('enabled', True)]


def dated_url(feed, day):
    return feed['date_pattern'].format(year=day.strftime('%Y'), month=day.strftime('%m'),
                                       date=day.strftime('%Y%m%d'))


def saved_urls(path=None):
    path = path or ROOT / 'health.json'
    if not path.exists():
        return {}
    report = json.loads(path.read_text(encoding='utf-8'))
    return {(row['id'], row['format']): row['last_valid_url']
            for row in report.get('sources', []) if row.get('last_valid_url')}


def selected_url(source, kind, previous):
    feed = source['formats'][kind]
    return previous.get((source['id'], kind), feed['url']) if 'date_pattern' in feed else feed['url']


def append_archive(text, urls):
    """Keep existing archive entries and append missing retired URLs exactly once."""
    urls = list(dict.fromkeys(urls))
    if not urls:
        return text
    if ARCHIVE not in text:
        return text.rstrip() + '\n\n' + ARCHIVE + '\n' + '\n'.join(urls) + '\n-->\n'
    before, rest = text.split(ARCHIVE, 1)
    archive, after = rest.split('-->', 1)
    existing = set(URL_PATTERN.findall(archive))
    additions = [url for url in urls if url not in existing]
    if not additions:
        return text
    return before + ARCHIVE + archive.rstrip() + '\n' + '\n'.join(additions) + '\n-->' + after


def generated_files(sources, previous, root=ROOT):
    """Return deterministic contents without modifying unrelated document sections."""
    result = {}
    for kind in ('clash', 'v2ray'):
        urls = [selected_url(source, kind, previous) for source in sources
                if kind in active_formats(source)]
        result[root / f'{kind}sub.txt'] = '\n'.join(urls) + '\n'
    for name, kind in DOCUMENTS.items():
        path = root.parent / name
        text = path.read_text(encoding='utf-8')
        if text.count(START) != 1 or text.count(END) != 1:
            raise ValueError(f'{name}: expected exactly one subscription marker pair')
        before, rest = text.split(START)
        old_links, after = rest.split(END)
        lines = [f"* {source['name']}: {selected_url(source, kind, previous)}"
                 for source in sources if kind in active_formats(source)]
        active = {selected_url(source, kind, previous) for source in sources
                  if kind in active_formats(source)}
        retired = [url for url in URL_PATTERN.findall(old_links) if url not in active]
        retired.extend(source['formats'][kind]['url'] for source in sources
                       if kind in source['formats'] and kind not in active_formats(source)
                       and source['formats'][kind]['url'] not in active)
        updated = before + START + '\n' + '\n'.join(lines) + '\n' + END + after
        result[path] = append_archive(updated, retired)
    return result


def sync_links(sources=None, previous=None, root=ROOT, check=False):
    sources = load_sources() if sources is None else sources
    previous = saved_urls() if previous is None else previous
    changed = []
    for path, content in generated_files(sources, previous, root).items():
        if not path.exists() or path.read_text(encoding='utf-8') != content:
            changed.append(path)
            if not check:
                path.write_text(content, encoding='utf-8')
    return changed


def main():
    parser = argparse.ArgumentParser(description='Generate source links without network requests')
    parser.add_argument('--check', action='store_true', help='Fail if generated links are out of date')
    args = parser.parse_args()
    changed = sync_links(check=args.check)
    for path in changed:
        print(f'{"Out of date" if args.check else "Updated"}: {path.name}')
    return 1 if args.check and changed else 0


if __name__ == '__main__':
    raise SystemExit(main())
