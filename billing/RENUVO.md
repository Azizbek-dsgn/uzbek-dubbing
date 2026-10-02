# UzScribe + Renuvo · sinov integratsiyasi

Tanlangan obuna provayderi: **Renuvo**. Adapter rasmiy [Tenant API hujjati](https://renuvo.uz/en/docs) bo‘yicha yozilgan (2026-10-03). Mahalliy testlar fake transport bilan bajariladi; haqiqiy Renuvo sandbox acceptance hali bajarilmagan.

**Muhim:** Renuvo hujjatining “Known limitations” bo‘limida Payme/ATMOS adapterlari faqat mock server bilan sinalgani, haqiqiy provayder sandboxida hali tekshirilmagani yozilgan. Landing sahifadagi “live” marketing matniga qaramay, real to‘lovga tayyorlikni provayder bilan tasdiqlang. Bu integratsiyani tayyor sotuv xizmati deb ko‘rsatmang.

## Kabinet va ulanish

Renuvo’da hozir mustaqil signup yo‘q: [@renuvo_uz](https://t.me/renuvo_uz) orqali UzScribe biznes kabineti, **sandbox API key**, tenant ID va tarif plan ID’larini so‘rang. Renuvo uchun o‘z Payme yoki ATMOS merchant shartnomangiz kerak. Hujjatga ko‘ra, provayder tasdiqlanmagan production tenant obuna yaratishda 404 qaytaradi.

1. `billing.manage` bilan private server kalitlari va public panel konfiguratsiyasini yarating; mavjud signing key’ni qayta yaratmang.
2. Mavjud serverning private `server.env` fayliga quyidagilarni kiriting. API/webhook kalitlarini panelga, ZIP’ga, GitHub’ga yoki chatga yubormang.

```sh
UZSCRIBE_BILLING_PROVIDER=renuvo
RENUVO_API_URL=https://test.renuvo.uz
RENUVO_API_KEY=YOUR_SANDBOX_KEY
RENUVO_TENANT_ID=YOUR_TENANT_ID
RENUVO_WEBHOOK_SECRET=YOUR_RANDOM_SECRET_AT_LEAST_32_CHARS
RENUVO_PLAN_IDS='{"monthly":"YOUR_MONTHLY_PLAN_ID","yearly":"YOUR_YEARLY_PLAN_ID"}'
RENUVO_PLAN_CATALOG='{"monthly":{"title":"UzScribe Pro · oylik","price_uzs":49000,"days":30,"seats":2},"yearly":{"title":"UzScribe Pro · yillik","price_uzs":490000,"days":365,"seats":2}}'
```

Narxlar namuna. **Haqiqiy yechiladigan narx, interval va trial Renuvo kabinetidagi tarifdan olinadi.** `PLAN_CATALOG` faqat UzScribe ko‘rsatadigan tarif va qurilma limitini belgilaydi; uni Renuvo tariflariga moslang. Oylik interval 30 kun bilan bir xil bo‘lmasligi mumkin: litsenziya muddati har doim Renuvo qaytargan `currentPeriodEnd` orqali aniqlanadi. Free trial bu adapterda pullik huquq bermaydi. Renuvo kabinetida yoqilgan va portal orqali tanlanishi mumkin bo‘lgan barcha plan ID’larini mappingga kiriting.

3. HTTPS serverni deploy qiling. Webhook manzil: `https://YOUR-DOMAIN/webhooks/renuvo`. Renuvo operatoriga manzil va webhook secret’ni xavfsiz kanal orqali bering; webhook sozlamasi hozir operator tomonidan tenantga yoziladi.
4. Server xizmatining environment’iga qiymatlarni yuklang va qayta ishga tushiring. `.env` avtomatik o‘qilmaydi. `/health` konfiguratsiya borligini ko‘rsatadi; u provayder acceptance o‘tganini bildirmaydi.
5. Public panel konfiguratsiyasini paid ZIP’ga builder orqali kiriting. Community beta obunasiz qoladi. Buyer ZIP ichida billing server/API key bo‘lmaydi.

## Ishlash tartibi

- “Obuna olish” → litsenziya kaliti → Renuvo hosted checkout. Customer `externalRef` ichida UzScribe license ID ishlatiladi; audio/model fayllari yuborilmaydi.
- Imzolangan webhook → Renuvo’dan obunaning haqiqiy holatini GET orqali tekshirish → ACTIVE + PAID + UZS bo‘lsa davrni saqlash. Brauzer qaytishi, checkbox yoki webhookning o‘zi huquq bermaydi.
- Yangilanishlar Renuvo tomonida. Takroriy/eski webhook kunlarni qo‘shmaydi; server absolute davr oxirini saqlaydi.
- “Holatni yangilash”/activation obunani qayta tekshiradi: o‘tkazib yuborilgan renewal webhookni ham tiklaydi. Renuvo ishlamasa yangi lease chiqarilmaydi; mijozning mavjud imzolangan lease’i ko‘pi bilan 3 kun ishlaydi. Bekor qilinganda oldingi offline lease shu muddatgacha qolishi mumkin.
- “Obunani boshqarish” → Renuvo portal: kartani almashtirish, bekor qilish, tarif almashtirish. Faol obunaga ikkinchi xarid urinishidagi 409 portalga olib boradi.
- PENDING, TRIALING, PAST_DUE, CANCELED va SCHEDULED huquq bermaydi. Davr oxirida bekor qilishda ACTIVE holati davr tugaguncha ishlaydi. UzScribe admin orqali berilgan alohida promo huquqlari mustaqil saqlanadi.
- Mahalliy admin litsenziya/blok/qurilmalarni boshqaradi. Renuvo narxlarini mahalliy admin formasi o‘zgartirmaydi. Daromad ko‘rsatkichi faqat adapter kuzatgan paid invoice’lar yig‘indisi: to‘liq moliyaviy hisobot, komissiya yoki refund hisoboti emas. O‘tkazib yuborilgan eski invoice tarixini import qiladigan API hujjatda yo‘q; to‘liq hisob Renuvo/provayder kabinetida.
- Renuvo refund webhookini hujjatlashtirmagan. Refund holatida litsenziya kerak bo‘lsa admin orqali bloklanadi; pul qaytarish provayder kabinetida amalga oshiriladi.

## Sinovdan production’ga

```sh
python -m unittest discover -s tests -p 'test_renuvo.py' -v
```

Real sandbox key bilan checkout, to‘lov, webhook HMAC, yangilanish, noto‘g‘ri karta, period-end cancellation, immediate cancellation, portal/plan switch va xizmat uzilishini sinang. Renuvo operatoridan haqiqiy Payme/ATMOS sandbox acceptance tasdig‘ini oling. Shundan keyin production tenant/key/plan ID va `RENUVO_API_URL=https://api.renuvo.uz`ga o‘ting; sandbox va production ma’lumotlarini alohida saqlang. Boshqa hostga Bearer secret yuborish yoki HTTP redirect orqali keyni ko‘chirish adapterda taqiqlangan. API POST’lar avtomatik qayta urilmaydi: idempotency kontrakti hujjatlashtirilmagan.
