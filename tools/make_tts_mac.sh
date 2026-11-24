#!/bin/bash
# 미션 3 원본 음성 만들기 (맥 내장 한국어 음성 Yuna). 맥 터미널에서 프로젝트 폴더에서 실행:
#   bash tools/make_tts_mac.sh
# Yuna 음성이 없으면: 시스템 설정 → 손쉬운 사용 → 읽기 및 말하기 → 시스템 음성 → 음성 관리 → 한국어 Yuna 내려받기
set -e
cd "$(dirname "$0")/.."
mkdir -p audio/originals
i=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  i=$((i+1)); n=$(printf "s%02d" $i)
  say -v Yuna -r 165 -o "audio/originals/$n.aiff" "$line"
  afconvert -f WAVE -d LEI16@44100 -c 1 "audio/originals/$n.aiff" "audio/originals/$n.wav"
  rm "audio/originals/$n.aiff"
  echo "$n $line"
done < missions/m3_sinewave/sentences.txt
echo "audio/originals/ 에 $i개 만듦 (맥 Yuna 음성)"
echo "mac-yuna" > audio/originals/VOICE.txt
