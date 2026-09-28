# Uzbek Dubbing Pipeline

Ingliz yoki rus tilidagi video va podkastlarni o‘zbek tiliga tabiiy dublyaj qilish uchun mahalliy Python pipeline.

Pipeline audio ajratadi, `faster-whisper` bilan vaqt kodli transkripsiya yaratadi, Gemini yordamida tabiiy o‘zbekchaga tarjima qiladi, Edge-TTS orqali Sardor yoki Madina ovozini hosil qiladi, segmentlarni original timeline bo‘yicha yig‘adi va original fon ovozini pasaytirib yakuniy video yaratadi.

## O‘rnatish

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r dubbing/requirements.txt
sudo apt install ffmpeg
cp dubbing/.env.example .env
```

`.env` ichiga `GEMINI_API_KEY` qiymatini yozing. `.env` Git’ga kiritilmaydi.

## Ishlatish

```bash
python3 -m dubbing \
  --input /path/to/video.mp4 \
  --voice sardor \
  --lang auto \
  --output output_uzbek.mp4
```

YouTube URL uchun:

```bash
python3 -m dubbing --input "https://www.youtube.com/watch?v=VIDEO_ID" --voice madina
```

Lokal audio manbada natija `output_uzbek.wav` bo‘ladi. `--whisper-model large-v3` sifatni oshiradi, ammo `medium` boshlash uchun yengilroq variant.

## Davom ettirish

`--work-dir` katalogida `checkpoint.json`, transkripsiya, tarjimalar va tayyor segmentlar saqlanadi. Jarayon Gemini yoki TTS bosqichida to‘xtasa, qayta ishga tushirilganda tugallangan bosqichlar qayta bajarilmaydi.

To‘liq texnik ma’lumot: [`dubbing/README.md`](dubbing/README.md).

## O‘zbekcha subtitr plagini

Premiere Pro va After Effects uchun bepul, lokal CEP paneli qo‘shildi. U faol timeline’dagi In/Out yoki to‘liq audioni transkripsiya qiladi va subtitrlarni o‘z vaqtida timeline’ga joylaydi. Qator, so‘z va pauza sozlamalari bor; o‘zbekchaga maxsus NavAI modelini ham qo‘llaydi. Gemini kaliti kerak emas. O‘rnatish va ishlatish: [`subtitles/README.md`](subtitles/README.md).
