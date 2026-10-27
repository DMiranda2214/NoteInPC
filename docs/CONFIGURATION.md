# Configuración

## 1. Acceso a Google Drive con rclone

```bash
rclone config
```

1. `n` (nuevo remoto) y nombre **`gdrive`** (es el que usa el botón Sincronizar por defecto).
2. Tipo `drive` (Google Drive).
3. `client_id` y `client_secret`: Enter para dejarlos vacíos.
4. Alcance (`scope`): **`drive.readonly`** (solo lectura).
5. `Use auto config`: `y`; se abre el navegador para autorizar la cuenta.
6. No es un Shared Drive: `n`.

Comprobar y hacer la primera copia:

```bash
rclone lsd gdrive:                                   # debe aparecer NoteInDataSync
rclone sync gdrive:NoteInDataSync ./NoteInDataSync   # Drive -> PC
```

`rclone sync` hace que la carpeta local sea un espejo de Drive: lo que borres en Drive
desaparece del PC. Nunca modifica Drive con el alcance de solo lectura.

Si el token caduca o se revoca: `rclone config reconnect gdrive:`.

> **Seguridad:** el token queda en `~/.config/rclone/rclone.conf`. No lo copies al repositorio
> ni lo pegues en chats o issues. Si se expone, revoca el acceso en
> <https://myaccount.google.com/permissions> y vuelve a autorizar.

## 2. Servidor

Opciones por línea de comandos o variable de entorno (la opción de línea de comandos gana):

| Opción | Variable | Por defecto | Descripción |
|---|---|---|---|
| `--data` | `NOTEIN_DATA` | `<repo>/NoteInDataSync` | Carpeta con los archivos sincronizados |
| `--port` | `NOTEIN_PORT` | `8765` | Puerto (siempre en `127.0.0.1`) |
| `--remote` | `NOTEIN_REMOTE` | `gdrive:NoteInDataSync` | Origen que usa el botón Sincronizar |
| `--cache` | `NOTEIN_CACHE` | `~/.cache/notein-viewer` | Cuadernos descomprimidos y PNG de fondos |

Ejemplo:

```bash
NOTEIN_PORT=9000 python3 -I visor/server.py --data ~/Documentos/NoteIn
```

La cache se puede borrar sin riesgo: se regenera al abrir los cuadernos.

## 3. Arranque automático (systemd de usuario)

```bash
deploy/install.sh              # instala y arranca
deploy/install.sh --uninstall  # lo quita
```

El instalador escribe `~/.config/systemd/user/notein-viewer.service` con la ruta real del
repositorio y crea `~/.config/notein-viewer/env` (opcional) con las variables anteriores.
Después de editar ese archivo:

```bash
systemctl --user restart notein-viewer
journalctl --user -u notein-viewer -f      # registros
```

Si mueves la carpeta del proyecto, vuelve a ejecutar `deploy/install.sh`.

## 4. Sincronización periódica (opcional)

Además del botón, puedes sincronizar cada hora con cron:

```cron
0 * * * * /usr/bin/rclone sync gdrive:NoteInDataSync /ruta/a/NoteInPC/NoteInDataSync
```

## 5. Usar el proyecto en otro equipo

```bash
git clone <URL-del-repositorio> NoteInPC && cd NoteInPC
sudo apt install poppler-utils rclone
rclone config                                       # autorizar la cuenta en ESTE equipo
rclone sync gdrive:NoteInDataSync ./NoteInDataSync
deploy/install.sh
```

Los cuadernos no viajan por git: cada equipo los obtiene de Drive.

## 6. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| «No hay cuadernos» | La carpeta de datos está vacía o mal indicada: revisa `NOTEIN_DATA` o ejecuta `rclone sync`. |
| `empty token found` en rclone | Falta autorizar: `rclone config reconnect gdrive:`. |
| Páginas con PDF sin fondo | Falta `pdftoppm`: `sudo apt install poppler-utils`. |
| El puerto está ocupado | Cambia `NOTEIN_PORT` o detén el otro proceso (`ss -ltnp \| grep 8765`). |
| Un cuaderno no se abre tras actualizar NoteIn | El formato pudo cambiar; abre un issue con el mensaje de error del servidor. |
