#!/usr/bin/env python3
"""Visor local de cuadernos NoteIn. Solo escucha en 127.0.0.1.

    python3 server.py [--data ../NoteInDataSync] [--port 8765]
"""
import argparse
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import notein  # noqa: E402
STATIC = os.path.join(HERE, 'static')
sync_lock = threading.Lock()
CFG = {}


class Handler(BaseHTTPRequestHandler):
    server_version = 'NoteInViewer/1.0'

    def log_message(self, fmt, *args):
        pass

    # --- utilidades ---
    def send_bytes(self, code, body, ctype, cache='no-cache'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', cache)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj, code=200):
        self.send_bytes(code, json.dumps(obj, separators=(',', ':')).encode(), 'application/json; charset=utf-8')

    def host_ok(self):
        # Defensa contra DNS rebinding: solo se acepta el host local.
        return (self.headers.get('Host') or '').split(':')[0] in ('127.0.0.1', 'localhost')

    # --- rutas ---
    def do_GET(self):
        if not self.host_ok():
            return self.send_json({'error': 'host'}, 403)
        path = unquote(urlparse(self.path).path)
        try:
            if path == '/api/tree':
                return self.send_json(notein.tree(CFG['data']))
            m = re.fullmatch(r'/api/note/([0-9a-f-]{36})', path)
            if m:
                note = notein.open_note(CFG['data'], CFG['cache'], m.group(1))
                return self.send_json(note.summary()) if note else self.send_json({'error': 'no existe'}, 404)
            m = re.fullmatch(r'/api/note/([0-9a-f-]{36})/page/(\d+)', path)
            if m:
                note = notein.open_note(CFG['data'], CFG['cache'], m.group(1))
                i = int(m.group(2))
                if not note or i >= len(note.pages):
                    return self.send_json({'error': 'no existe'}, 404)
                return self.send_json(note.page(i))
            m = re.fullmatch(r'/api/note/([0-9a-f-]{36})/bg/(\d+)\.png', path)
            if m:
                note = notein.open_note(CFG['data'], CFG['cache'], m.group(1))
                i = int(m.group(2))
                png = note.pdf_png(i, CFG['cache']) if note and i < len(note.pages) else None
                if not png:
                    return self.send_json({'error': 'sin fondo'}, 404)
                with open(png, 'rb') as f:
                    return self.send_bytes(200, f.read(), 'image/png', 'max-age=86400')
            m = re.fullmatch(r'/api/folder/([0-9a-f-]{36})/thumb', path)
            if m:
                data = notein.folder_thumb(CFG['data'], m.group(1))
                if not data:
                    return self.send_json({'error': 'sin miniatura'}, 404)
                ctype = 'image/png' if data[:4] == b'\x89PNG' else 'image/jpeg'
                return self.send_bytes(200, data, ctype, 'max-age=3600')
            return self.static(path)
        except Exception as e:  # noqa: BLE001 - devolver el error al cliente en vez de cortar la conexion
            return self.send_json({'error': '%s: %s' % (type(e).__name__, e)}, 500)

    def do_POST(self):
        if not self.host_ok() or self.headers.get('X-NoteIn') != '1':
            return self.send_json({'error': 'prohibido'}, 403)
        if urlparse(self.path).path != '/api/sync':
            return self.send_json({'error': 'no existe'}, 404)
        rclone = shutil.which('rclone')
        if not rclone:
            return self.send_json({'ok': False, 'log': 'rclone no esta instalado'})
        if not sync_lock.acquire(blocking=False):
            return self.send_json({'ok': False, 'log': 'Ya hay una sincronizacion en curso'})
        try:
            r = subprocess.run([rclone, 'sync', CFG['remote'], CFG['data']], capture_output=True, text=True, timeout=900)
            log = (r.stdout + r.stderr).strip()[-2000:]
            return self.send_json({'ok': r.returncode == 0, 'log': log or 'Sincronizado'})
        except subprocess.TimeoutExpired:
            return self.send_json({'ok': False, 'log': 'Tiempo agotado'})
        finally:
            sync_lock.release()

    def static(self, path):
        if path in ('', '/'):
            path = '/index.html'
        full = os.path.normpath(os.path.join(STATIC, path.lstrip('/')))
        if not full.startswith(STATIC + os.sep) or not os.path.isfile(full):
            return self.send_json({'error': 'no existe'}, 404)
        with open(full, 'rb') as f:
            body = f.read()
        ctype = mimetypes.guess_type(full)[0] or 'application/octet-stream'
        if ctype.startswith('text/') or ctype in ('application/javascript', 'application/json'):
            ctype += '; charset=utf-8'
        return self.send_bytes(200, body, ctype)


def main():
    env = os.environ.get
    ap = argparse.ArgumentParser(description='Visor local de cuadernos NoteIn (solo lectura).')
    ap.add_argument('--data', default=env('NOTEIN_DATA', os.path.join(HERE, '..', 'NoteInDataSync')),
                    help='carpeta con los archivos sincronizados [NOTEIN_DATA]')
    ap.add_argument('--port', type=int, default=int(env('NOTEIN_PORT', '8765')),
                    help='puerto en 127.0.0.1 [NOTEIN_PORT]')
    ap.add_argument('--remote', default=env('NOTEIN_REMOTE', 'gdrive:NoteInDataSync'),
                    help='origen de rclone para el boton Sincronizar [NOTEIN_REMOTE]')
    ap.add_argument('--cache', default=env('NOTEIN_CACHE', os.path.expanduser('~/.cache/notein-viewer')),
                    help='cache de cuadernos descomprimidos [NOTEIN_CACHE]')
    a = ap.parse_args()
    CFG.update(data=os.path.abspath(a.data), cache=a.cache, remote=a.remote)
    srv = ThreadingHTTPServer(('127.0.0.1', a.port), Handler)
    print('Visor NoteIn en http://127.0.0.1:%d  (datos: %s)' % (a.port, CFG['data']))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
