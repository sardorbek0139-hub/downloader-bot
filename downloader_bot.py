import asyncio
import os
import re
import threading
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask
from yt_dlp import YoutubeDL
import imageio_ffmpeg

# Render uchun ffmpeg yo'lini avtomatik topish
ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

BOT_TOKEN = "8995513531:AAGgkooEJXFkdXoF5OpT25gliipK_Zq1Z14"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

URL_REGEX = r'https?://[^\s]+'

# Har bir foydalanuvchi uchun qidiruv natijalarini saqlash
user_search_results = {}

# Flask serverini yaratamiz
app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


@dp.message(Command('start'))
async def send_welcome(message: types.Message):
  await message.answer(
      "Salom! Menga istalgan qo'shiq nomini yozib yuboring (masalan: `Osmon Navro'z`)"
      " yoki ijtimoiy tarmoq havolasini yuboring, uni yuklab beraman."
  )


@dp.message(F.text)
async def handle_message(message: types.Message):
  text = message.text.strip()

  if re.match(URL_REGEX, text):
    await download_and_send_media(message, text)
  else:
    waiting_msg = await message.answer(
        f"🔍 '{text}' bo'yicha qidirilmoqda..."
    )

    try:
      ydl_opts = {
          'extract_flat': True, 
          'quiet': True, 
          'default_search': 'ytsearch10',
          'http_headers': {
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          }
      }
      with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(text, download=False)
        entries = info.get('entries', [])

      if not entries:
        await bot.edit_message_text(
            "❌ Hech narsa topilmadi.",
            chat_id=message.chat.id,
            message_id=waiting_msg.message_id,
        )
        return

      results_text = f"🔍 <b>'{text}'</b> bo'yicha topilgan natijalar:\n\n"
      user_links = []

      for i, entry in enumerate(entries, 1):
        title = entry.get('title', 'Nomaʼlum')
        url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
        user_links.append(url)
        results_text += f"{i}. {title}\n"

      user_search_results[message.from_user.id] = user_links

      keyboard_buttons = [
          InlineKeyboardButton(text=str(i), callback_data=f"dl_{i}")
          for i in range(1, len(entries) + 1)
      ]
      keyboard = InlineKeyboardMarkup(
          inline_keyboard=[
              keyboard_buttons[:5],
              keyboard_buttons[5:],
          ]
      )

      await bot.edit_message_text(
          results_text,
          chat_id=message.chat.id,
          message_id=waiting_msg.message_id,
          reply_markup=keyboard,
          parse_mode='HTML',
      )

    except Exception as e:
      await bot.edit_message_text(
          f"❌ Qidirishda xatolik yuz berdi: {e}",
          chat_id=message.chat.id,
          message_id=waiting_msg.message_id,
      )


@dp.callback_query(F.data.startswith('dl_'))
async def callback_download(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  if user_id not in user_search_results:
    await callback.answer("Eski qidiruv natijasi. Qaytadan qidiring.", show_alert=True)
    return

  index = int(callback.data.split('_')[1]) - 1
  links = user_search_results[user_id]

  if index >= len(links):
    await callback.answer("Topilmadi.", show_alert=True)
    return

  url = links[index]
  await callback.answer("Musiqa yuklab olinmoqda, kuting...")
  
  status_msg = await callback.message.answer("📥 Yuklab olinmoqda va yuborilmoqda...")
  
  await download_and_send_media(status_msg, url, edit_msg=True)


async def download_and_send_media(message: types.Message, url: str, edit_msg=False):
  output_template = 'downloads/%(id)s.%(ext)s'
  os.makedirs('downloads', exist_ok=True)

  ydl_opts = {
      'format': 'bestaudio/best',
      'outtmpl': output_template,
      'ffmpeg_location': ffmpeg_path,
      'http_headers': {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      },
      'postprocessors': [{
          'key': 'FFmpegExtractAudio',
          'preferredcodec': 'mp3',
          'preferredquality': '192',
      }],
      'quiet': True,
  }

  file_path = None
  try:
    with YoutubeDL(ydl_opts) as ydl:
      info = ydl.extract_info(url, download=True)
      filename = ydl.prepare_filename(info)
      file_path = os.path.splitext(filename)[0] + '.mp3'
      title = info.get('title', 'audio')

    if os.path.exists(file_path):
      audio = FSInputFile(file_path)
      if edit_msg:
        await message.answer_audio(audio, caption=title)
        await message.delete()
      else:
        await message.answer_audio(audio, caption=title)
    else:
      if edit_msg:
        await message.edit_text("⚠️ Musiqani yuklab bo'lmadi.")
      else:
        await message.answer("⚠️ Musiqani yuklab bo'lmadi.")
  except Exception as e:
    err_text = f"⚠️ Xatolik yuz berdi: {str(e)[:100]}"
    if edit_msg:
      await message.edit_text(err_text)
    else:
      await message.answer(err_text)
  finally:
    if file_path and os.path.exists(file_path):
      try:
        os.remove(file_path)
      except:
        pass


async def main():
  web_thread = threading.Thread(target=run_web)
  web_thread.daemon = True
  web_thread.start()

  await dp.start_polling(bot)


if __name__ == '__main__':
  asyncio.run(main())
