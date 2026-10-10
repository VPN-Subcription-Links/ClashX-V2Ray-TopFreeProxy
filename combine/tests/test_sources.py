from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

from combine.refresh import resolve_feed, run
from combine.sources import DOCUMENTS, END, START, load_sources, sync_links
from test_combine import TEMPLATE, config
import yaml

NOW = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
SOURCE = {'id': 'example', 'name': 'Example', 'enabled': True, 'formats': {
    'clash': {'url': 'https://example.com/old.yaml',
              'date_pattern': 'https://example.com/{year}/{month}/{date}.yaml'},
    'v2ray': {'url': 'https://example.com/nodes.txt'},
}}


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / 'combine'
        self.root.mkdir()
        (self.root / 'sources.json').write_text(json.dumps([SOURCE]))
        (self.root / 'blacklists.txt').write_text('')
        (self.root / 'clash.config.template.yaml').write_text(yaml.safe_dump(TEMPLATE))
        for name in DOCUMENTS:
            (self.root.parent / name).write_text(f'intro\n{START}\n{END}\ndisclaimer retained\n')

    def test_legacy_script_entry_point(self):
        script = Path(__file__).resolve().parents[1] / 'combine.py'
        result = subprocess.run([sys.executable, str(script), '--help'],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--output-dir', result.stdout)

    def test_registry_rejects_duplicate_ids_and_invalid_urls(self):
        for data in ([SOURCE, SOURCE], [dict(SOURCE, formats={'clash': {'url': 'http://example.com'}})],
                     [dict(SOURCE, formats={'clash': {'url': 'https://user:secret@example.com'}})]):
            path = self.root / 'sources.json'
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_sources(path)

    def test_dated_feed_skips_http_success_with_unusable_content(self):
        calls = []
        def fetch(url):
            calls.append(url)
            return '<html>error</html>' if '20261010' in url else config()
        row, content = resolve_feed(SOURCE, 'clash', {}, NOW.date(), fetch)
        self.assertTrue(content)
        self.assertIn('20261009', row['url'])
        self.assertEqual(row['attempts'][0]['status'], 'unusable')
        self.assertEqual(len(calls), 2)

    def test_fallback_to_last_valid_daily_feed(self):
        old_url = 'https://example.com/2026/09/20260901.yaml'
        previous = {('example', 'clash'): {'last_valid_url': old_url,
                                         'configured_url': SOURCE['formats']['clash']['url']}}
        row, _ = resolve_feed(SOURCE, 'clash', previous, NOW.date(),
                              lambda url: config() if url == old_url else None)
        self.assertEqual(row['url'], old_url)
        self.assertEqual(row['status'], 'parsed')
        self.assertEqual(len(row['attempts']), 4)

    def test_generated_links_are_consistent_and_preserve_other_sections(self):
        chosen = {('example', 'clash'): 'https://example.com/2026/10/20261010.yaml'}
        self.assertTrue(sync_links([SOURCE], chosen, self.root))
        self.assertFalse(sync_links([SOURCE], chosen, self.root, check=True))
        url = (self.root / 'clashsub.txt').read_text().strip()
        for name in ('README.md', 'clash中文版.md'):
            text = (self.root.parent / name).read_text()
            self.assertIn(url, text)
            self.assertTrue(text.endswith('disclaimer retained\n'))

    def test_partial_failure_preserves_both_outputs_and_timestamp(self):
        for name in ('clash.config.yaml', 'v2ray.config.txt', '.timestamp'):
            (self.root / name).write_text('previous')
        fetch = lambda url: config() if url.endswith('.yaml') else None
        self.assertEqual(run(self.root, fetch=fetch, now=NOW), 1)
        for name in ('clash.config.yaml', 'v2ray.config.txt', '.timestamp'):
            self.assertEqual((self.root / name).read_text(), 'previous')
        health = json.loads((self.root / 'health.json').read_text())
        self.assertFalse(health['published'])
        self.assertFalse(health['connectivity_tested'])
        self.assertEqual(health['sources'][1]['status'], 'fetch_failed')

    def test_success_and_later_failure_keep_last_publication(self):
        fetch = lambda url: config() if url.endswith('.yaml') else 'vless://00000000-0000-4000-8000-000000000001@example.com:443'
        self.assertEqual(run(self.root, fetch=fetch, now=NOW), 0)
        before = (self.root / 'clash.config.yaml').read_text()
        self.assertEqual(run(self.root, fetch=lambda url: None, now=NOW), 1)
        self.assertEqual((self.root / 'clash.config.yaml').read_text(), before)
        health = json.loads((self.root / 'health.json').read_text())
        self.assertEqual(health['last_successful_publication'], '2026-10-10T12:00:00Z')
        self.assertEqual(health['sources'][0]['last_successful_fetch'], '2026-10-10T12:00:00Z')

    def test_disabled_sources_are_not_generated_or_fetched(self):
        disabled = dict(SOURCE, id='disabled', name='Disabled', enabled=False)
        (self.root / 'sources.json').write_text(json.dumps([SOURCE, disabled]))
        sync_links([SOURCE, disabled], {}, self.root)
        self.assertNotIn('Disabled', (self.root.parent / 'README.md').read_text())
        calls = []
        def fetch(url):
            calls.append(url)
            return config() if url.endswith('.yaml') else 'vless://00000000-0000-4000-8000-000000000001@example.com:443'
        self.assertEqual(run(self.root, fetch=fetch, now=NOW), 0)
        self.assertEqual(len(calls), 2)
        report = json.loads((self.root / 'health.json').read_text())
        self.assertTrue(all(row['id'] != 'disabled' for row in report['sources']))

    def test_mixed_provider_skips_only_disabled_format(self):
        mixed = json.loads(json.dumps(SOURCE))
        mixed['formats']['clash']['enabled'] = False
        mixed['formats']['clash']['notes'] = 'Unusable Clash feed; V2Ray remains enabled'
        backup = {'id': 'backup', 'name': 'Backup', 'enabled': True,
                  'formats': {'clash': {'url': 'https://example.com/backup.yaml'}}}
        (self.root / 'sources.json').write_text(json.dumps([mixed, backup]))
        calls = []
        def fetch(url):
            calls.append(url)
            return config() if url.endswith('.yaml') else 'vless://00000000-0000-4000-8000-000000000001@example.com:443'
        self.assertEqual(run(self.root, fetch=fetch, now=NOW), 0)
        self.assertEqual(set(calls), {'https://example.com/backup.yaml', 'https://example.com/nodes.txt'})
        self.assertNotIn('Example:', (self.root.parent / 'README.md').read_text())
        self.assertIn('Example:', (self.root.parent / 'v2ray.md').read_text())
        report = json.loads((self.root / 'health.json').read_text())
        self.assertEqual(report['disabled_sources'][0]['format'], 'clash')
        self.assertIn('Unusable Clash feed', (self.root / 'health.md').read_text())

    def test_invalid_format_enabled_flag_is_rejected(self):
        source = json.loads(json.dumps(SOURCE))
        source['formats']['clash']['enabled'] = 'false'
        (self.root / 'sources.json').write_text(json.dumps([source]))
        with self.assertRaises(ValueError):
            load_sources(self.root / 'sources.json')

    def test_removed_links_are_archived_without_duplicates(self):
        backup = {'id': 'backup', 'name': 'Backup', 'enabled': True,
                  'formats': {'clash': {'url': 'https://example.com/backup.yaml'}}}
        path = self.root.parent / 'README.md'
        path.write_text(f'intro\n{START}\n{END}\n<!-- Archived Reference:\nhttps://example.com/legacy\n-->\ndisclaimer retained\n')
        sync_links([SOURCE, backup], {}, self.root)
        sync_links([backup], {}, self.root)
        text = path.read_text()
        active = text.split(START)[1].split(END)[0]
        archive = text.split('<!-- Archived Reference:')[1].split('-->')[0]
        self.assertNotIn('https://example.com/old.yaml', active)
        self.assertIn('https://example.com/old.yaml', archive)
        self.assertIn('https://example.com/legacy', archive)
        self.assertTrue(text.endswith('disclaimer retained\n'))
        self.assertFalse(sync_links([backup], {}, self.root, check=True))
        sync_links([backup], {}, self.root)
        self.assertEqual(path.read_text().count('https://example.com/old.yaml'), 1)

    def test_large_drop_keeps_both_outputs_and_can_be_overridden(self):
        full_clash = yaml.safe_dump({'proxies': [yaml.safe_load(config(str(index)))['proxies'][0]
                                               for index in range(4)]})
        full_v2ray = '\n'.join(f'vless://00000000-0000-4000-8000-{index:012d}@example.com:443' for index in range(4))
        def initial(url):
            return full_clash if url.endswith('.yaml') else full_v2ray
        self.assertEqual(run(self.root, fetch=initial, now=NOW), 0)
        before = {name: (self.root / name).read_text()
                  for name in ('clash.config.yaml', 'v2ray.config.txt', '.timestamp')}
        def reduced(url):
            return config() if url.endswith('.yaml') else 'vless://00000000-0000-4000-8000-000000000002@example.com:443'
        self.assertEqual(run(self.root, fetch=reduced, now=NOW), 1)
        for name, content in before.items():
            self.assertEqual((self.root / name).read_text(), content)
        report = json.loads((self.root / 'health.json').read_text())
        self.assertEqual(report['previous_entries'], {'clash': 4, 'v2ray': 4})
        self.assertEqual(report['merged_entries'], {'clash': 1, 'v2ray': 1})
        self.assertEqual(len(report['errors']), 2)
        self.assertIn('entries dropped from 4 to 1', (self.root / 'health.md').read_text())
        self.assertEqual(run(self.root, fetch=reduced, now=NOW, min_retained_ratio=0), 0)
        self.assertNotEqual((self.root / 'clash.config.yaml').read_text(), before['clash.config.yaml'])

    def test_retention_guard_uses_published_files_after_failed_attempt(self):
        full_clash = yaml.safe_dump({'proxies': [yaml.safe_load(config(str(index)))['proxies'][0]
                                               for index in range(4)]})
        full = lambda url: full_clash if url.endswith('.yaml') else 'vless://00000000-0000-4000-8000-000000000001@example.com:443'
        self.assertEqual(run(self.root, fetch=full, now=NOW), 0)
        reduced = lambda url: config() if url.endswith('.yaml') else 'vless://00000000-0000-4000-8000-000000000001@example.com:443'
        self.assertEqual(run(self.root, fetch=reduced, now=NOW), 1)
        self.assertEqual(run(self.root, fetch=reduced, now=NOW), 1)
        report = json.loads((self.root / 'health.json').read_text())
        self.assertEqual(report['previous_entries']['clash'], 4)

    def test_exactly_half_the_published_count_is_allowed(self):
        full_clash = yaml.safe_dump({'proxies': [yaml.safe_load(config(str(index)))['proxies'][0]
                                               for index in range(4)]})
        half_clash = yaml.safe_dump({'proxies': yaml.safe_load(full_clash)['proxies'][:2]})
        fetch = lambda url: full_clash if url.endswith('.yaml') else 'vless://00000000-0000-4000-8000-000000000001@example.com:443'
        self.assertEqual(run(self.root, fetch=fetch, now=NOW), 0)
        fetch = lambda url: half_clash if url.endswith('.yaml') else 'vless://00000000-0000-4000-8000-000000000001@example.com:443'
        self.assertEqual(run(self.root, fetch=fetch, now=NOW), 0)
        report = json.loads((self.root / 'health.json').read_text())
        self.assertEqual(report['merged_entries']['clash'], 2)
        self.assertEqual(report['errors'], [])

    def test_invalid_retained_ratio_is_rejected_before_fetching(self):
        for ratio in (-0.1, 1.1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                run(self.root, min_retained_ratio=ratio, fetch=lambda url: self.fail('Must not fetch'))

    def test_isolated_live_check_does_not_change_guides(self):
        output = self.root.parent / 'isolated'
        before = (self.root.parent / 'README.md').read_text()
        fetch = lambda url: config() if url.endswith('.yaml') else 'vless://00000000-0000-4000-8000-000000000001@example.com:443'
        self.assertEqual(run(self.root, output_dir=output, fetch=fetch, now=NOW), 0)
        self.assertEqual((self.root.parent / 'README.md').read_text(), before)
        self.assertFalse((self.root / 'clash.config.yaml').exists())
        self.assertTrue((output / 'health.md').exists())


if __name__ == '__main__':
    unittest.main()
