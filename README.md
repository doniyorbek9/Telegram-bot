# Kamalim kanal boti

Har kuni soat **12:00** da @sadaf_media_1 kanaliga AI generatsiya qilgan post (rasm + uzun caption)
avtomatik joylanadi. Postdan 2 daqiqa oldin (11:58) sizga tasdiqlash uchun yuboriladi.

## Ishlash tartibi

1. **11:58** — bot Gemini orqali mavzu tanlaydi (kamera/video-montaj/to'y-video), internetdan
   (Google Search grounding) so'nggi ma'lumot topadi, rasm va uzun caption yaratadi.
2. Sizga (admin) rasm + caption + **"✅ Qabul qilish"** / **"🔄 Qaytadan"** tugmalari yuboriladi.
3. **Qabul qilish** — post darhol kanalga yuboriladi.
4. **Qaytadan** — yangi post generatsiya qilinadi, yana o'sha tugmalar bilan yuboriladi (istalgancha
   takrorlash mumkin, har safar 2 daqiqalik hisoblagich qayta boshlanadi).
5. Agar **2 daqiqa** ichida hech qanday tugma bosilmasa — oxirgi taklif qilingan post avtomatik
   kanalga yuboriladi (taxminan soat 12:00 da).

Qo'lda test qilish uchun bot'ga `/generate` buyrug'ini yuboring (faqat admin ishlata oladi).

## O'rnatish (Railway)

1. Ushbu papkani GitHub repo qilib yuklang (yoki to'g'ridan-to'g'ri Railway'ga ulang).
2. Railway'da yangi loyiha yarating, shu repo'ni ulang.
3. Railway "Variables" bo'limida `.env.example` dagi barcha o'zgaruvchilarni kiriting:
   - `BOT_TOKEN` — @BotFather dan olingan token
   - `CHANNEL_USERNAME` — `@sadaf_media_1`
   - `ADMIN_CHAT_ID` — sizning shaxsiy Telegram ID'ingiz (masalan @userinfobot orqali olinadi)
   - `GEMINI_API_KEY` — Google AI Studio (aistudio.google.com) dan olinadi
4. **Muhim:** botni kanalga (@sadaf_media_1) **admin** qilib qo'ying — aks holda kanalga post
   yubora olmaydi.
5. Start command: `python main.py`

## Muhim texnik eslatma

- Telegram'da rasmli xabarning caption qismi maksimal **1024 belgi**gacha bo'lishi mumkin. Agar
  generatsiya qilingan matn undan uzun bo'lsa, bot avtomatik ravishda qolgan qismini alohida
  matnli xabar sifatida, rasmdan keyin yuboradi — natijada foydalanuvchi uchun bir butun post
  bo'lib ko'rinadi.
- Rasm generatsiya modeli (`GEMINI_IMAGE_MODEL`) va matn modeli (`GEMINI_TEXT_MODEL`) `.env` orqali
  osongina almashtirilishi mumkin, agar kelajakda Google model nomlarini yangilasa.
- Mavzular ro'yxati (`content.py` faylidagi `TOPICS`) osongina kengaytirilishi yoki tahrirlanishi
  mumkin.

## Fayllar

- `main.py` — bot logikasi, scheduler, tugmalar, kanalga joylash
- `content.py` — Gemini bilan matn (internet qidiruvi bilan) va rasm generatsiyasi
- `requirements.txt` — kerakli kutubxonalar
- `.env.example` — muhit o'zgaruvchilari namunasi
