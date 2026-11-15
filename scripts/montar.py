#!/usr/bin/env python3
"""Monta o video final a partir de uma lista de cortes (JSON), sem audio.

Uso: python3 -I montar.py <roteiro.json> <saida.mp4>

roteiro.json:
{
  "largura": 1080, "altura": 1920, "fps": 30,
  "titulo_png": "caminho/opcional.png",       # sobreposto do inicio ao fim (com fade-in)
  "titulo_inicio": 0.6,
  "fade_inicio": 0.5, "fade_fim": 0.8,
  "cortes": [
    {"arquivo": "brutos/IMG_1.mov", "inicio": 0.0, "fim": 4.0},
    {"arquivo": "brutos/IMG_2.mov", "inicio": 1.0, "fim": 6.0, "entrada": "fusao", "dur_fusao": 0.5}
  ]
}
"entrada" = como o corte entra apos o anterior: "corte" (corte seco, padrao) ou "fusao" (dissolve).
"""
import json
import os
import subprocess
import sys
import tempfile

COR = "eq=contrast=1.04:saturation=1.06:gamma=1.0"


def run(cmd):
    subprocess.run(cmd, check=True)


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def main():
    rot = json.load(open(sys.argv[1]))
    saida = sys.argv[2]
    W, H, FPS = rot["largura"], rot["altura"], rot.get("fps", 30)
    tmp = tempfile.mkdtemp(prefix="montar_", dir=os.path.dirname(os.path.abspath(saida)))

    # 1) normaliza cada trecho: corta, enquadra (cobre o quadro sem distorcer), fps, cor, sem audio
    partes = []
    for i, c in enumerate(rot["cortes"]):
        p = os.path.join(tmp, f"p{i:02d}.mp4")
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
              f"fps={FPS},{COR},format=yuv420p")
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(c["inicio"]), "-to", str(c["fim"]),
             "-i", c["arquivo"], "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast",
             "-crf", "12", p])
        partes.append((p, dur(p), c.get("entrada", "corte"), c.get("dur_fusao", 0.5)))

    # 2) encadeia: corte seco = concat, fusao = xfade
    ins = []
    for p, _, _, _ in partes:
        ins += ["-i", p]
    fc = [f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS[s{i}]" for i in range(len(partes))]
    atual = "[s0]"
    total = partes[0][1]
    for i in range(1, len(partes)):
        _, d, modo, df = partes[i]
        out = f"[v{i}]"
        if modo == "fusao":
            fc.append(f"{atual}[s{i}]xfade=transition=fade:duration={df}:offset={total - df:.3f},settb=AVTB{out}")
            total += d - df
        else:
            fc.append(f"{atual}[s{i}]concat=n=2:v=1:a=0,settb=AVTB{out}")
            total += d
        atual = out

    fi, ff = rot.get("fade_inicio", 0.5), rot.get("fade_fim", 0.8)
    fc.append(f"{atual}fade=t=in:st=0:d={fi},fade=t=out:st={total - ff:.3f}:d={ff}[base]")
    final = "[base]"
    if rot.get("titulo_png"):
        ins += ["-loop", "1", "-i", rot["titulo_png"]]
        k = len(partes)
        t0 = rot.get("titulo_inicio", 0.6)
        fc.append(f"[{k}:v]format=rgba,fade=t=in:st={t0}:d=0.6:alpha=1,"
                  f"fade=t=out:st={total - ff:.3f}:d={ff}:alpha=1[tit]")
        fc.append(f"[base][tit]overlay=0:0:shortest=1[comtit]")
        final = "[comtit]"

    run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc), "-map", final,
         "-t", f"{total:.3f}", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
         "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
         "-movflags", "+faststart", saida])
    for p, *_ in partes:
        os.remove(p)
    os.rmdir(tmp)
    print(f"{saida}: {total:.1f}s")


if __name__ == "__main__":
    main()
