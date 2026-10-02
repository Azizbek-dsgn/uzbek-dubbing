# UzScribe monetizatsiyasi — 2026-10-03

## Tavsiya etilgan boshlanish

**Pro obuna:** subtitr + animatsiya + Premiere Podcast/Reels, ikki kompyuter. Mahalliy ASR audio/video fayllarni serverga yubormaydi. Sotuv qiymati: qulay ish jarayoni, tayyor o‘rnatish, yangilanish va yordam. ASR modeli boshqa muallifniki; sotilayotgan narsa UzScribe integratsiyasi va xizmatidir.

| Taklif | Boshlang‘ich namuna narx | Izoh |
|---|---:|---|
| Pro · 30 kun | 49 000 so‘m | Barcha mavjud imkoniyatlar, 2 kompyuter |
| Pro · 365 kun | 490 000 so‘m | Yillik to‘lov, 2 kompyuter |
| Studio | Keyin kelishiladi | Ko‘p o‘rinli litsenziya va yordam |
| O‘rnatib berish / trening | Alohida xizmat | Tijoriy yordam va montaj bo‘yicha trening |

Narxlar foydalanuvchi tasdiqlamaguncha **namuna**. Boshqaruv ekranida o‘zgartiriladi. Cheksiz lifetime litsenziya doimiy yangilash xarajatini qoplamasligi mumkin; avval 30/365 kunlik tarifni real mijozlarda sinang. Public beta hozir community rejimida ishlaydi; pullik ZIP alohida sozlanadi.

100 ta 30 kunlik 49 000 so‘mlik obuna **4 900 000 so‘m yalpi tushum** beradi. Bu prognoz emas: chegirma, qaytarish, provayder komissiyasi, soliq, server va qo‘llab-quvvatlash xarajatlari ayriladi. Faol obuna sonini tushum yoki kafolatlangan daromad bilan tenglashtirmang.

## Mahalliy to‘lov yo‘llari

| Usul | Qayerga mos | Hozirgi holat |
|---|---|---|
| Payme Merchant API | Payme checkout orqali so‘mda to‘lov, callback bilan litsenziya ochish | Kodga qo‘shildi; real merchant va sandbox tasdig‘i kerak |
| Payme Subscribe API | Karta tokeni va rozilik bilan takroriy yechish | Tadqiq qilindi; avtomatik yechish bu versiyada yo‘q |
| Click Shop API | UZCARD/HUMO va Click foydalanuvchilariga qo‘shimcha kanal | Tadqiq qilindi; adapter hali yozilmadi |
| Qo‘lda beriladigan litsenziya | Hamkor, sinov, promo, yordam | Admin orqali kun va qurilma soni bilan beriladi |

[Payme Business](https://b2b-partner.payme.uz/) hamkorlikka ariza va shartnoma orqali ulanadi; rasmiy sahifada o‘zini o‘zi band qilganlar, YTT va tashkilotlar keltirilgan. Aniq e-commerce ulanishi va komissiyani merchant shartnomasi bilan tasdiqlang. [Click Business](https://business.click.uz/ru) sayt integratsiyasi uchun UZCARD/HUMO komissiyasini 1,5–2,5% deb ko‘rsatadi; konkret xizmatga mos shartni provayder bilan kelishing.

Payme [Merchant API](https://developer.help.paycom.uz/protokol-merchant-api/) JSON-RPC callbacklaridan foydalanadi. [Checkout summasi](https://developer.help.paycom.uz/initsializatsiya-platezhey/otpravka-cheka-po-metodu-get/) **tiyinda** yuboriladi: 49 000 so‘m = 4 900 000 tiyin. Saytda so‘m ko‘rinadi; hisob-kitobda integer tiyin ishlatiladi.

[Subscribe API](https://developer.help.paycom.uz/protokol-subscribe-api/) Merchant API’dan alohida. Karta ma’lumotlari Payme tizimida tokenlashtiriladi. Avtomatik yechish uchun merchantdan kerakli ruxsat, foydalanuvchi roziligi, bekor qilish va retry tartibi kerak. Ushbu versiya **qo‘lda uzayadigan obuna**: kartadan avtomatik pul olinmaydi.

[Click rasmiy hujjatlari](https://docs.click.uz/) Shop API Prepare/Complete va to‘lov havolasi oqimini beradi. CLICK’ning o‘z premium obunasi mavjudligi tashqi merchantga avtomatik yechish huquqi borligini anglatmaydi.

## Boshqarish

- Tarif nomi, UZS narxi, davomiyligi, kompyuter soni va sotuv holati.
- Mijoz litsenziyasi, muddati, bloklash/ochish, qo‘lda uzaytirish.
- Qurilmalarni uzish, to‘lovlar va amallar tarixi.
- Keyingi to‘lov muddati bor obunani uzaytiradi; takroriy callback ikki marta uzaytirmaydi.
- Refund Payme kabinetida amalga oshiriladi; tasdiqlangan CancelTransaction tegishli davrni bekor qiladi. Admin sahifasi pulni o‘zi qaytarmaydi.
- RSA imzoli litsenziya 3 kungacha offline ishlaydi, obuna tugashidan oshmaydi. Bloklash/qaytarish offline qurilmada oldingi lease tugaganda sezilishi mumkin.

## Sotuvga chiqarish chegaralari

Server domeni, merchant rekvizitlari, biznes shartnomasi va sandbox qabul sinovi hali mavjud emas. Hozir yozilgan tizimni haqiqiy payment-ready do‘kon deb ko‘rsatmang. Sotuvchi rekvizitlari, xarid shartlari, yordam/qaytarish tartibi va tegishli fiskal ma’lumotlar real biznesga mos tasdiqlanadi. Mahalliy server va mijoz fayllari litsenziya/tokenlarni saqlaydi; audio serverga chiqmaydi.

Public JavaScript/Python kodi ochiq bo‘lsa, litsenziya tekshiruvini forkda olib tashlash mumkin. Ushbu tizim buzilmas DRM emas. Kuchli tijoriy himoya kerak bo‘lsa, pullik distributiv va yangilanish xizmatini alohida yuriting; serverning merchant va imzolash kalitlari doim maxfiy qoladi. Uchinchi tomon modellarining litsenziya bildirishlarini saqlang. Adobe ichidagi jonli sinovlar va imzolangan paket bo‘yicha `SELLER-RELEASE.md` talablari qoladi.
