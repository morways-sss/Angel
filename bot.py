import telebot
from telebot import types
import logging
import html

# --- НАСТРОЙКИ ---
BOT_TOKEN = "СЮДА_ВСТАВЬ_НОВЫЙ_ТОКЕН_БРАТА"  # Токен нового бота от BotFather
ADMIN_CHAT_ID = -1003897470783  # ID нового канала брата
# ------------------

bot = telebot.TeleBot(BOT_TOKEN)
logging.basicConfig(level=logging.INFO)

# Временное хранилище для активных заявок
user_requests = {}

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # Изменённая кнопка: геймпад заменён на мешок с деньгами 💰
    btn_payout = types.KeyboardButton("💰 Получить выплату за промокод")
    btn_profile = types.KeyboardButton("👤 Личный кабинет")
    btn_support = types.KeyboardButton("🆘 Поддержка")
    markup.add(btn_payout)
    markup.add(btn_profile, btn_support)
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(
        message.chat.id, 
        f"Привет, {message.from_user.first_name}! Добро пожаловать в бот выплат. Воспользуйся меню ниже:",
        reply_markup=get_main_keyboard()
    )

# --- ОБРАБОТКА ОТВЕТОВ ИЗ КАНАЛА ---
@bot.channel_post_handler(func=lambda message: message.reply_to_message is not None)
def handle_admin_reply(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return

    original_text = message.reply_to_message.caption or message.reply_to_message.text
    if not original_text or "User_ID:" not in original_text:
        return

    try:
        # Умный поиск ID (извлекает только цифры после двоеточия, исключая любые теги)
        raw_part = original_text.split("User_ID:")[1]
        clean_id = "".join(c for c in raw_part if c.isdigit())
        
        user_id = int(clean_id)
        
        if "Новый вопрос в поддержку!" in original_text:
            response_text = f"📢 <b>Ответ от поддержки:</b>\n\n{html.escape(message.text)}"
        else:
            response_text = f"📢 <b>Ответ по вашей заявке:</b>\n\n{html.escape(message.text)}"

        bot.send_message(chat_id=user_id, text=response_text, parse_mode="HTML")
        bot.send_message(ADMIN_CHAT_ID, f"✅ Ответ успешно отправлен игроку (ID: {user_id})", reply_markup=None)
    except Exception as e:
        bot.send_message(ADMIN_CHAT_ID, f"❌ Не удалось отправить ответ: {e}")

# --- ГЛАВНОЕ МЕНЮ ---
@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    if message.text == "💰 Получить выплату за промокод":
        user_requests[message.chat.id] = {}
        msg = bot.send_message(
            message.chat.id, 
            "<b>Шаг 1 из 3</b>\n\nОтправьте скриншот момента, как вы ввели промокод (из окна F2, где чётко видно, какой промокод был введён).\n\nПожалуйста, отправьте как изображение, а не файлом:", 
            parse_mode="HTML",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_step_screenshot)

    elif message.text == "👤 Личный кабинет":
        username = f"@{message.from_user.username}" if message.from_user.username else "Нет юзернейма"
        text = (
            f"👤 <b>Ваш Личный Кабинет</b>\n\n"
            f"Имя: {html.escape(message.from_user.full_name)}\n"
            f"Юзернейм: {html.escape(username)}\n"
            f"ID в Telegram: <code>{message.chat.id}</code>\n\n"
            f"Для подачи заявки на выплату используйте кнопку меню."
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=get_main_keyboard())

    elif message.text == "🆘 Поддержка":
        msg = bot.send_message(
            message.chat.id, 
            "Напишите ниже свой вопрос или опишите проблему. Администрация рассмотрит обращение в ближайшее время:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_support_question)

# --- ШАГИ ОФОРМЛЕНИЯ ЗАЯВКИ НА ВЫПЛАТУ ---
def process_step_screenshot(message):
    if message.text in ["💰 Получить выплату за промокод", "👤 Личный кабинет", "🆘 Поддержка"]:
        handle_menu(message)
        return

    if not message.photo:
        msg = bot.send_message(message.chat.id, "⚠️ Пожалуйста, отправьте именно скриншот (картинку):")
        bot.register_next_step_handler(msg, process_step_screenshot)
        return

    user_requests[message.chat.id]['photo_id'] = message.photo[-1].file_id

    msg = bot.send_message(
        message.chat.id, 
        "<b>Шаг 2 из 3</b>\n\nНапишите номер вашего банковского счёта на сервере:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_step_bank)

def process_step_bank(message):
    if message.text in ["💰 Получить выплату за промокод", "👤 Личный кабинет", "🆘 Поддержка"]:
        handle_menu(message)
        return

    if not message.text:
        msg = bot.send_message(message.chat.id, "⚠️ Пожалуйста, введите номер банковского счёта текстом:")
        bot.register_next_step_handler(msg, process_step_bank)
        return

    user_requests[message.chat.id]['bank'] = message.text

    msg = bot.send_message(
        message.chat.id, 
        "<b>Шаг 3 из 3</b>\n\nНапишите название или номер сервера Majestic RP, на котором вы играете (например: Detroit):",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_step_server)

def process_step_server(message):
    if message.text in ["💰 Получить выплату за промокод", "👤 Личный кабинет", "🆘 Поддержка"]:
        handle_menu(message)
        return

    if not message.text:
        msg = bot.send_message(message.chat.id, "⚠️ Пожалуйста, укажите ваш сервер текстом:")
        bot.register_next_step_handler(msg, process_step_server)
        return

    user_requests[message.chat.id]['server'] = message.text

    req_data = user_requests[message.chat.id]
    username = f"@{message.from_user.username}" if message.from_user.username else "Нет юзернейма"

    # Экранирование HTML-тегов, чтобы бот не крашился из-за спецсимволов игроков
    safe_name = html.escape(message.from_user.full_name)
    safe_username = html.escape(username)
    safe_server = html.escape(req_data['server'])
    safe_bank = html.escape(req_data['bank'])

    admin_text = (
        f"🚨 <b>Новая заявка на выплату!</b>\n\n"
        f"👤 <b>Игрок:</b> {safe_name} ({safe_username})\n"
        f"🌐 <b>Сервер:</b> {safe_server}\n"
        f"💳 <b>Банковский счёт:</b> <code>{safe_bank}</code>\n\n"
        f"User_ID: <code>{message.chat.id}</code>"
    )

    try:
        bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=req_data['photo_id'], caption=admin_text, parse_mode="HTML")
        bot.send_message(
            message.chat.id, 
            "✅ Спасибо! Ваша заявка, скриншот и данные успешно отправлены администрации на проверку. Ожидайте выплату.", 
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка при отправке заявки. Обратитесь в поддержку. ({e})", reply_markup=get_main_keyboard())
    
    if message.chat.id in user_requests:
        del user_requests[message.chat.id]

# --- ПОДДЕРЖКА ---
def process_support_question(message):
    if message.text in ["💰 Получить выплату за промокод", "👤 Личный кабинет", "🆘 Поддержка"]:
        handle_menu(message)
        return

    if not message.text:
        msg = bot.send_message(message.chat.id, "Пожалуйста, отправьте текстовое сообщение с вашим вопросом:")
        bot.register_next_step_handler(msg, process_support_question)
        return

    username = f"@{message.from_user.username}" if message.from_user.username else "Нет юзернейма"
    
    safe_name = html.escape(message.from_user.full_name)
    safe_username = html.escape(username)
    safe_question = html.escape(message.text)

    admin_text = (
        f"❓ <b>Новый вопрос в поддержку!</b>\n\n"
        f"👤 <b>Отправитель:</b> {safe_name} ({safe_username})\n"
        f"📝 <b>Вопрос:</b> {safe_question}\n\n"
        f"User_ID: <code>{message.chat.id}</code>"
    )

    bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text, parse_mode="HTML")
    bot.send_message(
        message.chat.id, 
        "Ваш вопрос отправлен администрации.", 
        reply_markup=get_main_keyboard()
    )

if __name__ == '__main__':
    print("Бот успешно запущен со встроенным меню...")
    bot.infinity_polling()