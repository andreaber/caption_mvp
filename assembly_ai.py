# assembly_ai.py
import os
import time
import requests
from dotenv import load_dotenv

# Carga variables de entorno (.env con ASSEMBLYAI_KEY=...)
load_dotenv()
API_KEY = os.getenv("ASSEMBLYAI_KEY")
if not API_KEY:
    raise RuntimeError("Falta ASSEMBLYAI_KEY en .env")

UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
TRANSCRIBE_URL = "https://api.assemblyai.com/v2/transcript"
HEADERS = {"authorization": API_KEY}

def upload_file(path: str) -> str:
    """
    Sube un archivo local (MP4/MP3/WAV) a AssemblyAI y devuelve la URL temporal.
    """
    def _read_file(fn, chunk_size=5_242_880):  # ~5MB
        with open(fn, "rb") as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                yield data

    r = requests.post(UPLOAD_URL, headers=HEADERS, data=_read_file(path))
    r.raise_for_status()
    return r.json()["upload_url"]

def transcribe(audio_url: str, lang_hint: str | None = None, poll_secs: int = 3) -> dict:
    """
    Crea una transcripción y espera a que termine. Devuelve el JSON completo.
    lang_hint: "es" o "en" (opcional).
    """
    payload = {"audio_url": audio_url, "speaker_labels": True}
    if lang_hint in {"es", "en"}:
        payload["language_code"] = lang_hint  # pista de idioma (opcional)

    r = requests.post(TRANSCRIBE_URL, headers=HEADERS, json=payload)
    r.raise_for_status()
    tid = r.json()["id"]

    # Polling hasta que finalice
    while True:
        j = requests.get(f"{TRANSCRIBE_URL}/{tid}", headers=HEADERS)
        j.raise_for_status()
        data = j.json()
        status = data.get("status")
        # Opcional: print("Estado ASR:", status) para debug
        if status in ("completed", "error"):
            return data
        time.sleep(poll_secs)

def save_srt(transcript_id: str, out_path: str = "subtitulos.srt") -> str:
    """
    Descarga el SRT final para una transcripción completada y lo guarda en disco.
    """
    srt_resp = requests.get(f"{TRANSCRIBE_URL}/{transcript_id}/srt", headers=HEADERS)
    srt_resp.raise_for_status()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(srt_resp.text)
    return out_path
