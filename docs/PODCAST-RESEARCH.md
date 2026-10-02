# Podcast montaji tadqiqoti — 2026-10-02

## Manbalar

- [AutoPod rasmiy sayti](https://www.autopod.fm/): 10 kamera / 10 mikrofon, sozlanadigan wide shot, pauzaga ko‘ra jump cut, social In/Out yangi sequence va auto-reframe. AutoPodning o‘z ochiq kodini tasdiqlaydigan manba topilmadi.
- [Podcut](https://github.com/benjaminkapell/podcut): MIT, lokal mikrofon loudness va ixtiyoriy pyannote diarizatsiya; Premiere FCP7 XML. Repo hali yosh: uni tayyor ishlab chiqarish poydevori deb qabul qilinmadi.
- [Auto-Editor](https://github.com/WyattBlue/auto-editor): Unlicense, audio faolligiga ko‘ra bo‘sh vaqtlarni olib tashlash va Premiere eksporti.
- [Premiere sequence XML eksporti](https://ppro-scripting.docsforadobe.dev/sequence/sequence/#sequenceexportasfinalcutproxml), [Project importFiles](https://ppro-scripting.docsforadobe.dev/general/project/#projectimportfiles): hujjatlashtirilgan ExtendScript usullari.
- [Apple FCP XML elementlari](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/FinalCutPro_XML/Elements/Elements.html).

## UzScribe’da qo‘shilgan

O‘z algoritmimiz: timeline FCP7 XML → har mikrofonning original source kanalidan FFmpeg PCM → bundled Silero nutq detektori + loudness → minimal kadr/reaksiya/bleed farqi/wide qoidalari → frame grid bo‘yicha pauza va kamera jadvali → yangi XML → Premiere’da alohida sequence importi. Transkripsiya talab etilmaydi, nutq tili montaj algoritmini almashtirmaydi.

1–10 foydalanuvchi belgilaydigan audio/video moslik, umumiy kamera, saqlanadigan sozlamalar, In/Out yoki full, pauza handle’lari, cut report, bekor qilish va import uchun active sequence ID tekshiruvi bor. Social formatlar statik center crop; AutoPoddagi auto-reframe, watermark/endpage va batch render hali yo‘q. Umumiy audioda kameralarni diarizatsiyaga ko‘ra tanlash ham yo‘q; faqat pauza kesish ishlaydi. After Effects podcast montaji qo‘llanmaydi.

Sinxronlangan oddiy kliplar kerak. FCP XML Premiere effektlarini to‘liq saqlamasligi mumkin. Manba fayllar va asl sequence o‘zgartirilmaydi. Beta tayyorligi bilan Adobe ichidagi haqiqiy versiya sinovlarini farqlash kerak.
