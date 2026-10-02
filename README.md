# UzScribe

Premiere Pro va After Effects uchun lokal CEP panel. U faol sequence yoki kompozitsiyadagi audioni eksport qiladi, tanlangan model bilan o‘zbekcha nutqni so‘z vaqtigacha taniydi va subtitrlarni timeline’ga qo‘yadi. API kaliti kerak emas; o‘rnatishdan keyin transkripsiya internet talab qilmaydi.

**Boshqa foydalanuvchilar uchun:** `tools/build_release.py` yordamida Whisper large-v3 modeli bilan macOS/Windows beta ZIP yaratiladi; ZIP o‘rnatkichi GigaAM Uzbek’ni internetdan qo‘shimcha yuklaydi. Xaridor ko‘rsatmasi [README-INSTALL.md](README-INSTALL.md), sotuvdan oldingi majburiy tekshiruvlar [SELLER-RELEASE.md](SELLER-RELEASE.md) faylida. Imzolangan ZXP va haqiqiy Windows sinovi tugamaguncha paketni yakuniy sotuv versiyasi deb belgilamang.

**Terminaldan o‘rnatish:** macOS Terminal, Windows PowerShell yoki Windows CMD uchun [README-INSTALL.md](README-INSTALL.md)dagi tegishli bitta buyruq kodni, kerak bo‘lsa Python’ni, Whisper large-v3 va GigaAM Uzbek 600M modellarini o‘rnatadi. Adobe dasturlarining o‘zi oldindan o‘rnatilgan bo‘lishi kerak.

**Reels montaji:** pauza va qayta yozilgan dubllarni bitta tugmada tozalash, alohida sequence va dubllarni qaytarish. [Yo‘riqnoma](README-INSTALL.md#reels--takroriy-dubllarni-tozalash), [tadqiqot](docs/REELS-RESEARCH.md).

**After Effects 0.5.2:** alohida kompozitsiya, Work Area va Render Queue adapteri. WAV/AIFF shablonlari avtomatik tanlanadi; AE’da Premiere EPR preset’i talab qilinmaydi. [Batafsil](README-INSTALL.md#052--after-effects-alohida-ish-yoli).

## Ishlatish

1. Premiere Pro’da sequence’ni yoki After Effects’da kompozitsiyani oching.
2. Premiere’da In/Out (I/O), AE’da Work Area (B/N) belgilang. Belgilanmagan bo‘lsa butun timeline olinadi.
3. **Window → Extensions → UzScribe** panelini oching. Asosiy ekranda oraliq, qator va so‘z sonini tanlang. Model, gap bo‘linishi, timing va boshqa tanlovlar **Qo‘shimcha sozlamalar** ichida.
4. **Subtitr yaratish** tugmasini bosing. Natija qisqa ro‘yxatda ochiladi: qatorni tanlab, matnini oddiy maydonda tuzating. So‘ng **Timeline’ga qo‘shish** ni bosing. Premiere’da caption track, AE’da vaqtli matn qatlamlari yaratiladi. SRT nusxasi `exports/` papkasida qoladi. **SRT saqlansin** tugmasi timeline’ga qo‘ymasdan faylni saqlaydi.

After Effects’da **Animatsiya → Animation Composer’da ochish** tanlansa, yaratilgan matn qatlamlari tanlanadi va o‘rnatilgan Mister Horse paneli ochiladi. Presetni Composer ichida tanlang. Composer presetini boshqa paneldan avtomatik qo‘llash uchun ochiq API topilmadi. Premiere caption treki AE matn qatlami bo‘lmagani uchun bu tanlov Premiere’da o‘chiriladi.

Tanlangan sozlamalar panel qayta ochilganda saqlanadi. Batafsil SRT vaqt kodlari va qayta tanish **Vaqt va qo‘shimcha tahrir** ichida qoladi.

## Yangi imkoniyatlar

- **UzScribe Uzbek** (GigaAM Uzbek 600M) asosiy model. **UzScribe Global** (Whisper large-v3) ham avtomatik o‘rnatiladi. Mavjud NavAI medium **UzScribe Uzbek Studio** nomida chiqadi. Small/tiny va tajriba variantlari paneldan chiqarilgan. **Ikkinchi model bilan solishtirish** ikkala natijani yaratadi; bu ish vaqtini oshiradi.
- **Podcast** bo‘limi Premiere Pro’da 1–10 mikrofon–kamera mosligi, umumiy kadr, avtomatik kamera tanlash, pauza kesish, In/Out va social center crop sozlamalarini beradi. Natija alohida sequence. [Yo‘riqnoma](README-INSTALL.md#podcast-montaji), [tadqiqot](docs/PODCAST-RESEARCH.md).
- **Adabiy yozuv** tanlovi keng tarqalgan so‘zlashuv shakllarini (`qivotti` → `qilyapti`, `shunaqa` → `shunday`) so‘z vaqtlarini o‘zgartirmasdan to‘g‘rilaydi. Bu cheklangan qoida to‘plami: butun gapni uslubiy qayta yozmaydi. Boshqa iboralarni natija oynasida yoki atamalar lug‘atida tuzating.
- **Tekshirish oynasi** audio to‘lqini, subtitrlar ro‘yxati, past ishonchli so‘zlar va modellar kelishmagan joylarni ko‘rsatadi. Bitta subtitrni tanlab, boshqa model bilan faqat shu oralig‘ini qayta tanish mumkin. GigaAM CTC chiqishida ishonch ballari yo‘q; uning uchun ikkinchi model bilan kelishmovchilik belgilanadi.
- **So‘zlovchilarni ajratish** lokal model bilan ixtiyoriy ishlaydi. So‘zlovchilar sonini avtomatik, 2, 3 yoki 4 ga sozlash, tekshirish oynasida har bir subtitr belgisini qo‘lda tuzatish mumkin. Belgilar JSON va ASS faylida saqlanadi; After Effects’da matn ranglari farqlanadi. Premiere caption track individual ranglarni skript orqali qo‘ymaydi.
- **So‘zma-so‘z** rejimi har so‘z uchun alohida caption yaratadi. After Effects’da so‘z boshlanishida yengil kattalashish/opacity animatsiyasi qo‘shiladi. Premiere’da har so‘z alohida caption bo‘ladi.
- **Lotin/Kirill**, **VTT**, **ASS** chiqishi mavjud. SRT tekshirish oynasida tahrirlansa, VTT/ASS ham qayta yoziladi. Kirill transliteratsiyasi qoida asosida ishlaydi; atoqli otlarni tekshiring.
- Premiere’da **bitta audio trekni** tanlash mumkin. Eksport vaqtida boshqa treklar vaqtincha o‘chiriladi va avvalgi holati tiklanadi. AE’da kompozitsiya ovozi olinadi.
- **Bir nechta media fayl** bo‘limida papka yo‘lini kiriting; har bir audio/video uchun SRT (tanlangan bo‘lsa VTT/ASS ham) `exports/batch/` ichida yaratiladi. Bu bo‘lim fayllarni timeline’ga import qilmaydi.

Yangi model va speaker fayllari o‘rnatilgan runtime `models/` papkasida. Faqat source ZIP’ni boshqa kompyuterga ko‘chirsangiz, modellarni alohida o‘rnatishingiz kerak. Speaker modeli [`pyannote-community/speaker-diarization-community-1`](https://huggingface.co/pyannote-community/speaker-diarization-community-1), CC BY 4.0 litsenziyasi bilan. Uni ishlatish uchun `pip install -r subtitles/requirements-speakers.txt` va model snapshot’ini `models/speaker-diarization/` ga yuklang. Audio torchcodec ishlamaydigan macOS’da ffmpeg orqali xotiraga o‘qiladi.

Bizning 6 ta qisqa FLEURS o‘qib aytilgan nutq sinovimizda (jami 50 referens so‘z) NavAI small 6, GigaAM 8, NavAI medium 9 so‘z xatosi berdi. Bu juda kichik namuna va real suhbatdagi ustunlikni isbotlamaydi. Mualliflar natijalari ham turli benchmarklarda olingan. Sizning audiongiz berilmagani uchun o‘sha nutqda aniqlikni baholay olmadik.

**Atamalar lug‘ati**da takroriy tanish xatolarini har qatorda `xato = to‘g‘ri` shaklida kiriting. Har bir qoida bitta so‘zni almashtiradi; so‘zning audio vaqti o‘zgarmaydi. Gap yoki iboralarni natija oynasida tuzating.

Ko‘rib chiqish oynasidagi SRT formatini saqlang: har bir blokda raqam, `00:00:00,000 --> 00:00:01,000` shaklidagi vaqt va matn bo‘lishi kerak. Panel bo‘sh yoki ustma-ust vaqtlarni import qilishdan oldin bildiradi. Faol timeline transkripsiya vaqtida almashtirilsa, panel uning identifikatorini tekshirib, boshqa sequence yoki kompozitsiyaga subtitr qo‘yishdan saqlaydi.

Oraliq tanlovida **Faqat In/Out** belgilar bo‘lmasa xato beradi; **To‘liq timeline** belgilarni e’tiborsiz qoldiradi. GigaAM Uzbek o‘rnatilgan bo‘lsa panel uni dastlab tanlaydi. Panelda faqat GigaAM, Whisper large-v3 va o‘rnatilgan NavAI medium tanlanadi. GigaAM tinish belgilarini va so‘z vaqtlarini o‘z CTC chiqishidan oladi. Qator va so‘z chegaralari transkripsiya matnini bo‘ladi; xato eshitilgan so‘zni o‘zi tuzatmaydi.

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
