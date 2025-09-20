# Caption MVP — Subir MP4 → generar SRT → (opcional) traducir → quemar subtítulos → descargar MP4

**Demo:** https://caption-mvp.onrender.com

## ¿Qué hace?
- **Subís un MP4 corto**, genera **subtítulos (.srt)** con AssemblyAI.
- (Opcional) **Traduce** el SRT con **DeepL API** (ES → EN/IT/FR/PT/DE).
- **Quema** el SRT activo en el video con **FFmpeg** y permite **descargar** el MP4 final.
- Para la demo: **origen fijado en Español (ES)** para máxima calidad (sin “spanglish”).
- El MP4 final se **escala a máx. 720 px** de ancho antes de quemar subtítulos.

## Flujo de uso (UX)
1. **📤 Subir MP4** (10–20 s recomendado, audio claro, sin subtítulos).
2. **📝 Generar SRT (ES)** → queda **SRT activo**.
3. **🌐 Traducir** (opcional) al idioma destino → queda **SRT activo** el traducido.
4. **🎞️ Quemar subtítulos** (usa el SRT activo) → **Descargar MP4**.
5. **⬇️ Descargas**: SRT/TXT del activo.
6. **🧹 Limpieza**: borra temporales y resetea estado.

> **Consejo para demo:** clips cortos (≤20s, ≤720p, <10 MB) para evitar consumo y demoras.

---

## Requisitos
- Python **3.10+**
- **FFmpeg** instalado y accesible en `PATH`
- Claves: `ASSEMBLYAI_KEY` y `DEEPL_API_KEY`

## Instalación (local)
```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```


Crear .env (no subir) a partir de .env.example:

ASSEMBLYAI_KEY=TU_CLAVE_ASSEMBLYAI
DEEPL_API_KEY=TU_CLAVE_DEEPL
FFMPEG_BIN=ffmpeg


Windows (si no tenés FFmpeg en PATH):

FFMPEG_BIN=C:\ffmpeg\bin\ffmpeg.exe


Ejecutar:

streamlit run app.py


Deploy en Render

1. Subí el repo a GitHub.
2. En Render: New → Web Service → Connect repo.
3. Environment (Settings → Environment):
   * ASSEMBLYAI_KEY = tu clave
   * DEEPL_API_KEY = tu clave
   * FFMPEG_BIN = ffmpeg
4. Start command:
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
5. Deploy. (Si no ves cambios: Manual Deploy → Deploy latest commit y recargá el navegador).


Estructura del proyecto

.
├─ app.py                 # UI + flujo (Streamlit)
├─ burn.py                # FFmpeg: escalado + quemado (subtitles)
├─ assembly_ai.py         # Upload/transcribe/save_srt (AssemblyAI)
├─ requirements.txt
├─ .env.example           # variables de entorno (ejemplo, sin claves reales)
├─ .gitignore
└─ workdir/               # archivos temporales (excluidos del repo)




Notas técnicas

- Transcripción: AssemblyAI con hint es (origen fijado).
- Traducción: DeepL API. Mapeo automático a variantes requeridas (p. ej., en → EN-US, pt → PT-BR).
- Quemado: FFmpeg scale='min(720,iw)':-2 + subtitles=... con estilo opcional (tamaño/contorno/sombra).
- Preview: reproductor de Streamlit limitado y centrado para evitar videos gigantes.
- workdir/: almacena MP4/SRT/TXT temporales; no se versiona.