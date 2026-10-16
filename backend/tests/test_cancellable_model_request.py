import json
import multiprocessing
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.utils.cancellable_model_request import ModelRequestCancelled
from app.utils.vision_llm_client import VisionLlmClient


class CancellableModelRequestTest(unittest.TestCase):
    def setUp(self):
        self.received = threading.Event()
        self.release = threading.Event()
        test = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                test.received.set()
                test.release.wait(8)
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'choices': [{'message': {'content': '{"features": []}'}}]}).encode())
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.client = VisionLlmClient(base_url=f'http://127.0.0.1:{self.server.server_port}', api_key='synthetic', model='fixture', timeout_sec=None)

    def tearDown(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()

    def test_unlimited_request_returns_valid_response(self):
        threading.Timer(.6, self.release.set).start()
        self.assertEqual(self.client.complete_json('system', 'prompt', []), {'features': []})
        self.assertTrue(self.received.is_set())
        self.assertEqual(self.client.requests_made, 1)

    def test_cancel_blocked_io_terminates_request_worker(self):
        children = {p.pid for p in multiprocessing.active_children()}
        self.client.cancel_check = self.received.is_set
        started = time.monotonic()
        with self.assertRaises(ModelRequestCancelled):
            self.client.complete_json('system', 'prompt', [])
        self.assertLess(time.monotonic() - started, 4)
        self.assertEqual({p.pid for p in multiprocessing.active_children()}, children)

    def test_cancelled_before_start_does_not_call_provider(self):
        self.client.cancel_check = lambda: True
        with self.assertRaises(ModelRequestCancelled):
            self.client.complete_json('system', 'prompt', [])
        self.assertEqual(self.client.requests_made, 0)
