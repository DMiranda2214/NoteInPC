"""Pruebas con datos sinteticos (no usan cuadernos personales).

    python3 -I -m unittest discover -s tests -v
"""
import json
import os
import struct
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'visor'))
import notein  # noqa: E402


def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def pb_bytes(field, data):
    return varint(field << 3 | 2) + varint(len(data)) + data


def pb_varint(field, n):
    return varint(field << 3) + varint(n)


def pb_float(field, x):
    return varint(field << 3 | 5) + struct.pack('<f', x)


def make_stroke(points, pressure, size=2.0, color=0xFF00000000000000):
    flat = struct.pack('<%df' % (2 * len(points)), *[v for p in points for v in p])
    rec = struct.pack('<%df' % (5 * len(points)), *[v for q in pressure for v in (0.0, q, 0.0, 1.57, 0.02)])
    return (pb_bytes(1, b'id') + pb_bytes(2, b'default') + pb_float(4, size) + pb_varint(5, color)
            + pb_bytes(7, b'notein-fountain-v2') + pb_bytes(10, flat) + pb_bytes(11, rec))


class ProtobufTests(unittest.TestCase):
    def test_decode_basic_fields(self):
        m = notein.decode_pb(pb_bytes(1, b'hola') + pb_varint(3, 300) + pb_float(4, 1.5))
        self.assertEqual(m[1], b'hola')
        self.assertEqual(m[3], 300)
        self.assertAlmostEqual(m[4], 1.5)

    def test_unknown_wire_type_raises(self):
        with self.assertRaises(ValueError):
            notein.decode_pb(varint(1 << 3 | 3))

    def test_css_color(self):
        self.assertEqual(notein.css_color(0xFFE02020), '#e02020')
        self.assertEqual(notein.css_color(-16777216), '#000000')
        self.assertTrue(notein.css_color(0x80FF0000).startswith('rgba(255,0,0,'))


class StrokeTests(unittest.TestCase):
    def test_stroke_is_recentered_on_bbox(self):
        pts = [(100.0, 200.0), (110.0, 210.0), (120.0, 200.0)]
        bbox = (10.0, 20.0, 30.0, 40.0)               # centro (20, 30)
        s = notein.Note._stroke(make_stroke(pts, [0.2, 0.5, 0.8]), bbox)
        xs, ys = s['p'][0::2], s['p'][1::2]
        self.assertAlmostEqual((min(xs) + max(xs)) / 2, 20.0, places=1)
        self.assertAlmostEqual((min(ys) + max(ys)) / 2, 30.0, places=1)
        self.assertEqual(s['c'], '#000000')
        self.assertEqual(s['q'], [0.2, 0.5, 0.8])
        self.assertEqual(s['brush'], 'notein-fountain-v2')

    def test_missing_pressure_defaults(self):
        blob = (pb_bytes(10, struct.pack('<4f', 1, 2, 3, 4)) + pb_bytes(11, b''))
        s = notein.Note._stroke(blob, (0, 0, 4, 4))
        self.assertEqual(s['q'], [0.5, 0.5])


class IndexTests(unittest.TestCase):
    def test_tree_nests_notes_in_folders_and_hides_trash(self):
        with tempfile.TemporaryDirectory() as d:
            def put(name, member, payload):
                with zipfile.ZipFile(os.path.join(d, name), 'w') as z:
                    z.writestr(member, json.dumps(payload))
                    z.writestr('folder_labels.json', '[]')
            put('f1', 'folder_Materias', dict(id='f1', title='Materias', coverColor=-1))
            put('n1', 'note_meta.json', dict(id='n1', title='Fisica', parentId='f1', totalPagesCount=3))
            put('n2', 'note_meta.json', dict(id='n2', title='Borrado', parentId='f1', inTrashBin=True))
            put('n3', 'note_meta.json', dict(id='n3', title='Suelto'))
            with open(os.path.join(d, 'basura.txt'), 'w') as f:
                f.write('no es un zip')
            t = notein.tree(d)
            self.assertEqual([n['title'] for n in t], ['Materias', 'Suelto'])
            self.assertEqual([c['title'] for c in t[0]['children']], ['Fisica'])
            self.assertEqual(t[0]['children'][0]['pages'], 3)
            self.assertNotIn('path', t[0])            # no se filtran rutas locales al cliente


if __name__ == '__main__':
    unittest.main()
