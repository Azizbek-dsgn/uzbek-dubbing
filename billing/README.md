# UzScribe obuna serveri

Flask + Waitress + SQLite. Bitta persistent server uchun; bir nechta konteyner/replika yoki serverless vaqtinchalik diskka mos emas. Audio/model fayllari bu serverga yuborilmaydi.

## Tanlangan provayder: Renuvo

Yangi konfiguratsiya Renuvo sandbox rejimiga tayyorlanadi. Avval [Renuvo ulanish yo‘riqnomasi](RENUVO.md) bilan API/tenant/plan ID va webhookni ulang. Real to‘lov yoqilmagan; Renuvo hujjatidagi haqiqiy provayder sinovi cheklovi ham tekshirilishi kerak.

Quyidagi Payme qadamlar alohida legacy adapterga tegishli: uni ishlatish uchun `UZSCRIBE_BILLING_PROVIDER=payme` qo‘ying.

## Mahalliy va production tayyorlash

```sh
python3 -m venv .billing-venv
.billing-venv/bin/python -m pip install -r billing/requirements.txt
.billing-venv/bin/python -m billing.manage --data-dir /absolute/private/uzscribe-data --api-url https://YOUR-DOMAIN --panel-config /absolute/public/license-config.json
```

`server.env` va `signing.pem` faqat private data papkasida. Admin kalit faylda; uni chatga, GitHub’ga yoki buyer ZIP’ga kiritmang. `license-config.json` faqat public RSA key va API URL: pullik panelga yuborish mumkin.

1. Payme Business bilan virtual kassa oching. Account maydoni **order_id** bo‘lsin.
2. `server.env`ga sandbox merchant ID va kalitini yozing. `PAYME_TEST=1` qolsin. Merchant ID faqat oddiy identifikator bo‘lsin, `;` yoki `=` belgisi kiritilmasin.
3. Reverse proxy bilan HTTPS domenni tayyorlang. `/webhooks/payme` Payme callback manzili. `/` — xarid; `/admin` — boshqaruv. TLS sertifikatini to‘g‘ri o‘rnating.
4. Servis muhitiga private `server.env` qiymatlarini kiriting. Uni repoga kiritmang.

POSIX mahalliy ishga tushirish namunasi:

```sh
set -a
. /absolute/private/uzscribe-data/server.env
set +a
.billing-venv/bin/waitress-serve --listen=127.0.0.1:8765 billing.wsgi:app
```

Windows serverida shu env qiymatlarni xizmat muhitiga kiriting va `.billing-venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8765 billing.wsgi:app` ishga tushiring. Flask development serveridan production’da foydalanmang ([Flask deployment hujjati](https://flask.palletsprojects.com/en/stable/deploying/)). `.env` avtomatik o‘qilmaydi; qiymatlarni service environment orqali yuklash kerak.

SQLite disk persistent bo‘lsin. Zaxira nusxani SQLite backup API orqali oling; faqat `.sqlite` faylini ishlayotgan WAL bazadan ko‘chirish yetarli emas. Reverse proxy request limit, timeout va rate limitni sozlang; ilova rate limiti bitta server jarayoniga tegishli. Proxy oldida IP limitlarini qo‘llang. Faqat bitta ishonchli reverse proxy va yopiq backend bo‘lsa, proxy X-Forwarded-For’ni almashtirib yuborsin va service environment’da `UZSCRIBE_TRUST_PROXY=1` qo‘ying (bir proxy hop). Backendga tashqaridan to‘g‘ridan-to‘g‘ri kirish bo‘lmasin; aks holda bu flag’ni yoqmang. Default `0` holatda proxyning IP’si bo‘yicha umumiy limit ishlaydi; ilova tekshirilmagan X-Forwarded-For’ga ishonmaydi.

## Pullik ZIP

```sh
python3 tools/build_release.py --model-dir /absolute/models/large-v3 --output UzScribe-Pro.zip --license-config /absolute/public/license-config.json
```

Buyer ZIP ichiga server kirmaydi. Public beta konfiguratsiyasi `community`; pullik ZIP `subscription`. Signed ZXP uchun konfiguratsiyani **imzolashdan oldin** panelga yozing; signed paketdan keyin config override qilinmaydi. Paid config haqiqiy HTTPS serverga mos kelishi kerak. Kalit rotatsiyasi mavjud mijozlarga yangi public key yetkazishni talab qiladi.

## Payment acceptance sinovlari

Avval mahalliy:

```sh
python -m unittest discover -s tests -p test_billing.py -v
```

So‘ng Payme sandbox’da checkout, noto‘g‘ri summa, takroriy callback, parallel callback, to‘lovdan oldingi cancellation, refund, 12 soatlik timeout va qayta to‘lovni tasdiqlang. `SetFiscalData` jo‘natmasi saqlanadi; bu fiskal chekni o‘zi yaratmaydi. Tovar/xizmat uchun IKPU, soliq va fiskal detal tarkibini merchant mutaxassisi bilan tasdiqlang; zarur bo‘lsa CheckPerformTransaction detail obyekti shu real rekvizitlar bilan kengaytiriladi. Merchant acceptance va real test to‘lovi o‘tmaguncha `PAYME_TEST=0` qo‘ymang.

## Foydalanuvchi

1. Panel → **Obuna** → tarif → Payme’da to‘lash.
2. Kalit kompyuterga saqlanadi; checkout browserda ochiladi.
3. To‘lovdan keyin **Holatni yangilash**: imzolangan device lease olinadi.
4. 3 kungacha offline ishlaydi; keyin internetda tasdiqlanadi. Online tekshiruv har 4 soatda yoki foydalanuvchi bosganda bajariladi; serverning 401/403 rad javobi cached lease’ni bekor qiladi. Qurilma bindinglarini reset qilish limitni bo‘shatadi; kaliti mavjud eski mijoz qayta bog‘lanishi mumkin. Barcha eski mijozni to‘xtatish uchun litsenziyani bloklang. Obuna muddati tugasa yangi ishlar uchun uzaytirish kerak.
5. Kompyuter almashtirish uchun **Bu kompyuterni uzish** yoki admin qurilmalarni uzadi.

Kalit bearer credential: uni ommaga yubormang. Ikki Adobe host bitta runtime papkasini ishlatsa, bitta installation ID ishlatiladi. Bu hardware DRM emas; runtime papkasini nusxalash qurilma identifikatorini ham nusxalaydi. Maxfiy server kaliti public kodda mavjud emas. Community beta obunasiz ishlaydi; paid build config alohida beriladi.
