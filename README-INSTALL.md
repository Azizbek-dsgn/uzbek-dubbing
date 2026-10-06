# UzScribe — o‘rnatish

O‘rnatish yoki yangilashdan oldin Premiere Pro va After Effects’ni yoping. Intel Mac va Apple Silicon uchun mos Python kutubxonalari avtomatik tanlanadi. GigaAM checkpointining yuklangan nusxasi SHA-256 bilan tekshiriladi.

Bu beta paket. macOS’da lokal transkripsiya sinovdan o‘tgan; Windows’da avtomatik kod testlari o‘tgan, lekin Premiere Pro va After Effects ichida jonli import hali tekshirilmagan.

**Talab:** avvaldan o‘rnatilgan Premiere Pro yoki After Effects va birinchi o‘rnatish uchun internet. Git, Python, `pip` yoki `uv`ni qo‘lda o‘rnatish shart emas. O‘rnatkich kerak bo‘lsa Python 3.12 ni, so‘ng UzScribe Global (Whisper large-v3) va GigaAM Uzbek 600M modellarini tayyorlaydi. GigaAM checkpointining o‘zi taxminan 2.3 GB; Python/PyTorch paketlari va vaqtinchalik fayllar uchun yana bir necha GB bo‘sh joy qoldiring. ZIP paketida UzScribe Global (Whisper large-v3) bor; nutq fayllari kompyuteringizda ishlanadi.

## GitHub’dan bir buyruq bilan o‘rnatish

Quyidagi buyruqlar Git yoki Python’ni oldindan o‘rnatishni talab qilmaydi. Ular GitHub’dan kodni yuklab, Python 3.12 kerak bo‘lsa [uv](https://docs.astral.sh/uv/getting-started/installation/) orqali o‘rnatadi, [Whisper large-v3](https://huggingface.co/Systran/faster-whisper-large-v3) va [GigaAM Uzbek](https://huggingface.co/rustam1221/uzbek-asr-gigaam) modellarini yuklaydi hamda panelni Adobe CEP katalogiga qo‘yadi. Noldan to‘liq o‘rnatish uchun taxminan 25 GB (kamida 22 GiB) bo‘sh disk joyi va internet kerak; keyingi transkripsiya offline ishlaydi. Adobe Premiere Pro yoki After Effects o‘zi avvaldan o‘rnatilgan bo‘lishi kerak.

macOS Terminal:

```sh
bash -c 'set -o pipefail; curl -fsSL "https://raw.githubusercontent.com/Azizbek-dsgn/uzbek-dubbing/feat/uzbek-subtitles-adobe/bootstrap-mac.sh?v=0.8.1" | bash'
```

Windows PowerShell:

```powershell
powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -Command "irm 'https://raw.githubusercontent.com/Azizbek-dsgn/uzbek-dubbing/feat/uzbek-subtitles-adobe/bootstrap-windows.ps1?v=0.8.1' | iex"
```

Windows **Command Prompt (CMD, `C:\Users\...>` oynasi)**:

```bat
powershell -NoProfile -NoExit -ExecutionPolicy Bypass -Command "Invoke-RestMethod 'https://raw.githubusercontent.com/Azizbek-dsgn/uzbek-dubbing/feat/uzbek-subtitles-adobe/bootstrap-windows.ps1?v=0.8.1' | Invoke-Expression"
```

Faqat oynangizga mos **bitta buyruqni** joylang. `bootstrap-windows.ps1` faylining ichidagi `$python`, `Invoke-WebRequest` kabi qatorlarni CMD’ga alohida joylamang; ular PowerShell sintaksisidir.

Yangilash uchun o‘sha buyruqni qayta ishga tushiring; mavjud model qayta yuklanmaydi. O‘rnatish uzilib qolsa, shu buyruqni qayta bajaring. Panel imzosiz beta bo‘lgani uchun skript joriy foydalanuvchida Adobe CEP debug rejimini yoqadi. Adobe dasturlarini qayta oching: **Window → Extensions → UzScribe**. Manifest Premiere Pro 2020+ va After Effects 2020+ versiyalariga mo‘ljallangan; har bir yilning Adobe ichidagi jonli integratsiya sinovi hali tugamagan.

Windows’da xato bo‘lsa PowerShell oynasi ochiq qoladi. Jurnal `%LOCALAPPDATA%\UzbekSubtitles\install.log` faylida saqlanadi; o‘rnatish tugamaganda shu faylning oxirgi qatorlarini yuboring. Xatoni ko‘rmasdan eski o‘rnatmani o‘chirmang.

macOS’da jurnal `~/Library/Application Support/UzbekSubtitles/install.log` faylida saqlanadi. O‘rnatgich uzilgan model yuklashini uch marta urinib ko‘radi, buzilgan Python muhitini eski nusxasini saqlagan holda qayta yaratadi. Yakunda Whisper large-v3 va GigaAM’ni CPU’da amalda ochib, audio ishlov berish sinovini bajaradi. Faqat shu tekshiruv o‘tganda o‘rnatish muvaffaqiyatli deb ko‘rsatiladi. Bu tekshiruv model ishlashini tasdiqlaydi; nutq aniqligi va Adobe ichidagi integratsiya alohida sinov talab qiladi.

## macOS

1. ZIP’ni oching. Python o‘rnatish shart emas; internetni yoqing.
2. `Install-mac.command` ni ishga tushiring. macOS bloklasa, Terminal’da shu papkaga o‘tib `zsh Install-mac.command` bajaring.
3. O‘rnatkich Python, kutubxonalar va GigaAM’ni yuklab, panelni Adobe CEP katalogiga qo‘yadi. Imzolangan `UzScribe.zxp` paketining Adobe o‘rnatuvchisi orqali alohida qo‘shilishi sotuv versiyasi uchun rejalashtirilgan.
4. Premiere Pro yoki After Effects’ni qayta oching: **Window → Extensions → UzScribe**.

## Windows

1. ZIP’ni oching. Python o‘rnatish shart emas; internetni yoqing.
2. PowerShell’da shu papkada `powershell -ExecutionPolicy Bypass -File .\Install-Windows.ps1` bajaring.
3. O‘rnatkich Python, kutubxonalar va GigaAM’ni yuklab, panelni Adobe CEP katalogiga qo‘yadi. Imzolangan `UzScribe.zxp` paketining Adobe o‘rnatuvchisi orqali alohida qo‘shilishi sotuv versiyasi uchun rejalashtirilgan.
4. Premiere Pro yoki After Effects’ni qayta oching: **Window → Extensions → UzScribe**.

Model va Python muhiti macOS’da `~/Library/Application Support/UzbekSubtitles`, Windows’da `%LOCALAPPDATA%\UzbekSubtitles` ga o‘rnatiladi. Audio va SRT ham shu papkaning `exports` qismida saqlanadi. O‘rnatishdagi xatoni to‘liq matni bilan sotuvchiga yuboring. Premiere audio eksport preset’i avtomatik topilmasa, paneldagi **Qo‘shimcha sozlamalar → Fayl va texnik sozlamalar** maydoniga Adobe o‘rnatgan `WAV_Mono_16bit_16kHz.epr` fayl yo‘lini kiriting.

Beta o‘rnatish Adobe CEP `PlayerDebugMode` ni joriy foydalanuvchi uchun yoqadi. Sotuv versiyasi uchun imzolangan ZXP ishlatilishi kerak.


## Podcast montaji

Premiere panelida **Podcast** bo‘limini oching. 1–10 ta odam uchun audio trek va kamera video trekini tanlang; umumiy kamera ixtiyoriy. Har mikrofon alohida timeline trekida, kameralar esa avval sinxronlangan bo‘lishi kerak. Mosliklar va montaj sozlamalari kompyuterda saqlanadi.

- **Kamera almashish + pauzalar:** mikrofonlardagi nutq faolligi bo‘yicha kadr tanlanadi. Qisqa oraliq gaplar kadrni darhol almashtirmaydi; bir vaqtda gaplashish umumiy kamerani tanlashi mumkin.
- **Faqat pauzalarni kesish:** bitta umumiy audio uchun ham ishlaydi. Nutq detektori tilga bog‘liq transkripsiya qilmaydi, shuning uchun o‘zbekcha va boshqa tillarda ishlatish mumkin. Nutq darajasi va mikrofon bleed’i natijaga ta’sir qiladi.
- In/Out tanlansa, faqat shu oraliq montaj qilinadi; undan tashqaridagi kliplar saqlanib, pauzalar olib tashlanganda keyingi material birga siljiydi.
- **Montaj tayyorlash** XML va ko‘rib chiqish hisobotini `exports/podcast` ichiga yozadi. **Yangi sequence qo‘shish** natijani loyiha ichiga import qiladi. Asl sequence va media o‘zgarmaydi. Yangi sequence’ni Project panelidan oching.
- Kadr uzunligi, reaksiyasi, ovoz chegarasi, mikrofon farqi, pauza, pauza yonidagi saqlanadigan vaqt va umumiy kamera oralig‘i sozlanadi.
- Social formatlar markazdan crop qiladi; avtomatik yuz kuzatish yo‘q. Kamera bo‘lmagan oraliq aniqlansa, jarayon xato bilan tugaydi; mavjud muqobil kamera bo‘lsa, shu olinadi.

Hozirgi podcast integratsiyasi **Premiere Pro uchun beta**; After Effects’da subtitr va Animation Composer ishlari davom etadi. Nested/multicam kliplarni flatten qiling, speed/time-remap va transitionlarni avval olib tashlang. FCP7 XML barcha Adobe effektlarini ko‘chirmaydi; montajni effekt va subtitrlardan oldin bajaring. Tahlil manba audio kanalidan olinadi, timeline mixer gain/effect’i hisobga olinmaydi. Umumiy audio ichidan odamga qarab kamera tanlash hozir qo‘llanmaydi.

## Kuchli model nomlari

| Panel nomi | Asl model | O‘rnatish |
|---|---|---|
| UzScribe Uzbek | GigaAM Uzbek 600M | Avtomatik, asosiy |
| UzScribe Global | Whisper large-v3 | Avtomatik, katta model |
| UzScribe Uzbek Studio | NavAI Whisper medium Uzbek | Mavjud bo‘lsa panelda |

Bular paneldagi qulay nomlar; modellarni UzScribe o‘qitgan degan da’vo yo‘q. Small/tiny va tajriba variantlari tanlovdan chiqarildi. Yangilash muvaffaqiyatli tugagach, pluginning `models/navai-small`, `models/small`, `models/tiny` papkalari tozalanadi. Foydalanuvchining boshqa keshlariga tegilmaydi. Standart transkripsiya tili o‘zbekcha. To‘liq model to‘plami va NavAI’ni birinchi tayyorlash uchun vaqtinchalik fayllar ham yuklanadi. Python muhiti bilan taxminan 25 GB (kamida 22 GiB) bo‘sh disk joyi tavsiya etiladi. Yangilashda o‘rnatuvchi faqat yetishmayotgan modellar va ishchi fayllar uchun joy hisoblaydi.

Podcast avtomatik sinovlari: sintetik mikrofonlar bilan FFmpeg tahlili, haqiqiy Silero VAD, kamera tanlash, pauzani kesish, FPS va audio/video sinxronligi, panel workflow hamda host mock. Haqiqiy Premiere Pro’da 2020+ versiyalarning barchasi hali tekshirilmagan.


## Reels — takroriy dubllarni tozalash

Premiere’da **Reels** bo‘limini oching, nutq audio trekini tanlang va **Reels’ni tozalash** tugmasini bosing. Pauzalar qisqaradi, yaqin oraliqda qayta aytilgan aniq gaplar va yarim qolgan boshlanishlar topiladi. Eng to‘liq dubl, teng bo‘lsa oxirgisi qoladi. Natija avtomatik ravishda alohida **UzScribe Reels** sequence sifatida import qilinadi; uni Project panelidan oching. Asl sequence va media o‘zgarmaydi.

Qo‘shimcha sozlamalarda model, In/Out/full, dubl tanlovi, pauza, gap chegarasi va kadr formati bor. **Avval natijani tekshirish** avtomatik importni o‘chiradi. Natijadagi **Bu dubl saqlansin** belgisini yoqib, **Tanlov bo‘yicha qayta tayyorlash** bilan kerakli dubllarni qaytaring. Transkripsiya keshga saqlanadi; audio/model/oraliq o‘zgarmasa qayta ASR bajarilmaydi. Import xatosida natija saqlanib, qayta qo‘shish mumkin.

Ehtiyotkor rejim aniq takrorlar uchun; ikkinchi rejim faqat kichik yordamchi so‘z farqlariga ruxsat beradi. Son, inkor, mazmunli so‘z yoki ishonch darajasi pastligi gapni avtomatik o‘chirishdan saqlaydi. Qasddan qaytarilgan gap ham dublga o‘xshashi mumkin — tayyor montajni tekshiring. Har qanday parafrazani semantik tushunib kesadigan LLM tizimi qo‘shilmagan. Hech qanday API kaliti/obuna talab qilinmaydi; o‘rnatilgandan keyin offline ishlaydi.

Reels hozir Premiere uchun beta. After Effects’da captions ishlaydi. Nested/multicam’ni flatten qiling, audio/video sinxron bo‘lsin, transition/effekt/subtitrlarni keyin qo‘shing. 9:16 tanlovi markazdan crop qiladi. Tahlil timeline mixer effektlaridan oldingi manba audio kanalidan olinadi. Bir nechta video/audio treklar birga siljiydi. [Tadqiqot va tekshiruvlar](docs/REELS-RESEARCH.md).

## Tabiiy subtitr bo‘linishi

Oddiy subtitr rejimida gap/pauza chegaralari va o‘zbekcha yordamchi so‘zlar hisobga olinadi. “Taxminiy so‘z / qator” qat’iy sanash emas: iborani tugatish uchun 1–2 so‘z ortishi mumkin. Qatorlar, belgilar va davomiylik chegaralari saqlanadi. So‘zma-so‘z animatsiya rejimi avvalgidek bir so‘zdan almashadi. Bu lokal qoidalar asosidagi bo‘linish; tinish belgisi yoki tanilgan matn xato bo‘lsa, natijani tahrirlash kerak bo‘lishi mumkin.

## Panel boshqaruvi

Asosiy tugma oynaning pastida doim ko‘rinadi; sozlamalar alohida aylantiriladi. Subtitr uchun nutq modeli asosiy sahifada. Matn uzunligi, gap bo‘linishi, lug‘at va texnik sozlamalar nomlangan ochiladigan bo‘limlarga yig‘ilgan. Reels sahifasida audio, qism va pauza/takroriy dubl tanlovlari darhol ko‘rinadi. Natija fayli yo‘li alohida ochiladigan bo‘limda.

## 0.5.0 — subtitr animatsiyalari

Olti animatsiya, uslub saqlash, so‘z vaqti/urg‘u tahriri, subtitrni birlashtirish va bo‘lish qo‘shildi. AE’da matn qatlamlari, Premiere’da shaffof MOV, AE orqali MOGRT eksporti: [qo‘llanma](docs/ANIMATIONS.md). Yangilash uchun yuqoridagi o‘rnatish buyrug‘ini yana bajaring; modellar qayta yuklanmaydi, mavjud fayllar tekshiriladi. Adobe’ni qayta oching.

### 0.5.1 — tahrir va haqiqiy preview

Tanlangan subtitrning haqiqiy animatsiya preview’i, 40 qadam Undo/Redo va oxirgi tahrirni tiklash qo‘shildi. Wi‑Fi kabi ASR bo‘laklari asl timing bilan moslashtiriladi. AE import xatosida yaratilgan qatlamlar tozalanadi; MOGRT manifestlari boshqa kompyuterga butun papka bilan ko‘chadi.

### 0.5.2 — After Effects alohida ish yo‘li

- Premiere: Sequence → In/Out → WAV preset → caption track yoki animatsiya klipi.
- After Effects: Composition → Work Area (B/N) yoki to‘liq kompozitsiya → native Render Queue audiosi → vaqtli matn qatlamlari. Premiere EPR preset’i AE’da kerak emas. Podcast/Reels montaji hozir Premiere uchun; AE’da bu bo‘limlar yashiriladi.
- AE dasturi `CompItem` va CEP host identifikatori bilan aniqlanadi. `app.name` tekshiruviga bog‘lanmaydi.
- Audio shablonlari nomiga emas, haqiqiy WAV/AIFF formatiga qarab tanlanadi. AIFF avtomatik 16 kHz mono WAV’ga aylantiriladi. Eksportdan so‘ng avvalgi Render Queue navbati tiklanadi.
- Agar AE’da umuman WAV/AIFF Output Module shabloni bo‘lmasa: Render Queue → Output Module’da WAV yoki AIFF tanlang, audio yoqilsin, **UzScribe Audio** nomi bilan shablon saqlang. Panel shu shablonni keyingi safar avtomatik topadi.
- AE importidagi matn va transform parametrlari tilga bog‘lanmagan matchName orqali olinadi.

Mahalliy tekshiruv: 70 Python test, 8 Node test to‘plami va haqiqiy AIFF → WAV konvertatsiyasi o‘tdi. AE sinovlari host API maketlarida tekshirilgan; ochiq Adobe oynasidagi fayl tanlash boshqaruvi javob bermagani sababli ushbu tuzatishning native render/import sinovi hali tasdiqlanmagan.

### 0.6.2 — After Effects subtitr layerlari

Har bir subtitr bloki alohida tahrirlanadigan text layer. So‘z animatsiyalari layer ichida, tartib raqami va o‘z in/out vaqti bilan. Pill uchun bitta qo‘shimcha highlight shape. Panelni yopib qayta oching.

### 0.6.1 — Renuvo sinov integratsiyasi

Avtomatik obuna adapteri, imzolangan webhook tekshiruvi va panelda “Obunani boshqarish”. Public beta community rejimida; Renuvo sandbox/API kaliti va real provayder acceptance alohida talab qilinadi. [Ulanish](https://github.com/Azizbek-dsgn/uzbek-dubbing/blob/feat/uzbek-subtitles-adobe/billing/RENUVO.md).

### 0.6.0 — obuna uchun tayyor tizim

Panelga **Obuna** bo‘limi qo‘shildi: kalit faollashtirish, Payme’da tarif olish/uzaytirish va kompyuterni uzish. Merchant va domen ulanmaguncha public beta **community** rejimida qoladi. Pullik distributiv uchun `tools/build_release.py --license-config` orqali public server konfiguratsiyasini berish kerak.

Tariflar so‘mda; obuna hozir **qo‘lda uzayadi**, kartadan avtomatik yechilmaydi. Serverda tarif, mijoz, muddat, qurilma, to‘lov va audit boshqariladi. [Serverni tayyorlash](https://github.com/Azizbek-dsgn/uzbek-dubbing/blob/feat/uzbek-subtitles-adobe/billing/README.md), [monetizatsiya yo‘llari](https://github.com/Azizbek-dsgn/uzbek-dubbing/blob/feat/uzbek-subtitles-adobe/docs/MONETIZATION.md).


### 0.6.9 · Windows subtitles and After Effects audio

Optional speaker labeling no longer aborts a completed transcription when the
local speaker model or pyannote runtime is unavailable. The SRT is created, with
an explicit warning in the review and JSON metadata; speaker labels can still be
assigned manually. All caption Python processes use UTF-8 on Windows.

For a selected ordinary file video layer (100% speed, no remap/effects, static
0 dB audio levels), After Effects supplies the source file and trim to FFmpeg:
no Render Queue item is created. Layer startTime and Work Area trims are honored;
the source file is never deleted during conversion, cancellation or cleanup.
Stretched/remapped/effected footage and precomps retain the isolated native
WAV/AIFF audio render to preserve the layer's actual sound. This exports audio,
not a finished video. Existing queue flags and original composition are retained.

Verified: 25 subtitle tests, selected-layer/direct-source host tests, and panel
workflow tests with simulated Windows environment, UTF-8, trim and source-file
preservation. Windows native AE was not available for an end-to-end OS test.
Use the same one-command installers above to update; no uninstall is required.


### 0.7.0 · Complete one-command setup

The same Mac/Windows commands now also install NavAI medium Uzbek (converted
locally to int8), Rubai transcript correction, and token-free ONNX speaker
segmentation/embedding models. Python/FFmpeg, GigaAM, Whisper, Silero VAD and
animation dependencies remain automatic. The installer validates feature files,
loads the engines and processes test audio/text before reporting success. A
runtime `install-report.json` lists verified models. Failed/interrupted downloads
can be retried with the same command. Existing complete ASR models are reused;
corrupt speaker files are replaced atomically after SHA-256 verification. New
model downloads need internet and can take time. Software cannot guarantee
success on arbitrary hardware, unavailable network services or blocked Adobe.

AE direct source audio now handles positive static layer stretch (1–10000%) via
FFmpeg tempo and source seek, plus common visual effects such as Lumetri, Curves,
Tint and Gaussian Blur. Work Area/selected layer timing is preserved. Active
unknown/audio effects, animated audio levels, negative stretch, Time Remap and
precomps use isolated native audio rendering to preserve their sound/timing.
No finished video render is produced. Effect-name reference:
https://ae-scripting.docsforadobe.dev/matchnames/effects/firstparty/

Verified locally: speaker model downloads/checksums, Uzbek source audio,
public four-speaker demo (four clusters), Whisper conversion architecture fixture,
real FFmpeg 0.5x/1x/2x durations and original-file preservation, installer/asset
failure tests and Windows panel simulation. Windows native Adobe and a fresh
Intel Mac installation still require separate device tests.

The full offline installer verification also passed on the current Mac: Whisper,
GigaAM, NavAI, ONNX speakers, Rubai generation and animation font loading.
Dynamic model code caches now live in the plugin runtime, avoiding a separate
home-directory cache permission requirement. This is a test of existing models
plus fresh public speaker downloads, not a clean Windows/Intel installation.

### 0.8.0 · Caption design studio

12 replacement presets, 6 manual typography layouts plus automatic selection, configurable shape backgrounds and independent text/shape light sweeps. Installed system fonts are reused; no extra model or browser download is needed. After Effects creates editable native layers; Premiere imports a transparent MOV overlay. Close/reopen the panel after updating. See [animation guide](docs/ANIMATIONS.md).

### 0.8.1 · Disk joyi va model yuklash

`No space left on device` / `Errno 28` — o‘rnatish diskida joy tugagan. Plaginni o‘chirmang: shu diskda joy bo‘shating va yuqoridagi buyruqni qayta bajaring. O‘rnatuvchi yetishmayotgan modellarga qarab **bo‘sh / kerakli GiB** miqdorini ko‘rsatadi; boshqa diskdagi bo‘sh joy C: diskdagi o‘rnatmaga yordam bermaydi.

- Python yuklashidan avval bootstrap diskida kamida 1 GiB tekshiriladi; kutubxona va modellardan avval to‘liq hisob tekshiriladi.
- Disk to‘lishi yuklash uzilishi deb olinmaydi va uch marta qayta urinilmaydi (chiqish kodi 28).
- NavAI xom modeli pluginning `models/.downloads/navai-<revision>` papkasida saqlanadi. Konvertatsiya uzilsa, qayta ishga tushirish shu yuklangan nusxani ishlatadi. Muvaffaqiyatli konvertatsiyadan keyin faqat shu vaqtinchalik nusxa tozalanadi.
- Tayyor NavAI va Global modellari bir disk ichida ko‘chiriladi; `model.bin` uchun ikkinchi katta nusxa yozilmaydi.
- Avvalgi o‘rnatuvchi xatoda o‘chirgan vaqtinchalik NavAI faylini tiklab bo‘lmaydi: bu safar u bir marta qayta yuklanadi.

Bo‘sh joy o‘rnatish davomida boshqa dastur tomonidan kamayishi mumkin. Shunda o‘rnatish tushunarli xato bilan to‘xtaydi; u diskda yangi joy yarata olmaydi.
