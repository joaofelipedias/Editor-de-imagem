#!/usr/bin/env python3
"""Analisa os brutos: orientacao (deitado/em pe), duracao e qualidade por segundo.

Uso: python3 -I analisar.py <pasta_ou_arquivos...> --saida <relatorio.json> --folhas <pasta_contact_sheets>

Para cada video:
  - orientacao de exibicao (considera a rotacao gravada pelo celular)
  - nitidez (variancia do Laplaciano), brilho medio e tremor (deslocamento global entre quadros)
  - uma folha de contato (contact sheet) com miniaturas a cada ~2 s, para revisao visual
"""
import argparse
import json
import os
import subprocess
import sys

import cv2
import numpy as np

EXTS = {".mov", ".mp4", ".m4v", ".avi", ".mkv", ".3gp", ".hevc"}


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
        capture_output=True, text=True, check=True,
    ).stdout
    info = json.loads(out)
    v = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    if v is None:
        return None
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    tags = v.get("tags", {})
    if "rotate" in tags:
        rot = int(tags["rotate"])
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) % 180 == 90:
        dw, dh = h, w
    else:
        dw, dh = w, h
    num, den = v.get("avg_frame_rate", "30/1").split("/")
    fps = float(num) / float(den) if float(den) else 30.0
    dur = float(info["format"].get("duration", v.get("duration", 0)) or 0)
    has_audio = any(s.get("codec_type") == "audio" for s in info["streams"])
    return {
        "largura": dw, "altura": dh, "rotacao": rot, "fps": round(fps, 3),
        "duracao": round(dur, 2), "codec": v.get("codec_name"),
        "orientacao": "deitado" if dw > dh else ("em_pe" if dh > dw else "quadrado"),
        "tem_audio": has_audio,
        "color_transfer": v.get("color_transfer"),
    }


def decode_small(path, step_s, width=320):
    """Decodifica quadros pequenos em intervalos regulares via ffmpeg (ja aplica a rotacao)."""
    fps = 1.0 / step_s
    cmd = [
        "ffmpeg", "-v", "error", "-i", path,
        "-vf", f"fps={fps},scale={width}:-2,format=gray", "-f", "rawvideo", "-",
    ]
    meta = probe(path)
    dw, dh = meta["largura"], meta["altura"]
    h = int(round(width * dh / dw / 2) * 2)
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (width * h)
    return np.frombuffer(raw[: n * width * h], dtype=np.uint8).reshape(n, h, width)


def analyse(path, step_s=0.25):
    frames = decode_small(path, step_s)
    rows = []
    prev = None
    for i, f in enumerate(frames):
        sharp = float(cv2.Laplacian(f, cv2.CV_64F).var())
        bright = float(f.mean())
        shake = 0.0
        if prev is not None:
            try:
                (dx, dy), _ = cv2.phaseCorrelate(prev.astype(np.float32), f.astype(np.float32))
                shake = float(np.hypot(dx, dy))
            except cv2.error:
                shake = 0.0
        rows.append({"t": round(i * step_s, 2), "nitidez": round(sharp, 1),
                     "brilho": round(bright, 1), "tremor": round(shake, 2)})
        prev = f
    return rows


def contact_sheet(path, out_png, every_s=2.0, cols=6):
    meta = probe(path)
    tw = 320 if meta["orientacao"] == "deitado" else 180
    cmd = [
        "ffmpeg", "-v", "error", "-y", "-i", path,
        "-vf", (f"fps=1/{every_s},scale={tw}:-2,"
                f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"text='%{{eif\\:n*{every_s}\\:d}}s':x=6:y=6:fontsize=20:fontcolor=yellow:box=1:boxcolor=black@0.6,"
                f"tile={cols}x0:padding=4:color=black"),
        "-frames:v", "1", out_png,
    ]
    # tile precisa de linhas fixas; calcula
    n = max(1, int(meta["duracao"] // every_s) + 1)
    rows = (n + cols - 1) // cols
    cmd[cmd.index("-vf") + 1] = cmd[cmd.index("-vf") + 1].replace(f"tile={cols}x0", f"tile={cols}x{rows}")
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entradas", nargs="+")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--folhas", required=True)
    a = ap.parse_args()
    os.makedirs(a.folhas, exist_ok=True)
    files = []
    for e in a.entradas:
        if os.path.isdir(e):
            for n in sorted(os.listdir(e)):
                if os.path.splitext(n)[1].lower() in EXTS:
                    files.append(os.path.join(e, n))
        elif os.path.splitext(e)[1].lower() in EXTS:
            files.append(e)
    report = []
    for p in files:
        meta = probe(p)
        if meta is None:
            continue
        rows = analyse(p)
        sh = [r["nitidez"] for r in rows] or [0]
        br = [r["brilho"] for r in rows] or [0]
        tr = [r["tremor"] for r in rows[1:]] or [0]
        sheet = os.path.join(a.folhas, os.path.splitext(os.path.basename(p))[0] + ".png")
        contact_sheet(p, sheet)
        report.append({
            "arquivo": p, **meta,
            "resumo": {
                "nitidez_mediana": round(float(np.median(sh)), 1),
                "brilho_medio": round(float(np.mean(br)), 1),
                "tremor_mediano": round(float(np.median(tr)), 2),
                "tremor_p90": round(float(np.percentile(tr, 90)), 2),
            },
            "por_quadro": rows,
            "folha": sheet,
        })
        print(f"{os.path.basename(p):40s} {meta['orientacao']:8s} {meta['largura']}x{meta['altura']} "
              f"{meta['duracao']:6.1f}s  nitidez={report[-1]['resumo']['nitidez_mediana']:7.1f} "
              f"brilho={report[-1]['resumo']['brilho_medio']:5.1f} tremor_p90={report[-1]['resumo']['tremor_p90']:5.2f}",
              file=sys.stderr)
    with open(a.saida, "w") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
