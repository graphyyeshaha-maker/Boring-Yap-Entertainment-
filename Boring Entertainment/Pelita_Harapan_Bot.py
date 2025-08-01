# -*- coding: utf-8 -*-

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
# --- PERBAIKAN: Impor BadRequest dari telegram.error ---
from telegram.error import BadRequest

TOKEN = '7483858287:AAGurzaLVWptHMHfVBpOqHA_luwLUkSuTwM'

# --- Konfigurasi Logging (Sangat disarankan untuk debugging) ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Manajemen Status (Menggunakan set untuk performa lebih baik) ---
waiting_users = set()  # Antrian user yang mencari partner
active_chats = {}  # Pasangan chat aktif: {user_id: partner_id}


# --- Helper & Keyboard ---

def get_chat_controls():
    """Mengembalikan keyboard kontrol saat sedang dalam percakapan."""
    keyboard = [
        [
            InlineKeyboardButton("⏭️ Next", callback_data="next"),
            InlineKeyboardButton("⛔ Stop", callback_data="stop"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_start_keyboard():
    """Mengembalikan keyboard untuk menu utama."""
    keyboard = [[InlineKeyboardButton("💬 Mulai Chat", callback_data="start_chat")]]
    return InlineKeyboardMarkup(keyboard)


# --- Handler Perintah & Tombol ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah /start."""
    user_id = update.effective_user.id
    # Beri pesan berbeda jika user sudah dalam chat atau antrian
    if user_id in active_chats:
        await update.message.reply_text("Kamu sudah terhubung. Gunakan tombol di bawah.",
                                        reply_markup=get_chat_controls())
    elif user_id in waiting_users:
        await update.message.reply_text("🔎 Kamu sudah dalam antrian, mohon tunggu...")
    else:
        await update.message.reply_text(
            "👋 *Welcome to Pelita Harapan Chat Bot!*\n\n"
            "Di sini kamu bisa ngobrol secara random dan anonim dengan sesama Pelajar dan Mahasiswa Pelita Harapan Group. "
            "Pastikan kamu bersikap baik dan sopan 🙏\n\n"
            "Tekan tombol di bawah untuk mulai mencari teman ngobrol!",
            parse_mode="Markdown",
            reply_markup=get_start_keyboard()
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani callback dari tombol 'Mulai Chat', 'Next', dan 'Stop'."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    # --- PERBAIKAN UTAMA ADA DI SINI ---
    # Gunakan query.delete_message() untuk menghapus pesan dengan tombol.
    try:
        await query.delete_message()
    except BadRequest as e:
        logger.warning(f"Could not delete message: {e}")

    if query.data == "start_chat":
        await find_partner(user_id, context)
    elif query.data == "next":
        await end_chat(user_id, context)  # Akhiri chat lama dulu
        await find_partner(user_id, context)  # Baru cari lagi
    elif query.data == "stop":
        await end_chat(user_id, context)


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah manual /stop."""
    await end_chat(update.effective_user.id, context)


async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah manual /next."""
    user_id = update.effective_user.id
    await end_chat(user_id, context)
    await find_partner(user_id, context)


# --- Logika Inti Bot ---

async def find_partner(user_id, context: ContextTypes.DEFAULT_TYPE):
    """Mencari pasangan untuk user."""
    if user_id in active_chats or user_id in waiting_users:
        await context.bot.send_message(chat_id=user_id, text="⚠️ Kamu sudah dalam sesi atau antrian!")
        return

    await context.bot.send_message(chat_id=user_id, text="🔎 Mencari partner, mohon tunggu...")

    # Coba cari partner dari antrian
    if waiting_users:
        partner_id = waiting_users.pop()  # Ambil satu user dari antrian
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        logger.info(f"Partner found: {user_id} <-> {partner_id}")

        await context.bot.send_message(chat_id=user_id, text="🎉 Partner ditemukan!", reply_markup=get_chat_controls())
        await context.bot.send_message(chat_id=partner_id, text="🎉 Partner ditemukan!",
                                       reply_markup=get_chat_controls())
    else:
        # Jika tidak ada, masukkan ke antrian
        waiting_users.add(user_id)
        logger.info(f"User {user_id} added to waiting queue.")


async def end_chat(user_id, context: ContextTypes.DEFAULT_TYPE):
    """Menghentikan sesi chat dan membersihkan status."""
    partner_id = active_chats.pop(user_id, None)
    if partner_id:
        active_chats.pop(partner_id, None)
        await context.bot.send_message(chat_id=user_id, text="⛔ Kamu telah meninggalkan chat.",
                                       reply_markup=get_start_keyboard())
        await context.bot.send_message(chat_id=partner_id, text="⚠️ Partner kamu telah meninggalkan chat.",
                                       reply_markup=get_start_keyboard())
        logger.info(f"Chat ended between {user_id} and {partner_id}")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await context.bot.send_message(chat_id=user_id, text="✅ Kamu telah keluar dari antrian.",
                                       reply_markup=get_start_keyboard())
    else:
        # Jika user menekan stop/next tanpa dalam chat/antrian
        await context.bot.send_message(chat_id=user_id, text="❌ Kamu tidak sedang dalam chat.",
                                       reply_markup=get_start_keyboard())


async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Menyalin dan mengirim pesan ke partner untuk menjaga anonimitas.
    Fungsi ini tidak lagi menggunakan `message.forward()`, melainkan memeriksa
    tipe pesan (teks, foto, stiker, dll.) lalu mengirim salinannya.
    """
    user_id = update.effective_user.id
    partner_id = active_chats.get(user_id)

    if partner_id:
        message = update.message
        # Cek tipe pesan dan kirim salinannya sebagai pesan baru dari bot
        if message.text:
            await context.bot.send_message(chat_id=partner_id, text=message.text)
        elif message.photo:
            await context.bot.send_photo(chat_id=partner_id, photo=message.photo[-1].file_id, caption=message.caption)
        elif message.sticker:
            await context.bot.send_sticker(chat_id=partner_id, sticker=message.sticker.file_id)
        elif message.video:
            await context.bot.send_video(chat_id=partner_id, video=message.video.file_id, caption=message.caption)
        elif message.voice:
            await context.bot.send_voice(chat_id=partner_id, voice=message.voice.file_id)
        elif message.document:
            await context.bot.send_document(chat_id=partner_id, document=message.document.file_id, caption=message.caption)
        elif message.audio:
            await context.bot.send_audio(chat_id=partner_id, audio=message.audio.file_id, caption=message.caption)
        else:
            await context.bot.send_message(chat_id=user_id, text="Maaf, tipe pesan ini belum bisa dikirim.")
    else:
        await update.message.reply_text("❗ Kamu belum dalam percakapan. Gunakan /start untuk mulai.", reply_markup=get_start_keyboard())


async def set_commands(application: Application):
    """Mengatur daftar perintah yang akan muncul di menu Telegram."""
    await application.bot.set_my_commands([
        ("start", "Mulai bot dan lihat menu"),
        ("next", "Cari partner baru"),
        ("stop", "Akhiri chat saat ini"),
    ])
    logger.info("Command menu has been set.")


# --- Fungsi Utama ---
def main():
    """Fungsi utama untuk menjalankan bot."""
    logger.info("Starting bot...")

    # Menggunakan Application.builder() yang merupakan cara modern
    application = Application.builder().token(TOKEN).build()

    # Menambahkan semua handler
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("next", next_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_message))

    # Mengatur menu perintah setelah bot siap
    application.post_init = set_commands

    logger.info("✅ Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
