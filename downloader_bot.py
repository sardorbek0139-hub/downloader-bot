import asyncio
import os
import re
import threading
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask
from yt_dlp import YoutubeDL

BOT_TOKEN = "8995513531:AAGgkoOeJXFKdXoF5oPt25gliipK_ZqlZ14"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

URL_REGEX = r"https?://[^\s]+"
user_links = {}
user_search_results = {}

# --- RENDER TIMEOUT BERMASLIGI UCHIN FLASK SERVER ---
app = Flask(__name__)


@app.route("/", methods=["GET", "HEAD"])
def home():
  return "Bot is running!", 200


def run_web():
  app.run(host="0.0.0.0", port=10000)


# --- 1. HAVOLADAN VIDEONI YUKLAB OLISH ---
def download_video(url: str):
  out_template = "downloads/%(id)s.%(ext)s"
  ydl_opts = {
      "format": "best/bestvideo+bestaudio",
      "outtmpl": out_template,
      "max_filesize": 50 * 1024 * 1024,
      "quiet": True,
      "no_warnings": True,
      "geo_bypass": True,
      "nocheckcertificate": True,
      "user_agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
  }

  with YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=True)
    filename = ydl.prepare_filename(info)

    if not os.path.exists(filename):
      base = os.path.splitext(filename)[0]
      for ext in [".mp4", ".mkv", ".webm", ".mov"]:
        if os.path.exists(base + ext):
          filename = base + ext
          break

    title = info.get("title", "Video")
    return filename, title


# --- 2. QO'SHIQ NOMI BO'YICHA QIDIRISH (10 TA VARIANT) ---
def search_songs(query: str):
  ydl_opts = {
      "format": "bestaudio/best",
      "quiet": True,
      "no_warnings": True,
      "extract_flat": True,
  }
  search_query = f"ytsearch10:{query}"

  with YoutubeDL(ydl_opts) as ydl:
    try:
      info = ydl.extract_info(search_query, download=False)
      if "entries" in info:
        return info["entries"]
    except Exception as e:
      print(f"Qidirishda xatolik: {e}")
  return []


# --- 3. TANLANGAN MUSIQANI YUKLAB OLISH ---
def download_audio_by_url(video_url: str):
  out_template = "downloads/%(id)s_audio.%(ext)s"
  ydl_opts = {
      "format": "bestaudio/best",
      "outtmpl": out_template,
      "max_filesize": 50 * 1024 * 1024,
      "quiet": True,
      "no_warnings": True,
  }

  with YoutubeDL(ydl_opts) as ydl:
    try:
      info = ydl.extract_info(video_url, download=True)
      filename = ydl.prepare_filename(info)
      song_title = info.get("title", "Musiqa")
      return filename, song_title
    except Exception as e:
      print(f"Musiqani yuklab olishda xatolik: {e}")
      return None, None


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
  await message.answer(
      "👋 **Assalomu alaykum!**\n\n"
      "📥 Menga Instagram, YouTube yoki TikTok **havolasini** yuboring (videoni yuklab beraman).\n"
      "🎵 Yoki istalgan **qo'shiq nomini yozing**, men sizga 10 ta variant chiqarib beraman!"
  )


# --- HAVOLA KELGANDA ---
@dp.message(F.text.regexp(URL_REGEX))
async def handle_url(message: types.Message):
  url = re.search(URL_REGEX, message.text).group(0)
  status_msg = await message.answer(
      "⏳ *Video yuklanmoqda, kuting...*", parse_mode="Markdown"
  )

  loop = asyncio.get_event_loop()
  bot_info = await bot.get_me()

  try:
    user_links[message.from_user.id] = url
    video_path, video_title = await loop.run_in_executor(
        None, download_video, url
    )

    if video_path and os.path.exists(video_path):
      video = FSInputFile(video_path)
      keyboard = InlineKeyboardMarkup(inline_keyboard=[[
          InlineKeyboardButton(
              text="📥 Qo'shiqni yuklab olish", callback_data="download_song"
          )
      ]])

      await message.answer_video(
          video=video,
          caption=f"🎬 **{video_title[:100]}**\n\n🤖 @{bot_info.username}",
          reply_markup=keyboard,
      )
      os.remove(video_path)

    await status_msg.delete()

  except Exception as e:
    await status_msg.edit_text(
        "⚠️ Xatolik yuz berdi. Havolani tekshirib qaytadan yuboring."
    )
    print(f"Xatolik: {e}")


# --- MATN (QO'SHIQ NOMI) KELGANDA ---
@dp.message(F.text)
async def handle_text_search(message: types.Message):
  query = message.text.strip()
  status_msg = await message.answer(
      "🔍 *Musiqalar qidirilmoqda, kuting...*", parse_mode="Markdown"
  )

  loop = asyncio.get_event_loop()
  entries = await loop.run_in_executor(None, search_songs, query)

  if not entries:
    await status_msg.edit_text(
        "⚠️ Hech qanday musiqa topilmadi. Boshqa nom yozib ko'ring."
    )
    return

  user_search_results[message.from_user.id] = entries

  text_response = f"🔍 **'{query}'** bo'yicha topilgan natijalar:\n\n"
  buttons = []
  row = []

  for idx, entry in enumerate(entries[:10], start=1):
    title = entry.get("title", "Noma'lum")
    duration = entry.get("duration_string", "")
    if duration:
      text_response += f"{idx}. {title} - {duration}\n"
    else:
      text_response += f"{idx}. {title}\n"

    row.append(
        InlineKeyboardButton(
            text=str(idx), callback_data=f"select_song_{idx-1}"
        )
    )
    if len(row) == 5:
      buttons.append(row)
      row = []

  if row:
    buttons.append(row)

  keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
  await status_msg.edit_text(
      text=text_response, parse_mode="Markdown", reply_markup=keyboard
  )


# --- TUGMA BOSILganda (QO'SHIQNI TANLAB YUKLAB OLISH) ---
@dp.callback_query(F.data.startswith("select_song_"))
async def callback_select_song(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  if (
      user_id not in user_search_results
      or not user_search_results[user_id]
  ):
    await callback.answer(
        "⚠️ Natijalar eskirgan. Qaytadan qidiruv bering.", show_alert=True
    )
    return

  index = int(callback.data.split("_")[2])
  entries = user_search_results[user_id]

  if index >= len(entries):
    await callback.answer("⚠️ Xatolik yuz berdi.", show_alert=True)
    return

  selected_track = entries[index]
  video_url = selected_track.get("url")
  if not video_url:
    video_url = f"https://www.youtube.com/watch?v={selected_track.get('id')}"

  await callback.answer("🎵 Tanlangan musiqa yuklanmoqda...")
  wait_msg = await callback.message.answer(
      "📥 *Musiqa yuklab olinmoqda, kuting...*", parse_mode="Markdown"
  )

  loop = asyncio.get_event_loop()
  bot_info = await bot.get_me()

  audio_path, audio_title = await loop.run_in_executor(
      None, download_audio_by_url, video_url
  )

  if audio_path and os.path.exists(audio_path):
    audio = FSInputFile(audio_path)
    await callback.message.answer_audio(
        audio=audio,
        caption=(
            f"🎵 **{audio_title[:100]}**\n\n🤖 @{bot_info.username}"
            " | [Yuklaydi Bot]"
        ),
    )
    os.remove(audio_path)
  else:
    await callback.message.answer(
        "⚠️ Musiqani yuklab bo'lmadi. Boshqasini tanlab ko'ring."
    )

  await wait_msg.delete()


@dp.callback_query(F.data == "download_song")
async def callback_download_song(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  if user_id not in user_links:
    await callback.answer(
        "⚠️ Havola eskirgan. Qaytadan yuboring.", show_alert=True
    )
    return

  url = user_links[user_id]
  await callback.answer("🎵 Qo'shiq qidirilmoqda...")

  wait_msg = await callback.message.answer(
      "🔍 *Musiqaning full versiyasi qidirilmoqda...*", parse_mode="Markdown"
  )
  loop = asyncio.get_event_loop()
  bot_info = await bot.get_me()

  try:
    audio_path, audio_title = await loop.run_in_executor(
        None, download_audio_by_url, url
    )

    if audio_path and os.path.exists(audio_path):
      audio = FSInputFile(audio_path)
      await callback.message.answer_audio(
          audio=audio,
          caption=(
              f"🎵 **{audio_title[:100]} (Full Versiya)**\n\n🤖"
              f" @{bot_info.username}"
          ),
      )
      os.remove(audio_path)
    else:
      await callback.message.answer("⚠️ Bu musiqani topib bo'lmadi.")

    await wait_msg.delete()

  except Exception as e:
    await wait_msg.edit_text("⚠️ Musiqani yuklab olishda xatolik yuz berdi.")
    print(f"Xatolik: {e}")


async def main():
  if not os.path.exists("downloads"):
    os.makedirs("downloads")
  print("Bot muvaffaqiyatli ishga tushdi...")
  await dp.start_polling(bot)


if __name__ == "__main__":
  # Render port talabini qondirish uchun Flask serverni ishga tushiramiz
  threading.Thread(target=run_web, daemon=True).start()
  asyncio.run(main())
