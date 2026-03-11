#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import threading
import time
from typing import Any
from datetime import datetime, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = '0.0.0.0'
PORT = int(os.getenv('PORT', '4173'))
ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT_DIR / 'data' / 'aosa_dataset.json'
DB_PATH = Path(os.getenv('DB_PATH', str(ROOT_DIR / 'data' / 'app.db')))
SESSION_COOKIE = 'arcade_session'
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'join.ydsingh@gmail.com')
BOOTSTRAP_ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')

SESSIONS: dict[str, dict[str, object]] = {}
SESSIONS_LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def pbkdf2_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 120_000).hex()


def make_password_record(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    return salt, pbkdf2_hash(password, salt)


def normalize_identifier(value: str) -> str:
    return value.strip()


def normalize_admin_email(value: str) -> str:
    return value.strip().lower()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'learner')),
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS progress (
                user_id INTEGER PRIMARY KEY,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            '''
        )
        admin_email = normalize_admin_email(ADMIN_EMAIL)
        admin_row = conn.execute('SELECT * FROM users WHERE username = ?', (admin_email,)).fetchone()

        if admin_row:
            conn.execute("UPDATE users SET role = 'admin', active = 1 WHERE username = ?", (admin_email,))
        else:
            if not BOOTSTRAP_ADMIN_PASSWORD:
                raise RuntimeError('Set ADMIN_PASSWORD for the first startup so the admin account can be created.')
            salt, password_hash = make_password_record(BOOTSTRAP_ADMIN_PASSWORD)
            conn.execute(
                'INSERT INTO users (username, salt, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, 1, ?)',
                (admin_email, salt, password_hash, 'admin', utc_now()),
            )

        conn.execute("UPDATE users SET role = 'learner' WHERE role = 'admin' AND username != ?", (admin_email,))
        conn.commit()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def default_progress() -> dict:
    return {
        'completed': [],
        'bookmarked': [],
        'notes': {},
        'completionLog': {},
        'readerVisits': [],
    }


def get_progress(conn: sqlite3.Connection, user_id: int) -> dict:
    row = conn.execute('SELECT payload_json FROM progress WHERE user_id = ?', (user_id,)).fetchone()
    if not row:
        return default_progress()
    try:
        return json.loads(row['payload_json'])
    except json.JSONDecodeError:
        return default_progress()


def upsert_progress(conn: sqlite3.Connection, user_id: int, payload: dict) -> None:
    conn.execute(
        '''
        INSERT INTO progress (user_id, payload_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET payload_json = excluded.payload_json, updated_at = excluded.updated_at
        ''',
        (user_id, json.dumps(payload), utc_now()),
    )
    conn.commit()


def user_public(row: sqlite3.Row) -> dict:
    return {
        'id': row['id'],
        'username': row['username'],
        'role': row['role'],
        'active': bool(row['active']),
        'created_at': row['created_at'],
    }


def verify_user(conn: sqlite3.Connection, username: str, password: str) -> sqlite3.Row | None:
    identifier = normalize_identifier(username)
    candidates = [identifier]
    if '@' in identifier:
        candidates = [normalize_admin_email(identifier)]
    row = None
    for candidate in candidates:
        row = conn.execute('SELECT * FROM users WHERE username = ?', (candidate,)).fetchone()
        if row:
            break
    if not row or not row['active']:
        return None
    if pbkdf2_hash(password, row['salt']) != row['password_hash']:
        return None
    return row


class ArcadeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == '/api/bootstrap':
            return self.handle_bootstrap()
        if parsed.path == '/api/me':
            return self.handle_me()
        if parsed.path == '/api/admin/users':
            return self.handle_admin_users()
        if parsed.path.startswith('/content/'):
            user = self.require_user()
            if not user:
                return
            return super().do_GET()
        if parsed.path in {'/', '/index.html', '/styles.css', '/app.js'}:
            if parsed.path == '/':
                self.path = '/index.html'
            return super().do_GET()
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == '/api/login':
            return self.handle_login()
        if parsed.path == '/api/logout':
            return self.handle_logout()
        if parsed.path == '/api/admin/users':
            return self.handle_create_user()
        if parsed.path == '/api/admin/change-password':
            return self.handle_change_password()
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == '/api/progress':
            return self.handle_save_progress()
        self.send_error(HTTPStatus.NOT_FOUND)

    def parse_json_body(self) -> dict:
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length) if length else b'{}'
        return json.loads(raw.decode('utf-8'))

    def send_json(self, status: int, payload: Any) -> None:
        encoded = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def get_session_token(self) -> str | None:
        cookie = SimpleCookie(self.headers.get('Cookie'))
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else None

    def current_user(self) -> sqlite3.Row | None:
        token = self.get_session_token()
        if not token:
            return None
        with SESSIONS_LOCK:
            session = SESSIONS.get(token)
        if not session:
            return None
        with db() as conn:
            return conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    def require_user(self) -> sqlite3.Row | None:
        user = self.current_user()
        if not user:
            self.send_json(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})
            return None
        return user

    def require_admin(self) -> sqlite3.Row | None:
        user = self.require_user()
        if not user:
            return None
        if user['role'] != 'admin':
            self.send_json(HTTPStatus.FORBIDDEN, {'error': 'Admin access required'})
            return None
        return user

    def set_session(self, user_id: int) -> None:
        token = secrets.token_urlsafe(32)
        with SESSIONS_LOCK:
            SESSIONS[token] = {'user_id': user_id, 'created_at': time.time()}
        self.send_header('Set-Cookie', f'{SESSION_COOKIE}={token}; HttpOnly; Path=/; SameSite=Lax')

    def clear_session(self) -> None:
        token = self.get_session_token()
        if token:
            with SESSIONS_LOCK:
                SESSIONS.pop(token, None)
        self.send_header('Set-Cookie', f'{SESSION_COOKIE}=; HttpOnly; Path=/; Max-Age=0; SameSite=Lax')

    def handle_bootstrap(self) -> None:
        user = self.current_user()
        if not user:
            self.send_json(HTTPStatus.UNAUTHORIZED, {'error': 'Authentication required'})
            return
        dataset = json.loads(DATASET_PATH.read_text(encoding='utf-8'))
        with db() as conn:
            progress = get_progress(conn, user['id'])
        self.send_json(
            HTTPStatus.OK,
            {
                'user': user_public(user),
                'dataset': dataset,
                'progress': progress,
            },
        )

    def handle_me(self) -> None:
        user = self.require_user()
        if not user:
            return
        self.send_json(HTTPStatus.OK, user_public(user))

    def handle_login(self) -> None:
        try:
            payload = self.parse_json_body()
        except json.JSONDecodeError:
            self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'Invalid JSON'})
            return

        username = normalize_identifier(str(payload.get('username', '')))
        password = str(payload.get('password', ''))
        if not username or not password:
            self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'Username and password are required'})
            return

        with db() as conn:
            user = verify_user(conn, username, password)
            if not user:
                self.send_json(HTTPStatus.UNAUTHORIZED, {'error': 'Invalid credentials'})
                return
            dataset = json.loads(DATASET_PATH.read_text(encoding='utf-8'))
            progress = get_progress(conn, user['id'])

        payload_out = json.dumps({
            'user': user_public(user),
            'dataset': dataset,
            'progress': progress,
        }).encode('utf-8')
        self.send_response(HTTPStatus.OK)
        self.set_session(user['id'])
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload_out)))
        self.end_headers()
        self.wfile.write(payload_out)

    def handle_logout(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.clear_session()
        self.end_headers()

    def handle_save_progress(self) -> None:
        user = self.require_user()
        if not user:
            return
        try:
            payload = self.parse_json_body()
        except json.JSONDecodeError:
            self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'Invalid JSON'})
            return

        with db() as conn:
            upsert_progress(conn, user['id'], payload)
        self.send_json(HTTPStatus.OK, {'ok': True})

    def handle_admin_users(self) -> None:
        if not self.require_admin():
            return
        with db() as conn:
            users = conn.execute('SELECT id, username, role, active, created_at FROM users ORDER BY created_at ASC').fetchall()
        self.send_json(HTTPStatus.OK, [user_public(user) for user in users])

    def handle_create_user(self) -> None:
        if not self.require_admin():
            return
        try:
            payload = self.parse_json_body()
        except json.JSONDecodeError:
            self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'Invalid JSON'})
            return

        username = normalize_identifier(str(payload.get('username', '')))
        password = str(payload.get('password', ''))
        if not username or not password:
            self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'Username and password are required'})
            return
        if normalize_admin_email(username) == normalize_admin_email(ADMIN_EMAIL):
            self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'This email is reserved for the admin account'})
            return
        if '@' in username:
            self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'Learner accounts should use a username, not an email address'})
            return

        salt, password_hash = make_password_record(password)
        try:
            with db() as conn:
                conn.execute(
                    'INSERT INTO users (username, salt, password_hash, role, active, created_at) VALUES (?, ?, ?, ?, 1, ?)',
                    (username, salt, password_hash, 'learner', utc_now()),
                )
                conn.commit()
        except sqlite3.IntegrityError:
            self.send_json(HTTPStatus.CONFLICT, {'error': 'Username already exists'})
            return

        self.send_json(HTTPStatus.CREATED, {'ok': True})

    def handle_change_password(self) -> None:
        user = self.require_admin()
        if not user:
            return
        try:
            payload = self.parse_json_body()
        except json.JSONDecodeError:
            self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'Invalid JSON'})
            return

        current_password = str(payload.get('current_password', ''))
        new_password = str(payload.get('new_password', ''))
        if not current_password or not new_password:
            self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'Current and new password are required'})
            return
        if len(new_password) < 8:
            self.send_json(HTTPStatus.BAD_REQUEST, {'error': 'New password must be at least 8 characters'})
            return

        with db() as conn:
            fresh_user = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
            if not fresh_user or pbkdf2_hash(current_password, fresh_user['salt']) != fresh_user['password_hash']:
                self.send_json(HTTPStatus.UNAUTHORIZED, {'error': 'Current password is incorrect'})
                return
            salt, password_hash = make_password_record(new_password)
            conn.execute(
                'UPDATE users SET salt = ?, password_hash = ? WHERE id = ?',
                (salt, password_hash, user['id']),
            )
            conn.commit()
        self.send_json(HTTPStatus.OK, {'ok': True})


def main() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), ArcadeHandler)
    print(f'Serving {ROOT_DIR} on http://{HOST}:{PORT}')
    print(f'Admin account: {normalize_admin_email(ADMIN_EMAIL)}')
    if BOOTSTRAP_ADMIN_PASSWORD:
        print('Admin password loaded from ADMIN_PASSWORD for first-run bootstrap.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
