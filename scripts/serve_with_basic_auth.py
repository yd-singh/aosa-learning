#!/usr/bin/env python3
from __future__ import annotations

import base64
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = '0.0.0.0'
PORT = 4173
USERNAME = 'techpm'
PASSWORD = 'p@sswordTechPm'
ROOT_DIR = Path(__file__).resolve().parent.parent
REALM = 'Architecture Arcade'

EXPECTED_TOKEN = base64.b64encode(f'{USERNAME}:{PASSWORD}'.encode('utf-8')).decode('ascii')


class BasicAuthHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def do_AUTHHEAD(self) -> None:
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header('WWW-Authenticate', f'Basic realm="{REALM}"')
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()

    def _is_authorized(self) -> bool:
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Basic '):
            return False
        provided = auth_header.split(' ', 1)[1].strip()
        return provided == EXPECTED_TOKEN

    def _require_auth(self) -> bool:
        if self._is_authorized():
            return True
        self.do_AUTHHEAD()
        self.wfile.write(b'Authentication required.\n')
        return False

    def do_GET(self) -> None:  # noqa: N802
        if not self._require_auth():
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        if not self._require_auth():
            return
        super().do_HEAD()


if __name__ == '__main__':
    server = ThreadingHTTPServer((HOST, PORT), BasicAuthHandler)
    print(f'Serving {ROOT_DIR} on http://{HOST}:{PORT} with HTTP Basic Auth')
    print(f'Username: {USERNAME}')
    print('Password: p@sswordTechPm')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
