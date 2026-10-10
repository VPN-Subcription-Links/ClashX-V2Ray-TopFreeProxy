import unittest
from unittest.mock import MagicMock, patch

import requests

from combine.download import fetch_subscription
from combine.refresh import resolve_feed
from test_sources import NOW, SOURCE


def response(status=200, chunks=None, headers=None):
    result = MagicMock()
    result.__enter__.return_value = result
    result.status_code = status
    result.headers = headers or {}
    result.iter_content.return_value = chunks if chunks is not None else [b'valid']
    return result


class DownloadTests(unittest.TestCase):
    @patch('combine.download.time.sleep')
    @patch('combine.download.requests.get')
    def test_transient_http_error_recovers(self, get, sleep):
        first, second = response(503), response(chunks=[b'\xef\xbb\xbfhello'])
        get.side_effect = [first, second]
        result = fetch_subscription('https://example.com')
        self.assertEqual(result.content, 'hello')
        self.assertEqual([row['http_status'] for row in result.requests], [503, 200])
        sleep.assert_called_once_with(1)
        self.assertEqual(first.__exit__.call_count, 1)
        self.assertEqual(second.__exit__.call_count, 1)
        self.assertTrue(get.call_args.kwargs['stream'])
        self.assertNotEqual(get.call_args.kwargs.get('verify'), False)

    @patch('combine.download.time.sleep')
    @patch('combine.download.requests.get', side_effect=requests.Timeout)
    def test_timeouts_stop_after_three_attempts(self, get, sleep):
        result = fetch_subscription('https://example.com')
        self.assertIsNone(result.content)
        self.assertEqual(result.error, 'timeout')
        self.assertEqual(get.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2])

    @patch('combine.download.requests.get')
    def test_permanent_http_error_does_not_retry(self, get):
        get.return_value = response(404)
        result = fetch_subscription('https://example.com')
        self.assertEqual(result.http_status, 404)
        self.assertEqual(result.error, 'http_404')
        self.assertEqual(get.call_count, 1)

    @patch('combine.download.requests.get', side_effect=requests.exceptions.SSLError)
    def test_certificate_error_does_not_retry(self, get):
        result = fetch_subscription('https://example.com')
        self.assertEqual(result.error, 'tls_error')
        self.assertEqual(get.call_count, 1)

    @patch('combine.download.requests.get')
    def test_streamed_size_limit_without_content_length(self, get):
        get.return_value = response(chunks=[b'123', b'456'])
        result = fetch_subscription('https://example.com', max_bytes=5)
        self.assertIsNone(result.content)
        self.assertEqual(result.error, 'response_too_large')
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.return_value.__exit__.call_count, 1)

    @patch('combine.download.requests.get')
    def test_declared_oversized_response_is_not_read(self, get):
        get.return_value = response(headers={'Content-Length': '6'})
        result = fetch_subscription('https://example.com', max_bytes=5)
        self.assertEqual(result.error, 'response_too_large')
        get.return_value.iter_content.assert_not_called()

    @patch('combine.download.requests.get')
    def test_invalid_utf8_is_not_retried(self, get):
        get.return_value = response(chunks=[b'\xff'])
        result = fetch_subscription('https://example.com')
        self.assertEqual(result.error, 'invalid_utf8')
        self.assertEqual(result.http_status, 200)
        self.assertEqual(get.call_count, 1)

    @patch('combine.download.requests.get')
    def test_diagnostics_reach_source_report_without_content(self, get):
        get.return_value = response(404)
        row, content = resolve_feed(SOURCE, 'v2ray', {}, NOW.date())
        self.assertIsNone(content)
        self.assertEqual(row['status'], 'fetch_failed')
        self.assertEqual(row['attempts'][0]['http_status'], 404)
        self.assertEqual(row['attempts'][0]['error'], 'http_404')
        self.assertNotIn('content', row['attempts'][0])
        self.assertEqual(len(row['attempts'][0]['requests']), 1)


if __name__ == '__main__':
    unittest.main()
