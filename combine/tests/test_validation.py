import base64
import gzip
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

from combine.combine import load_proxies, load_v2ray, merge_clash
from combine.engine import EngineValidationError, validate_clash
from combine.install_engine import install
from combine.refresh import run
from test_combine import TEMPLATE, config
import test_sources

UUID = '00000000-0000-4000-8000-000000000001'


def encoded(value):
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip('=')


class ProtocolValidationTests(unittest.TestCase):
    def test_clash_protocol_credentials_and_transport_shapes(self):
        common = {'name': 'node', 'server': 'example.com', 'port': 443}
        cases = [
            ({'type': 'ss', 'cipher': 'aes-128-gcm', 'password': 'secret'}, 'password', ''),
            ({'type': 'ss', 'cipher': 'aes-128-gcm', 'password': 'secret'}, 'cipher', 'unsupported'),
            ({'type': 'ssr', 'cipher': 'aes-128-cfb', 'password': 'secret', 'protocol': 'origin', 'obfs': 'plain'}, 'protocol', None),
            ({'type': 'vmess', 'uuid': UUID, 'cipher': 'auto'}, 'uuid', 'invalid'),
            ({'type': 'vmess', 'uuid': UUID, 'cipher': 'auto'}, 'alterId', -1),
            ({'type': 'vless', 'uuid': UUID}, 'uuid', None),
            ({'type': 'trojan', 'password': 'secret'}, 'password', 123),
            ({'type': 'anytls', 'password': 'secret'}, 'password', ''),
            ({'type': 'tuic', 'uuid': UUID, 'password': 'secret'}, 'uuid', 'invalid'),
            ({'type': 'hysteria', 'up': 10, 'down': 20}, 'up', False),
            ({'type': 'hysteria2', 'password': 'secret'}, 'password', {}),
            ({'type': 'socks5'}, 'server', 'bad host'),
            ({'type': 'vless', 'uuid': UUID}, 'ws-opts', {'headers': {'Host': ['example.com']}}),
        ]
        for fields, key, invalid in cases:
            good = dict(common, **fields)
            bad = dict(good, **{key: invalid})
            with self.subTest(protocol=fields['type'], field=key):
                self.assertEqual(len(load_proxies(yaml.safe_dump({'proxies': [good, bad]}))), 1)
                self.assertEqual(len(yaml.safe_load(merge_clash([yaml.safe_dump({'proxies': [good, bad]})], TEMPLATE))['proxies']), 1)

    def test_uri_formats_and_ipv6(self):
        vmess = 'vmess://' + encoded(json.dumps({'add': 'example.com', 'port': '443', 'id': UUID, 'aid': '0'}))
        valid = [vmess, f'vless://{UUID}@[2001:db8::1]:443?security=tls',
                 'trojan://secret@example.com:443',
                 'ss://' + encoded('aes-128-gcm:secret') + '@example.com:443#node',
                 'ss://' + encoded('aes-128-gcm:secret@127.0.0.1:443'),
                 'ss://aes-128-gcm:secret@example.com:443',
                 'ssr://' + encoded('example.com:443:origin:aes-128-cfb:plain:' + encoded('secret') + '/?remarks='),
                 'hy2://secret@example.com', 'hysteria2://secret@example.com:443',
                 'hysteria://example.com:443?upmbps=10&downmbps=20',
                 f'tuic://{UUID}:secret@example.com:443']
        self.assertEqual(load_v2ray('\n'.join(valid)), valid)
        self.assertEqual(load_v2ray(encoded('\n'.join(valid))), valid)

    def test_invalid_uri_payloads_ports_and_credentials_are_skipped(self):
        bad = ['vmess://not-base64', 'vmess://' + encoded('{}'),
               'vmess://' + encoded(json.dumps({'add': 'x', 'port': 443, 'id': 'bad'})),
               'vless://bad@example.com:443', f'vless://{UUID}@example.com:65536',
               'trojan://@example.com:443', 'trojan://secret@example.com:noport',
               'ss://broken@example.com:443', 'ss://' + encoded('aes-128-gcm:') + '@example.com:443',
               'ss://' + encoded('unsupported:secret') + '@example.com:443',
               'ss://' + encoded('2022-blake3-aes-128-gcm:short') + '@example.com:443',
               'ssr://' + encoded('wrong'), 'hy2://secret@example.com:0',
               f'tuic://{UUID}@example.com:443', 'hysteria://example.com:443?upmbps=-1&downmbps=20']
        good = f'vless://{UUID}@example.com:443'
        self.assertEqual(load_v2ray('\n'.join([good] + bad)), [good])

    def test_relaxed_baseline_counts_previously_published_invalid_entries(self):
        content = 'vless://invalid@example.com:443'
        self.assertEqual(load_v2ray(content), [])
        self.assertEqual(len(load_v2ray(content, validate_protocols=False)), 1)


class EngineTests(unittest.TestCase):
    @patch('combine.engine.shutil.which', return_value='/tmp/mihomo')
    @patch('combine.engine.subprocess.run')
    def test_engine_rejection_timeout_and_missing_binary(self, execute, which):
        execute.return_value.returncode = 1
        with self.assertRaises(EngineValidationError):
            validate_clash(config(), 'mihomo')
        execute.side_effect = subprocess.TimeoutExpired('mihomo', 90)
        with self.assertRaisesRegex(EngineValidationError, 'timed out'):
            validate_clash(config(), 'mihomo')
        which.return_value = None
        with self.assertRaisesRegex(EngineValidationError, 'not found'):
            validate_clash(config(), 'mihomo')

    def test_failed_engine_preserves_outputs_timestamp_and_reports_failure(self):
        # Reuse the temporary registry fixture, not its test methods.
        fixture = test_sources.SourceTests()
        fixture.setUp()
        try:
            for name in ('clash.config.yaml', 'v2ray.config.txt', '.timestamp'):
                (fixture.root / name).write_text('previous')
            fetch = lambda url: config() if url.endswith('.yaml') else f'vless://{UUID}@example.com:443'
            with patch('combine.refresh.validate_clash', side_effect=EngineValidationError('Engine rejected configuration')):
                self.assertEqual(run(fixture.root, fetch=fetch, mihomo='mihomo'), 1)
            for name in ('clash.config.yaml', 'v2ray.config.txt', '.timestamp'):
                self.assertEqual((fixture.root / name).read_text(), 'previous')
            report = json.loads((fixture.root / 'health.json').read_text())
            self.assertFalse(report['published'])
            self.assertEqual(report['engine_validation']['status'], 'failed')
        finally:
            fixture.doCleanups()

    @patch('combine.install_engine.platform.machine', return_value='arm64')
    @patch('combine.install_engine.platform.system', return_value='Darwin')
    @patch('combine.install_engine.requests.get')
    def test_checksum_mismatch_does_not_replace_executable(self, get, system, machine):
        get.return_value.__enter__.return_value.iter_content.return_value = [gzip.compress(b'fake')]
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'mihomo'
            destination.write_bytes(b'previous')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                install(destination)
            self.assertEqual(destination.read_bytes(), b'previous')
