#!/usr/bin/env python3
"""Folha de revisao: uma linha por video, um quadro por segundo, com nome e tempo."""
import json, subprocess, sys, io
from PIL import Image, ImageDraw, ImageFont
rel = json.load(open(sys.argv[1])); orient = sys.argv[2]; out = sys.argv[3]
th = 150 if orient == "deitado" else 220
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
rows = []
for r in rel:
    if r["orientacao"] != orient: continue
    n = int(r["duracao"]) + 1
    raw = subprocess.run(["ffmpeg","-v","error","-i",r["arquivo"],"-vf",f"fps=1,scale=-2:{th}","-f","image2pipe","-vcodec","png","-"],capture_output=True).stdout
    imgs=[]; i=0
    while i < len(raw):
        j = raw.find(b"IEND", i)
        if j < 0: break
        imgs.append(Image.open(io.BytesIO(raw[i:j+8])).convert("RGB")); i = j+8
    tw = imgs[0].width
    row = Image.new("RGB", (130 + len(imgs)*(tw+4), th), "black")
    d = ImageDraw.Draw(row); name = r["arquivo"].split("/")[-1].replace(".mov","")
    d.text((6, th//2-20), name, fill="yellow", font=font)
    d.text((6, th//2+2), f'{r["duracao"]:.1f}s', fill="white", font=font)
    for k, im in enumerate(imgs):
        x = 130 + k*(tw+4); row.paste(im, (x,0))
        ImageDraw.Draw(row).text((x+4,4), f"{k}s", fill="yellow", font=font, stroke_width=2, stroke_fill="black")
    rows.append(row)
W = max(r.width for r in rows); H = sum(r.height+6 for r in rows)
sheet = Image.new("RGB", (W,H), (40,40,40)); y=0
for r in rows: sheet.paste(r,(0,y)); y += r.height+6
sheet.save(out); print(out, sheet.size)
