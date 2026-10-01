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
