"""Refresh both subscription formats and record fetch/parse health."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path

import yaml

from .combine import ROOT, atomic_write, load_proxies, load_v2ray, merge_clash, merge_v2ray, read_links
from .download import FetchResult, fetch_subscription
from .engine import validate_clash
from .sources import active_formats, dated_url, load_sources, sync_links


def resolve_feed(source, kind, previous, day, fetch=fetch_subscription):
    feed = source['formats'][kind]
    old = previous.get((source['id'], kind), {})
    candidates = []
    if 'date_pattern' in feed:
        candidates.extend(dated_url(feed, day - timedelta(days=offset)) for offset in range(3))
        if old.get('last_valid_url') and old.get('configured_url') == feed['url']:
            candidates.append(old['last_valid_url'])
    candidates.append(feed['url'])
    attempts = []
    parse = load_proxies if kind == 'clash' else load_v2ray
    content = None
    count = 0
    for url in dict.fromkeys(candidates):
        result = fetch(url)
        if not isinstance(result, FetchResult):
            result = FetchResult(content=result, error='fetch_failed' if result is None else None)
        candidate = result.content
        count = len(parse(candidate))
        status = 'parsed' if count else ('fetch_failed' if candidate is None else 'unusable')
        attempts.append({'url': url, 'status': status, 'parsed_entries': count,
                         'http_status': result.http_status, 'error': result.error,
                         'requests': result.requests})
        if count:
            content = candidate
            break
    row = {
        'id': source['id'], 'name': source['name'], 'format': kind,
        'configured_url': feed['url'], 'url': url, 'status': status,
        'parsed_entries': count, 'attempts': attempts,
        'last_valid_url': url if count else old.get('last_valid_url'),
        'last_successful_fetch': old.get('last_successful_fetch'),
    }
    return row, content


def render_health(report):
    lines = ['# Subscription source status / 订阅来源状态', '',
             f"Checked (UTC): {report['checked_at']}", '',
             f"Published this run: {'yes' if report['published'] else 'no; previous outputs retained'}", '',
             f"Last successful publication (UTC): {report.get('last_successful_publication') or 'not recorded'}", '',
             'Status describes fetching and parsing only. Node connectivity has not been tested.',
             '状态仅表示获取与解析结果，不代表节点可连接。', '',
             '| Source | Format | Status | Parsed entries | HTTP | Detail | Requests |',
             '| --- | --- | --- | ---: | ---: | --- | ---: |']
    for row in report['sources']:
        name = row['name'].replace('|', '\\|').replace('\n', ' ')
        last = row['attempts'][-1]
        http_status = last.get('http_status') or '—'
        detail = last.get('error') or ('no_recognized_entries' if row['status'] == 'unusable' else '—')
        request_count = sum(len(attempt.get('requests') or [attempt]) for attempt in row['attempts'])
        lines.append(f"| {name} | {row['format']} | {row['status']} | {row['parsed_entries']} | {http_status} | {detail} | {request_count} |")
    lines.extend(['', 'Detailed fetch attempts and last usable URLs: [health.json](health.json).', '',
                  'The merged totals exclude duplicate entries and blacklisted Clash endpoints.', '',
                  f"Merged Clash entries: {report['merged_entries']['clash']}; V2Ray entries: {report['merged_entries']['v2ray']}.", ''])
    if report.get('previous_entries') is not None:
        lines.extend(['| Format | Previously published entries | This attempt |',
                      '| --- | ---: | ---: |'])
        for kind in ('clash', 'v2ray'):
            lines.append(f"| {kind} | {report['previous_entries'][kind]} | {report['merged_entries'][kind]} |")
        lines.extend(['', f"Minimum retained ratio: {report['min_retained_ratio']:g}.", ''])
    if report.get('errors'):
        lines.extend(['## Refresh errors / 刷新错误', ''])
        lines.extend('* ' + error for error in report['errors'])
        lines.append('')
    if report.get('engine_validation'):
        lines.extend([f"Mihomo configuration validation: {report['engine_validation']['status']}.", '',
                      'Engine validation checks configuration compatibility, not node connectivity.', ''])
    if report.get('disabled_sources'):
        lines.extend(['## Disabled sources / 已停用来源', '',
                      'Retained for reference; skipped during refresh. Re-enable in the registry after verification.',
                      '保留来源记录；刷新时跳过。确认可用后可在目录中重新启用。', '',
                      '| Source | Format | Reason |', '| --- | --- | --- |'])
        for row in report['disabled_sources']:
            cells = [str(row[key]).replace('|', '\\|').replace('\n', ' ')
                     for key in ('name', 'format', 'reason')]
            lines.append('| ' + ' | '.join(cells) + ' |')
        lines.append('')
    return '\n'.join(lines)


def run(root=ROOT, registry=None, output_dir=None, fetch=fetch_subscription, now=None, min_retained_ratio=0.5, mihomo=None):
    if not math.isfinite(min_retained_ratio) or not 0 <= min_retained_ratio <= 1:
        raise ValueError("Minimum retained ratio must be between 0 and 1")
    root = Path(root).resolve()
    output_dir = Path(output_dir).resolve() if output_dir else root
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = load_sources(registry or root / 'sources.json')
    previous_path = output_dir / 'health.json'
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    previous_rows = {(row['id'], row['format']): row for row in previous.get('sources', [])}
    previous_counts = {}
    for kind, filename, parse in (
        ('clash', 'clash.config.yaml', load_proxies),
        ('v2ray', 'v2ray.config.txt', load_v2ray),
    ):
        path = output_dir / filename
        previous_counts[kind] = len(parse(path.read_text(encoding='utf-8'), validate_protocols=False)) if path.exists() else 0
    now = now or datetime.now(timezone.utc)
    checked = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    tasks = [(source, kind) for source in sources for kind in active_formats(source)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda task: resolve_feed(*task, previous_rows, now.date(), fetch), tasks))
    configs = {'clash': [], 'v2ray': []}
    rows = []
    for row, content in results:
        if content:
            row['last_successful_fetch'] = checked
            configs[row['format']].append(content)
        rows.append(row)
        print(f"[{row['status']}] {row['name']} / {row['format']}: {row['parsed_entries']} parsed entries")
    blacklist = []
    for line in read_links(root / 'blacklists.txt'):
        server, port = line.rsplit(':', 1)
        blacklist.append((server, int(port)))
    template = yaml.safe_load((root / 'clash.config.template.yaml').read_text())
    outputs, errors = {}, []
    for kind in ('clash', 'v2ray'):
        try:
            outputs[kind] = (merge_clash(configs[kind], template, blacklist) if kind == 'clash'
                             else merge_v2ray(configs[kind]))
        except ValueError as exc:
            errors.append(str(exc))
    merged_counts = {kind: len((load_proxies if kind == 'clash' else load_v2ray)(outputs.get(kind)))
                     for kind in ('clash', 'v2ray')}
    for kind, count in merged_counts.items():
        previous_count = previous_counts[kind]
        if kind in outputs and count < previous_count * min_retained_ratio:
            errors.append(f'{kind} entries dropped from {previous_count} to {count}; '
                          f'minimum retained ratio is {min_retained_ratio:g}. '
                          'Preserving both subscriptions; verify source failures or use '
                          '--min-retained-ratio 0 for an intentional reduction.')
    engine_validation = {'engine': 'mihomo', 'status': 'not_requested'}
    if mihomo is not None and 'clash' in outputs:
        try:
            validate_clash(outputs['clash'], mihomo)
            engine_validation['status'] = 'passed'
        except ValueError as exc:
            engine_validation['status'] = 'failed'
            errors.append(str(exc))
    elif mihomo is not None:
        engine_validation['status'] = 'skipped_no_config'
    published = not errors
    report = {
        'checked_at': checked, 'published': published,
        'last_successful_publication': checked if published else previous.get('last_successful_publication'),
        'connectivity_tested': False, 'errors': errors,
        'engine_validation': engine_validation,
        'merged_entries': merged_counts,
        'previous_entries': previous_counts,
        'min_retained_ratio': min_retained_ratio,
        'sources': rows,
        'disabled_sources': [
            {'id': source['id'], 'name': source['name'], 'format': kind,
             'url': feed['url'], 'reason': feed.get('notes', source.get('notes', 'Disabled in registry'))}
            for source in sources for kind, feed in source['formats'].items()
            if kind not in active_formats(source)
        ],
    }
    # Validate both formats before replacing either subscription.
    if published:
        atomic_write(output_dir / 'clash.config.yaml', outputs['clash'])
        atomic_write(output_dir / 'v2ray.config.txt', outputs['v2ray'])
        atomic_write(output_dir / '.timestamp', checked + '\n')
    atomic_write(output_dir / 'health.json', json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    atomic_write(output_dir / 'health.md', render_health(report))
    # Isolated output directories are useful for live checks without changing published files.
    if output_dir == root:
        selected = {(row['id'], row['format']): row['last_valid_url'] for row in rows if row['last_valid_url']}
        sync_links(sources, selected, root=root)
    for error in errors:
        print(f'[!] {error}')
    return 0 if published else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, help='Write outputs and reports in an isolated directory')
    parser.add_argument('--mihomo', help='Require this Mihomo executable to validate the merged Clash config before publishing either format')
    parser.add_argument('--min-retained-ratio', type=float, default=0.5, metavar='RATIO',
                        help='Retain at least this fraction of published entries (0 to 1, default: 0.5; 0 allows intentional reductions)')
    args = parser.parse_args()
    if not math.isfinite(args.min_retained_ratio) or not 0 <= args.min_retained_ratio <= 1:
        parser.error('--min-retained-ratio must be between 0 and 1')
    return run(output_dir=args.output_dir, min_retained_ratio=args.min_retained_ratio, mihomo=args.mihomo)


if __name__ == '__main__':
    raise SystemExit(main())
