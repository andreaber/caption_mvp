# translate_srt.py
from deep_translator import GoogleTranslator
from pathlib import Path
import sys
import re

def translate_srt(input_path: str, output_path: str, src="es", tgt="en"):
    inp = Path(input_path)
    if not inp.exists():
        raise FileNotFoundError(f"No existe: {inp}")

    outp = Path(output_path)
    gt = GoogleTranslator(source=src, target=tgt)

    # Reglas SRT:
    # 1) línea 1: índice (número)
    # 2) línea 2: tiempo "00:00:00,000 --> 00:00:00,000"
    # 3+) 1..N líneas de texto (traducir), luego línea en blanco
    time_pat = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}$")

    with inp.open("r", encoding="utf-8", errors="ignore") as fin, \
         outp.open("w", encoding="utf-8") as fout:

        block = []
        for line in fin:
            line = line.rstrip("\n")
            if line.strip() == "":
                # procesar bloque completo
                _write_translated_block(block, gt, time_pat, fout)
                block = []
            else:
                block.append(line)

        # último bloque si no termina en blanco
        if block:
            _write_translated_block(block, gt, time_pat, fout)

    return str(outp)

def _write_translated_block(block, translator, time_pat, fout):
    if not block:
        fout.write("\n")
        return
    # Escribir índice
    fout.write(block[0] + "\n")
    # Escribir timing
    if len(block) >= 2 and time_pat.match(block[1].strip()):
        fout.write(block[1] + "\n")
        text_lines = block[2:]
    else:
        # SRT malformado; escribir tal cual
        for ln in block[1:]:
            fout.write(ln + "\n")
        fout.write("\n")
        return

    # Traducir solo las líneas de texto (conservando cursivas, etc.)
    for tl in text_lines:
        src_text = tl.strip()
        if not src_text:
            fout.write("\n")
            continue
        try:
            translated = translator.translate(src_text)
        except Exception as e:
            # Si falla la traducción, deja el original para no romper el SRT
            translated = src_text
        fout.write(translated + "\n")

    fout.write("\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python translate_srt.py ruta\\al\\archivo.srt [es] [en]")
        sys.exit(1)
    srt_in = sys.argv[1]
    src = sys.argv[2] if len(sys.argv) > 2 else "es"
    tgt = sys.argv[3] if len(sys.argv) > 3 else "en"
    out_path = str(Path(srt_in).with_name(Path(srt_in).stem + f"_{tgt}.srt"))
    p = translate_srt(srt_in, out_path, src=src, tgt=tgt)
    print("✅ SRT traducido:", p)
