#!/usr/bin/env python3
"""Owned loopback-only UI evaluation specimen; not a hosted application."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import sqlite3
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
SEEDS = [
    ('navigation', 'A library that keeps its place', 'https://ui.shadcn.com/docs/components/sidebar', 'Interface', 'Navigation should preserve context. Study the distinction between a persistent desktop sidebar and a focused mobile sheet.'),
    ('drafts', 'Keep the work, even when a save fails', 'https://github.com/excalidraw/excalidraw', 'Interaction', 'Local recovery and a completed server save are different promises. Make both states legible.'),
    ('collections', 'Collections give references a home', 'https://github.com/linkwarden/linkwarden', 'Interface', 'One collection per reference; retrieval should also search the reason it was collected.'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True, help='Private task-owned SQLite path')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--save-delay', type=float, default=0, help='Evaluation-only injected delay, 0..5 seconds')
    parser.add_argument('--fail-first-save', action='store_true', help='Evaluation-only first request failure before mutation')
    args = parser.parse_args()
    if not 0 <= args.save_delay <= 5:
        parser.error('delay must be 0..5 seconds')
    db = args.database.absolute()
    if db.is_symlink():
        parser.error('database may not be a symlink')
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, title TEXT, url TEXT, collection TEXT, notes TEXT, revision INTEGER NOT NULL)')
        connection.executemany('INSERT OR IGNORE INTO items VALUES (?,?,?,?,?,1)', SEEDS)
    lock = threading.Lock()
    faults = [args.fail_first_save]

    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, payload, kind='application/json'):
            data = json.dumps(payload).encode() if kind == 'application/json' else payload
            self.send_response(code)
            self.send_header('Content-Type', kind + ('; charset=utf-8' if kind.startswith('text/') or kind == 'application/json' else ''))
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/api/items':
                with sqlite3.connect(db) as connection:
                    connection.row_factory = sqlite3.Row
                    items = [dict(row) for row in connection.execute('SELECT * FROM items ORDER BY rowid')]
                self.reply(200, {'items': items})
            elif path in {'/', '/app.js', '/style.css'}:
                filename = 'index.html' if path == '/' else path[1:]
                kind = {'index.html': 'text/html', 'app.js': 'text/javascript', 'style.css': 'text/css'}[filename]
                self.reply(200, (ROOT / filename).read_bytes(), kind)
            elif path == '/design/component-study.html':
                self.reply(200, (ROOT / 'design/component-study.html').read_bytes(), 'text/html')
            elif path in {'/design/fonts/Geist-variable.ttf', '/design/fonts/Fraunces-variable.ttf'}:
                self.reply(200, (ROOT / path[1:]).read_bytes(), 'font/ttf')
            elif path == '/design/icons/hugeicons.js':
                self.reply(200, (ROOT / 'design/icons/hugeicons.js').read_bytes(), 'text/javascript')
            else:
                self.reply(404, {'error': 'Not found'})

        def do_POST(self):
            # No cross-origin mutation. This is a private local specimen, with no auth claim.
            origin = self.headers.get('Origin')
            if origin and origin != f'http://127.0.0.1:{args.port}':
                return self.reply(403, {'error': 'Origin not permitted'})
            if self.path != '/api/items':
                return self.reply(404, {'error': 'Not found'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 65536:
                    raise ValueError('Request outside size bound')
                data = json.loads(self.rfile.read(size))
                if set(data) != {'id', 'title', 'url', 'collection', 'notes', 'revision'}:
                    raise ValueError('Incomplete reference')
                if not all(isinstance(data[k], str) for k in ('id', 'title', 'url', 'collection', 'notes')):
                    raise ValueError('Reference fields must be text')
                if not re.fullmatch(r'[a-zA-Z0-9-]{1,64}', data['id']):
                    raise ValueError('Invalid reference identity')
                if not data['title'].strip() or len(data['title']) > 240:
                    raise ValueError('Title is required, up to 240 characters')
                url = urlsplit(data['url'])
                if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or len(data['url']) > 2048:
                    raise ValueError('Use a complete HTTP or HTTPS URL without credentials')
                if data['collection'] not in ('Interface', 'Interaction', 'Research') or len(data['notes']) > 20000:
                    raise ValueError('Invalid collection or oversized notes')
                if type(data['revision']) is not int or data['revision'] < 0:
                    raise ValueError('Invalid revision')
            except (ValueError, TypeError, KeyError) as exc:
                return self.reply(400, {'error': str(exc)})
            time.sleep(args.save_delay)
            with lock:
                if faults[0]:
                    faults[0] = False
                    return self.reply(503, {'error': 'Save unavailable. Your draft has been kept; try again.'})
            with sqlite3.connect(db) as connection:
                connection.execute('BEGIN IMMEDIATE')
                row = connection.execute('SELECT revision FROM items WHERE id=?', (data['id'],)).fetchone()
                actual = row[0] if row else 0
                if actual != data['revision']:
                    return self.reply(409, {'error': 'This reference changed elsewhere. Your draft is kept; reload and review before saving.'})
                data['revision'] = actual + 1
                connection.execute('INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?)', tuple(data[k] for k in ('id','title','url','collection','notes','revision')))
            self.reply(200, {'item': data})

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Owned specimen: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
