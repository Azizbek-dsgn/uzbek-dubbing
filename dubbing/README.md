# O‘zbekcha video/podkast dublyaj pipeline’i

Bu katalog mavjud Telegram botdan mustaqil ishlaydigan mahalliy pipeline’ni taqdim etadi. U lokal video/audio yoki YouTube URL manbasini oladi, audio ajratadi, `faster-whisper` bilan transkripsiya qiladi, Gemini yordamida tabiiy o‘zbekchaga tarjima qiladi, Edge-TTS orqali ovoz chiqaradi va segmentlarni original vaqt kodlariga qayta joylashtiradi.

## O‘rnatish

Repo ildizida virtual muhit yarating va dublyaj dependencyalarini o‘rnating:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r dubbing/requirements.txt
```

FFmpeg ham tizimda bo‘lishi kerak:

```bash
sudo apt install ffmpeg
```

`dubbing/.env.example` faylini repo ildizida `.env` nomi bilan nusxalang va `GEMINI_API_KEY` qiymatini kiriting:

```bash
cp dubbing/.env.example .env
```

API kalitini Git’ga commit qilmang. `.gitignore` `.env` fayllarini allaqachon chiqarib tashlaydi.

## Ishga tushirish

Lokal video uchun:

```bash
python -m dubbing \
  --input /path/to/video.mp4 \
  --voice sardor \
  --lang auto \
  --output output_uzbek.mp4
```

YouTube video uchun:

```bash
python -m dubbing --input "https://www.youtube.com/watch?v=VIDEO_ID" --voice madina
```

Faqat audio manba berilsa, natija `output_uzbek.wav` ko‘rinishida chiqadi. `--whisper-model large-v3` aniqroq, ammo sekinroq va ko‘proq RAM/VRAM talab qiladi; `medium` kundalik boshlang‘ich variant sifatida qoldirilgan.

## Checkpoint va davom ettirish

`--work-dir` katalogida `checkpoint.json`, yuklangan manba, transkripsiya, tarjima va segment audio fayllari saqlanadi. Gemini yoki TTS bosqichida internet uzilsa, jarayon qayta ishga tushirilganda tugallangan segmentlarni qayta hisoblamaydi.

## Muhim cheklovlar

Tarjima uchun internet va Gemini API kaliti kerak. STT va audio yig‘ish lokal ishlaydi. Edge-TTS ovoz yaratishi uchun tarmoq aloqasi talab qilinadi. TTS matni original segmentga sig‘masa, vaqt 0.9x–1.15x oralig‘ida moslanadi, so‘ng segment aniq vaqt oralig‘iga trim/pad qilinadi. Original fon ovozi mavjud bo‘lsa, u pasaytiriladi va o‘zbekcha ovoz ustiga aralashtiriladi.
