# 미션 3 원본 음성 만들기 (윈도우 내장 한국어 음성 Heami). PowerShell 에서 프로젝트 폴더에서 실행:
#   powershell -ExecutionPolicy Bypass -File tools\make_tts_windows.ps1
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$ko = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq "ko-KR" } | Select-Object -First 1
if (-not $ko) { Write-Error "한국어 음성이 없습니다. 설정 → 시간 및 언어 → 언어 → 한국어 → 음성 내려받기"; exit 1 }
$s.SelectVoice($ko.VoiceInfo.Name)
$s.Rate = 0
New-Item -ItemType Directory -Force -Path audio\originals | Out-Null
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(44100, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$i = 0
Get-Content -Encoding UTF8 missions\m3_sinewave\sentences.txt | Where-Object { $_.Trim() } | ForEach-Object {
  $i++; $n = "s{0:D2}" -f $i
  $s.SetOutputToWaveFile("audio\originals\$n.wav", $fmt); $s.Speak($_); $s.SetOutputToNull()
  Write-Output "$n $_"
}
Set-Content -Path audio\originals\VOICE.txt -Value ("windows-" + $ko.VoiceInfo.Name)
Write-Output "audio\originals 에 $i 개 만듦 ($($ko.VoiceInfo.Name))"
