#!/bin/bash
# Comprime um video para um tamanho alvo em MB (2 passadas, H.264, 30 fps, audio AAC 64k).
# Uso: comprimir_alvo.sh entrada saida alvo_mb
in="$1"; out="$2"; mb="$3"
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in")
tot=$(python3 -c "print(int($mb*8*1000/$dur))")
akbps=0; aopt=(-an)
if ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$in" | grep -q .; then akbps=64; aopt=(-c:a aac -b:a 64k); fi
v=$((tot - akbps - 40))
log=$(mktemp -u)
ffmpeg -v error -y -i "$in" -vf fps=30 -c:v libx264 -preset slower -b:v ${v}k -pass 1 -passlogfile $log -an -f null /dev/null &&
ffmpeg -v error -y -i "$in" -vf fps=30 -c:v libx264 -preset slower -b:v ${v}k -maxrate $((v*3/2))k -bufsize $((v*2))k -pass 2 -passlogfile $log -pix_fmt yuv420p "${aopt[@]}" -movflags +faststart "$out"
rm -f $log*
echo "$(basename "$out"): $(stat -c%s "$out") bytes, video ${v}k"
