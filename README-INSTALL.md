# Uzbek Subtitles — o‘rnatish

Bu beta paket. macOS’da lokal transkripsiya sinovdan o‘tgan; Windows’da avtomatik kod testlari o‘tgan, lekin Premiere Pro va After Effects ichida jonli import hali tekshirilmagan.

**Talab:** Premiere Pro yoki After Effects, internet (birinchi o‘rnatishda Python paketlari uchun), Python 3.10–3.12, taxminan 1 GB bo‘sh joy. NavAI small modeli ZIP ichida; nutq fayllari kompyuteringizda ishlanadi.

## macOS

1. ZIP’ni oching. Python 3.10–3.12 o‘rnatilgan bo‘lsin.
2. `Install-mac.command` ni ishga tushiring. macOS bloklasa, Terminal’da shu papkaga o‘tib `zsh Install-mac.command` bajaring.
3. Paketda `UzbekSubtitles.zxp` bo‘lsa, uni ikki marta bosib Adobe o‘rnatuvchisi orqali qo‘shing. Beta ZIP’da ZXP bo‘lmasa skript panelni test rejimida o‘zi o‘rnatadi.
4. Premiere Pro yoki After Effects’ni qayta oching: **Window → Extensions → Uzbek Subtitles**.

## Windows

1. ZIP’ni oching. Python 3.10–3.12 ni `python.org` dan o‘rnating va Python Launcher (`py`)ni tanlang.
2. PowerShell’da shu papkada `powershell -ExecutionPolicy Bypass -File .\Install-Windows.ps1` bajaring.
3. Paketda `UzbekSubtitles.zxp` bo‘lsa, uni ikki marta bosib Adobe o‘rnatuvchisi orqali qo‘shing. Beta ZIP’da ZXP bo‘lmasa skript panelni test rejimida o‘zi o‘rnatadi.
4. Premiere Pro yoki After Effects’ni qayta oching: **Window → Extensions → Uzbek Subtitles**.

Model va Python muhiti macOS’da `~/Library/Application Support/UzbekSubtitles`, Windows’da `%LOCALAPPDATA%\UzbekSubtitles` ga o‘rnatiladi. Audio va SRT ham shu papkaning `exports` qismida saqlanadi. O‘rnatishdagi xatoni to‘liq matni bilan sotuvchiga yuboring. Premiere audio eksport preset’i avtomatik topilmasa, paneldagi **Qo‘shimcha sozlamalar → Fayl va texnik sozlamalar** maydoniga Adobe o‘rnatgan `WAV_Mono_16bit_16kHz.epr` fayl yo‘lini kiriting.

Beta o‘rnatish Adobe CEP `PlayerDebugMode` ni joriy foydalanuvchi uchun yoqadi. Sotuv versiyasi uchun imzolangan ZXP ishlatilishi kerak.
