# Changelog

Todos los cambios relevantes de este proyecto se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
versionado según [SemVer](https://semver.org/lang/es/).

## [Unreleased]

## [0.1.0] - 2026-10-27

### Añadido
- Lector del formato de NoteIn: ZIP con base SQLite (Room) y trazos en protobuf.
- Servidor HTTP local (solo `127.0.0.1`) con API de árbol, páginas, fondos PDF y miniaturas.
- Interfaz web: árbol de carpetas, búsqueda, desplazamiento continuo con carga perezosa,
  zoom, atajos de teclado, tema claro/oscuro y enlace directo a cuaderno y página.
- Dibujo vectorial de trazos (color, presión), formas y cuadros de texto.
- Papel liso, cuadriculado, punteado, rayado y de dos columnas; fondos PDF vía `pdftoppm`.
- Botón de sincronización con `rclone sync` (solo lectura sobre Drive).
- Configuración por variables de entorno `NOTEIN_DATA`, `NOTEIN_PORT`, `NOTEIN_REMOTE`, `NOTEIN_CACHE`.
- Servicio systemd de usuario e instalador (`deploy/install.sh`).
- Pruebas unitarias con datos sintéticos y documentación (requisitos, configuración, formato).

### Seguridad
- Comprobación de la cabecera `Host` (anti DNS-rebinding) y cabecera obligatoria en `POST /api/sync`.
- Extracción de ZIP que ignora entradas con rutas anidadas.
- Los datos personales y credenciales quedan fuera de git mediante `.gitignore`.

[Unreleased]: https://github.com/DMiranda2214/NoteInPC/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/DMiranda2214/NoteInPC/releases/tag/v0.1.0
