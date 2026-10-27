# Requisitos

## Sistema

| Componente | Versión | Para qué | Obligatorio |
|---|---|---|---|
| Python | 3.9 o superior (probado con 3.14) | Servidor y lector del formato | Sí |
| poppler-utils (`pdftoppm`) | cualquiera reciente | Fondos PDF de los cuadernos | Solo para cuadernos con PDF |
| rclone | 1.60 o superior | Sincronizar Drive con el PC | Solo para sincronizar |
| Navegador moderno | Chrome, Firefox, Edge, Safari recientes | Interfaz (canvas, `IntersectionObserver`) | Sí |
| systemd (usuario) | cualquiera | Arranque automático | Opcional |
| git | cualquiera | Descargar y versionar el código | Opcional |

Sistema probado: Ubuntu 26.04. Debería funcionar en otras distribuciones Linux y en macOS.
En Windows funciona el servidor manual; `deploy/install.sh` no aplica.

### Instalación en Debian/Ubuntu

```bash
sudo apt install python3 poppler-utils rclone git
```

## Dependencias de Python

Ninguna de terceros: solo biblioteca estándar. [requirements.txt](../requirements.txt)
existe únicamente para dejarlo explícito.

## Cuenta y permisos de Google

- Una cuenta de Google con la carpeta `NoteInDataSync` creada por la app NoteIn.
- Permiso **solo lectura** (`drive.readonly`) para rclone. No se necesita escritura.

## Recursos

- Espacio en disco: igual al tamaño de tus cuadernos (decenas de MB) más una cache de
  cuadernos descomprimidos en `~/.cache/notein-viewer` (aprox. 1–3 veces ese tamaño).
- Memoria: se mantienen en el navegador como máximo 10 páginas con datos a la vez.
- Red: solo para sincronizar con Drive. El visor no usa internet.
