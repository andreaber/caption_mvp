# burn.py
import os
import subprocess
from pathlib import Path

# Lee la ruta del binario de ffmpeg desde .env o usa 'ffmpeg' si ya está en PATH
FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")

def burn_subtitles(input_mp4: str, srt_path: str, output_mp4: str, fontsize: int = 16) -> None:
    """
    Quema el archivo .srt dentro del MP4 usando FFmpeg.
    Requiere que ffmpeg esté instalado. Si no está en PATH, definir FFMPEG_BIN en .env.
    """
    in_mp4 = Path(input_mp4).resolve()
    srt = Path(srt_path).resolve()
    out_mp4 = Path(output_mp4).resolve()

    # En Windows, al filtro subtitles le gustan las rutas con / y el : escapado
    srt_esc = str(srt).replace("\\", "/").replace(":", r"\:")

    if fontsize:
        vf = f"subtitles='{srt_esc}':force_style='Fontsize={fontsize},Outline=1,Shadow=1'"
    else:
        vf = f"subtitles='{srt_esc}'"

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i", str(in_mp4),
        "-vf", vf,
        "-c:a", "copy",
        str(out_mp4),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg falló:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
