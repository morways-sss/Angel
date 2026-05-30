import telebot
from telebot import types
import logging
import html

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8799157488:AAGyd29t4Ip3dK5AnY2O5gJWCPXMKkgaAwg"  # Токен бота
ADMIN_CHAT_ID = -1003897470783  # ID канала брата
# ------------------

bot = telebot.TeleBot(BOT_TOKEN)
logging.basicConfig(level=logging.INFO)

# Временное хранилище данных
user_requests = {}

# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_payout = types.KeyboardButton("💰 Оформить выплату")
    btn_profile = types.KeyboardButton("👤 Мой профиль")
    btn_support = types.KeyboardButton("🆘 Связь с админом")
    markup.add(btn_payout)
    markup.add(btn_profile, btn_support)
    return markup

def get_cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_cancel = types.KeyboardButton("🔙 Назад в меню")
    markup.add(btn_cancel)
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    welcome_text = (
        f"Приветствуем, {message.from_user.first_name}!\n\n"
        f"Это официальный автоматизированный сервис по обработке промокодов и выдаче вознаграждений. "
        f"Используйте интерактивное меню ниже для навигации:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

# --- ОБРАБОТКА ОТВЕТОВ ИЗ КАНАЛА ---
@bot.channel_post_handler(func=lambda message: message.reply_to_message is not None)
def handle_admin_reply(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return

    original_text = message.reply_to_message.caption or message.reply_to_message.text
    if not original_text or "User_ID:" not in original_text:
        return

    try:
        raw_part = original_text.split("User_ID:")[1]
        clean_id = "".join(c for c in raw_part if c.isdigit())
        user_id = int(clean_id)
        
        if "Поступило новое обращение!" in original_text:
            response_text = f"✉️ <b>Официальный ответ администрации:</b>\n\n{html.escape(message.text)}"
        else:
            response_text = f"💵 <b>Статус вашей заявки изменен:</b>\n\n{html.escape(message.text)}"

        bot.send_message(chat_id=user_id, text=response_text, parse_mode="HTML")
        bot.send_message(ADMIN_CHAT_ID, f"✅ Уведомление отправлено пользователю (ID: {user_id})", reply_markup=None)
    except Exception as e:
        bot.send_message(ADMIN_CHAT_ID, f"❌ Ошибка отправки: {e}")

# --- ГЛАВНОЕ МЕНЮ ---
@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    if message.text == "🔙 Назад в меню":
        if message.chat.id in user_requests:
            del user_requests[message.chat.id]
        bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=get_main_keyboard())
        return

    if message.text == "💰 Оформить выплату":
        user_requests[message.chat.id] = {}
        msg = bot.send_message(
            message.chat.id, 
            "<b>Этап 1 из 3: Верификация промокода</b>\n\n"
            "Пожалуйста, отправьте скриншот из игры (меню F2), подтверждающий успешную активацию промокода.\n\n"
            "<i>Важно: отправляйте файл как обычное изображение (сжатое), а не документом.</i>", 
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        bot.register_next_step_handler(msg, process_step_screenshot)

    elif message.text == "👤 Мой профиль":
        username = f"@{message.from_user.username}" if message.from_user.username else "Не установлен"
        text = (
            f"📋 <b>Информация об аккаунте</b>\n\n"
            f"• Пользователь: {html.escape(message.from_user.full_name)}\n"
            f"• Telegram-логин: {html.escape(username)}\n"
            f"• Ваш уникальный ID: <code>{message.chat.id}</code>\n\n"
            f"Все активные операции и запросы осуществляются через вкладки меню."
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=get_main_keyboard())

    elif message.text == "🆘 Связь с админом":
        msg = bot.send_message(
            message.chat.id, 
            "<b>Техническая поддержка</b>\n\n"
            "Опишите вашу проблему или задайте интересующий вопрос в одном текстовом сообщении. "
            "Специалисты рассмотрят его в порядке очереди.",
            reply_markup=get_cancel_keyboard()
        )
        bot.register_next_step_handler(msg, process_support_question)

# --- ЭТАПЫ КВЕСТА НА ВЫПЛАТУ ---
def process_step_screenshot(message):
    if message.text == "🔙 Назад в меню" or message.text in ["💰 Оформить выплату", "👤 Мой профиль", "🆘 Связь с админом"]:
        handle_menu(message)
        return

    if not message.photo:
        msg = bot.send_message(message.chat.id, "⚠️ Система ожидает изображение. Пожалуйста, отправьте скриншот:")
        bot.register_next_step_handler(msg, process_step_screenshot)
        return

    user_requests[message.chat.id]['photo_id'] = message.photo[-1].file_id

    msg = bot.send_message(
        message.chat.id, 
        "<b>Этап 2 из 3: Платёжные реквизиты</b>\n\n"
        "Укажите номер вашего банковского счёта внутри игры, куда должны поступить средства:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_step_bank)

def process_step_bank(message):
    if message.text == "🔙 Назад в меню" or message.text in ["💰 Оформить выплату", "👤 Мой профиль", "🆘 Связь с админом"]:
        handle_menu(message)
        return

    if not message.text:
        msg = bot.send_message(message.chat.id, "⚠️ Текст не распознан. Наберите номер банковского счёта вручную:")
        bot.register_next_step_handler(msg, process_step_bank)
        return

    user_requests[message.chat.id]['bank'] = message.text

    msg = bot.send_message(
        message.chat.id, 
        "<b>Этап 3 из 3: Игровой мир</b>\n\n"
        "Напишите название игрового сервера Majestic RP (например: San Francisco, Detroit, New York):",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_step_server)

def process_step_server(message):
    if message.text == "🔙 Назад в меню" or message.text in ["💰 Оформить выплату", "👤 Мой профиль", "🆘 Связь с админом"]:
        handle_menu(message)
        return

    if not message.text:
        msg = bot.send_message(message.chat.id, "⚠️ Пожалуйста, введите название сервера текстом:")
        bot.register_next_step_handler(msg, process_step_server)
        return

    user_requests[message.chat.id]['server'] = message.text

    req_data = user_requests[message.chat.id]
    username = f"@{message.from_user.username}" if message.from_user.username else "Отсутствует"

    safe_name = html.escape(message.from_user.full_name)
    safe_username = html.escape(username)
    safe_server = html.escape(req_data['server'])
    safe_bank = html.escape(req_data['bank'])

    admin_text = (
        f"📊 <b>Зарегистрирована новая анкета на выплату!</b>\n\n"
        f"• <b>Пользователь:</b> {safe_name} ({safe_username})\n"
        f"• <b>Игровой сервер:</b> {safe_server}\n"
        f"• <b>Реквизиты банка:</b> <code>{safe_bank}</code>\n\n"
        f"User_ID: <code>{message.chat.id}</code>"
    )

    try:
        bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=req_data['photo_id'], caption=admin_text, parse_mode="HTML")
        bot.send_message(
            message.chat.id, 
            "✨ Направление успешно сформировано! Ваша заявка и скриншот переданы на модерацию администраторам. Ожидайте зачисления транзакции.", 
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Сбой отправки пакета данных. Обратитесь к кураторам. ({e})", reply_markup=get_main_keyboard())
    
    if message.chat.id in user_requests:
        del user_requests[message.chat.id]

# --- ПОДДЕРЖКА ---
def process_support_question(message):
    if message.text == "🔙 Назад в меню" or message.text in ["💰 Оформить выплату", "👤 Мой профиль", "🆘 Связь с админом"]:
        handle_menu(message)
        return

    if not message.text:
        msg = bot.send_message(message.chat.id, "Пожалуйста, сформулируйте ваше текстовое обращение:")
        bot.register_next_step_handler(msg, process_support_question)
        return

    username = f"@{message.from_user.username}" if message.from_user.username else "Отсутствует"
    
    safe_name = html.escape(message.from_user.full_name)
    safe_username = html.escape(username)
    safe_question = html.escape(message.text)

    admin_text = (
        f"📬 <b>Поступило новое обращение!</b>\n\n"
        f"• <b>Отправитель:</b> {safe_name} ({safe_username})\n"
        f"• <b>Суть вопроса:</b> {safe_question}\n\n"
        f"User_ID: <code>{message.chat.id}</code>"
    )

    bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text, parse_mode="HTML")
    bot.send_message(
        message.chat.id, 
        "Ваш тикет зарегистрирован. Когда руководство подготовит ответ, он отобразится прямо в этом диалоге.", 
        reply_markup=get_main_keyboard()
    )

if __name__ == '__main__':
    print("Бот успешно запущен со встроенным меню...")
    bot.infinity_polling()
