import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import requests
import yaml
from combine.combine import atomic_write, fetch_html, load_proxies, load_v2ray, merge_clash, merge_v2ray

TEMPLATE = {'proxy-groups': [{'name': 'select', 'proxies': ['DIRECT', 'xxx']}]}


def config(password='secret', name='example'):
    return yaml.safe_dump({'proxies': [{'name': name, 'type': 'ss', 'server': 'example.com',
                                       'port': '443', 'cipher': 'aes-128-gcm', 'password': password}]})


class CombineTests(unittest.TestCase):
    def test_invalid_unicode_nodes_do_not_break_publication(self):
        for bad in (config(password='bad\ud800'), config(name='bad\udfff')):
            self.assertEqual(load_proxies(bad), [])
            output = merge_clash([bad, config(name='香港')], TEMPLATE)
            output.encode('utf-8')
            self.assertEqual(len(yaml.safe_load(output)['proxies']), 1)

    def test_bad_sources_do_not_break_good_sources(self):
        result = yaml.safe_load(merge_clash([None, '<html>error</html>', '[]', 'proxies: [null]', config()], TEMPLATE))
        self.assertEqual(len(result['proxies']), 1)
        self.assertEqual(result['proxy-groups'][0]['proxies'][1], result['proxies'][0]['name'])

    def test_identity_preserves_distinct_credentials_and_stable_names(self):
        first = merge_clash([config(), config(name='renamed'), config('different')], TEMPLATE)
        second = merge_clash([config('different'), config()], TEMPLATE)
        self.assertEqual(first, second)
        self.assertEqual(len(yaml.safe_load(first)['proxies']), 2)

    def test_readable_labels_are_bounded_and_disambiguated(self):
        result = yaml.safe_load(merge_clash([config(name='香港 节点'), config('other', name='香港 节点'),
                                            config('long', name='x' * 100 + '\x00')], TEMPLATE))
        names = [proxy['name'] for proxy in result['proxies']]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(sum(name.startswith('香港 节点 [') for name in names), 2)
        self.assertTrue(all(len(name) <= 83 and '\x00' not in name for name in names))

    def test_short_id_collision_is_resolved(self):
        with patch('combine.combine.hashlib.sha256') as digest:
            digest.return_value.hexdigest.side_effect = ['a' * 64, 'a' * 16 + 'b' * 48]
            result = yaml.safe_load(merge_clash([config(), config('other')], TEMPLATE))
        names = [proxy['name'] for proxy in result['proxies']]
        self.assertEqual(len(set(names)), 2)
        self.assertTrue(any('b' * 8 in name for name in names))

    def test_blacklist_and_empty_output(self):
        with self.assertRaises(ValueError):
            merge_clash([config()], TEMPLATE, [('example.com', 443)])
        with self.assertRaises(ValueError):
            merge_v2ray([None, '<html>error</html>'])

    def test_v2ray_normalizes_encoded_and_plain_sources(self):
        plain = 'vless://00000000-0000-4000-8000-000000000001@example.com:443\ntrojan://secret@example.com:443'
        encoded = base64.b64encode(plain.encode()).decode()
        merged = merge_v2ray([encoded, plain, None])
        self.assertEqual(len(load_v2ray(merged)), 2)
        self.assertEqual(merge_v2ray([plain]), merged)

    def test_invalid_ports_and_shapes(self):
        for content in ('null', 'proxies: null', 'proxies: [{name: n, type: ss, server: x, port: true}]'):
            self.assertEqual(load_proxies(content), [])

    def test_fetch_failure(self):
        with patch('combine.download.requests.get', side_effect=requests.ConnectionError), patch('combine.download.time.sleep'):
            self.assertIsNone(fetch_html('https://example.com'))

    def test_atomic_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'output'
            path.write_text('previous')
            atomic_write(path, 'new')
            self.assertEqual(path.read_text(), 'new')
            self.assertEqual(list(Path(directory).iterdir()), [path])


if __name__ == '__main__':
    unittest.main()
