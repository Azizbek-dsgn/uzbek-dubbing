# O‘zbekcha subtitr plagini

Premiere Pro va After Effects uchun bepul, lokal CEP panel. U faol sequence yoki kompozitsiyadagi audioni eksport qiladi, tanlangan model bilan o‘zbekcha nutqni so‘z vaqtigacha taniydi va subtitrlarni timeline’ga qo‘yadi. API kaliti kerak emas; model bir marta yuklangach internet talab qilinmaydi.

## Ishlatish

1. Premiere Pro’da sequence’ni yoki After Effects’da kompozitsiyani oching.
2. Kerakli joyga In/Out nuqtalarini qo‘ying. AE’da Work Area belgilang. Belgilanmagan bo‘lsa butun timeline olinadi.
3. **Window → Extensions → Uzbek Subtitles** panelini oching, oraliq va modelni tanlang. Qisqa, O‘rta yoki Uzun uslubini tanlang yoki qatorlar soni, har qatordagi so‘z, belgi va davomiylikni qo‘lda kiriting. Nuqta/undov/so‘roq, vergul va pauza bo‘yicha bo‘lishni alohida yoqing. Boshlanish/oxir vaqtini millisekundlarda surish va minimal ko‘rinish vaqtini ham sozlash mumkin.
4. **Timeline’ga subtitr qo‘shish** tugmasi bir bosishda import qiladi. **Avval matnni tekshirish** tugmasi SRT matni va vaqtlarini tahrirlash oynasini ochadi; tekshirgach timeline’ga joylang. Transkripsiya foizi panelda ko‘rinadi va **Bekor qilish** mumkin; Adobe audio eksporti boshlangan bo‘lsa bekor qilish eksport tugagach yakunlanadi. Premiere’da caption track, AE’da vaqtli matn qatlamlari yaratiladi. SRT nusxasi `exports/` papkasida qoladi.

Panelning asosiy qismida timeline, model, uslub, qator va so‘z soni ko‘rinadi. Gap bo‘linishi, pauza, timing, FPS va Python yo‘li **Batafsil sozlamalar** ichida. Tanlangan sozlamalar panel qayta ochilganda saqlanadi.

**Atamalar lug‘ati**da takroriy tanish xatolarini har qatorda `xato = to‘g‘ri` shaklida kiriting. Har bir qoida bitta so‘zni almashtiradi; so‘zning audio vaqti o‘zgarmaydi. Gap yoki iboralarni tuzatish uchun **Avval matnni tekshirish** rejimidan foydalaning.

Ko‘rib chiqish oynasidagi SRT formatini saqlang: har bir blokda raqam, `00:00:00,000 --> 00:00:01,000` shaklidagi vaqt va matn bo‘lishi kerak. Panel bo‘sh yoki ustma-ust vaqtlarni import qilishdan oldin bildiradi. Faol timeline transkripsiya vaqtida almashtirilsa, panel boshqa loyihaga subtitr qo‘yishdan saqlaydi.

Oraliq tanlovida **Faqat In/Out** belgilar bo‘lmasa xato beradi; **To‘liq timeline** belgilarni e’tiborsiz qoldiradi. GigaAM Uzbek o‘rnatilgan bo‘lsa panel uni dastlab tanlaydi. NavAI va umumiy `large-v3`, `medium`, `small` modellari ham qoladi. GigaAM tinish belgilarini va so‘z vaqtlarini o‘z CTC chiqishidan oladi. Qator va so‘z chegaralari transkripsiya matnini bo‘ladi; xato eshitilgan so‘zni o‘zi tuzatmaydi.

## Suhbat nutqi uchun GigaAM Uzbek

[`rustam1221/uzbek-asr-gigaam`](https://huggingface.co/rustam1221/uzbek-asr-gigaam) `large_full_600m` modeli o‘zbekcha suhbat nutqiga moslashtirilgan. Uni o‘rnatish uchun loyiha ildizida:

```bash
python3 -m pip install -r subtitles/requirements.txt -r subtitles/requirements-gigaam.txt huggingface_hub
python3 -c 'from huggingface_hub import snapshot_download; snapshot_download("ai-sage/GigaAM-Multilingual", revision="large_ctc", local_dir="models/gigaam-base-large", allow_patterns=["config.json", "modeling_gigaam.py"])'
python3 -c 'from huggingface_hub import hf_hub_download; hf_hub_download("rustam1221/uzbek-asr-gigaam", "checkpoints/large_full_600m/best.pt", local_dir="models/gigaam-uzbek")'
```

Taxminan 2.3 GB checkpoint yuklanadi. Mavjud o‘rnatilgan plagin uchun Python paketlarini uning `.venv/bin/python` fayli bilan o‘rnating. Model bir marta yuklangach internet talab qilmaydi. Boshqa ovozlar, shevalar va shovqinda sifat o‘zgaradi; yakuniy subtitrni tekshiring.

## O‘zbekchaga maxsus model

[`navai-uz/whisper-medium-uzbek`](https://huggingface.co/navai-uz/whisper-medium-uzbek) Apache-2.0 litsenziyali model. Uni `faster-whisper` uchun CTranslate2 `int8` formatiga o‘girib `models/navai-medium/` papkasiga joylang:

```bash
python3 -m pip install 'transformers>=4.40,<5' 'torch>=2.2'
python3 -c 'from huggingface_hub import snapshot_download; snapshot_download("navai-uz/whisper-medium-uzbek", local_dir="models/navai-medium-source")'
python3 -c 'from transformers import AutoTokenizer; p="models/navai-medium-source"; AutoTokenizer.from_pretrained(p, use_fast=True).save_pretrained(p)'
ct2-transformers-converter --model models/navai-medium-source \
  --output_dir models/navai-medium --quantization int8 \
  --copy_files tokenizer.json preprocessor_config.json
```

Konvertatsiya uchun qo‘shimcha disk va xotira kerak. Model bir marta tayyorlangach lokal ishlaydi. Nutqdagi sheva, shovqin yoki ruscha/turkcha aralash so‘zlar uchun 100% aniqlik kafolati yo‘q.

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
