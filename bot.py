
import sys
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
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
# КОНФИГУРАЦИЯ
# ────────────────────────────────────────────────

BOT_TOKEN = "8589427171:AAEZ2J3Eug-ynLUuGZlM4ByYeY-sGWjFe2Q"          # ← обязательно заменить!
ADMIN_ID = 1165444045             # ← ID менеджера
# храним соответствие: сообщение менеджеру → клиент
ADMIN_LAST_REQUEST = {}


# Health check сервер для Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

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


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number
    state = context.user_data.get('state')

    if state == 'WAIT_ORDER':
        await process_photo_request(update, context, phone)
    else:
        context.user_data['phone'] = phone
        context.user_data['bonuses'] = 300
        await update.message.reply_text("🎉 Регистрация успешна! Вам начислено 300 бонусов.")
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
        await update.message.reply_text("Выберите категорию для просмотра нашего ассортимента:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if msg == "⭐ Оставить отзыв":
        context.user_data['state'] = 'WAIT_REVIEW'
        kb = [
            [InlineKeyboardButton("Яндекс", url="https://yandex.ru/maps/org/fruttosmile/58246506027/?ll=104.353133%2C52.259946&z=14"), InlineKeyboardButton("2ГИС", url="https://2gis.ru/irkutsk/firm/1548641653278292/104.353179%2C52.259892")],
            [InlineKeyboardButton("Avito", url="https://www.avito.ru/brands/i190027211?ysclid=ml5c5ji39d797258865"), InlineKeyboardButton("VK", url="https://vk.com/fruttosmile?ysclid=ml5b4zi1us569177487")]
        ]
        await update.message.reply_text(
            "⭐ Оставьте отзыв о Fruttosmile на любой площадке и пришлите скриншот сюда.\n\n"
            "После модерации мы начислим вам 250 бонусов! 📸",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    if msg == "📍 Адреса самовывоза":
        await update.message.reply_text("📍 Мы ждем вас по адресу: [Иркутск, Улица Дыбовского, 8/5]\n⏰ Работаем каждый день с 09:00 до 20:00")
        return

    if msg == "📊 Информация о бонусах":
        bonuses = context.user_data.get('bonuses', 0)
        if 'phone' not in context.user_data:
            await update.message.reply_text("Сначала зарегистрируйтесь!")
        else:
            await update.message.reply_text(f"🎁 Ваш баланс: {bonuses} бонусов.")
        return

    if msg == "🛒 Оформить заказ":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Оформить на сайте", url="https://fruttosmile.ru/")]
        ])
        await update.message.reply_text("Перейдите на сайт для оформления заказа 🍓", reply_markup=kb)
        return


async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "confirm_photo_request":
        phone = context.user_data.get('phone')
        uid = update.effective_user.id
        
        if not phone:
            await query.message.reply_text("Сначала зарегистрируйтесь (поделитесь номером).")
            return

        await process_photo_request(update, context, phone)

        # Запоминаем, что ждём фото для этого клиента
        ADMIN_LAST_REQUEST[ADMIN_ID] = uid

        await query.message.reply_text(
            "✅ Запрос отправлен.\nМенеджер пришлёт фото, как только заказ будет готов."
        )
        context.user_data.pop('state', None)

    elif data == "cancel_photo_request":
        await query.edit_message_text("Запрос отменён.")
        context.user_data.pop('state', None)
        await send_main_menu(update, context)

    elif data.startswith("st_"):
        parts = data.split("_")
        if len(parts) < 3:
            await query.answer("Ошибка в данных", show_alert=True)
            return

        uid = int(parts[2])

        if "ready" in data:
            txt = "✅ Заказ готов! Фото придёт скоро."
            await context.bot.send_message(chat_id=uid, text=txt)

            # Запоминаем клиента, для которого ждём фото
            ADMIN_LAST_REQUEST[ADMIN_ID] = uid

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "📸 **Отправьте фото заказа** (просто прикрепите фото в этот чат)\n"
                    f"Оно будет автоматически отправлено клиенту (ID: {uid})"
                ),
                parse_mode="Markdown"
            )
            await query.answer("Ожидаю фото от вас ✅")

        elif "work" in data:
            txt = "⏳ Заказ в работе!"
            await context.bot.send_message(chat_id=uid, text=txt)
            await query.answer("Статус обновлён")

        else:
            txt = "❌ Заказ не найден."
            await context.bot.send_message(chat_id=uid, text=txt)
            await query.answer("Статус обновлён")

    # Логика обработки кнопок отзыва — ВЫНЕСЕНА НА УРОВЕНЬ ВЫШЕ
    elif data.startswith("rev_"):
        parts = data.split("_")
        if len(parts) < 3:
            await query.answer("Ошибка в данных отзыва", show_alert=True)
            return

        action = parts[1]  # app или rej
        client_id = int(parts[2])

        if action == "app":
            # Начисляем бонусы пользователю
            user_data = context.application.user_data.get(client_id, {})
            current_bonuses = user_data.get('bonuses', 0)
            user_data['bonuses'] = current_bonuses + 250
            context.application.user_data[client_id] = user_data

            await context.bot.send_message(
                chat_id=client_id,
                text="🎉 Ваш отзыв проверен! Вам начислено 250 бонусов."
            )
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n✅ ОДОБРЕНО. +250 бонусов."
            )

        elif action == "rej":
            await context.bot.send_message(
                chat_id=client_id,
                text="❌ Ваш отзыв не прошел модерацию."
            )
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n❌ ОТКЛОНЕНО."
            )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id

    # Фото от администратора — отправка фото заказа клиенту
    if user_id == ADMIN_ID and message.photo:
        target_id = ADMIN_LAST_REQUEST.get(ADMIN_ID)

        if not target_id:
            await message.reply_text("❌ Сейчас нет активного запроса на отправку фото.")
            return

        try:
            await context.bot.send_photo(
                chat_id=target_id,
                photo=message.photo[-1].file_id,
                caption="📸 Ваш заказ готов! Приятного аппетита! 🍓"
            )

            await message.reply_text(
                f"✅ Фото успешно отправлено клиенту (ID: {target_id})"
            )

            # Очищаем — больше не ждём фото для этого клиента
            del ADMIN_LAST_REQUEST[ADMIN_ID]

        except Exception as e:
            await message.reply_text(f"❌ Ошибка при отправке фото: {str(e)}")

        return

    # Обработка скриншотов отзывов (от клиента)
    if context.user_data.get('state') == 'WAIT_REVIEW':
        phone = context.user_data.get('phone', 'Не указан')
        name = update.message.from_user.full_name
        client_id = update.effective_user.id

        await update.message.reply_text("✅ Скриншот принят! Ожидайте начисления бонусов. 💛")

        # Добавляем кнопки для админа
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


def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(query_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
