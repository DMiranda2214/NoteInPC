"""Lectura de cuadernos NoteIn (.dbfile / .folders) sincronizados desde Drive.

Cada archivo es un ZIP:
  - cuaderno: note_meta.json + base SQLite (Room) + PDF opcional
  - carpeta:  folder_<titulo> (JSON) + folder_tn_<id> (miniatura opcional)
Solo lectura: nunca se modifica el original; se descomprime en una cache.
"""
import glob
import json
import os
import sqlite3
import struct
import subprocess
import threading
import zipfile

_lock = threading.Lock()
_index_cache = {}      # ruta -> (firma, item)
_note_cache = {}       # id -> Note


# ---------- protobuf minimo (campos planos) ----------

def _varint(b, i):
    s = v = 0
    while True:
        x = b[i]
        i += 1
        v |= (x & 0x7F) << s
        s += 7
        if x < 0x80:
            return v, i


def decode_pb(b):
    """Mensaje protobuf -> {campo: valor} (se queda con la primera aparicion)."""
    i, out = 0, {}
    while i < len(b):
        k, i = _varint(b, i)
        f, w = k >> 3, k & 7
        if w == 0:
            v, i = _varint(b, i)
        elif w == 1:
            v = struct.unpack('<d', b[i:i + 8])[0]
            i += 8
        elif w == 5:
            v = struct.unpack('<f', b[i:i + 4])[0]
            i += 4
        elif w == 2:
            n, i = _varint(b, i)
            v = b[i:i + n]
            i += n
        else:
            raise ValueError('wire type %d' % w)
        out.setdefault(f, v)
    return out


def _floats(b):
    return struct.unpack('<%df' % (len(b) // 4), b)


def css_color(argb):
    argb &= 0xFFFFFFFF
    a, r, g, b = (argb >> 24) & 255, (argb >> 16) & 255, (argb >> 8) & 255, argb & 255
    if a == 255:
        return '#%02x%02x%02x' % (r, g, b)
    return 'rgba(%d,%d,%d,%.3f)' % (r, g, b, a / 255)


# ---------- indice de carpetas y cuadernos ----------

def _read_item(path):
    st = os.stat(path)
    sig = (st.st_mtime_ns, st.st_size)
    hit = _index_cache.get(path)
    if hit and hit[0] == sig:
        return hit[1]
    item = None
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            if 'note_meta.json' in names:
                m = json.loads(z.read('note_meta.json'))
                item = dict(kind='note', id=m['id'], title=m.get('title', '').strip() or 'Sin titulo',
                            parent=m.get('parentId'), pages=m.get('totalPagesCount', 0),
                            modified=m.get('lastModificationTime', 0), trashed=m.get('inTrashBin', False),
                            favorite=m.get('favorite', False), locked=m.get('lockAdded', False))
            else:
                fn = [n for n in names if n.startswith('folder_') and n != 'folder_labels.json'
                      and not n.startswith('folder_tn_')]
                if fn:
                    m = json.loads(z.read(fn[0]))
                    thumb = [n for n in names if n.startswith('folder_tn_')]
                    item = dict(kind='folder', id=m['id'], title=m.get('title', '').strip() or 'Carpeta',
                                parent=m.get('parentId'), modified=m.get('lastModificationTime', 0),
                                trashed=m.get('inTrashBin', False), color=css_color(m.get('coverColor', -1)),
                                has_thumb=bool(thumb))
    except (zipfile.BadZipFile, KeyError, ValueError):
        item = None
    if item:
        item['path'] = path
    _index_cache[path] = (sig, item)
    return item


def scan(data_dir):
    """Devuelve {id: item} de todo lo que haya en data_dir."""
    items = {}
    for p in sorted(glob.glob(os.path.join(data_dir, '*'))):
        if os.path.isfile(p):
            it = _read_item(p)
            if it:
                items[it['id']] = it
    return items


def tree(data_dir):
    items = scan(data_dir)
    kids = {}
    for it in items.values():
        if it['trashed']:
            continue
        parent = it['parent'] if it['parent'] in items else None
        kids.setdefault(parent, []).append(it)

    def build(parent):
        out = []
        for it in sorted(kids.get(parent, []), key=lambda x: (x['kind'] != 'folder', x['title'].lower())):
            n = {k: it[k] for k in it if k not in ('path', 'parent')}
            if it['kind'] == 'folder':
                n['children'] = build(it['id'])
            out.append(n)
        return out
    return build(None)


def folder_thumb(data_dir, folder_id):
    it = scan(data_dir).get(folder_id)
    if not it or it['kind'] != 'folder' or not it.get('has_thumb'):
        return None
    with zipfile.ZipFile(it['path']) as z:
        for n in z.namelist():
            if n.startswith('folder_tn_'):
                return z.read(n)
    return None


# ---------- cuaderno abierto ----------

class Note:
    def __init__(self, item, cache_dir):
        self.item = item
        sig = os.stat(item['path']).st_mtime_ns
        self.dir = os.path.join(cache_dir, '%s_%d' % (item['id'], sig))
        if not os.path.isdir(self.dir):
            tmp = self.dir + '.tmp'
            os.makedirs(tmp, exist_ok=True)
            with zipfile.ZipFile(item['path']) as z:
                for n in z.namelist():
                    if '/' in n or '\\' in n or n.startswith('.'):
                        continue                      # evita rutas raras dentro del ZIP
                    with z.open(n) as src, open(os.path.join(tmp, n), 'wb') as dst:
                        while True:
                            chunk = src.read(1 << 20)
                            if not chunk:
                                break
                            dst.write(chunk)
            os.rename(tmp, self.dir)
        dbs = glob.glob(os.path.join(self.dir, '*_db'))
        self.db_path = dbs[0]
        pdfs = glob.glob(os.path.join(self.dir, '*.pdf'))
        self.pdf = pdfs[0] if pdfs else None
        db = self.connect()
        self.page_ids = json.loads(db.execute('select page_list from NoteContentEntity').fetchone()[0] or '[]')
        self.hidden_layers = {r[0] for r in db.execute('select id from PageLayerEntity where visible=0')}
        self.pages = []
        for pid in self.page_ids:
            spec, theme = db.execute('select paper_spec, paper_theme from PageEntity where id=?', (pid,)).fetchone()
            spec = json.loads(spec or '{}')
            theme = json.loads(theme or '{}')
            self.pages.append(dict(
                w=spec.get('width', 1240), h=spec.get('height', 1754),
                pdf=(theme.get('pageNum') if 'PdfPaperTheme' in theme.get('type', '') else None)))
        db.close()

    def connect(self):
        return sqlite3.connect(self.db_path)

    def summary(self):
        return dict(id=self.item['id'], title=self.item['title'], pdf=bool(self.pdf), pages=self.pages)

    # ----- una pagina -----
    def page(self, idx):
        pid = self.page_ids[idx]
        db = self.connect()
        try:
            spec, theme = db.execute('select paper_spec, paper_theme from PageEntity where id=?', (pid,)).fetchone()
            theme = json.loads(theme or '{}')
            paper = self._paper(theme)
            elems, errors = [], 0

            for ct, lay, blob, l, t, r, b in db.execute(
                    'select creation_time, layer_id, ink_stroke_blob, left, top, right, bottom '
                    'from StrokeEntity where page_id=?', (pid,)):
                if lay in self.hidden_layers or not blob:
                    continue
                try:
                    s = self._stroke(blob, (l, t, r, b))
                except Exception:
                    errors += 1
                    continue
                s['z'] = ct
                elems.append(s)

            for ct, lay, pts, color, width, ty in db.execute(
                    'select creation_time, layer_id, points, color, width, type from ShapeEntity where page_id=?', (pid,)):
                if lay in self.hidden_layers:
                    continue
                p = [(round(q['x'], 1), round(q['y'], 1)) for q in json.loads(pts)]
                elems.append(dict(k='l', z=ct, c=css_color(color), w=round(width, 2), p=p, closed=ty in (6, 8)))

            for ct, lay, text, size, bw, color, l, t, r, b in db.execute(
                    'select creation_time, layer_id, text, text_size, box_width, default_text_color, '
                    'left, top, right, bottom from TextBoxEntity where page_id=?', (pid,)):
                if lay in self.hidden_layers:
                    continue
                elems.append(dict(k='t', z=ct, html=text, size=size, c=css_color(color),
                                  x=l, y=t, w=r - l, h=b - t))
            elems.sort(key=lambda e: e['z'])
            return dict(w=self.pages[idx]['w'], h=self.pages[idx]['h'], paper=paper,
                        pdf=self.pages[idx]['pdf'], elems=elems, errors=errors)
        finally:
            db.close()

    @staticmethod
    def _paper(theme):
        base = theme.get('baseTheme') or theme
        bg = css_color(base['color']) if 'color' in base else '#fcf9f4'
        style = theme.get('paperStyle') or {}
        kind = style.get('type', '').split('.')[-1]
        keys = ('requiredItemSpace', 'leftPadding', 'rightPadding', 'topPadding', 'bottomPadding')
        return dict(bg=bg, style=kind, **{k: style[k] for k in keys if k in style})

    @staticmethod
    def _stroke(blob, bbox):
        m = decode_pb(blob)
        p = _floats(m[10])
        xs, ys = p[0::2], p[1::2]
        rec = _floats(m[11])
        pres = rec[1::5]
        if len(pres) != len(xs):
            pres = [0.5] * len(xs)
        # Los puntos guardados llevan un desplazamiento propio por trazo; se recolocan
        # centrandolos en la caja (left, top, right, bottom) que guarda la tabla.
        l, t, r, b = bbox
        dx = (l + r) / 2 - (min(xs) + max(xs)) / 2
        dy = (t + b) / 2 - (min(ys) + max(ys)) / 2
        flat = []
        for x, y in zip(xs, ys):
            flat += [round(x + dx, 1), round(y + dy, 1)]
        color = css_color(m.get(5, 0xFF00000000000000) >> 32)
        return dict(k='s', c=color, w=round(m.get(4, 2.0), 2), p=flat,
                    q=[round(v, 2) for v in pres], brush=m.get(7, b'').decode('ascii', 'ignore'))

    # ----- fondo PDF -----
    def pdf_png(self, idx, cache_dir):
        pg = self.pages[idx]
        if not self.pdf or pg['pdf'] is None:
            return None
        out = os.path.join(self.dir, 'bg_%d' % pg['pdf'])
        if not os.path.exists(out + '.png'):
            subprocess.run(['pdftoppm', '-f', str(pg['pdf'] + 1), '-l', str(pg['pdf'] + 1), '-png', '-singlefile',
                            '-scale-to-x', str(int(pg['w'] * 2)), '-scale-to-y', str(int(pg['h'] * 2)),
                            self.pdf, out], check=True, capture_output=True, timeout=120)
        return out + '.png'


def open_note(data_dir, cache_dir, note_id):
    with _lock:
        it = scan(data_dir).get(note_id)
        if not it or it['kind'] != 'note':
            return None
        sig = os.stat(it['path']).st_mtime_ns
        hit = _note_cache.get(note_id)
        if hit and hit[0] == sig:
            return hit[1]
        os.makedirs(cache_dir, exist_ok=True)
        note = Note(it, cache_dir)
        _note_cache[note_id] = (sig, note)
        return note
