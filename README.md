# 🌟 IMKON — Talabalar Bandligi va Davlat Amaliyoti Platformasi

> **Intelektual Hakaton** uchun yaratilgan talabalar bandligi, rasmiy davlat amaliyotlari va OTM tyutorlik monitoring tizimi.

Telegram Bot: **[@imkon_ish_bot](https://t.me/imkon_ish_bot)**

---

## 📌 Loyiha Haqida

**Imkon** — talabalarga darsdan bo'sh vaqtlarida o'z mutaxassisliklariga mos sohalarda xavfsiz va kafolatlangan ish hamda davlat organlarida rasmiy amaliyot (stajirovka) topishga yordam beruvchi innovatsion ekotizim.

OTM tyutorlari, dekanat va ish beruvchilar uchun yagona avtomatlashtirilgan monitoring va nazorat tizimini taqdim etadi.

---

## 🚀 Asosiy Imkoniyatlar va Panellar

### 1. 🎓 Foydalanuvchi / Talaba Paneli
* **Mos ishlar lentasi (Smart Matching):** Talabaning dars jadvali, yashash manzili (TTJ / ijara kvartira geolokatsiyasi), yoshi va GPA bahosiga 100% mos keluvchi bo'sh ish o'rinlari filtri.
* **Davlat & Kasbiy Amaliyotlar:** O'zbekiston Respublikasi Adliya, Sud, IT Park, Shifoxona, Kapitalbank kabi nufuzli tashkilotlarda rasmiy amaliyot kvotalari.
* **Kontrakt to'lanadigan ishlar:** Ish beruvchi korxonalar tomonidan talabaning yillik kontrakt to'lovi qoplab beriladigan grant dasturlari (Soliq kodeksi 378-moddasi).
* **Smart Rezyume (CV Card):** O'zbekiston standartlari bo'yicha talaba profili va amaliyot natijalarini jamlovchi tezkor rezyume kartasi.
* **Elektron Amaliyot Kundaligi:** Kunlik amaliyot soatlarini kiritish va korxona murabbiyi tomonidan tasdiqlash.
* **14 kunlik mehnat shartnomasini bekor qilish arizasi shabloni (Mehnat kodeksi 160-moddasi).**

### 2. 🧑‍🏫 Tyutor Paneli (OTM Mas'ullari Uchun)
* **Talabalar Monitoring Dossiesi:** Guruh talabalarining qayerda ishlayotgani, korxona manzili, ish beruvchi telefoni va amaliyot soatlarini real vaqt rejimida kuzatish.
* **Sessiya va Imtihonlar Qulfi (Guruh & Individual):** Sessiya davrida talabalarning chalg'imasligi uchun ularga ish arizalari topshirishni to'liq pauzaga o'tkazish.
* **Avtomatik Push Xabarnomalar:** Tyutor sessiya qulfini yoqqanida yoki ochganida barcha talabalarga zudlik bilan Telegram orqali xabar yuboriladi.
* **Guruh Bandlik Hisoboti (CSV / Excel formatda yuklab olish):** Dekanat va Rektorat uchun rasmiy hisobotni UTF-8 BOM formatida bir zumda yuklab olish.

### 3. 🏢 Ish Beruvchi & Davlat Organi Paneli
* Vakansiya va amaliyot kvotalarini joylash.
* Nomzodlar anketasini ko'rib chiqish (GPA, ishonch balli, dars jadvali).
* Nomzodni bir zumda qabul qilish, zaxiraga olish yoki rad etish.
* Qabul qilingan talabalarga avtomatik joylashuv va kontakt ma'lumotlarini yetkazish.

### 4. 👑 Administrator Boshqaruvi
* Tyutorlarni tayinlash, guruhlarga biriktirish va boshqarish.
* Ish beruvchi tashkilotlarni verifikatsiyadan o'tkazish (✔️ Rasmiy tasdiq).
* Real-vaqt analitika dashboardi va butun baza eksporti.
* `/switch_role` — Barcha rollarni bevosita sinab ko'rish imkoniyati.

---

## 🛠 Texnologiyalar Steki

* **Til:** Python 3.10+
* **Telegram Framework:** Aiogram 3.x (Asinxron, FSM, CallbackQuery)
* **Ma'lumotlar Bazasi:** PostgreSQL (Production) / SQLite WAL mode (Lokal & Fallback)
* **Drayverlar:** `asyncpg`, `aiosqlite`
* **Xavfsizlik & Anti-Flood:** Custom Throttling Middleware, Token Protection
* **Konteynerlashtirish:** Docker, Docker Compose

---

## ⚙️ Ishga Tushirish Qo'llanmasi

### 1. Repozitoriyani klonlash
```bash
git clone https://github.com/durd1ma7ov06/Intelektual-hakaton-.git
cd Intelektual-hakaton-
```

### 2. Virtual muhitni yaratish va faollashtirish
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 3. Bog'liqliklarni o'rnatish
```bash
pip install -r requirements.txt
```

### 4. Sozlamalarni kiritish
`.env.example` faylidan nusxa olib, `.env` faylini yarating:
```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
BOT_NAME=imkon_ish_bot
ADMIN_IDS=6956456422
USE_SQLITE_FALLBACK=True
SQLITE_PATH=imkon.db
DEFAULT_LANGUAGE=uz
```

### 5. Botni ishga tushirish
```bash
python -m bot.main
```

### 6. Testlarni tekshirish
```bash
python -m unittest discover tests
```

---

## 👥 Mualliflar

* **Intelektual Hakaton Jamoasi**
* Bot: [@imkon_ish_bot](https://t.me/imkon_ish_bot)
