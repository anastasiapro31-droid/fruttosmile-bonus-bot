import sys
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
from datetime import datetime
import asyncio
 
import gspread
from google.oauth2.service_account import Credentials
 
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
 
# ────────────────────────────────────────────────
# КОНФИГУРАЦИЯ — меняй только здесь
# ────────────────────────────────────────────────
 
BOT_TOKEN = "8589427171:AAHtbVHDeErpwwXMjOL7zs71ZmHh7ZnW-hI"          # ← ОБЯЗАТЕЛЬНО ЗАМЕНИ!
 
ADMIN_ID = 1165444045
ADMIN_LAST_REQUEST = {}
ADMIN_STATES = {}  # {user_id: state}
BROADCAST_DATA = {}  # временное хранение рассылки для админа
 
RETAILCRM_URL = "https://xtv17101986.retailcrm.ru"     # ← замени или удали блоки ниже
RETAILCRM_API_KEY = "6ipmvADZaxUSe3usdKOauTFZjjGMOlf7"               # ← замени или удали
RETAILCRM_HEADERS = {
    "X-API-KEY": RETAILCRM_API_KEY,
    "Content-Type": "application/json"
}
 
SHEET_NAME = "Fruttosmile Bonus CRM"
 
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
 
CREDS_FILE = "credentials.json"
 
users_sheet = None
logs_sheet = None
 
try:
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPE)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open(SHEET_NAME)
    users_sheet = spreadsheet.worksheet("users")
    logs_sheet = spreadsheet.worksheet("logs")
    print("Google Sheets подключена успешно")
except Exception as e:
    print(f"Ошибка подключения Google Sheets: {e}")
 
# НОРМАЛИЗАЦИЯ ТЕЛЕФОНА
def normalize_phone(phone: str) -> str:
    phone = re.sub(r'[^0-9+]', '', phone)
 
    # если начинается с +7 -> оставляем
    if phone.startswith("+7") and len(phone) == 12:
        return phone
 
    # если начинается с 8 -> меняем на +7
    if phone.startswith("8") and len(phone) == 11:
        return "+7" + phone[1:]
 
    # если начинается с 7 -> добавляем +
    if phone.startswith("7") and len(phone) == 11:
        return "+7" + phone[1:]
 
    return phone
 
# ВАРИАНТЫ НОМЕРА ДЛЯ ПОИСКА (все 3 формата)
def get_phone_variants(phone: str) -> list:
    norm = normalize_phone(phone)
    variants = [norm]
    if norm.startswith("+7") and len(norm) == 12:
        variants.append("8" + norm[2:])
        variants.append("7" + norm[2:])
    return variants
 
# Health check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
 
def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()
 
# КАТАЛОГ ТОВАРОВ
PRODUCTS = {
    "boxes": [
        {"name": "Бенто-торт из клубники (8 ягод)", "price": "2490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/07/photoeditorsdk-export4.png"},
        {"name": "Набор клубники и малины в шоколаде", "price": "2990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/06/malinki-takie-vecerinki.jpg"},
        {"name": "Бокс «С надписью» Средний", "price": "5990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/boks-s-nadpisyu.jpg"},
        {"name": "Корзина клубники в шоколаде S", "price": "5990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/korzina-klubniki-v-shokolade-s.jpeg"},
        {"name": "Торт из клубники в шоколаде", "price": "7490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/photo_2025_02_25_16_20_32_481x582.jpg"}
    ],
    "flowers": [
        {"name": "Букет «Зефирка»", "price": "4490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/photoeditorsdk_export_37__481x582.png"},
        {"name": "Букет из роз и эустомы", "price": "3490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/buket-iz-roz-i-eustomy.jpg"},
        {"name": "Моно букет «Диантусы»", "price": "2690", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/mono-buket-diantusy.png"}
    ],
    "sweet": [
        {"name": "Букет клубничный S Ажурный", "price": "3990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/buket-klubnichnyj-s-azhurnyj-1.jpg"},
        {"name": "Букет «Ягодное ассорти»", "price": "6490", "photo": "http://fruttosmile.su/wp-content/uploads/2016/12/photo_2024-04-05_17-55-09.jpg"},
        {"name": "Букет из цельных фруктов «С любовью»", "price": "3990", "photo": "http://fruttosmile.su/wp-content/uploads/2016/04/photo_2022-12-09_15-56-56.jpg"}
    ],
    "meat": [
        {"name": "Букет «Мясной» стандарт", "price": "5990", "photo": "http://fruttosmile.su/wp-content/uploads/2017/02/photo_2024-08-08_16-52-24.jpg"},
        {"name": "Букет из королевских креветок и клешней краба", "price": "9990", "photo": "http://fruttosmile.su/wp-content/uploads/2018/08/photo_2022-12-09_18-05-36-2.jpg"},
        {"name": "Мужская корзина «Брутал»", "price": "12990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/whatsapp202023_10_1620v2014.38.08_14f00b4d_481x582.jpg"}
    ]
}
 
# ========================================================
#  ФУНКЦИИ
# ========================================================
 
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup([
        ["📊 Информация о бонусах", "📖 Каталог товаров"],
        ["🛒 Оформить заказ", "📸 Получить фото заказа"],
        ["⭐ Оставить отзыв", "📍 Адреса самовывоза"]
    ], resize_keyboard=True)
    msg = "Выберите действие в меню FruttoSmile: 🍓"
    await update.effective_message.reply_text(msg, reply_markup=kb)
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn = KeyboardButton("📲 Регистрация и +300 бонусов", request_contact=True)
    await update.message.reply_text(
        "🍓 Добро пожаловать!\n\nДля активации бонусов нажмите кнопку ниже 👇",
        reply_markup=ReplyKeyboardMarkup([[btn]], resize_keyboard=True, one_time_keyboard=True)
    )
 
async def process_photo_request(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
    uid = update.effective_user.id
    user = update.effective_user
 
    first_name = user.first_name or "не указано"
    last_name  = user.last_name  or ""
    username   = user.username   or "нет"
    full_name = f"{first_name} {last_name}".strip()
 
    await update.effective_message.reply_text(
        "🔍 Запрос отправлен менеджеру!\nМы сообщим вам, когда статус изменится."
    )
 
    admin_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Готов",    callback_data=f"st_ready_{uid}"),
            InlineKeyboardButton("⏳ В работе", callback_data=f"st_work_{uid}"),
            InlineKeyboardButton("❌ Заказа нет", callback_data=f"st_none_{uid}")
        ]
    ])
 
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"🔔 ЗАПРОС ФОТО ЗАКАЗА\n"
            f"👤 Имя: {full_name}\n"
            f"📱 Телефон: {phone}\n"
            f"🆔 ID: {uid}\n"
            f"@{username}"
        ),
        reply_markup=admin_kb
    )
 
    ADMIN_LAST_REQUEST[ADMIN_ID] = uid
 
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = normalize_phone(update.message.contact.phone_number)
 
    state = context.user_data.get('state')
 
    if state == 'WAIT_ORDER':
        context.user_data['phone'] = phone
        await process_photo_request(update, context, phone)
        return
 
    context.user_data['phone'] = phone
    uid = update.effective_user.id
    name = update.effective_user.full_name or "Клиент"
 
    # RetailCRM — поиск по всем вариантам номера
    try:
        variants = get_phone_variants(phone)
        customers = []
 
        for variant in variants:
            search_url = f"{RETAILCRM_URL}/api/v5/customers"
            search_response = requests.get(
                search_url,
                headers=RETAILCRM_HEADERS,
                params={
                    "filter[phones][]": variant,
                    "limit": 20,
                    "page": 1
                }
            )
 
            print("RetailCRM SEARCH:", variant, search_response.status_code, search_response.text)
            
            search_response.raise_for_status()
            found = search_response.json().get("customers", [])
            if found:
                customers = found
                break
 
        if not customers:
            create_url = f"{RETAILCRM_URL}/api/v5/customers/create"
            resp = requests.post(create_url, headers=RETAILCRM_HEADERS, json={
                "customer": {
                    "firstName": name,
                    "phones": [{"number": phone}]
                }
            })
            
            resp.raise_for_status()
            
            print("RetailCRM CREATE STATUS:", resp.status_code)
            print("RetailCRM CREATE RESPONSE:", resp.text)
 
        else:
            print("RetailCRM: клиент уже существует — ничего не меняем")
    except Exception as e:
        print(f"RetailCRM error: {e}")
 
    # Google Sheets — поиск по всем вариантам
    if users_sheet:
        try:
            variants = get_phone_variants(phone)
            cell = None
 
            for variant in variants:
                try:
                    cell = users_sheet.find(variant, in_column=4)
                    if cell:
                        break
                except:
                    pass
 
            if cell:
                await update.message.reply_text("Вы уже зарегистрированы!")
            else:
                new_row = [
                    uid,
                    update.effective_user.username or "",
                    name,
                    phone,
                    300,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "False"
                ]
                users_sheet.append_row(new_row, value_input_option="RAW")
 
                if logs_sheet:
                    logs_sheet.append_row([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        uid,
                        "registration",
                        phone,
                        300,
                        "Регистрация через бот"
                    ], value_input_option="RAW")
 
                await update.message.reply_text("🎉 Регистрация успешна! Начислено 300 бонусов.")
        except Exception as e:
            print(f"Google Sheets error: {e}")
            await update.message.reply_text("Ошибка регистрации в базе.")
 
    await send_main_menu(update, context)
 
async def show_photo_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'phone' not in context.user_data:
        btn = KeyboardButton("📲 Подтвердить номер", request_contact=True)
        await update.effective_message.reply_text(
            "Для запроса фото нужно подтвердить номер телефона.",
            reply_markup=ReplyKeyboardMarkup([[btn], ["⬅️ Назад"]], resize_keyboard=True)
        )
        context.user_data['state'] = 'WAIT_ORDER'
        return
 
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, запросить", callback_data="confirm_photo_request"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_photo_request")
        ]
    ]
    await update.effective_message.reply_text(
        "Запросить фото заказа у менеджера?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['state'] = 'AWAITING_PHOTO_CONFIRM'
 
async def global_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    # Если это админ и у него активно какое-то состояние (поиск или рассылка)
    if uid == ADMIN_ID and ADMIN_STATES.get(uid):
        await admin_text_handler(update, context)
        return

    # Во всех остальных случаях — обычное меню
    await text_handler(update, context)
 
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    state = context.user_data.get('state')
 
    if msg == "⬅️ Назад":
        context.user_data.pop('state', None)
        await send_main_menu(update, context)
        return
 
    if msg == "📸 Получить фото заказа":
        await show_photo_confirmation(update, context)
        return
 
    if msg == "📖 Каталог товаров":
        kb = [
            [InlineKeyboardButton("🎁 Подарочные боксы", callback_data="cat_boxes")],
            [InlineKeyboardButton("🍓 Сладкие букеты", callback_data="cat_sweet")],
            [InlineKeyboardButton("💐 Цветы", callback_data="cat_flowers")],
            [InlineKeyboardButton("🍖 Мужские букеты", callback_data="cat_meat")]
        ]
        await update.message.reply_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(kb))
        return
 
    if msg == "⭐ Оставить отзыв":
        context.user_data['state'] = 'WAIT_REVIEW'
        kb = [
            [InlineKeyboardButton("Яндекс", url="https://yandex.ru/maps/org/fruttosmile/58246506027/?ll=104.353133%2C52.259946&z=14")],
            [InlineKeyboardButton("2ГИС", url="https://2gis.ru/irkutsk/firm/1548641653278292/104.353179%2C52.259892")],
            [InlineKeyboardButton("Avito", url="https://www.avito.ru/brands/i190027211?ysclid=ml5c5ji39d797258865")],
            [InlineKeyboardButton("VK", url="https://vk.com/fruttosmile?ysclid=ml5b4zi1us569177487")]
        ]
        await update.message.reply_text(
            "⭐ Оставьте отзыв на любой площадке и пришлите скриншот сюда.\n\nПосле модерации +250 бонусов!",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return
 
    if msg == "📍 Адреса самовывоза":
        await update.message.reply_text("📍 Иркутск, Улица Дыбовского, 8/5\n⏰ 09:00-20:00")
        return
 
    if msg == "🛒 Оформить заказ":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Заказать на сайте", url="https://fruttosmile.ru/")],
            [InlineKeyboardButton("🤖 Заказать через бота", url="https://t.me/fruttosmile_bot")],
            [InlineKeyboardButton("💬 Связаться с магазином", url="https://t.me/@fruttosmile")]
        ])
        await update.message.reply_text("Выберите способ заказа:", reply_markup=kb)
        return
 
    if msg == "📊 Информация о бонусах":
        if not users_sheet:
            await update.message.reply_text("База недоступна.")
            return
 
        phone = context.user_data.get('phone')
        if not phone:
            await update.message.reply_text("Сначала зарегистрируйтесь!")
            return
 
        phone = normalize_phone(phone)
 
        try:
            cell = None
            variants = get_phone_variants(phone)
            for variant in variants:
                try:
                    cell = users_sheet.find(variant, in_column=4)
                    if cell:
                        break
                except:
                    pass
 
            if cell:
                balance = int(users_sheet.cell(cell.row, 5).value or 0)
                await update.message.reply_text(f"🎁 Ваш баланс: {balance} бонусов.")
            else:
                await update.message.reply_text("Номер не найден.")
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {str(e)}")
        return
 
    await update.message.reply_text("Неизвестная команда.")
 
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
 
    # ====== РАССЫЛКА: админ отправляет фото ======
    if user_id == ADMIN_ID and context.user_data.get("broadcast_waiting_photo"):
        file_id = message.photo[-1].file_id
 
        BROADCAST_DATA[ADMIN_ID]["photo"] = file_id
        context.user_data["broadcast_waiting_photo"] = False
        ADMIN_STATES[ADMIN_ID] = "ADMIN_BROADCAST_WAIT_DELAY"
 
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏱ 1 минута", callback_data="broadcast_delay_60")],
            [InlineKeyboardButton("⏱ 2 минуты", callback_data="broadcast_delay_120")],
            [InlineKeyboardButton("⏱ 5 минут", callback_data="broadcast_delay_300")]
        ])
 
        await update.message.reply_text(
            "📷 Фото сохранено!\n\nТеперь выберите интервал отправки:",
            reply_markup=kb
        )
        return
 
    if user_id == ADMIN_ID and message.photo:
        target_id = ADMIN_LAST_REQUEST.get(ADMIN_ID)
        if not target_id:
            await message.reply_text("❌ Нет активного запроса на фото.")
            return
 
        await context.bot.send_photo(
            chat_id=target_id,
            photo=message.photo[-1].file_id,
            caption="📸 Ваш заказ готов! Приятного аппетита! 🍓"
        )
        await message.reply_text(f"✅ Фото отправлено клиенту (ID: {target_id})")
        del ADMIN_LAST_REQUEST[ADMIN_ID]
        return
 
    if context.user_data.get('state') == 'WAIT_REVIEW':
        phone = context.user_data.get('phone', 'Не указан')
        name = update.message.from_user.full_name
        client_id = update.effective_user.id
 
        await update.message.reply_text("✅ Скриншот принят! Ожидайте начисления бонусов.")
 
        admin_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Принять (+250)", callback_data=f"rev_app_{client_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"rev_rej_{client_id}")
            ]
        ])
 
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"📸 <b>НОВЫЙ ОТЗЫВ!</b>\n👤 {name}\n📱 {phone}\n🆔 ID: {client_id}",
            parse_mode="HTML",
            reply_markup=admin_kb
        )
        context.user_data['state'] = None
 
    return
 
async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
 
    print("USER CALLBACK:", data)
 
    if data.startswith("cat_"):
        category = data.split("_")[1]
        items = PRODUCTS.get(category, [])
 
        if not items:
            await query.message.reply_text("Категория не найдена.")
            return
 
        for item in items:
            caption = f"{item['name']}\nЦена: {item['price']} руб."
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Заказать на сайте", url="https://fruttosmile.ru/")],
                [InlineKeyboardButton("Связаться с магазином", url="https://t.me/fruttosmile_bot")]
            ])
            await context.bot.send_photo(
                chat_id=query.message.chat.id,
                photo=item['photo'],
                caption=caption,
                reply_markup=kb
            )
 
        return
 
    if data == "confirm_photo_request":
        phone = context.user_data.get('phone')
        uid = update.effective_user.id
 
        if not phone:
            await query.message.reply_text("Сначала зарегистрируйтесь.")
            return
 
        await process_photo_request(update, context, phone)
 
        context.user_data.pop('state', None)
        return
 
    if data == "cancel_photo_request":
        await query.edit_message_text("Запрос отменён.")
        context.user_data.pop('state', None)
        await send_main_menu(update, context)
        return
 
    if data.startswith("st_"):
        parts = data.split("_")
        if len(parts) < 3:
            return
 
        uid = int(parts[2])
 
        if "ready" in data:
            await context.bot.send_message(uid, "✅ Заказ готов! Фото скоро придёт.")
            ADMIN_LAST_REQUEST[ADMIN_ID] = uid
            await context.bot.send_message(
                ADMIN_ID,
                f"📸 Отправьте фото заказа клиенту (ID: {uid})"
            )
 
        elif "work" in data:
            await context.bot.send_message(uid, "⏳ Заказ в работе!")
 
        else:
            await context.bot.send_message(uid, "❌ Заказ не найден.")
 
        return
 
    if data.startswith("rev_"):
        parts = data.split("_")
        if len(parts) < 3:
            return
 
        action = parts[1]
        client_id = int(parts[2])
 
        if action == "app":
            if users_sheet:
                try:
                    cell = users_sheet.find(str(client_id), in_column=1)
                    if cell:
                        row = cell.row
                        current = int(users_sheet.cell(row, 5).value or 0)
                        new_balance = current + 250
                        users_sheet.update_cell(row, 5, new_balance)
                        users_sheet.update_cell(row, 7, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
 
                        if logs_sheet:
                            logs_sheet.append_row([
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                ADMIN_ID,
                                "review_bonus",
                                users_sheet.cell(row, 4).value or "Не указан",
                                250,
                                "Бонус за отзыв"
                            ], value_input_option="RAW")
 
                        await context.bot.send_message(client_id, "🎉 Отзыв проверен! +250 бонусов.")
                        await query.edit_message_caption(caption=query.message.caption + "\n\n✅ ОДОБРЕНО. +250")
                except Exception as e:
                    await context.bot.send_message(client_id, f"Ошибка: {str(e)}")
 
        elif action == "rej":
            await context.bot.send_message(client_id, "❌ Отзыв отклонён.")
            await query.edit_message_caption(caption=query.message.caption + "\n\n❌ ОТКЛОНЕНО.")
            return
 
        return
 
# ========================================================
#  АДМИНКА + РАССЫЛКА
# ========================================================
 
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Доступ запрещён.")
        return
 
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Найти клиента", callback_data="admin_find_client")],
        [InlineKeyboardButton("📢 Сделать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]
    ])
 
    await update.message.reply_text("🛠 Админ-панель", reply_markup=kb)
 
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
 
    print("ADMIN CALLBACK:", data)
 
    uid = query.from_user.id
 
    if uid != ADMIN_ID:
        return
 
    if data == "admin_find_client":
        ADMIN_STATES[uid] = "ADMIN_WAIT_PHONE"
        await query.message.reply_text(
            "Введите номер телефона клиента (например +79991234567):",
            reply_markup=ReplyKeyboardRemove()
        )
 
    elif data == "admin_back":
        ADMIN_STATES.pop(uid, None)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Найти клиента", callback_data="admin_find_client")],
            [InlineKeyboardButton("📢 Сделать рассылку", callback_data="admin_broadcast")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]
        ])
        await query.message.reply_text("🛠 Админ-панель", reply_markup=kb)
        return
 
    elif data == "admin_broadcast":
        ADMIN_STATES[uid] = "ADMIN_BROADCAST_WAIT_TEXT"
        BROADCAST_DATA[uid] = {"text": None, "photo": None, "delay": 60}
        context.user_data["broadcast_waiting_photo"] = False  # Сброс старого
        await query.message.reply_text("📢 Введите текст рассылки.\n\nЕсли хотите отменить — напишите /admin")
        return
 
    elif data == "broadcast_skip_photo":
        BROADCAST_DATA[uid]["photo"] = None
        ADMIN_STATES[uid] = "ADMIN_BROADCAST_WAIT_DELAY"
        context.user_data["broadcast_waiting_photo"] = False
 
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏱ 1 минута", callback_data="broadcast_delay_60")],
            [InlineKeyboardButton("⏱ 2 минуты", callback_data="broadcast_delay_120")],
            [InlineKeyboardButton("⏱ 5 минут", callback_data="broadcast_delay_300")]
        ])
 
        await query.message.reply_text(
            "📢 Фото пропущено.\n\nТеперь выберите интервал отправки:",
            reply_markup=kb
        )
        return
 
    elif data.startswith("broadcast_delay_"):
        delay = int(data.split("_")[-1])
        BROADCAST_DATA[uid]["delay"] = delay
 
        text_preview = BROADCAST_DATA[uid]["text"]
        photo_preview = BROADCAST_DATA[uid]["photo"]
 
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Готово (начать рассылку)", callback_data="broadcast_start")],
            [InlineKeyboardButton("✏️ Изменить текст", callback_data="broadcast_edit_text")],
            [InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")]
        ])
 
        await query.message.reply_text(
            f"📌 Проверьте рассылку:\n\n"
            f"📝 Текст:\n{text_preview}\n\n"
            f"⏱ Интервал: {delay} секунд\n\n"
            f"Фото: {'Да' if photo_preview else 'Нет'}",
            reply_markup=kb
        )
        return
 
    elif data == "broadcast_edit_text":
        ADMIN_STATES[uid] = "ADMIN_BROADCAST_WAIT_TEXT"
        await query.message.reply_text("✏️ Введите новый текст рассылки:")
        return
 
    elif data == "broadcast_cancel":
        ADMIN_STATES.pop(uid, None)
        BROADCAST_DATA.pop(uid, None)
        context.user_data["broadcast_waiting_photo"] = False
 
        await query.message.reply_text("❌ Рассылка отменена.")
        await admin_panel(update, context)
        return
 
    elif data == "broadcast_start":
        text_msg = BROADCAST_DATA[uid]["text"]
        photo_id = BROADCAST_DATA[uid]["photo"]
        delay = BROADCAST_DATA[uid]["delay"]
 
        await query.message.reply_text("🚀 Рассылка началась...")
 
        ADMIN_STATES.pop(uid, None)
        BROADCAST_DATA.pop(uid, None)  # ← ДОБАВЛЕНО: очистка после старта
 
        asyncio.create_task(start_broadcast(context, text_msg, photo_id, delay))
 
        return
 
    elif data.startswith("admin_add_"):
        safe_phone = data.split("_")[2]
        phone = "+" + safe_phone
        phone = normalize_phone(phone)
        ADMIN_STATES[uid] = f"ADMIN_WAIT_AMOUNT_ADD_{safe_phone}"
        await query.message.reply_text(f"Введите сумму для добавления клиенту {phone}:")
        return
 
    elif data.startswith("admin_sub_"):
        safe_phone = data.split("_")[2]
        phone = "+" + safe_phone
        phone = normalize_phone(phone)
        ADMIN_STATES[uid] = f"ADMIN_WAIT_AMOUNT_SUB_{safe_phone}"
        await query.message.reply_text(f"Введите сумму для списания у клиента {phone}:")
        return
 
    else:
        print("UNHANDLED ADMIN CALLBACK:", data)
        return
 
async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return
 
    text = update.message.text.strip()
    state = ADMIN_STATES.get(uid)
 
    # ====== РАССЫЛКА ======
    if state == "ADMIN_BROADCAST_WAIT_TEXT":
        BROADCAST_DATA[uid]["text"] = text
        ADMIN_STATES[uid] = "ADMIN_BROADCAST_WAIT_PHOTO_OR_SKIP"
        context.user_data["broadcast_waiting_photo"] = True
 
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📷 Пропустить фото", callback_data="broadcast_skip_photo")]
        ])
 
        await update.message.reply_text(
            "✅ Текст сохранён.\n\nТеперь отправьте фото для рассылки или нажмите «Пропустить фото».",
            reply_markup=kb
        )
        return
 
    if state == "ADMIN_WAIT_PHONE":
        phone = normalize_phone(text)
 
        if not users_sheet:
            await update.message.reply_text("База недоступна.")
            ADMIN_STATES.pop(uid, None)
            return
 
        try:
            cell = None
            variants = get_phone_variants(phone)
            for variant in variants:
                try:
                    cell = users_sheet.find(variant, in_column=4)
                    if cell:
                        break
                except:
                    pass
 
            if cell:
                row = cell.row
                name = users_sheet.cell(row, 3).value or "Не указано"
                balance = int(users_sheet.cell(row, 5).value or 0)
 
                safe_phone = phone.replace("+", "")
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Добавить", callback_data=f"admin_add_{safe_phone}")],
                    [InlineKeyboardButton("➖ Списать", callback_data=f"admin_sub_{safe_phone}")],
                    [InlineKeyboardButton("🔍 Найти другого клиента", callback_data="admin_find_client")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]
                ])
 
                await update.message.reply_text(
                    f"Клиент найден:\nИмя: {name}\nТелефон: {phone}\nБаланс: {balance} бонусов",
                    reply_markup=kb
                )
                # ← НЕ УДАЛЯЕМ СОСТОЯНИЕ здесь! Оставляем, чтобы можно было нажать Добавить/Списать
            else:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Найти другого клиента", callback_data="admin_find_client")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]
                ])
                await update.message.reply_text(f"❌ Клиент с номером {phone} не найден.", reply_markup=kb)
                ADMIN_STATES.pop(uid, None)  # ← УДАЛЯЕМ ТОЛЬКО если не найден
 
        except Exception as e:
            await update.message.reply_text(f"Ошибка поиска: {str(e)}")
            ADMIN_STATES.pop(uid, None)
 
        return
 
    if state and state.startswith("ADMIN_WAIT_AMOUNT_ADD_"):
        if not users_sheet:
            await update.message.reply_text("База недоступна.")
            ADMIN_STATES.pop(uid, None)
            return
 
        safe_phone = state.split("_")[-1]
        phone = "+" + safe_phone
        phone = normalize_phone(phone)
 
        try:
            amount = int(text)
            if amount <= 0:
                raise ValueError
 
            cell = None
            variants = get_phone_variants(phone)
            for variant in variants:
                try:
                    cell = users_sheet.find(variant, in_column=4)
                    if cell:
                        break
                except:
                    pass
 
            if cell:
                row = cell.row
                current = int(users_sheet.cell(row, 5).value or 0)
                new_balance = current + amount
                users_sheet.update_cell(row, 5, new_balance)
                users_sheet.update_cell(row, 7, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
 
                if logs_sheet:
                    logs_sheet.append_row([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ADMIN_ID,
                        f"admin_add {amount}",
                        phone,
                        amount,
                        "Добавлено админом"
                    ], value_input_option="RAW")
 
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Найти клиента", callback_data="admin_find_client")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]
                ])
 
                await update.message.reply_text(f"Добавлено {amount} бонусов. Новый баланс: {new_balance}", reply_markup=kb)
            else:
                await update.message.reply_text("Клиент не найден.")
        except:
            await update.message.reply_text("Введите положительное число.")
 
        ADMIN_STATES.pop(uid, None)
        return
 
    if state and state.startswith("ADMIN_WAIT_AMOUNT_SUB_"):
        if not users_sheet:
            await update.message.reply_text("База недоступна.")
            ADMIN_STATES.pop(uid, None)
            return
 
        safe_phone = state.split("_")[-1]
        phone = "+" + safe_phone
        phone = normalize_phone(phone)
 
        try:
            amount = int(text)
            if amount <= 0:
                raise ValueError
 
            cell = None
            variants = get_phone_variants(phone)
            for variant in variants:
                try:
                    cell = users_sheet.find(variant, in_column=4)
                    if cell:
                        break
                except:
                    pass
 
            if cell:
                row = cell.row
                current = int(users_sheet.cell(row, 5).value or 0)
                new_balance = max(0, current - amount)
                users_sheet.update_cell(row, 5, new_balance)
                users_sheet.update_cell(row, 7, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
 
                if logs_sheet:
                    logs_sheet.append_row([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ADMIN_ID,
                        f"admin_sub {amount}",
                        phone,
                        -amount,
                        "Списано админом"
                    ], value_input_option="RAW")
 
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Найти клиента", callback_data="admin_find_client")],
                    [InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]
                ])
 
                await update.message.reply_text(f"Списано {amount} бонусов. Новый баланс: {new_balance}", reply_markup=kb)
            else:
                await update.message.reply_text("Клиент не найден.")
        except:
            await update.message.reply_text("Введите положительное число.")
 
        ADMIN_STATES.pop(uid, None)
        return
 
# ФУНКЦИЯ РАССЫЛКИ — исправленная версия
async def start_broadcast(context: ContextTypes.DEFAULT_TYPE, text: str, photo: str, delay: int):
    if not users_sheet:
        await context.bot.send_message(chat_id=ADMIN_ID, text="❌ Ошибка: База данных недоступна.")
        return
 
    try:
        # Получаем все ID за один запрос к таблице, чтобы не нагружать API
        ids = users_sheet.col_values(1)[1:] 
    except Exception as e:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ Ошибка чтения таблицы: {e}")
        return
 
    sent, failed = 0, 0
    for uid_raw in ids:
        if not str(uid_raw).strip(): 
            continue # Пропуск пустых строк
        try:
            target_id = int(uid_raw)
            if photo:
                await context.bot.send_photo(chat_id=target_id, photo=photo, caption=text)
            else:
                await context.bot.send_message(chat_id=target_id, text=text)
            sent += 1
            # Анти-спам задержка: Telegram рекомендует не более 30 сообщ/сек
            await asyncio.sleep(delay) 
        except Exception:
            failed += 1
            continue
 
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"✅ Рассылка завершена!\n\nОтправлено: {sent}\nОшибок (блок бота): {failed}"
    )
 
def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

    # Обработка текста через глобальный распределитель
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, global_text_handler))

    # 1. Сначала админские действия и рассылка (admin_ и broadcast_)
    app.add_handler(CallbackQueryHandler(
        admin_callback, 
        pattern=r"^(admin_|broadcast_)"
    ))
    
    # 2. Потом действия, общие для всех (отзывы rev_, статусы st_, категории cat_, подтверждения confirm_/cancel_)
    app.add_handler(CallbackQueryHandler(
        query_handler, 
        pattern=r"^(cat_|confirm_|cancel_|st_|rev_)"
    ))
    
    app.run_polling()
 
if __name__ == "__main__":
    main()
