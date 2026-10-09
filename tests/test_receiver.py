import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

spec = importlib.util.spec_from_file_location('receiver', Path(__file__).parents[1] / 'server-test/receiver.py')
receiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receiver)

class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), receiver.Receiver)
        self.server.token = 'test-secret'
        self.server.data_dir = Path(self.tmp.name)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, body, token='test-secret', hostname='PDA-001', path='/api/v1/agent'):
        conn = HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        conn.request('POST', path, body, {'Authorization': 'Bearer ' + token, 'X-CMK-Hostname': hostname})
        response = conn.getresponse()
        data = json.loads(response.read())
        conn.close()
        return response.status, data

    def test_authenticated_payload_and_replacement(self):
        body = b'<<<check_mk>>>\nHostname: PDA-001\n<<<local:sep(0)>>>\n0 "Test" - OK\n'
        self.assertEqual(self.request(body)[0], 200)
        self.assertEqual((self.server.data_dir / 'PDA-001.agent').read_bytes(), body)
        newer = body.replace(b'OK', b'new')
        self.assertEqual(self.request(newer)[0], 200)
        self.assertEqual((self.server.data_dir / 'PDA-001.agent').read_bytes(), newer)

    def test_reject_bad_token_without_writing(self):
        self.assertEqual(self.request(b'bad', token='wrong')[0], 401)
        self.assertEqual(list(self.server.data_dir.iterdir()), [])

    def test_validation(self):
        for body in (b'', b'bad', b'\xff'):
            self.assertEqual(self.request(body)[0], 400)
        self.assertEqual(self.request(b'x', path='/wrong')[0], 404)
        conn = HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        conn.request('POST', '/api/v1/agent', b'', {
            'Authorization': 'Bearer test-secret', 'Content-Length': str(2 * 1024 * 1024 + 1)})
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        response.read()
        conn.close()

    def test_hostname_cannot_escape_cache_dir(self):
        name = receiver.safe_hostname('../../etc/passwd')
        self.assertNotIn('/', name)
        self.assertEqual((self.server.data_dir / (name + '.agent')).parent, self.server.data_dir)

if __name__ == '__main__':
    unittest.main()
