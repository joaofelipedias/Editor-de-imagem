#!/bin/bash
# Comprime um video para caber abaixo de ~9,5 MB (limite de upload de 10 MB), 2 passadas.
# Uso: comprimir_10mb.sh entrada saida codec(x264|x265) [audio:sim|nao]
in="$1"; out="$2"; codec="$3"; audio="${4:-sim}"
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$in")
alvo_kbit=$(python3 -c "print(int(9.3*8*1024/$dur))")
akbps=0; aopt=(-an)
if [ "$audio" = sim ] && ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$in" | grep -q .; then akbps=96; aopt=(-c:a aac -b:a 96k); fi
v=$((alvo_kbit - akbps)); [ $v -gt 16000 ] && v=16000
log=$(mktemp -u)
if [ "$codec" = x265 ]; then
  ffmpeg -v error -y -i "$in" -c:v libx265 -preset medium -b:v ${v}k -x265-params pass=1:stats=$log.log:log-level=error -an -f null /dev/null &&
  ffmpeg -v error -y -i "$in" -c:v libx265 -preset medium -b:v ${v}k -x265-params pass=2:stats=$log.log:log-level=error -tag:v hvc1 -pix_fmt yuv420p "${aopt[@]}" -movflags +faststart "$out"
else
  ffmpeg -v error -y -i "$in" -c:v libx264 -preset slow -b:v ${v}k -pass 1 -passlogfile $log -an -f null /dev/null &&
  ffmpeg -v error -y -i "$in" -c:v libx264 -preset slow -b:v ${v}k -maxrate $((v*2))k -bufsize $((v*2))k -pass 2 -passlogfile $log -pix_fmt yuv420p "${aopt[@]}" -movflags +faststart "$out"
fi
rm -f $log*
echo "$(basename "$out"): $(stat -c%s "$out") bytes, video ${v}k"
