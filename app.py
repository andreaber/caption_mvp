# app.py
from pathlib import Path
import streamlit as st

from assembly_ai import upload_file, transcribe, save_srt
from burn import burn_subtitles

import re
from deep_translator import GoogleTranslator, MyMemoryTranslator


# =========================
# Helpers extra
# =========================

def srt_to_txt(srt_file: Path) -> str:
    """Convierte un .srt a texto plano (sin tiempos ni índices)."""
    time_pat = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}$")
    out_lines = []
    with srt_file.open("r", encoding="utf-8", errors="ignore") as f:
        block = []
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                if block:
                    out_lines.append(" ".join(block))
                    block = []
                continue
            if line.isdigit() or time_pat.match(line):
                continue
            block.append(line.strip())
        if block:
            out_lines.append(" ".join(block))
    return "\n\n".join(out_lines).strip()


# =========================
# Helpers extra (idioma activo)
# =========================
def _lang_from_srt(path: Path) -> str:
    """
    Intenta obtener el código de idioma del nombre del .srt.
    Si termina en _en/_es/_pt/_fr/_it/_de lo usa; si no, asume 'es'.
    """
    stem = Path(path).stem.lower()
    last = stem.split("_")[-1]
    return last if last in {"es", "en", "pt", "fr", "it", "de"} else "es"


# =========================
# Estado de SRTs en sesión
# =========================
def _init_srts():
    # dict idioma -> ruta SRT
    st.session_state.setdefault("srts", {})
    st.session_state.setdefault("active_lang", None)



# =========================
# Configuración básica
# =========================
st.set_page_config(page_title="Caption MVP", page_icon="🎬", layout="centered")
_init_srts()

# Limitar el ancho del <video> y centrarlo
st.markdown("""
<style>
div[data-testid="stVideo"] video {
  max-width: 480px !important;
  width: 100% !important;
  height: auto !important;
  display: block;
  margin: 0 auto;
}
</style>
""", unsafe_allow_html=True)

st.title("🎬 Caption MVP — Transcripción a SRT")
st.caption("Subí un MP4, elegí idioma y generá subtítulos (.srt).")

# Carpeta de trabajo para archivos temporales
WORKDIR = Path("workdir")
WORKDIR.mkdir(exist_ok=True)


# =========================
# Sidebar (opciones)
# =========================
st.sidebar.header("Opciones")
# Origen para transcripción (Auto = detección automática)
lang_src = st.sidebar.selectbox(
    "Idioma de origen (transcripción)",
    ["auto", "es", "en", "pt", "fr", "it", "de"],
    index=0
)

# Destino para traducción (— sin traducción — = usar SRT original)
lang_dst = st.sidebar.selectbox(
    "Idioma de destino (traducción)",
    ["— sin traducción —", "en", "es", "pt", "fr", "it", "de"],
    index=0
)

show_debug = st.sidebar.checkbox("Mostrar logs de depuración", value=False)


# =========================
# Subida de video
# =========================
uploaded = st.file_uploader("Subí un archivo de video (.mp4)", type=["mp4"])
video_local_path = None

if uploaded:
    # Guardar el video subido en disco para procesarlo
    video_local_path = WORKDIR / uploaded.name
    with open(video_local_path, "wb") as f:
        f.write(uploaded.getbuffer())

    # Vista previa centrada y con ancho controlado
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.video(str(video_local_path))
        size_mb = uploaded.size / (1024 * 1024)
        st.caption(f"Tamaño del clip: {size_mb:.1f} MB")
        if size_mb > 50:
            st.warning("Sugerencia: para la demo, usá clips cortos (< ~1 min).")

st.divider()


# =========================
# Botón: Transcribir → SRT
# =========================
if st.button("📝 Generar subtítulos (.srt)", disabled=not bool(video_local_path)):
    if not video_local_path:
        st.error("Primero subí un MP4.")
        st.stop()

    with st.spinner("Subiendo a AssemblyAI..."):
        try:
            audio_url = upload_file(str(video_local_path))
            if show_debug:
                st.info(f"URL subida: {audio_url[:80]}...")
        except Exception as e:
            st.error(f"Error subiendo el archivo: {e}")
            st.stop()

    with st.spinner("Transcribiendo... esto puede tardar según la duración del video."):
        try:
            # Si el usuario eligió "auto", no pasamos hint de idioma
            if lang_src == "auto":
                result = transcribe(audio_url)
            else:
                result = transcribe(audio_url, lang_hint=lang_src)
        except Exception as e:
            st.error(f"Error durante la transcripción: {e}")
            st.stop()

    status = result.get("status")
    if status != "completed":
        st.error(f"Transcripción no completada. Estado: {status}. Detalle: {result.get('error')}")
        st.stop()

    # Guardar SRT en disco
    srt_path = WORKDIR / f"{video_local_path.stem}.srt"
    try:
        save_srt(result["id"], out_path=str(srt_path))
    except Exception as e:
        st.error(f"No pude guardar el SRT: {e}")
        st.stop()

    st.success("✅ SRT generado con éxito.")

    # --- Estado: guardar y activar SRT original ---
    orig_lang = lang_src if lang_src != "auto" else "es"   # simple: si usaste auto, asumimos ES
    st.session_state["srts"][orig_lang] = str(srt_path)
    st.session_state["active_lang"] = orig_lang

    # Guardar rutas en sesión para habilitar el quemado
    st.session_state["last_video_path"] = str(video_local_path)
    st.session_state["last_srt_path"] = str(srt_path)

    # Preview del .srt (primeras líneas)
    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            preview_lines = "".join([next(f) for _ in range(5)])
        with st.expander("Ver preview del .srt"):
            st.code(preview_lines, language="text")
    except Exception:
        pass

    # Botón de descarga del .srt
    with open(srt_path, "rb") as f:
        st.download_button(
            label="⬇️ Descargar subtítulos (.srt)",
            data=f.read(),
            file_name=srt_path.name,
            mime="text/plain",
        )


# =========================
# Traducir SRT al idioma elegido (opcional)
# =========================
st.divider()
st.subheader("🌐 Traducir subtítulos (opcional)")

# def _translate_srt_file(input_srt: Path, src="auto", tgt="en") -> Path:
#     import re
#     from deep_translator import GoogleTranslator
#     time_pat = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}$")
#     # Si src == "auto", GoogleTranslator detecta automáticamente
#     gt = GoogleTranslator(source=src if src != "auto" else "auto", target=tgt)
#     out_path = input_srt.with_name(input_srt.stem + f"_{tgt}.srt")

#     with input_srt.open("r", encoding="utf-8", errors="ignore") as fin, \
#          out_path.open("w", encoding="utf-8") as fout:

#         block = []
#         def flush_block(lines):
#             if not lines:
#                 fout.write("\n"); return
#             fout.write(lines[0] + "\n")  # índice
#             if len(lines) >= 2 and time_pat.match(lines[1].strip()):
#                 fout.write(lines[1] + "\n")
#                 text_lines = lines[2:]
#             else:
#                 for ln in lines[1:]:
#                     fout.write(ln + "\n")
#                 fout.write("\n"); return
#             for tl in text_lines:
#                 t = tl.strip()
#                 if not t:
#                     fout.write("\n"); continue
#                 try:
#                     fout.write(gt.translate(t) + "\n")
#                 except Exception:
#                     fout.write(t + "\n")
#             fout.write("\n")

#         for line in fin:
#             line = line.rstrip("\n")
#             if line.strip() == "":
#                 flush_block(block); block = []
#             else:
#                 block.append(line)
#         if block:
#             flush_block(block)

#     return out_path

def _translate_srt_file(input_srt: Path, src="auto", tgt="en") -> Path:
    """
    Traduce solo las líneas de texto de un SRT (conserva índices y tiempos).
    Fuerza idioma de origen (evita 'spanglish') y usa fallback si Google falla.
    """
    time_pat = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}$")
    # Si el usuario puso 'auto', asumimos ES como origen para evitar autodetección inestable
    src_eff = src if src != "auto" else "es"

    def translate_line(txt: str) -> str:
        try:
            return GoogleTranslator(source=src_eff, target=tgt).translate(txt)
        except Exception:
            # Fallback público cuando el endpoint de Google bloquea desde el hosting
            return MyMemoryTranslator(source=src_eff, target=tgt).translate(txt)

    out_path = input_srt.with_name(input_srt.stem + f"_{tgt}.srt")

    with input_srt.open("r", encoding="utf-8", errors="ignore") as fin, \
         out_path.open("w", encoding="utf-8") as fout:

        block = []
        def flush_block(lines):
            if not lines:
                fout.write("\n"); return
            # índice
            fout.write(lines[0] + "\n")
            # tiempos
            if len(lines) >= 2 and time_pat.match(lines[1].strip()):
                fout.write(lines[1] + "\n")
                text_lines = lines[2:]
            else:
                for ln in lines[1:]:
                    fout.write(ln + "\n")
                fout.write("\n"); return
            # traducir solo texto
            for tl in text_lines:
                t = tl.strip()
                if not t:
                    fout.write("\n"); continue
                try:
                    fout.write(translate_line(t) + "\n")
                except Exception:
                    fout.write(t + "\n")
            fout.write("\n")

        for line in fin:
            line = line.rstrip("\n")
            if line.strip() == "":
                flush_block(block); block = []
            else:
                block.append(line)
        if block:
            flush_block(block)

    return out_path

if "last_srt_path" in st.session_state:
    # Si el usuario no eligió destino, no traducimos
    if lang_dst == "— sin traducción —":
        st.info("Destino: sin traducción. Se usará el SRT original.")
    else:
        if st.button(f"Traducir SRT a {lang_dst.upper()}"):
            src_srt = Path(st.session_state["last_srt_path"])
            try:
                # Preview y descarga del SRT traducido
                with st.spinner(f"Traduciendo a {lang_dst.upper()}..."):
                    # pasamos lang_src como origen (o 'auto' si así lo elegiste en la sidebar)
                    out_path = _translate_srt_file(src_srt, src=lang_src, tgt=lang_dst)
                
                # tras traducir a lang_dst:
                st.session_state["srts"][lang_dst] = str(out_path)
                st.session_state["active_lang"] = lang_dst
                st.session_state["last_srt_path"] = str(out_path)  # usar traducido para quemar
                st.success(f"✅ Traducido: {out_path.name} · SRT activo: {lang_dst.upper()}")

                # Preview y descarga del SRT traducido
                try:
                    with open(out_path, "r", encoding="utf-8", errors="ignore") as f:
                        preview = "".join(f.readlines()[:12])
                    with st.expander(f"Preview (.srt → {lang_dst.upper()})"):
                        st.code(preview, language="text")
                    with open(out_path, "rb") as f:
                        st.download_button(
                            label=f"⬇️ Descargar SRT ({lang_dst})",
                            data=f.read(),
                            file_name=out_path.name,
                            mime="text/plain",
                        )
                except Exception as e:
                    st.info(f"Traducción lista. No pude mostrar/descargar el preview ({e}).")
            except Exception as e:
                st.error(f"No se pudo traducir: {e}")
else:
    st.info("Generá primero el .srt para poder traducirlo.")


# =========================
# SRT activo (selector)
# =========================
if st.session_state["srts"]:
    langs = sorted(st.session_state["srts"].keys())
    current = st.session_state["active_lang"] or langs[0]
    choice = st.selectbox(
        "Elegí el subtítulo activo",
        options=langs,
        index=langs.index(current),
        help="Se usará para el quemado y para las descargas."
    )
    st.session_state["active_lang"] = choice
    st.session_state["last_srt_path"] = st.session_state["srts"][choice]
    st.markdown(f"**SRT activo:** {choice.upper()}")
else:
    st.info("Generá (o traducí) un SRT para habilitar el selector.")



# =========================
# Descargas adicionales (SRT y TXT)
# =========================
st.divider()
st.subheader("⬇️ Descargas adicionales")

if "last_srt_path" in st.session_state:
    srt_path_active = Path(st.session_state["last_srt_path"])
    active_lang = st.session_state.get("active_lang", "es")

    # Descargar SRT
    with open(srt_path_active, "rb") as f:
        st.download_button(
            label=f"Descargar SRT ({active_lang.upper()})",
            data=f.read(),
            file_name=srt_path_active.name,
            mime="text/plain",
        )
    # Descargar TXT
    try:
        txt_content = srt_to_txt(srt_path_active)
        st.download_button(
            label=f"Descargar TXT ({active_lang.upper()})",
            data=txt_content.encode("utf-8"),
            file_name=f"{srt_path_active.stem}.txt",
            mime="text/plain",
        )
    except Exception as e:
        st.info(f"No pude generar el .txt desde el SRT activo ({e}).")
else:
    st.info("Generá (o traducí) un SRT para habilitar las descargas.")



# =========================
# Limpieza (opcional)
# =========================
st.divider()
if st.button("🧹 Limpiar archivos temporales"):
    try:
        for p in WORKDIR.glob("*"):
            p.unlink(missing_ok=True)
        # limpiar estado
        for k in ("srts", "active_lang", "last_srt_path", "last_video_path"):
            st.session_state.pop(k, None)
        st.success("Se limpió la carpeta temporal.")
    except Exception as e:
        st.error(f"No se pudo limpiar: {e}")



# =========================
# Bloque fijo: Quemar subtítulos (usar SRT activo)
# =========================
st.divider()
st.subheader("🎞️ Quemar subtítulos (usar SRT activo)")

if "last_video_path" in st.session_state and "last_srt_path" in st.session_state:
    srt_active = Path(st.session_state["last_srt_path"])
    vid_path  = Path(st.session_state["last_video_path"])
    active_lang = st.session_state.get("active_lang", "es")

    st.markdown(f"**SRT activo:** {active_lang.upper()}  ·  Archivo: `{srt_active.name}`")

    # Nombre final claro: video_ES.mp4, video_EN.mp4, etc.
    output_path = WORKDIR / f"{vid_path.stem}_{active_lang}.mp4"

    fs = st.slider("Tamaño de letra", min_value=10, max_value=30, value=16)

    if st.button("🔥 Generar MP4 con subtítulos (usar activo)"):
        with st.spinner("Ejecutando FFmpeg..."):
            try:
                burn_subtitles(
                    input_mp4=str(vid_path),
                    srt_path=str(srt_active),
                    output_mp4=str(output_path),
                    fontsize=fs,               # <— usar slider
                )
                st.success(f"✅ Video generado con subtítulos en {active_lang.upper()}.")
                st.video(str(output_path))
                with open(output_path, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Descargar MP4 ({active_lang.upper()})",
                        data=f.read(),
                        file_name=output_path.name,
                        mime="video/mp4",
                    )
            except Exception as e:
                st.error(f"No se pudo generar el video: {e}")
else:
    st.info("Generá (o traducí) un SRT para habilitar el quemado.")
