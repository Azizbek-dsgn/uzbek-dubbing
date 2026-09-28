# O‘zbekcha subtitr plagini

Premiere Pro va After Effects uchun bepul, lokal CEP panel. U faol sequence yoki kompozitsiyadagi audioni eksport qiladi, `faster-whisper` bilan o‘zbekcha nutqni so‘z vaqtigacha taniydi va subtitrlarni timeline’ga qo‘yadi. API kaliti kerak emas; model bir marta yuklangach internet talab qilinmaydi.

## Ishlatish

1. Premiere Pro’da sequence’ni yoki After Effects’da kompozitsiyani oching.
2. Kerakli joyga In/Out nuqtalarini qo‘ying. AE’da Work Area belgilang. Belgilanmagan bo‘lsa butun timeline olinadi.
3. **Window → Extensions → Uzbek Subtitles** panelini oching, oraliq va modelni tanlang.
4. **Timeline’ga subtitr qo‘shish** tugmasini bosing. Premiere’da caption track, AE’da vaqtli matn qatlamlari yaratiladi. SRT nusxasi `exports/` papkasida qoladi.

Oraliq tanlovida **Faqat In/Out** belgilar bo‘lmasa xato beradi; **To‘liq timeline** belgilarni e’tiborsiz qoldiradi. Birinchi model yuklanishi uzoq davom etishi mumkin. `large-v3` yuqoriroq sifat, lekin taxminan 3 GB disk va ko‘proq xotira talab qiladi; `medium` va `small` yengilroq.

## O‘rnatish

Python 3.10+ bilan `pip install -r subtitles/requirements.txt` bajaring. `adobe/UzbekSubtitles` papkasini Adobe CEP extensions katalogiga symlink qiling. Imzosiz development paneli uchun `PlayerDebugMode=1` kerak. Adobe dasturini qayta ishga tushiring. Mac’da:

```bash
mkdir -p "$HOME/Library/Application Support/Adobe/CEP/extensions"
ln -s "$(pwd)/adobe/UzbekSubtitles" "$HOME/Library/Application Support/Adobe/CEP/extensions/UzbekSubtitles"
```

Panel repo ichidagi `.venv/bin/python` ni o‘zi topadi; boshqa Python ishlatsangiz paneldagi yo‘lni o‘zgartiring. Premiere eksporti Adobe o‘rnatgan `WAV_Mono_16bit_16kHz.epr` presetiga tayanadi; hozirgi avtomatik qidiruv macOS’dagi Premiere 2024–2026 paketlariga mo‘ljallangan.

## Alohida SRT yaratish

```bash
python3 subtitles/cli.py --input audio.wav --output audio.uz.srt --model large-v3 --fps 25
```

SRT UTF-8 BOM bilan yoziladi. Timestamps kadrga moslanadi. Sheva, fon shovqini va aralash til xatolar keltirishi mumkin, shuning uchun yakuniy subtitrni ko‘zdan kechiring.

`adobe/premiere-uxp` katalogidagi UXP panel SRT importi uchun qo‘shimcha fallback; avtomatik timeline jarayoni CEP panelida.
