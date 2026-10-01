# UzScribe — o‘rnatish

Bu beta paket. macOS’da lokal transkripsiya sinovdan o‘tgan; Windows’da avtomatik kod testlari o‘tgan, lekin Premiere Pro va After Effects ichida jonli import hali tekshirilmagan.

**Talab:** Premiere Pro yoki After Effects, internet (birinchi o‘rnatishda modellar va Python paketlari uchun), Python 3.10–3.12. Bir buyruqli o‘rnatishda NavAI small va GigaAM Uzbek 600M yuklanadi; GigaAM checkpointining o‘zi taxminan 2.3 GB. Python/PyTorch paketlari va vaqtinchalik fayllar uchun yana bir necha GB bo‘sh joy qoldiring. ZIP paketida NavAI small bor; nutq fayllari kompyuteringizda ishlanadi.

## GitHub’dan bir buyruq bilan o‘rnatish

Quyidagi buyruqlar Git yoki Python’ni oldindan o‘rnatishni talab qilmaydi. Ular GitHub’dan kodni yuklab, Python 3.12 kerak bo‘lsa [uv](https://docs.astral.sh/uv/getting-started/installation/) orqali o‘rnatadi, [NavAI](https://huggingface.co/navai-uz/whisper-small-uzbek) va [GigaAM Uzbek](https://huggingface.co/rustam1221/uzbek-asr-gigaam) modellarini yuklaydi hamda panelni Adobe CEP katalogiga qo‘yadi. Birinchi o‘rnatishda bir necha gigabayt bo‘sh disk joyi va internet kerak; keyingi transkripsiya offline ishlaydi. Adobe Premiere Pro yoki After Effects o‘zi avvaldan o‘rnatilgan bo‘lishi kerak.

macOS Terminal:

```sh
bash -c 'set -o pipefail; curl -fsSL https://raw.githubusercontent.com/Azizbek-dsgn/uzbek-dubbing/feat/uzbek-subtitles-adobe/bootstrap-mac.sh | bash'
```

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/Azizbek-dsgn/uzbek-dubbing/feat/uzbek-subtitles-adobe/bootstrap-windows.ps1 | iex
```

Windows **Command Prompt (CMD, `C:\Users\...>` oynasi)**:

```bat
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-RestMethod 'https://raw.githubusercontent.com/Azizbek-dsgn/uzbek-dubbing/feat/uzbek-subtitles-adobe/bootstrap-windows.ps1' | Invoke-Expression"
```

Faqat oynangizga mos **bitta buyruqni** joylang. `bootstrap-windows.ps1` faylining ichidagi `$python`, `Invoke-WebRequest` kabi qatorlarni CMD’ga alohida joylamang; ular PowerShell sintaksisidir.

Yangilash uchun o‘sha buyruqni qayta ishga tushiring; mavjud model qayta yuklanmaydi. O‘rnatish uzilib qolsa, shu buyruqni qayta bajaring. Panel imzosiz beta bo‘lgani uchun skript joriy foydalanuvchida Adobe CEP debug rejimini yoqadi. Adobe dasturlarini qayta oching: **Window → Extensions → UzScribe**. Manifest Premiere Pro 2020+ va After Effects 2020+ versiyalariga mo‘ljallangan; har bir yilning Adobe ichidagi jonli integratsiya sinovi hali tugamagan.

## macOS

1. ZIP’ni oching. Python 3.10–3.12 o‘rnatilgan bo‘lsin.
2. `Install-mac.command` ni ishga tushiring. macOS bloklasa, Terminal’da shu papkaga o‘tib `zsh Install-mac.command` bajaring.
3. Paketda `UzScribe.zxp` bo‘lsa, uni ikki marta bosib Adobe o‘rnatuvchisi orqali qo‘shing. Beta ZIP’da ZXP bo‘lmasa skript panelni test rejimida o‘zi o‘rnatadi.
4. Premiere Pro yoki After Effects’ni qayta oching: **Window → Extensions → UzScribe**.

## Windows

1. ZIP’ni oching. Python 3.10–3.12 ni `python.org` dan o‘rnating va Python Launcher (`py`)ni tanlang.
2. PowerShell’da shu papkada `powershell -ExecutionPolicy Bypass -File .\Install-Windows.ps1` bajaring.
3. Paketda `UzScribe.zxp` bo‘lsa, uni ikki marta bosib Adobe o‘rnatuvchisi orqali qo‘shing. Beta ZIP’da ZXP bo‘lmasa skript panelni test rejimida o‘zi o‘rnatadi.
4. Premiere Pro yoki After Effects’ni qayta oching: **Window → Extensions → UzScribe**.

Model va Python muhiti macOS’da `~/Library/Application Support/UzbekSubtitles`, Windows’da `%LOCALAPPDATA%\UzbekSubtitles` ga o‘rnatiladi. Audio va SRT ham shu papkaning `exports` qismida saqlanadi. O‘rnatishdagi xatoni to‘liq matni bilan sotuvchiga yuboring. Premiere audio eksport preset’i avtomatik topilmasa, paneldagi **Qo‘shimcha sozlamalar → Fayl va texnik sozlamalar** maydoniga Adobe o‘rnatgan `WAV_Mono_16bit_16kHz.epr` fayl yo‘lini kiriting.

Beta o‘rnatish Adobe CEP `PlayerDebugMode` ni joriy foydalanuvchi uchun yoqadi. Sotuv versiyasi uchun imzolangan ZXP ishlatilishi kerak.
