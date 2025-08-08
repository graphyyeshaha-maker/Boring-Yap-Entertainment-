# -*- coding: utf-8 -*-

import os
import logging
import sqlite3
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram import BotCommandScopeAllPrivateChats, BotCommandScopeChat
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)
from telegram.error import BadRequest, Forbidden

# --- Konfigurasi Admin dan Database ---
TOKEN = os.getenv("BOT_TOKEN")  # Ambil dari Environment Variable di Koyeb
ADMIN_IDS = [6132898723]        # GANTI DENGAN CHAT_ID ANDA!
DB_NAME = "yapchat_database.db" # Nama database khusus untuk bot ini

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation Handler States
SELECT_LANG, GET_AGE, GET_GENDER, GET_CITY = range(4)
CONFIRM_REPORT = range(1)

# --- Multi-Language Text ---
LANGUAGES = {
    'en': {
        "select_language": "Please select your language. / Silakan pilih bahasa Anda.",
        "ask_age": "First, let's set up your profile. How old are you?",
        "invalid_age": "Please enter a valid age (between 13 and 99).",
        "ask_gender": "Great! Now, please select your gender.",
        "invalid_gender": "Please select a valid option from the keyboard.",
        "ask_city": "Lastly, please enter your city of origin (e.g., London, New York).\n\n*This information is for demographic purposes only and will NOT be shown to other users.*",
        "profile_complete": "Your profile is all set up! Let the fun begin! 🎉",
        "cancel_setup": "Profile setup cancelled. You can start again with /start.",
        "main_menu": (
            "👋✨ *Bored? Looking for new networking? Someone to yap with?* lmao, this is the right place! 🥳\n\n"
            "👇 Press the button below to find a chat partner!"
        ),
        "start_chat_button": "💬 Start Chat",
        "already_in_chat": "You are already in a chat. Use the buttons below.",
        "already_in_queue": "🔎 You are already in the queue, please wait...",
        "finding_partner": "Hang tight! Finding someone cool for you to talk to... ⏳",
        "partner_found_with_profile": (
            "🎉 *It's a Match!* 🎉\n\n"
            "You've been connected with a new chat partner. Here's a little about them:\n\n"
            "👤 **Their Profile:**\n"
            "🎂 **Age:** {age}\n"
            "🎭 **Gender:** {gender}\n\n"
            "You can start chatting now. Have fun! 🚀"
        ),
        "left_chat": "⛔ You have left the chat.",
        "partner_left": "⚠️ Your partner has left the chat. Use /start to find a new one.",
        "left_queue": "✅ You have left the queue.",
        "not_in_chat": "❌ You are not in a chat.",
        "report_this_user": "Report This User",
        "yes_report": "Yes, Report",
        "cancel": "Cancel",
        "report_confirm": "You are about to report your chat partner (ID: *{anonymous_id}*). This will end the chat and send a transcript to the admin for review. Are you sure you want to continue?",
        "report_processed": "Processing report...",
        "report_submitted": "Thank you for helping keep our community safe! Your report (ID: {report_id}) has been submitted. 🙏",
        "report_cancelled": "Report cancelled. You are still in the chat.",
        "banned_message": "❌ Your account has been banned and you can no longer use this bot.",
        "error_saving_profile": "Something went wrong while saving your profile. Please try again later.",
        "reset_confirm": "Are you sure you want to reset your profile? All your data (age, gender, language) will be deleted and you will have to set it up again.",
        "reset_success": "✨ All clean! Your profile has been reset. Press /start to set up a new one.",
        "reset_cancelled": "Profile reset cancelled.",
        "yes_button": "Yes",
        "no_button": "No",
        "unsupported_message": "Sorry, this message type cannot be forwarded.",
        "error_finding_partner": "An error occurred while finding a partner. Please try again.",
        "error_sending_message": "Could not deliver your message. Your partner may have blocked the bot. The chat has been ended.",
        "myprofile_title": "👤 **Your Profile**",
        "myprofile_details": "🎂 **Age:** {age}\n🎭 **Gender:** {gender}\n🏙️ **City:** {city}",
        "myprofile_not_set": "You haven't set up your profile yet! Use /start to begin.",
        "unban_usage": "Usage: /unban <user_id>",
        "unban_success": "✅ User {user_id} has been successfully unbanned.",
        "unban_not_banned": "ℹ️ User {user_id} was not found in the ban list.",
        "unbanned_notification": "🎉 Good news! You have been unbanned by an admin and can now use the bot again.",
        "broadcast_header": "📢 **BOT INFO** 📢\n---------------------------------",
        "broadcast_footer": "---------------------------------\n*You are receiving this message because you are a user of this bot.*",
        "admin_forced_connection": "An admin has connected you with a new chat partner.",
    },
    'id': {
        "select_language": "Silakan pilih bahasa Anda. / Please select your language.",
        "ask_age": "Pertama, mari kita atur profil Anda. Berapa umur Anda?",
        "invalid_age": "Mohon masukkan umur yang valid (antara 13 dan 99).",
        "ask_gender": "Bagus! Sekarang, silakan pilih jenis kelamin Anda.",
        "invalid_gender": "Mohon pilih opsi yang valid dari keyboard.",
        "ask_city": "Terakhir, silakan masukkan kota asal Anda (contoh: Jakarta, Surabaya).\n\n*Informasi ini hanya untuk keperluan data demografi dan TIDAK akan ditampilkan ke pengguna lain.*",
        "profile_complete": "Profil Anda sudah siap! Mari mulai bersenang-senang! 🎉",
        "cancel_setup": "Pembuatan profil dibatalkan. Anda bisa mulai lagi dengan /start.",
        "main_menu": (
            "👋✨ *Bosen? Cari teman networking baru? Butuh teman ngobrol?* lmao, ini tempat yang pas! 🥳\n\n"
            "👇 Tekan tombol di bawah untuk mencari teman ngobrol!"
        ),
        "start_chat_button": "💬 Mulai Chat",
        "already_in_chat": "Anda sudah berada di dalam obrolan. Gunakan tombol di bawah.",
        "already_in_queue": "🔎 Anda sudah dalam antrian, mohon tunggu...",
        "finding_partner": "Tunggu sebentar! Mencari seseorang yang keren untukmu... ⏳",
        "partner_found_with_profile": (
            "🎉 *Ketemu Partner Ngobrol!* 🎉\n\n"
            "Anda telah terhubung dengan partner chat baru. Ini sedikit tentang mereka:\n\n"
            "👤 **Profil Partner:**\n"
            "🎂 **Umur:** {age}\n"
            "🎭 **Gender:** {gender}\n\n"
            "Anda bisa mulai mengobrol sekarang. Selamat bersenang-senang! 🚀"
        ),
        "left_chat": "⛔ Anda telah meninggalkan obrolan.",
        "partner_left": "⚠️ Partner Anda telah meninggalkan obrolan. Gunakan /start untuk mencari yang baru.",
        "left_queue": "✅ Anda telah keluar dari antrian.",
        "not_in_chat": "❌ Anda tidak sedang dalam obrolan.",
        "report_this_user": "Laporkan Pengguna Ini",
        "yes_report": "Ya, Laporkan",
        "cancel": "Batal",
        "report_confirm": "Anda akan melaporkan partner chat Anda (ID: *{anonymous_id}*). Tindakan ini akan mengakhiri obrolan dan mengirimkan transkrip ke admin untuk ditinjau. Yakin ingin melanjutkan?",
        "report_processed": "Memproses laporan...",
        "report_submitted": "Terima kasih telah membantu menjaga komunitas kita tetap aman! Laporan Anda (ID: {report_id}) telah dikirim. 🙏",
        "report_cancelled": "Laporan dibatalkan. Anda masih di dalam obrolan.",
        "banned_message": "❌ Akun Anda telah diblokir dan tidak dapat lagi menggunakan bot ini.",
        "error_saving_profile": "Terjadi kesalahan saat menyimpan profil Anda. Silakan coba lagi nanti.",
        "reset_confirm": "Apakah Anda yakin ingin mereset profil Anda? Semua data Anda (umur, jenis kelamin, bahasa) akan dihapus dan Anda harus mengaturnya kembali.",
        "reset_success": "✨ Beres! Profil Anda telah direset. Tekan /start untuk membuat yang baru.",
        "reset_cancelled": "Reset profil dibatalkan.",
        "yes_button": "Ya",
        "no_button": "Tidak",
        "unsupported_message": "Maaf, tipe pesan ini belum bisa diteruskan.",
        "error_finding_partner": "Terjadi kesalahan saat mencari partner. Silakan coba lagi.",
        "error_sending_message": "Gagal mengirim pesan Anda. Partner mungkin telah memblokir bot. Obrolan telah diakhiri.",
        "myprofile_title": "👤 **Profil Anda**",
        "myprofile_details": "🎂 **Umur:** {age}\n🎭 **Jenis Kelamin:** {gender}\n🏙️ **Kota:** {city}",
        "myprofile_not_set": "Anda belum mengatur profil! Gunakan /start untuk memulai.",
        "unban_usage": "Penggunaan: /unban <user_id>",
        "unban_success": "✅ Pengguna {user_id} telah berhasil di-unban.",
        "unban_not_banned": "ℹ️ Pengguna {user_id} tidak ditemukan di daftar blokir.",
        "unbanned_notification": "🎉 Kabar baik! Blokir Anda telah dicabut oleh admin dan Anda dapat menggunakan bot ini lagi.",
        "broadcast_header": "📢 **BOT INFO** �\n---------------------------------",
        "broadcast_footer": "---------------------------------\n*Anda menerima pesan ini karena Anda adalah pengguna bot kami.*",
        "admin_forced_connection": "Admin telah menghubungkan Anda dengan partner chat baru.",
    }
}


def get_text(key: str, lang: str, **kwargs) -> str:
    """Fetches and formats text from the language dictionary."""
    if not lang:
        lang = 'en'  # Default to English if language is not set
    return LANGUAGES.get(lang, LANGUAGES['en']).get(key, f"<{key}_not_found>").format(**kwargs)


# --- Database Management (Refactored) ---
def db_query(query: str, params: tuple = (), fetchone: bool = False, commit: bool = False):
    """A centralized function to handle database operations."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
            if cursor.lastrowid:
                return cursor.lastrowid
            return None
        return cursor.fetchone() if fetchone else cursor.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}\nQuery: {query}\nParams: {params}")
        return None
    finally:
        if conn:
            conn.close()


def setup_database():
    """Sets up the initial database schema."""
    logger.info("Setting up database...")
    db_query("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            join_date TEXT, chat_count INTEGER DEFAULT 0, age INTEGER,
            gender TEXT, language TEXT, city TEXT
        )
    """)
    db_query("""
        CREATE TABLE IF NOT EXISTS reports (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT, reporter_id INTEGER,
            reported_id INTEGER, timestamp TEXT, chat_log TEXT
        )
    """)
    db_query("""
        CREATE TABLE IF NOT EXISTS banned_users (
            chat_id INTEGER PRIMARY KEY, reason TEXT,
            banned_by INTEGER, timestamp TEXT
        )
    """)
    # Migration for older schemas
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'city' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN city TEXT")
            conn.commit()
            logger.info("Database migrated: Added 'city' column.")
    except sqlite3.Error as e:
        logger.error(f"Failed to migrate database: {e}")
    finally:
        if conn:
            conn.close()
    logger.info(f"Database '{DB_NAME}' is ready.")


def add_user_to_db(chat_id: int, username: str, first_name: str):
    """Adds a new user or updates an existing one in the database."""
    join_date = datetime.now().strftime("%d %b %Y, %H:%M")
    if not db_query("SELECT 1 FROM users WHERE chat_id = ?", (chat_id,), fetchone=True):
        db_query(
            "INSERT INTO users (chat_id, username, first_name, join_date) VALUES (?, ?, ?, ?)",
            (chat_id, username, first_name, join_date), commit=True
        )
    else:
        db_query(
            "UPDATE users SET username = ?, first_name = ? WHERE chat_id = ?",
            (username, first_name, chat_id), commit=True
        )


def get_user_data(user_id: int) -> tuple:
    """Fetches a user's profile (age, gender, language) from the database."""
    result = db_query("SELECT age, gender, language FROM users WHERE chat_id = ?", (user_id,), fetchone=True)
    return result if result else (None, None, None)


def is_user_banned(chat_id: int) -> bool:
    """Checks if a user is in the banned list."""
    return db_query("SELECT 1 FROM banned_users WHERE chat_id = ?", (chat_id,), fetchone=True) is not None


# --- Helper Functions & Keyboards ---
def get_chat_controls(lang: str):
    keyboard = [
        [
            InlineKeyboardButton("⏭️ Next", callback_data="next"),
            InlineKeyboardButton("⛔ Stop", callback_data="stop"),
        ],
        [InlineKeyboardButton(f"🚩 {get_text('report_this_user', lang)}", callback_data="report")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_start_keyboard(lang: str):
    keyboard = [[InlineKeyboardButton(f"{get_text('start_chat_button', lang)}", callback_data="start_chat")]]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_report_keyboard(lang: str):
    keyboard = [
        [InlineKeyboardButton(f"✅ {get_text('yes_report', lang)}", callback_data="confirm_report")],
        [InlineKeyboardButton(f"❌ {get_text('cancel', lang)}", callback_data="cancel_report")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_anonymous_id(user_id: int) -> str:
    """Creates a non-reversible anonymous ID for display."""
    return f"USER-{str(user_id)[-5:]}"


# --- Language and Profile Setup (ConversationHandler) ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the /start command, checking user status and directing them."""
    user = update.effective_user
    if is_user_banned(user.id):
        _, _, lang = get_user_data(user.id)
        await update.message.reply_text(get_text('banned_message', lang or 'en'))
        return ConversationHandler.END

    add_user_to_db(user.id, user.username, user.first_name)
    age, gender, lang = get_user_data(user.id)

    # If profile is complete, show main menu
    if lang and age and gender:
        if user.id in context.bot_data.get('active_chats', {}):
            await update.message.reply_text(get_text('already_in_chat', lang), reply_markup=get_chat_controls(lang))
        elif user.id in context.bot_data.get('waiting_users', set()):
            await update.message.reply_text(get_text('already_in_queue', lang))
        else:
            await show_main_menu(update, context, lang)
        return ConversationHandler.END

    # If profile is incomplete, start setup
    keyboard = [
        [InlineKeyboardButton("English 🇬🇧", callback_data="en")],
        [InlineKeyboardButton("Indonesia 🇮🇩", callback_data="id")]
    ]
    await update.message.reply_text(
        get_text('select_language', 'en'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_LANG


async def select_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    lang = query.data
    user_id = query.from_user.id
    await query.answer()

    db_query("UPDATE users SET language = ? WHERE chat_id = ?", (lang, user_id), commit=True)
    context.user_data['lang'] = lang
    await query.edit_message_text(text=get_text('ask_age', lang))
    return GET_AGE


async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get('lang')
    try:
        user_age = int(update.message.text)
        if not 13 <= user_age <= 99:
            await update.message.reply_text(get_text('invalid_age', lang))
            return GET_AGE
    except (ValueError, TypeError):
        await update.message.reply_text(get_text('invalid_age', lang))
        return GET_AGE

    context.user_data['age'] = user_age
    gender_keyboard = [["Male", "Female"], ["Other", "Prefer not to say"]]
    await update.message.reply_text(
        get_text('ask_gender', lang),
        reply_markup=ReplyKeyboardMarkup(gender_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return GET_GENDER


async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get('lang')
    context.user_data['gender'] = update.message.text
    await update.message.reply_text(
        get_text('ask_city', lang),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return GET_CITY


async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    lang = context.user_data.get('lang')
    user_city = update.message.text
    user_age = context.user_data['age']
    user_gender = context.user_data['gender']

    db_query(
        "UPDATE users SET age = ?, gender = ?, city = ? WHERE chat_id = ?",
        (user_age, user_gender, user_city, user_id),
        commit=True
    )

    await update.message.reply_text(get_text('profile_complete', lang))
    await show_main_menu(update, context, lang)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _, _, lang = get_user_data(update.effective_user.id)
    await update.message.reply_text(
        get_text('cancel_setup', lang or 'en'),
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str):
    """Displays the main menu with the start chat button."""
    welcome_message = get_text('main_menu', lang)
    chat_id = update.effective_chat.id
    # If called from a query, the original message might be deleted. Send a new one.
    if update.callback_query:
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_message,
            parse_mode="Markdown",
            reply_markup=get_start_keyboard(lang)
        )
    else:  # If called from a message (e.g. after profile setup)
        await update.message.reply_text(
            text=welcome_message,
            parse_mode="Markdown",
            reply_markup=get_start_keyboard(lang)
        )


# --- Core Chat Logic ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles main menu buttons like start, next, and stop."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    # It's good practice to delete the menu to avoid clutter
    try:
        await query.delete_message()
    except BadRequest:
        logger.warning(f"Could not delete menu message for {user_id}")

    if query.data == "start_chat":
        await find_partner(user_id, context)
    elif query.data == "next":
        await end_chat(user_id, context)
        await find_partner(user_id, context)
    elif query.data == "stop":
        await end_chat(user_id, context)


async def find_partner(user_id, context: ContextTypes.DEFAULT_TYPE):
    """Matches a user with a partner from the waiting queue or adds them to it."""
    _, _, lang = get_user_data(user_id)
    active_chats = context.bot_data['active_chats']
    waiting_users = context.bot_data['waiting_users']

    if user_id in active_chats:
        await context.bot.send_message(chat_id=user_id, text=get_text('already_in_chat', lang),
                                       reply_markup=get_chat_controls(lang))
        return
    if user_id in waiting_users:
        await context.bot.send_message(chat_id=user_id, text=get_text('already_in_queue', lang))
        return

    await context.bot.send_message(chat_id=user_id, text=get_text('finding_partner', lang))
    waiting_users.add(user_id)

    if len(waiting_users) >= 2:
        user1_id, user2_id = None, None
        try:
            user1_id = waiting_users.pop()
            user2_id = waiting_users.pop()

            user1_age, user1_gender, user1_lang = get_user_data(user1_id)
            user2_age, user2_gender, user2_lang = get_user_data(user2_id)

            active_chats[user1_id] = user2_id
            active_chats[user2_id] = user1_id

            # *** FIX ***: Initialize chat logs by modifying the inner dictionary.
            context.application.user_data[user1_id]['log'] = []
            context.application.user_data[user2_id]['log'] = []

            msg1 = get_text('partner_found_with_profile', user1_lang, age=user2_age, gender=user2_gender)
            msg2 = get_text('partner_found_with_profile', user2_lang, age=user1_age, gender=user1_gender)

            await context.bot.send_message(user1_id, msg1, parse_mode="Markdown",
                                           reply_markup=get_chat_controls(user1_lang))
            await context.bot.send_message(user2_id, msg2, parse_mode="Markdown",
                                           reply_markup=get_chat_controls(user2_lang))

            db_query("UPDATE users SET chat_count = chat_count + 1 WHERE chat_id IN (?, ?)", (user1_id, user2_id),
                     commit=True)
            logger.info(f"Partner found: {user1_id} <-> {user2_id}")

        except (Forbidden, BadRequest) as e:
            failed_id = user1_id if user1_id and e.message and str(user1_id) in e.message else user2_id
            other_id = user2_id if failed_id == user1_id else user1_id
            logger.warning(f"Failed to connect chat. User {failed_id} may have blocked bot. Re-queuing {other_id}.")
            if user1_id: active_chats.pop(user1_id, None)
            if user2_id: active_chats.pop(user2_id, None)
            if other_id: waiting_users.add(other_id)
        except Exception as e:
            logger.error(f"Unexpected error in find_partner: {e}")
            for uid in [user1_id, user2_id]:
                if uid:
                    _, _, u_lang = get_user_data(uid)
                    active_chats.pop(uid, None)
                    waiting_users.discard(uid)
                    await context.bot.send_message(uid, get_text('error_finding_partner', u_lang or 'en'))


async def end_chat(user_id, context: ContextTypes.DEFAULT_TYPE, is_report: bool = False):
    """Ends a chat for a user and their partner."""
    _, _, lang = get_user_data(user_id)
    active_chats = context.bot_data['active_chats']

    partner_id = active_chats.pop(user_id, None)
    if partner_id:
        _, _, partner_lang = get_user_data(partner_id)
        active_chats.pop(partner_id, None)

        # *** FIX ***: Clear the inner user_data dictionary instead of trying to pop from the proxy.
        if not is_report:
            if user_id in context.application.user_data:
                context.application.user_data[user_id].clear()
            if partner_id in context.application.user_data:
                context.application.user_data[partner_id].clear()

        try:
            await context.bot.send_message(user_id, get_text('left_chat', lang), reply_markup=get_start_keyboard(lang))
        except (Forbidden, BadRequest):
            logger.warning(f"Could not send 'left_chat' to {user_id}. Bot blocked?")

        try:
            await context.bot.send_message(partner_id, get_text('partner_left', partner_lang),
                                           reply_markup=get_start_keyboard(partner_lang))
        except (Forbidden, BadRequest):
            logger.warning(f"Could not notify partner {partner_id} of chat end. Bot blocked?")

        logger.info(f"Chat ended between {user_id} and {partner_id}")

    elif user_id in context.bot_data['waiting_users']:
        context.bot_data['waiting_users'].remove(user_id)
        await context.bot.send_message(user_id, get_text('left_queue', lang), reply_markup=get_start_keyboard(lang))
    else:
        if not is_report:
            # Avoid sending "not in chat" during forced reconnects or other edge cases
            pass


async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forwards messages (text, photo, sticker, etc.) between chat partners."""
    user_id = update.effective_user.id
    _, _, lang = get_user_data(user_id)
    partner_id = context.bot_data['active_chats'].get(user_id)

    if not partner_id:
        await show_main_menu(update, context, lang or 'en')
        return

    message = update.message
    log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] User {user_id}: "

    try:
        if message.text:
            log_entry += message.text
            await context.bot.send_message(chat_id=partner_id, text=message.text)
        elif message.photo:
            log_entry += "[Photo]"
            await context.bot.send_photo(chat_id=partner_id, photo=message.photo[-1].file_id, caption=message.caption)
        elif message.sticker:
            log_entry += "[Sticker]"
            await context.bot.send_sticker(chat_id=partner_id, sticker=message.sticker.file_id)
        elif message.voice:
            log_entry += "[Voice Message]"
            await context.bot.send_voice(chat_id=partner_id, voice=message.voice.file_id)
        elif message.video:
            log_entry += "[Video]"
            await context.bot.send_video(chat_id=partner_id, video=message.video.file_id, caption=message.caption)
        else:
            await message.reply_text(get_text('unsupported_message', lang))
            return

        # Append logs for both users. This relies on the log being initialized in find_partner.
        if user_id in context.application.user_data:
            context.application.user_data[user_id].setdefault('log', []).append(log_entry)
        if partner_id in context.application.user_data:
            context.application.user_data[partner_id].setdefault('log', []).append(log_entry)

    except (Forbidden, BadRequest):
        logger.warning(f"Failed to forward message to {partner_id}. Ending chat.")
        await message.reply_text(get_text('error_sending_message', lang))
        await end_chat(user_id, context)


# --- Reporting Flow (ConversationHandler) ---
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the report process. Entry point for the report ConversationHandler."""
    query = update.callback_query
    reporter_id = query.from_user.id
    _, _, lang = get_user_data(reporter_id)
    active_chats = context.bot_data['active_chats']

    if reporter_id not in active_chats:
        await query.answer(get_text('not_in_chat', lang), show_alert=True)
        return ConversationHandler.END

    await query.answer()
    partner_id = active_chats.get(reporter_id)
    context.user_data['partner_to_report'] = partner_id

    anonymous_id = get_anonymous_id(partner_id)
    confirmation_text = get_text('report_confirm', lang, anonymous_id=anonymous_id)

    await query.edit_message_text(
        text=confirmation_text,
        parse_mode="Markdown",
        reply_markup=get_confirm_report_keyboard(lang)
    )
    return CONFIRM_REPORT


async def confirm_report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the final confirmation of the report."""
    query = update.callback_query
    reporter_id = query.from_user.id
    _, _, lang = get_user_data(reporter_id)
    reported_id = context.user_data.get('partner_to_report')

    if not reported_id:
        logger.warning(f"confirm_report_callback triggered for {reporter_id} but no partner_to_report in user_data.")
        await query.edit_message_text("Error: Could not find partner to report. The chat may have already ended.")
        return ConversationHandler.END

    await query.answer(get_text('report_processed', lang))

    # Fetch log from application.user_data
    chat_log_list = context.application.user_data.get(reporter_id, {}).get('log', ["No chat log available."])
    chat_log_text = "\n".join(chat_log_list)

    report_id = db_query(
        "INSERT INTO reports (reporter_id, reported_id, timestamp, chat_log) VALUES (?, ?, ?, ?)",
        (reporter_id, reported_id, datetime.now().isoformat(), chat_log_text),
        commit=True
    )

    await query.edit_message_text(get_text('report_submitted', lang, report_id=report_id))

    admin_message = (
        f"🚨 *Laporan Baru Diterima!*\n\n"
        f"*ID Laporan:* `{report_id}`\n"
        f"*Pelapor:* `{reporter_id}` (tg://user?id={reporter_id})\n"
        f"*Terlapor:* `{reported_id}` (tg://user?id={reported_id})\n\n"
        f"*Cuplikan Chat:*\n"
        f"```\n{chat_log_text}\n```\n\n"
        f"Gunakan: `/ban {reported_id} Melanggar aturan di laporan #{report_id}`"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=admin_message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send report notification to admin {admin_id}: {e}")

    await end_chat(reporter_id, context, is_report=True)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the report process and restores the chat controls."""
    query = update.callback_query
    _, _, lang = get_user_data(query.from_user.id)
    await query.answer()
    await query.edit_message_text(get_text('report_cancelled', lang))
    await query.message.reply_text("You are back in the chat.", reply_markup=get_chat_controls(lang))
    context.user_data.pop('partner_to_report', None)
    return ConversationHandler.END


# --- User Commands ---
async def myprofile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user's current profile information."""
    user_id = update.effective_user.id
    user_data = db_query("SELECT age, gender, city, language FROM users WHERE chat_id = ?", (user_id,), fetchone=True)

    if user_data and all(user_data[:3]):
        age, gender, city, lang = user_data
        title = get_text('myprofile_title', lang)
        details = get_text('myprofile_details', lang, age=age, gender=gender, city=city)
        await update.message.reply_text(f"{title}\n\n{details}", parse_mode="Markdown")
    else:
        lang = user_data[3] if user_data else 'en'
        await update.message.reply_text(get_text('myprofile_not_set', lang))


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await end_chat(update.effective_user.id, context)


async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await end_chat(user_id, context)
    await find_partner(user_id, context)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks for confirmation to reset a user's profile."""
    _, _, lang = get_user_data(update.effective_user.id)
    keyboard = [
        [
            InlineKeyboardButton(f"✅ {get_text('yes_button', lang or 'en')}", callback_data="confirm_reset"),
            InlineKeyboardButton(f"❌ {get_text('no_button', lang or 'en')}", callback_data="cancel_reset"),
        ]
    ]
    await update.message.reply_text(get_text('reset_confirm', lang or 'en'),
                                    reply_markup=InlineKeyboardMarkup(keyboard))


async def confirmation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles generic confirmation callbacks like for resetting the profile."""
    query = update.callback_query
    user_id = query.from_user.id
    _, _, lang = get_user_data(user_id)
    await query.answer()

    if query.data == "confirm_reset":
        if user_id in context.bot_data['active_chats'] or user_id in context.bot_data['waiting_users']:
            await end_chat(user_id, context)
        db_query(
            "UPDATE users SET language = NULL, age = NULL, gender = NULL, city = NULL WHERE chat_id = ?",
            (user_id,), commit=True
        )
        await query.edit_message_text(get_text('reset_success', lang or 'en'))
    elif query.data == "cancel_reset":
        await query.edit_message_text(get_text('reset_cancelled', lang or 'en'))


# --- Admin Commands ---
async def get_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a detailed list of all users to the admin, including their real-time status."""
    if update.effective_user.id not in ADMIN_IDS: return

    # Fetch bot's live data
    active_chats = context.bot_data.get('active_chats', {})
    waiting_users = context.bot_data.get('waiting_users', set())

    # Fetch all users from the database
    all_users_data = db_query("""
        SELECT u.chat_id, u.username, u.first_name, u.join_date, u.chat_count,
               u.age, u.gender, u.city, b.chat_id IS NOT NULL AS is_banned
        FROM users u LEFT JOIN banned_users b ON u.chat_id = b.chat_id
        ORDER BY u.join_date DESC
    """)
    if not all_users_data:
        await update.message.reply_text("No users found in the database.")
        return

    await update.message.reply_text("📊 **Bot User Report**\n\nGenerating list... this may take a moment.")

    user_batch = []
    batch_size = 5  # Number of users per message

    for data in all_users_data:
        chat_id, username, first_name, join_date, chat_count, age, gender, city, is_banned = data

        # Determine real-time activity status
        if chat_id in active_chats:
            activity_status = f"🟢 In Chat with `{active_chats[chat_id]}`"
        elif chat_id in waiting_users:
            activity_status = "⏳ Waiting"
        else:
            activity_status = "⚪ Idle"

        # Determine ban status
        ban_status = "Banned" if is_banned else "Active"

        # Format profile and user entry
        profile_info = f"{age or 'N/A'}, {gender or 'N/A'}, {city or 'N/A'}"

        # *** FIX ***: Sanitize the first_name to escape any special Markdown characters
        safe_first_name = (first_name or 'User').replace('_', '\\_').replace('*', '\\*').replace('`', '\\`').replace(
            '[', '\\[')

        user_entry = (
            f"👤 **{safe_first_name}** ([Contact](tg://user?id={chat_id}))\n"
            f"   - **ID:** `{chat_id}`\n"
            f"   - **Username:** @{username if username else 'N/A'}\n"
            f"   - **Joined:** {join_date or 'N/A'}\n"
            f"   - **Matches:** {chat_count or 0}\n"
            f"   - **Activity:** {activity_status}\n"
            f"   - **Ban Status:** {ban_status}\n"
            f"   - **Profile:** {profile_info}\n"
            f"--------------------\n"
        )
        user_batch.append(user_entry)

        # When the batch is full, send it as one message
        if len(user_batch) >= batch_size:
            message_to_send = "".join(user_batch)
            try:
                await update.message.reply_text(message_to_send, parse_mode="Markdown", disable_web_page_preview=True)
            except BadRequest as e:
                logger.error(f"Error sending user list batch: {e}")
                await update.message.reply_text(f"A batch failed to send. Error: {e}")
            user_batch = []  # Reset for the next batch
            await asyncio.sleep(0.8)

    # Send any remaining users in the last batch
    if user_batch:
        message_to_send = "".join(user_batch)
        try:
            await update.message.reply_text(message_to_send, parse_mode="Markdown", disable_web_page_preview=True)
        except BadRequest as e:
            logger.error(f"Error sending final user list batch: {e}")
            await update.message.reply_text(f"The final batch failed to send. Error: {e}")


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /ban <user_id> [reason]")
        return
    try:
        user_to_ban_id = int(args[0])
        reason = " ".join(args[1:]) if len(args) > 1 else "No reason specified."
    except ValueError:
        await update.message.reply_text("User ID must be a number.")
        return

    db_query(
        "INSERT OR REPLACE INTO banned_users (chat_id, reason, banned_by, timestamp) VALUES (?, ?, ?, ?)",
        (user_to_ban_id, reason, update.effective_user.id, datetime.now().isoformat()),
        commit=True
    )
    await update.message.reply_text(f"✅ User {user_to_ban_id} has been successfully banned.")
    try:
        await context.bot.send_message(
            chat_id=user_to_ban_id,
            text=f"❌ You have been banned by an admin.\n\n*Reason:* {reason}",
            parse_mode="Markdown"
        )
    except (Forbidden, BadRequest):
        logger.warning(f"Could not send ban notification to {user_to_ban_id}.")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unbans a user, allowing them to use the bot again."""
    if update.effective_user.id not in ADMIN_IDS: return

    _, _, admin_lang = get_user_data(update.effective_user.id)
    admin_lang = admin_lang or 'en'

    args = context.args
    if not args:
        await update.message.reply_text(get_text('unban_usage', admin_lang))
        return
    try:
        user_to_unban_id = int(args[0])
    except ValueError:
        await update.message.reply_text("User ID must be a number.")
        return

    if not is_user_banned(user_to_unban_id):
        await update.message.reply_text(get_text('unban_not_banned', admin_lang, user_id=user_to_unban_id))
        return

    db_query("DELETE FROM banned_users WHERE chat_id = ?", (user_to_unban_id,), commit=True)
    await update.message.reply_text(get_text('unban_success', admin_lang, user_id=user_to_unban_id))

    try:
        notification_text = get_text('unbanned_notification', 'en') + "\n\n" + get_text('unbanned_notification', 'id')
        await context.bot.send_message(chat_id=user_to_unban_id, text=notification_text)
    except (Forbidden, BadRequest):
        logger.warning(f"Could not send unban notification to {user_to_unban_id}.")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a formatted broadcast message to all non-banned users."""
    if update.effective_user.id not in ADMIN_IDS: return

    message_to_send = " ".join(context.args)
    if not message_to_send:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    all_users = db_query("SELECT chat_id, language FROM users")
    if not all_users:
        await update.message.reply_text("No users to broadcast to.")
        return

    await update.message.reply_text(f"Starting formatted broadcast to {len(all_users)} users...")
    sent, failed, skipped = 0, 0, 0

    for user_id, lang in all_users:
        if is_user_banned(user_id):
            skipped += 1
            continue

        user_lang = lang or 'en'
        header = get_text('broadcast_header', user_lang)
        footer = get_text('broadcast_footer', user_lang)
        formatted_message = f"{header}\n\n{message_to_send}\n\n{footer}"

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=formatted_message,
                parse_mode="Markdown"
            )
            sent += 1
        except (Forbidden, BadRequest):
            failed += 1
            logger.warning(f"Broadcast failed for user {user_id}. They may have blocked the bot.")
        except Exception as e:
            logger.error(f"Broadcast error to {user_id}: {e}")
            failed += 1

        await asyncio.sleep(0.1)

    summary = f"✅ *Broadcast Complete*\n\nSent: {sent}\nFailed: {failed}\nSkipped (Banned): {skipped}"
    await update.message.reply_text(summary, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return

    total_users = db_query("SELECT COUNT(chat_id) FROM users", fetchone=True)[0]
    active_user_count = len(context.bot_data['active_chats'])
    waiting_user_count = len(context.bot_data['waiting_users'])

    stats_msg = (
        f"📊 *Current Bot Stats*\n\n"
        f"👥 Total Users: {total_users}\n"
        f"💬 Users in Active Chats: {active_user_count}\n"
        f"⏳ Users in Queue: {waiting_user_count}"
    )
    await update.message.reply_text(stats_msg, parse_mode="Markdown")


async def forcereconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forcibly connects two users, ending any of their current chats."""
    if update.effective_user.id not in ADMIN_IDS:
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Usage: /forcereconnect <user1_id> <user2_id>")
        return

    try:
        user1_id = int(args[0])
        user2_id = int(args[1])
    except ValueError:
        await update.message.reply_text("Both user IDs must be numbers.")
        return

    if user1_id == user2_id:
        await update.message.reply_text("Users cannot be connected to themselves.")
        return

    # Check if users exist and are not banned
    user1_db_data = db_query("SELECT chat_id FROM users WHERE chat_id = ?", (user1_id,), fetchone=True)
    user2_db_data = db_query("SELECT chat_id FROM users WHERE chat_id = ?", (user2_id,), fetchone=True)

    if not user1_db_data:
        await update.message.reply_text(f"User {user1_id} not found in the database.")
        return
    if not user2_db_data:
        await update.message.reply_text(f"User {user2_id} not found in the database.")
        return

    if is_user_banned(user1_id):
        await update.message.reply_text(f"User {user1_id} is banned and cannot be connected.")
        return
    if is_user_banned(user2_id):
        await update.message.reply_text(f"User {user2_id} is banned and cannot be connected.")
        return

    await update.message.reply_text(f"Attempting to force connect {user1_id} and {user2_id}...")

    # End any existing sessions for both users
    await end_chat(user1_id, context)
    await end_chat(user2_id, context)

    # Wait a moment to ensure state is cleared
    await asyncio.sleep(1)

    # Now, connect them
    active_chats = context.bot_data['active_chats']

    user1_age, user1_gender, user1_lang = get_user_data(user1_id)
    user2_age, user2_gender, user2_lang = get_user_data(user2_id)

    active_chats[user1_id] = user2_id
    active_chats[user2_id] = user1_id

    # *** FIX ***: Initialize chat logs by modifying the inner dictionary.
    context.application.user_data[user1_id]['log'] = []
    context.application.user_data[user2_id]['log'] = []

    # Log the forced connection
    log_entry = f"[{datetime.now().strftime('%H:%M:%S')}] Admin forced connection between {user1_id} and {user2_id}"
    context.application.user_data[user1_id]['log'].append(log_entry)
    context.application.user_data[user2_id]['log'].append(log_entry)

    try:
        # Notify user 1
        admin_msg1 = get_text('admin_forced_connection', user1_lang or 'en')
        profile_msg1 = get_text('partner_found_with_profile', user1_lang or 'en', age=user2_age, gender=user2_gender)
        await context.bot.send_message(user1_id, f"*{admin_msg1}*\n\n{profile_msg1}", parse_mode="Markdown",
                                       reply_markup=get_chat_controls(user1_lang or 'en'))

        # Notify user 2
        admin_msg2 = get_text('admin_forced_connection', user2_lang or 'en')
        profile_msg2 = get_text('partner_found_with_profile', user2_lang or 'en', age=user1_age, gender=user1_gender)
        await context.bot.send_message(user2_id, f"*{admin_msg2}*\n\n{profile_msg2}", parse_mode="Markdown",
                                       reply_markup=get_chat_controls(user2_lang or 'en'))

        db_query("UPDATE users SET chat_count = chat_count + 1 WHERE chat_id IN (?, ?)", (user1_id, user2_id),
                 commit=True)

        logger.info(f"Admin forced connection: {user1_id} <-> {user2_id}")
        await update.message.reply_text(f"✅ Successfully connected {user1_id} and {user2_id}.")

    except (Forbidden, BadRequest) as e:
        await update.message.reply_text(f"❌ Failed to connect users. One may have blocked the bot. Error: {e}")
        # Clean up the failed connection
        active_chats.pop(user1_id, None)
        active_chats.pop(user2_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ An unexpected error occurred: {e}")
        logger.error(f"Error in forcereconnect_command: {e}")
        active_chats.pop(user1_id, None)
        active_chats.pop(user2_id, None)


# --- Bot Setup and Initialization ---
async def post_init(application: Application):
    """Initializes bot data and sets commands after the bot starts."""
    application.bot_data['waiting_users'] = set()
    application.bot_data['active_chats'] = {}

    user_commands = [
        ("start", "Start the bot or create a profile"),
        ("myprofile", "View your current profile"),
        ("next", "Find a new chat partner"),
        ("stop", "End the current chat"),
        ("reset", "Reset your profile data"),
    ]
    await application.bot.set_my_commands(user_commands, scope=BotCommandScopeAllPrivateChats())

    admin_commands = user_commands + [
        ("getusers", "Get complete user list"),
        ("ban", "Ban a user by ID"),
        ("unban", "Unban a user by ID"),
        ("broadcast", "Send a message to all users"),
        ("stats", "View bot statistics"),
        ("forcereconnect", "Force two users into a chat"),
    ]
    for admin_id in ADMIN_IDS:
        try:
            await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except (Forbidden, BadRequest):
            logger.warning(f"Could not set commands for admin {admin_id}. Admin must start bot first.")


def main():
    """Main function to run the bot."""
    logger.info("Starting bot...")
    setup_database()

    application = Application.builder().token(TOKEN).post_init(post_init).build()

    setup_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            SELECT_LANG: [CallbackQueryHandler(select_language, pattern="^(en|id)$")],
            GET_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GET_GENDER: [MessageHandler(filters.Regex("^(Male|Female|Other|Prefer not to say)$"), get_gender)],
            GET_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
        },
        fallbacks=[CommandHandler("cancel", cancel_setup), CommandHandler("start", start_command)],
        per_user=True, per_chat=True,
    )

    report_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(report_command, pattern="^report$")],
        states={
            CONFIRM_REPORT: [
                CallbackQueryHandler(confirm_report_callback, pattern="^confirm_report$"),
                CallbackQueryHandler(cancel_report, pattern="^cancel_report$"),
            ],
        },
        fallbacks=[CommandHandler("start", start_command)],
        per_user=True, per_chat=True,
    )

    application.add_handler(setup_handler)
    application.add_handler(report_handler)

    application.add_handler(CommandHandler("myprofile", myprofile_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("next", next_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("getusers", get_users_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("forcereconnect", forcereconnect_command))

    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(start_chat|next|stop)$"))
    application.add_handler(CallbackQueryHandler(confirmation_handler, pattern="^(confirm_reset|cancel_reset)$"))


    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, forward_message))

       logger.info("Bot is running with webhook...")

    if not WEBHOOK_BASE:
        # Di Koyeb WAJIB webhook supaya app buka port, kalau tidak health check gagal.
        raise RuntimeError("WEBHOOK_BASE env var is required on Koyeb")

    # path webhook aman: pakai kiri token (bot id) saja
    url_path = f"/webhook/{TOKEN.split(':', 1)[0]}"
    webhook_url = f"{WEBHOOK_BASE}{url_path}"

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=url_path,
        webhook_url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":

    main()

