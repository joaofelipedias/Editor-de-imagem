#!/usr/bin/env python3
"""Gera o titulo (PNG transparente) no padrao dos reels da ICM Curitiba:
linha 1 em fonte manuscrita branca, linha 2 em caixa alta dentro de tarja vermelha arredondada.

Uso: python3 -I titulo.py --linha1 "Ensaio do Louvor" --linha2 "TROMBETAS E FESTAS" \
       --largura 1080 --altura 1920 --saida titulo.png
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(AQUI, "..", "fontes")
VERMELHO = (164, 30, 34, 255)  # mesmo tom dos destaques do perfil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--linha1", default="Ensaio do Louvor")
    ap.add_argument("--linha2", default="TROMBETAS E FESTAS")
    ap.add_argument("--largura", type=int, default=1080)
    ap.add_argument("--altura", type=int, default=1920)
    ap.add_argument("--y", type=float, default=0.70, help="posicao vertical do bloco (fracao da altura)")
    ap.add_argument("--saida", required=True)
    a = ap.parse_args()

    W, H = a.largura, a.altura
    base = min(W, H)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    script = ImageFont.truetype(os.path.join(FONTES, "GreatVibes-Regular.ttf"), int(base * 0.105))
    sans = ImageFont.truetype(os.path.join(FONTES, "Montserrat-VF.ttf"), int(base * 0.062))
    sans.set_variation_by_name("Bold")

    d = ImageDraw.Draw(img)
    b1 = d.textbbox((0, 0), a.linha1, font=script)
    b2 = d.textbbox((0, 0), a.linha2, font=sans)
    w1, h1 = b1[2] - b1[0], b1[3] - b1[1]
    w2, h2 = b2[2] - b2[0], b2[3] - b2[1]
    padx, pady = int(base * 0.035), int(base * 0.022)
    tag_w, tag_h = w2 + 2 * padx, h2 + 2 * pady
    y0 = int(H * a.y)

    # tarja vermelha
    tx0 = (W - tag_w) // 2
    ty0 = y0 + int(h1 * 0.85)
    d.rounded_rectangle([tx0, ty0, tx0 + tag_w, ty0 + tag_h], radius=int(tag_h * 0.28), fill=VERMELHO)
    d.text((tx0 + padx - b2[0], ty0 + pady - b2[1]), a.linha2, font=sans, fill=(255, 255, 255, 255))

    # linha manuscrita com sombra suave para leitura sobre qualquer fundo
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sombra)
    x1 = (W - w1) // 2 - b1[0]
    y1 = y0 - b1[1]
    ds.text((x1 + 3, y1 + 4), a.linha1, font=script, fill=(0, 0, 0, 170))
    sombra = sombra.filter(ImageFilter.GaussianBlur(6))
    img = Image.alpha_composite(sombra, img)
    ImageDraw.Draw(img).text((x1, y1), a.linha1, font=script, fill=(255, 255, 255, 255))

    img.save(a.saida)


if __name__ == "__main__":
    main()
