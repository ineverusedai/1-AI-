#!/bin/bash
# 미션 3 임시 원본 음성 (리눅스 espeak-ng 한국어). 사용자 컴퓨터 음성(tools/make_tts_mac.sh)으로 바꾸기 전 임시용.
set -e
cd "$(dirname "$0")/.."
mkdir -p audio/originals
i=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  i=$((i+1)); n=$(printf "s%02d" $i)
  espeak-ng -v ko -s 140 -w "audio/originals/$n.wav" "$line"
done < missions/m3_sinewave/sentences.txt
echo "espeak-ng" > audio/originals/VOICE.txt
echo "audio/originals/ 에 $i개 만듦 (임시: espeak-ng)"
