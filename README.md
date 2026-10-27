# NoteInPC

Visor web **local y de solo lectura** para los cuadernos que escribes a mano con la app
[NoteIn](https://play.google.com/store/apps/details?id=com.orion.notein.global) en la tablet.
Sincroniza la carpeta de Google Drive con `rclone` y la muestra en el navegador del PC:
árbol de carpetas, páginas con desplazamiento continuo, zoom, búsqueda y fondos PDF.

> Proyecto no oficial, sin relación con los autores de NoteIn. El formato de archivo se dedujo
> por ingeniería inversa (ver [docs/FORMAT.md](docs/FORMAT.md)) y puede cambiar con
> actualizaciones de la app.

## Características

- Navegación por carpetas y cuadernos con la misma jerarquía de la tablet; búsqueda por título.
- Trazos a mano en vectores (canvas), nítidos a cualquier zoom, con colores y presión.
- Formas, cuadros de texto y capas ocultas respetadas.
- Papel liso, cuadriculado, punteado, rayado y de dos columnas; fondos PDF.
- Carga perezosa: solo se dibujan las páginas visibles.
- Botón **Sincronizar** (`rclone sync` de Drive al PC; nunca escribe en Drive).
- Sin dependencias de Python de terceros; escucha solo en `127.0.0.1`.

## Requisitos

Python 3.9+, `poppler-utils` y, para sincronizar, `rclone`. Detalle en
[docs/REQUIREMENTS.md](docs/REQUIREMENTS.md).

## Instalación rápida

```bash
git clone <URL-del-repositorio> NoteInPC
cd NoteInPC
sudo apt install poppler-utils rclone     # Debian/Ubuntu
rclone config                             # remoto «gdrive», alcance drive.readonly (ver docs/CONFIGURATION.md)
rclone sync gdrive:NoteInDataSync ./NoteInDataSync
python3 -I visor/server.py                # http://127.0.0.1:8765
```

Para que arranque solo al iniciar sesión (servicio de usuario, sin `sudo`):

```bash
deploy/install.sh
```

## Uso

| Acción | Cómo |
|---|---|
| Abrir un cuaderno | Clic en la lista de la izquierda |
| Cambiar de página | `←` / `→`, o el campo numérico |
| Zoom | `+` / `−`; `F` ajusta al ancho |
| Buscar cuaderno | `/` |
| Actualizar desde Drive | Botón **Sincronizar** |

La URL guarda cuaderno y página (`#/note/<id>/<página>`), así que se puede marcar como favorito.

## Estructura

```
visor/notein.py    lector del formato (ZIP + SQLite + protobuf) y API de datos
visor/server.py    servidor HTTP local y endpoints /api
visor/static/      interfaz web (HTML, CSS, JS sin dependencias)
deploy/            servicio systemd de usuario e instalador
docs/              requisitos, configuración y descripción del formato
tests/             pruebas unitarias con datos sintéticos
NoteInDataSync/    TUS cuadernos (ignorada por git; la crea rclone)
```

## Privacidad

Los cuadernos son datos personales: `NoteInDataSync/` y los archivos descargados están en
[.gitignore](.gitignore) y **no deben subirse al repositorio**. El repositorio no contiene
credenciales: el token de Google vive en `~/.config/rclone/rclone.conf`, fuera del proyecto.

## Desarrollo

```bash
python3 -I -m unittest discover -s tests -v
```

Los cambios se registran en [CHANGELOG.md](CHANGELOG.md) (formato
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/), versionado
[SemVer](https://semver.org/lang/es/)).

## Limitaciones conocidas

- El grosor del trazo se estima a partir de la presión; puede diferir ligeramente de la tablet.
- Las formas se dibujan como polilíneas; las portadas decorativas de la app se muestran como papel liso.
- El audio, los enlaces y las citas de PDF no se muestran.
- Solo lectura: no edita ni sube cambios a Drive.
