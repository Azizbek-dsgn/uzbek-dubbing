# O‘zbekcha subtitr plagini

Premiere Pro va After Effects uchun lokal CEP panel. U faol sequence yoki kompozitsiyadagi audioni eksport qiladi, tanlangan model bilan o‘zbekcha nutqni so‘z vaqtigacha taniydi va subtitrlarni timeline’ga qo‘yadi. API kaliti kerak emas; o‘rnatishdan keyin transkripsiya internet talab qilmaydi.

## Ishlatish

1. Premiere Pro’da sequence’ni yoki After Effects’da kompozitsiyani oching.
2. Kerakli joyga In/Out nuqtalarini qo‘ying. AE’da Work Area belgilang. Belgilanmagan bo‘lsa butun timeline olinadi.
3. **Window → Extensions → UzScribe** panelini oching. Asosiy ekranda oraliq, qator va so‘z sonini tanlang. Model, gap bo‘linishi, timing va boshqa tanlovlar **Qo‘shimcha sozlamalar** ichida.
4. **Subtitr yaratish** tugmasini bosing. Natija qisqa ro‘yxatda ochiladi: qatorni tanlab, matnini oddiy maydonda tuzating. So‘ng **Timeline’ga qo‘shish** ni bosing. Premiere’da caption track, AE’da vaqtli matn qatlamlari yaratiladi. SRT nusxasi `exports/` papkasida qoladi. **SRT saqlansin** tugmasi timeline’ga qo‘ymasdan faylni saqlaydi.

After Effects’da **Animatsiya → Animation Composer’da ochish** tanlansa, yaratilgan matn qatlamlari tanlanadi va o‘rnatilgan Mister Horse paneli ochiladi. Presetni Composer ichida tanlang. Composer presetini boshqa paneldan avtomatik qo‘llash uchun ochiq API topilmadi. Premiere caption treki AE matn qatlami bo‘lmagani uchun bu tanlov Premiere’da o‘chiriladi.

Tanlangan sozlamalar panel qayta ochilganda saqlanadi. Batafsil SRT vaqt kodlari va qayta tanish **Vaqt va qo‘shimcha tahrir** ichida qoladi.

## Yangi imkoniyatlar

- **NavAI Uzbek small** mahalliy, yengilroq model sifatida o‘rnatilgan. Tabiiy suhbat uchun GigaAM Uzbek 600M dastlab tanlanadi; boshqa ovozlarda NavAI small va medium’ni sinab ko‘ring. **Ikkinchi model bilan solishtirish** yoqilsa, ikkala natija yaratiladi va tekshirish oynasida farqlari ko‘rsatiladi. Bu ish vaqtini taxminan ikki baravar oshiradi.
- **Gap va tinish belgilarini tiklash** odatda yoqilgan. Agar `models/rubai-transcript/` ichida [`islomov/rubai-corrector-transcript-uz`](https://huggingface.co/islomov/rubai-corrector-transcript-uz) modeli o‘rnatilgan bo‘lsa, u gap boshidagi bosh harf va tinish belgilarini taklif qiladi. Panel faqat tanilgan so‘zlarga mos tushgan belgilarni oladi; so‘zlarning o‘zi, tartibi va vaqtini o‘zgartirmaydi. Model mavjud bo‘lmasa, kuchli pauza va audio modelning o‘z belgilariga tayanadi. Tinish belgilari xato bo‘lishi mumkin; tekshirish oynasida tuzating.
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

Oraliq tanlovida **Faqat In/Out** belgilar bo‘lmasa xato beradi; **To‘liq timeline** belgilarni e’tiborsiz qoldiradi. GigaAM Uzbek o‘rnatilgan bo‘lsa panel uni dastlab tanlaydi. NavAI va umumiy `large-v3`, `medium`, `small` modellari ham qoladi. GigaAM tinish belgilarini va so‘z vaqtlarini o‘z CTC chiqishidan oladi. **So‘z / qator** va **Qatorlar** faqat ekrandagi subtitr hajmini belgilaydi; uzun gap bir nechta captionga davom etadi. Bu sozlamalar eshitilgan so‘zlarni tuzatmaydi.

Matn modelini boshqa kompyuterga o‘rnatish uchun loyiha ildizida `pip install transformers torch huggingface_hub` va quyidagini bajaring (model vaznlari source ZIP’ga kiritilmagan):

```bash
python3 -c 'from huggingface_hub import snapshot_download; snapshot_download("islomov/rubai-corrector-transcript-uz", local_dir="models/rubai-transcript", allow_patterns=["*.json", "model.safetensors"])'
```

Modelning o‘zi gap chegaralarini har doim topmaydi. Ayniqsa pauzasiz, tinish belgisiz uzun nutqda tekshirish oynasida gaplarni qo‘lda bo‘lish kerak bo‘lishi mumkin.

## Suhbat nutqi uchun GigaAM Uzbek

[`rustam1221/uzbek-asr-gigaam`](https://huggingface.co/rustam1221/uzbek-asr-gigaam) `large_full_600m` modeli o‘zbekcha suhbat nutqiga moslashtirilgan. Uni o‘rnatish uchun loyiha ildizida:

```bash
python3 -m pip install -r subtitles/requirements.txt -r subtitles/requirements-gigaam.txt huggingface_hub
python3 -c 'from huggingface_hub import snapshot_download; snapshot_download("ai-sage/GigaAM-Multilingual", revision="large_ctc", local_dir="models/gigaam-base-large", allow_patterns=["config.json", "modeling_gigaam.py"])'
python3 -c 'from huggingface_hub import hf_hub_download; hf_hub_download("rustam1221/uzbek-asr-gigaam", "checkpoints/large_full_600m/best.pt", local_dir="models/gigaam-uzbek")'
```

[`zafarrr/uzbek-stt-fastconformer-v1.2`](https://huggingface.co/zafarrr/uzbek-stt-fastconformer-v1.2) Apache-2.0 litsenziyali qo‘shimcha mahalliy model. So‘z vaqtlarini NeMo orqali beradi. Model kartasidagi 8,31% WER boshqa testga tegishli; bizning 6 ta FLEURS namunamizda 12/50 xato qildi (GigaAM 8/50). Shu sabab panelda **tajriba** deb ko‘rsatiladi va GigaAM o‘rniga avtomatik tanlanmaydi. Alohida solishtirish yoki ayrim qatorlarni qayta tanish uchun ishlating. O‘rnatish:

```sh
python3 -m pip install -r subtitles/requirements-fastconformer.txt huggingface_hub
python3 -c 'from huggingface_hub import snapshot_download; snapshot_download("zafarrr/uzbek-stt-fastconformer-v1.2", local_dir="models/zafar-fastconformer", allow_patterns=["uzbek_stt_v12.nemo", "README.md"])'
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

Xaridor ZIP’i uchun loyiha ildizidagi `README-INSTALL.md`dan foydalaning. Quyidagi usul faqat manba kodidan development o‘rnatish uchun: Python 3.10–3.12 bilan `pip install -r subtitles/requirements.txt` bajaring, `adobe/UzbekSubtitles` papkasini Adobe CEP extensions katalogiga symlink qiling. Imzosiz development paneli uchun `PlayerDebugMode=1` kerak. Adobe dasturini qayta ishga tushiring. Mac’da:

```bash
mkdir -p "$HOME/Library/Application Support/Adobe/CEP/extensions"
ln -s "$(pwd)/adobe/UzbekSubtitles" "$HOME/Library/Application Support/Adobe/CEP/extensions/UzbekSubtitles"
```

Panel o‘rnatilgan runtime’dagi `.venv` Python’ni o‘zi topadi; boshqa Python ishlatsangiz paneldagi yo‘lni o‘zgartiring. Premiere eksporti Adobe o‘rnatgan `WAV_Mono_16bit_16kHz.epr` presetiga tayanadi; avtomatik qidiruv ishlamasa panelning texnik sozlamalarida fayl yo‘lini kiriting.

## Alohida SRT yaratish

```bash
python3 subtitles/cli.py --input audio.wav --output audio.uz.srt --model large-v3 --fps 25
```

SRT UTF-8 BOM bilan yoziladi. Timestamps kadrga moslanadi. Sheva, fon shovqini va aralash til xatolar keltirishi mumkin, shuning uchun yakuniy subtitrni ko‘zdan kechiring.

`adobe/premiere-uxp` katalogidagi UXP panel SRT importi uchun qo‘shimcha fallback; avtomatik timeline jarayoni CEP panelida.
