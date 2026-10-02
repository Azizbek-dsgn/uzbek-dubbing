# UzScribe — o‘rnatish

O‘rnatish yoki yangilashdan oldin Premiere Pro va After Effects’ni yoping. Intel Mac va Apple Silicon uchun mos Python kutubxonalari avtomatik tanlanadi. GigaAM checkpointining yuklangan nusxasi SHA-256 bilan tekshiriladi.

Bu beta paket. macOS’da lokal transkripsiya sinovdan o‘tgan; Windows’da avtomatik kod testlari o‘tgan, lekin Premiere Pro va After Effects ichida jonli import hali tekshirilmagan.

**Talab:** avvaldan o‘rnatilgan Premiere Pro yoki After Effects va birinchi o‘rnatish uchun internet. Git, Python, `pip` yoki `uv`ni qo‘lda o‘rnatish shart emas. O‘rnatkich kerak bo‘lsa Python 3.12 ni, so‘ng UzScribe Global (Whisper large-v3) va GigaAM Uzbek 600M modellarini tayyorlaydi. GigaAM checkpointining o‘zi taxminan 2.3 GB; Python/PyTorch paketlari va vaqtinchalik fayllar uchun yana bir necha GB bo‘sh joy qoldiring. ZIP paketida UzScribe Global (Whisper large-v3) bor; nutq fayllari kompyuteringizda ishlanadi.

## GitHub’dan bir buyruq bilan o‘rnatish

Quyidagi buyruqlar Git yoki Python’ni oldindan o‘rnatishni talab qilmaydi. Ular GitHub’dan kodni yuklab, Python 3.12 kerak bo‘lsa [uv](https://docs.astral.sh/uv/getting-started/installation/) orqali o‘rnatadi, [Whisper large-v3](https://huggingface.co/Systran/faster-whisper-large-v3) va [GigaAM Uzbek](https://huggingface.co/rustam1221/uzbek-asr-gigaam) modellarini yuklaydi hamda panelni Adobe CEP katalogiga qo‘yadi. Birinchi o‘rnatishda bir necha gigabayt bo‘sh disk joyi va internet kerak; keyingi transkripsiya offline ishlaydi. Adobe Premiere Pro yoki After Effects o‘zi avvaldan o‘rnatilgan bo‘lishi kerak.

macOS Terminal:

```sh
bash -c 'set -o pipefail; curl -fsSL https://raw.githubusercontent.com/Azizbek-dsgn/uzbek-dubbing/feat/uzbek-subtitles-adobe/bootstrap-mac.sh | bash'
```

Windows PowerShell:

```powershell
powershell.exe -NoProfile -NoExit -ExecutionPolicy Bypass -Command "irm 'https://raw.githubusercontent.com/Azizbek-dsgn/uzbek-dubbing/feat/uzbek-subtitles-adobe/bootstrap-windows.ps1' | iex"
```

Windows **Command Prompt (CMD, `C:\Users\...>` oynasi)**:

```bat
powershell -NoProfile -NoExit -ExecutionPolicy Bypass -Command "Invoke-RestMethod 'https://raw.githubusercontent.com/Azizbek-dsgn/uzbek-dubbing/feat/uzbek-subtitles-adobe/bootstrap-windows.ps1' | Invoke-Expression"
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

Bular paneldagi qulay nomlar; modellarni UzScribe o‘qitgan degan da’vo yo‘q. Small/tiny va tajriba variantlari tanlovdan chiqarildi. Yangilash muvaffaqiyatli tugagach, pluginning `models/navai-small`, `models/small`, `models/tiny` papkalari tozalanadi. Foydalanuvchining boshqa keshlariga tegilmaydi. Standart transkripsiya tili o‘zbekcha. Global model va GigaAM jami taxminan 5.4 GB; Python muhiti bilan kamida 12 GB bo‘sh disk joyi tavsiya etiladi.

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

### 0.6.0 — obuna uchun tayyor tizim

Panelga **Obuna** bo‘limi qo‘shildi: kalit faollashtirish, Payme’da tarif olish/uzaytirish va kompyuterni uzish. Merchant va domen ulanmaguncha public beta **community** rejimida qoladi. Pullik distributiv uchun `tools/build_release.py --license-config` orqali public server konfiguratsiyasini berish kerak.

Tariflar so‘mda; obuna hozir **qo‘lda uzayadi**, kartadan avtomatik yechilmaydi. Serverda tarif, mijoz, muddat, qurilma, to‘lov va audit boshqariladi. [Serverni tayyorlash](https://github.com/Azizbek-dsgn/uzbek-dubbing/blob/feat/uzbek-subtitles-adobe/billing/README.md), [monetizatsiya yo‘llari](https://github.com/Azizbek-dsgn/uzbek-dubbing/blob/feat/uzbek-subtitles-adobe/docs/MONETIZATION.md).
