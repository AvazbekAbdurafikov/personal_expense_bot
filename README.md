# Shaxsiy Xarajatlar Boti

Bu Telegram bot shaxsiy xarajatlaringizni hisoblab borish uchun yaratilgan.

## Imkoniyatlar

- 💰 Xarajatlarni kategoriyalar bo'yicha kiritish
- 📊 Oylik hisobotlarni ko'rish
- 📋 So'nggi xarajatlarni ko'rish
- 📈 Kunlik statistikani ko'rish
- 🔒 Faqat bitta foydalanuvchi uchun

## O'rnatish

1. `.env.example` faylini `.env` ga nusxalang
2. `.env` fayliga o'z Bot Token va Telegram ID raqamingizni kiriting
3. Virtual muhit yarating: `python -m venv .venv`
4. Virtual muhitni faollashtiring:
   - Windows: `.venv\Scripts\activate`
5. Kerakli kutubxonalarni o'rnating: `pip install -r requirements.txt`
6. Botni ishga tushiring: `python main.py`

## Digital Ocean'ga joylash

1. Digital Ocean'da yangi Droplet yarating:
   - Ubuntu 22.04 LTS
   - Basic plan
   - Minimal resurslar (1GB RAM)

2. SSH orqali serverga ulanish:
   ```bash
   ssh root@your_server_ip
   ```

3. Kerakli paketlarni o'rnatish:
   ```bash
   apt update && apt upgrade -y
   apt install python3-pip python3-venv git -y
   ```

4. Botni serverga ko'chirish:
   ```bash
   git clone your_repository_url
   cd personal_expense_bot
   ```

5. Virtual muhit va bog'liqliklarni o'rnatish:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

6. `.env` faylini sozlash:
   ```bash
   cp .env.example .env
   nano .env  # Bot Token va User ID'ni kiriting
   ```

7. Systemd service yaratish:
   ```bash
   sudo nano /etc/systemd/system/expense-bot.service
   ```
   
   Quyidagi matnni kiriting:
   ```ini
   [Unit]
   Description=Personal Expense Telegram Bot
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/root/personal_expense_bot
   Environment=PATH=/root/personal_expense_bot/.venv/bin
   ExecStart=/root/personal_expense_bot/.venv/bin/python main.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

8. Serviceni ishga tushirish:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable expense-bot
   sudo systemctl start expense-bot
   ```

9. Status tekshirish:
   ```bash
   sudo systemctl status expense-bot
   ```

## Docker orqali ishga tushirish

1. Docker va Docker Compose o'rnatish:
   ```bash
   # Docker o'rnatish
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh

   # Docker Compose o'rnatish
   apt install docker-compose -y
   ```

2. `.env` faylini sozlash:
   ```bash
   cp .env.example .env
   nano .env  # Bot Token va User ID'ni kiriting
   ```

3. Docker image yaratish va ishga tushirish:
   ```bash
   docker-compose up -d --build
   ```

4. Loglarni ko'rish:
   ```bash
   docker-compose logs -f
   ```

5. Botni qayta ishga tushirish:
   ```bash
   docker-compose restart
   ```

6. Botni to'xtatish:
   ```bash
   docker-compose down
   ```

## Ma'lumotlar bazasi

- SQLite bazasi `data` papkasida saqlanadi
- Docker ishlatilganda, baza fayli `data` papkasida host mashinada saqlanadi
- Bazani zaxiralash uchun `data` papkasini kopiyalash kifoya

## Foydalanish

1. Botga `/start` buyrug'ini yuboring
2. "💰 Xarajat qo'shish" tugmasini bosib yangi xarajat qo'shing
3. Xarajat miqdorini kiriting
4. Kategoriyani tanlang
5. Izoh qoldiring (ixtiyoriy)

## Hisobotlar

- 📊 Oylik hisobot - har bir kategoriya bo'yicha oylik xarajatlar
- 📋 So'nggi xarajatlar - oxirgi 10 ta xarajat
- 📈 Kunlik statistika - so'nggi 7 kunlik xarajatlar

## Xavfsizlik

- Bot faqat `.env` faylidagi `ALLOWED_USER_IDS` ro'yxatida ko'rsatilgan foydalanuvchilar uchun ishlaydi
- Database fayli `personal_expenses.db` nomi bilan saqlanadi
- Barcha xarajatlar SQLite bazasida saqlanadi
