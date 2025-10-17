# SIVIA (Frontend + Backend)

Este directorio contiene una página estática (`sivia.html`) con una pequeña interfaz de chat y un backend minimalista en Flask (`server.py`) que actúa como proxy seguro hacia la API de Google Generative AI.

Requisitos
- Python 3.8+
- Clave `GOOGLE_API_KEY` en un archivo `.env` en este directorio.
- Entorno virtual recomendado

Instalación
```powershell
Set-Location -Path "C:\Users\s7\OneDrive\Documentos\MANOS UNIDAS\WEB\sivia"
python -m venv .venv
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt
```

Configurar API Key
1. Crea `.env` en este directorio con:
```
GOOGLE_API_KEY=TU_API_KEY_AQUI
```

Ejecutar servidor
```powershell
& ".venv\Scripts\python.exe" server.py
```
Luego abre `sivia.html` en un navegador (si sirves la carpeta con un servidor estático) o visita `http://127.0.0.1:5001` si sirves el frontend desde Flask/otro servidor.

Notas de despliegue
- No subas `.env` a GitHub. Añade la clave a los secretos del repositorio y gestiona variables en GitHub Actions si automatizas el despliegue.
