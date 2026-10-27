# Formato de archivos de NoteIn (deducido)

Descripción obtenida por observación de archivos propios; no es documentación oficial y puede
cambiar. Sirve para mantener el lector (`visor/notein.py`).

## Contenedor

Cada archivo de `NoteInDataSync` es un **ZIP**. Los tipos MIME en Drive son:

- `application/vnd.notein-apps.dbfile`: un cuaderno.
- `application/vnd.notein-apps.folders`: una carpeta.

El nombre es `Título_<uuid>`; el título real está en los metadatos.

### Carpeta

| Entrada | Contenido |
|---|---|
| `folder_<título>` | JSON: `id`, `title`, `parentId`, `coverColor` (ARGB con signo), fechas, `inTrashBin` |
| `folder_labels.json` | Etiquetas |
| `folder_tn_<id>` | Miniatura (opcional) |

### Cuaderno

| Entrada | Contenido |
|---|---|
| `note_meta.json` | `id`, `title`, `parentId` (carpeta), `totalPagesCount`, fechas, `inTrashBin` |
| `note_database_note_<id>_db` (+ `-wal`, `-shm`) | Base SQLite (Room de Android) en modo WAL |
| `note_pdf_*.pdf` | PDF original, si el cuaderno anota un PDF |
| `note_label.json`, `note_extra.json`, `note_in_flag.json`, `notepdf_lost_info.json` | Auxiliares |

La jerarquía se reconstruye con `parentId` (sin `parentId` = raíz).

## Base de datos

| Tabla | Uso |
|---|---|
| `NoteContentEntity.page_list` | JSON con los ids de página, en orden |
| `PageEntity` | `paper_spec` (ancho/alto, p. ej. 1240×1754), `paper_theme` (fondo) |
| `PageLayerEntity` | Capas y su visibilidad |
| `StrokeEntity` | Trazos a mano: `ink_stroke_blob` (protobuf) y caja `left/top/right/bottom` |
| `ShapeEntity` | Formas: `points` (JSON `[{x,y}]`), `color` (ARGB con signo), `width`, `type` |
| `TextBoxEntity` | Cuadros de texto en HTML, con caja y tamaño |
| `ImageEntity`, `HyperLinkEntity`, `QuoteEntity`, `AudioFileEntity` | No soportadas todavía |

Coordenadas en píxeles de página (origen arriba-izquierda).

### Temas de papel (`paper_theme`)

`LambdaPaperTheme` (color base + `paperStyle`), `PdfPaperTheme` (`pageNum` del PDF),
`LocalResPaperTheme` (portada de la app, no disponible fuera de ella). Estilos de papel:
`NewSquarePaperStyle`, `NewDotPaperStyle`, `NewLinePaperStyle`, `LineTwoColumnPaperStyle`,
`BlankPaperStyle`, con `requiredItemSpace` y márgenes.

### Tipos de forma (`ShapeEntity.type`)

7 = línea, 0 y 5 = trazo libre, 8 = rectángulo (cerrado), 6 = polígono (cerrado).
Solo observados en los cuadernos de prueba.

## Trazo (`ink_stroke_blob`, protobuf)

| Campo | Tipo | Significado |
|---|---|---|
| 1 | string | id del trazo |
| 2 | string | capa (`default`) |
| 3 | varint | marca de tiempo (ms) |
| 4 | float | grosor base |
| 5 | varint | color: `ULong` de Compose, ARGB en los 32 bits altos |
| 7 | string | pincel (`notein-fountain-v2`, `notein-pencil-v2`, `notein-ballpoint-v1`) |
| 10 | bytes | `float32` empaquetados `x,y,x,y,…` |
| 11 | bytes | `float32` empaquetados, 5 por punto: `[tiempo, presión, inclinación, orientación, …]` |
| 12 | bytes | 9 `float32`: matriz 3×3 de la vista (escala de zoom al dibujar) |

**Posición:** los puntos del campo 10 tienen la escala de la página pero un desplazamiento
distinto en cada trazo. Se recolocan centrándolos en la caja `left/top/right/bottom` de la
tabla (error inferior a ~0,1 px). Si NoteIn cambia esto, es el primer sitio donde mirar.

**Grosor:** el visor lo aproxima con `grosor_base × (0,54 + 0,9 × presión)`; no es la fórmula
real de la app.
