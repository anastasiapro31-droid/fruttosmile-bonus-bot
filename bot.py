import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8589427171:AAEZ2J3Eug-ynLUuGZlM4ByYeY-sGWjFe2Q" # Замени на токен нового бота
ADMIN_ID = 1165444045  # Твой ID, который ты скинула

# ================= ВЫБРАННЫЙ КАТАЛОГ ТОВАРОВ =================
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

# --- ОБНОВЛЕННЫЕ КНОПКИ КАТАЛОГА В text_handler ---
# (Замени блок elif msg == "📖 Каталог товаров" на этот)
    elif msg == "📖 Каталог товаров":
        kb = [
            [InlineKeyboardButton("🎁 Подарочные боксы", callback_data="cat_boxes")],
            [InlineKeyboardButton("🍓 Сладкие букеты", callback_data="cat_sweet")],
            [InlineKeyboardButton("💐 Цветы", callback_data="cat_flowers")],
            [InlineKeyboardButton("🍖 Мужские букеты", callback_data="cat_meat")]
        ]
        await update.message.reply_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(kb))

    elif msg == "📸 Получить фото заказа":
        context.user_data['state'] = 'WAIT_ORDER_NUMBER'
        phone_btn = KeyboardButton("📲 Отправить мой номер телефона", request_contact=True)
        back_kb = ReplyKeyboardMarkup([[phone_btn], ["⬅️ Назад"]], resize_keyboard=True)
        await update.message.reply_text("Подтвердите ваш номер телефона для поиска заказа:", reply_markup=back_kb)

# --- ОБНОВЛЕННЫЙ query_handler ---
async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("no_order_"):
        target_id = int(query.data.replace("no_order_", ""))
        await context.bot.send_message(chat_id=target_id, text="❌ К сожалению, заказ с таким номером не найден. Пожалуйста, проверьте номер или оформите новый заказ на сайте! 🍓")
        await query.edit_message_text(text=query.message.text + "\n\n🚫 ОТМЕНЕНО: Заказ не найден")

    elif query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
        products = PRODUCTS.get(category, [])
        
        # Удаляем сообщение с выбором категорий
        await query.message.delete()
        
        # Отправляем товары по одному
        for p in products:
            caption = f"<b>{p['name']}</b>\n💰 Цена: {p['price']}₽"
            try:
                await query.message.chat.send_photo(photo=p['photo'], caption=caption, parse_mode="HTML")
            except Exception as e:
                # Если ссылка на фото битая, отправим просто текст
                await query.message.chat.send_message(f"⚠️ Ошибка загрузки фото для: {p['name']}\n{caption}", parse_mode="HTML")

        # Добавляем кнопку назад после всех товаров
        back_kb = ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
        await query.message.chat.send_message("Это лишь малая часть нашей красоты! ✨\nЧтобы заказать, перейдите в раздел «Оформить заказ».", reply_markup=back_kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт и регистрация"""
    contact_btn = KeyboardButton("📲 Стать участником программы лояльности", request_contact=True)
    keyboard = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "Добро пожаловать в Fruttosmile! 🍓✨\n\n"
        "За регистрацию мы начисляем вам 300 приветственных бонусов.\n"
        "Нажмите кнопку ниже, чтобы войти в личный кабинет:",
        reply_markup=keyboard
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """После регистрации"""
    context.user_data['phone'] = update.message.contact.phone_number
    context.user_data['bonuses'] = 300 
    await update.message.reply_text("🎉 Поздравляем! Вам начислено 300 приветственных бонусов Fruttosmile!")
    await send_main_menu(update, context)

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню"""
    keyboard = [
        ['📊 Информация о бонусах', '📍 Адреса самовывоза'],
        ['🛒 Оформить заказ', '📖 Каталог товаров'],
        ['📸 Получить фото заказа', '⭐ Оставить отзыв']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    text = "Вы в главном меню Fruttosmile! 🍓 Чем можем помочь?"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_state = context.user_data.get('state')

    if msg == "⬅️ Назад":
        context.user_data['state'] = None
        await send_main_menu(update, context)
        return

    # МЕНЮ
    if msg == "📊 Информация о бонусах":
        bonuses = context.user_data.get('bonuses', 0)
        await update.message.reply_text(f"🎁 Ваш баланс: {bonuses} бонусов.\n\nИспользуйте их для оплаты заказов!")

    elif msg == "📍 Адреса самовывоза":
        await update.message.reply_text("📍 Мы ждем вас по адресу: Иркутск, Улица Дыбовского, 8/5\n⏰ Работаем каждый день с 09:00 до 20:00")

    elif msg == "🛒 Оформить заказ":
        kb = [[InlineKeyboardButton("🛍 Перейти на сайт", url="https://fruttosmile.ru")]]
        await update.message.reply_text("Оформить заказ можно на нашем сайте:", reply_markup=InlineKeyboardMarkup(kb))

    elif msg == "📖 Каталог товаров":
        kb = [
            [InlineKeyboardButton("🎁 Подарочные боксы", callback_data="cat_boxes")],
            [InlineKeyboardButton("🍓 Сладкие букеты", callback_data="cat_sweet")],
            [InlineKeyboardButton("💐 Цветы", callback_data="cat_flowers")],
            [InlineKeyboardButton("🍖 Мужские букеты", callback_data="cat_meat")]
        ]
        await update.message.reply_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(kb))

    elif msg == "⭐ Оставить отзыв":
        context.user_data['state'] = 'WAIT_REVIEW'
        back_kb = ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
        links = [
            [InlineKeyboardButton("Яндекс", url="https://yandex.ru/maps/org/fruttosmile/58246506027/"), 
             InlineKeyboardButton("2ГИС", url="https://2gis.ru/irkutsk/firm/1548641653278292/")],
            [InlineKeyboardButton("Avito", url="https://www.avito.ru/brands/i190027211"), 
             InlineKeyboardButton("VK", url="https://vk.com/fruttosmile")]
        ]
        await update.message.reply_text("⭐ Пришлите скриншот отзыва сюда для получения 250 бонусов!", reply_markup=back_kb)
        await update.message.reply_text("Ссылки на площадки:", reply_markup=InlineKeyboardMarkup(links))

    elif msg == "📸 Получить фото заказа":
        context.user_data['state'] = 'WAIT_ORDER_NUMBER'
        phone_btn = KeyboardButton("📲 Отправить мой номер телефона", request_contact=True)
        back_kb = ReplyKeyboardMarkup([[phone_btn], ["⬅️ Назад"]], resize_keyboard=True)
        await update.message.reply_text("Подтвердите ваш номер телефона для поиска заказа:", reply_markup=back_kb)

    elif user_state == 'WAIT_ORDER_NUMBER':
        # Если прислали контакт или текст
        search_phone = update.message.text if update.message.text else update.message.contact.phone_number
        user_id = update.message.from_user.id
        await update.message.reply_text(f"Ищу заказ по номеру: {search_phone}... 🔍\nЗапрос отправлен менеджеру!")
        
        admin_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Заказ не найден", callback_data=f"no_order_{user_id}")]])
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 <b>ЗАПРОС ФОТО</b>\n📱 Телефон: {search_phone}\n👤 Клиент: {update.message.from_user.full_name}\n🆔 ID: <code>{user_id}</code>",
            reply_markup=admin_kb,
            parse_mode="HTML"
        )
        context.user_data['state'] = None

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("no_order_"):
        target_id = int(query.data.replace("no_order_", ""))
        await context.bot.send_message(chat_id=target_id, text="❌ Заказ по этому номеру не найден. Попробуйте уточнить данные или оформите новый заказ! 🍓")
        await query.edit_message_text(text=query.message.text + "\n\n🚫 ОТМЕНЕНО")

    elif query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
        products = PRODUCTS.get(category, [])
        await query.message.delete()
        for p in products:
            await query.message.chat.send_photo(photo=p['photo'], caption=f"<b>{p['name']}</b>\n💰 Цена: {p['price']}₽", parse_mode="HTML")
        await query.message.chat.send_message("Для заказа вернитесь в меню.", reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True))

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID and update.message.reply_to_message:
        try:
            target_id = int(update.message.reply_to_message.text.split("🆔 ID: ")[1].strip())
            await context.bot.send_photo(chat_id=target_id, photo=update.message.photo[-1].file_id, caption="Ваше фото заказа! ✨")
            await update.message.reply_text("✅ Отправлено!")
        except:
            await update.message.reply_text("Ошибка отправки.")
            
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(query_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
