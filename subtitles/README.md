# O‘zbekcha subtitr plagini

Premiere Pro va After Effects uchun lokal subtitr yechimi. O‘zbekcha nutqni `faster-whisper` bilan o‘qiydi, so‘z vaqtlaridan ikki qatorli subtitrlar tuzadi va `.srt` yaratadi. Gemini kaliti, pullik API va TTS kerak emas. Model birinchi ishlatishda yuklanadi; undan keyin transkripsiya kompyuterda bajariladi.

## Talablar

- Python 3.10 yoki yangiroq
- `pip install -r subtitles/requirements.txt`
- CEP paneli uchun uni qo‘llaydigan Premiere Pro yoki After Effects versiyasi; yangi Premiere uchun UXP import paneli ham bor
- Model uchun disk joyi va yetarli RAM; `large-v3` eng sifatli, `medium` tezroq

## CEP panelini o‘rnatish (After Effects va mos Premiere versiyalari)

Repo katalogini kompyuterga saqlang. `adobe/UzbekSubtitles` papkasini **symlink** sifatida CEP extensions katalogiga ulang, shunda panel Python modulini repo ichidan topadi:

macOS:

```bash
mkdir -p "$HOME/Library/Application Support/Adobe/CEP/extensions"
ln -s "$(pwd)/adobe/UzbekSubtitles" "$HOME/Library/Application Support/Adobe/CEP/extensions/UzbekSubtitles"
```

Windows PowerShell (Developer Mode yoki administrator huquqi bilan):

```powershell
New-Item -ItemType SymbolicLink -Path "$env:APPDATA\Adobe\CEP\extensions\UzbekSubtitles" -Target "$(Get-Location)\adobe\UzbekSubtitles"
```

Bu manba kodidagi imzosiz CEP paneli. Ishlab chiqish rejimida `PlayerDebugMode=1` yoqilishi kerak; Adobe’ning CEP qo‘llanmasidagi operatsion tizimingizga mos ko‘rsatmadan foydalaning. Adobe dasturini qayta ishga tushirib, **Window → Extensions → Uzbek Subtitles** ni oching.

## Yangi Premiere uchun UXP paneli

Premiere Pro 25.6+ da `adobe/premiere-uxp` papkasini **UXP Developer Tool** orqali yuklang (Premiere’da Developer Mode yoqilgan bo‘lishi kerak). UXP paneli SRT’ni loyiha ichiga import qiladi. Hozircha UXP ichidan Python jarayonini ishga tushirish yo‘q: avval pastdagi CLI bilan SRT yarating, keyin **SRT import qilish** ni bosing. Adobe UXP jarayon ishga tushirish APIsi argument va chiqishni bermaydi, shu sabab avtomatik transkripsiya CEP panelida mavjud.

## Ishlatish

1. Video/audio faylni tanlang; Python yo‘lini kerak bo‘lsa to‘liq ko‘rsating.
2. Model va timeline FPS ni tanlab **Subtitr yaratish** ni bosing.
3. Media yonida `<nom>.uz.srt` yaratiladi. Premiere Pro’da u loyiha ichiga import qilinadi; caption track uchun uni timeline’ga torting. After Effects’da faol kompozitsiyaga vaqtli matn qatlamlari qo‘shiladi.

Faylni boshqa yo‘l bilan ham yaratish mumkin:

```bash
python3 subtitles/cli.py --input video.mp4 --output video.uz.srt --model large-v3 --fps 25
```

SRT UTF-8 BOM bilan yoziladi, Adobe importi uchun. So‘z vaqt kodlari kadrga moslanadi. Murakkab fon, aralash til va sheva aniqlikka ta’sir qilishi mumkin; yakuniy subtitrni tahririyat tekshiruvidan o‘tkazing.
