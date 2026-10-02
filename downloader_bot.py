import os
import re
import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL

BOT_TOKEN = "8995513531:AAGgkoOeJXFKdXoF5oPt25gliipK_ZqlZ14"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

URL_REGEX = r'https?://[^\s]+'
user_links = {}

# --- 1. VIDEONI YUKLAB OLISH ---
def download_video(url: str):
    out_template = 'downloads/%(id)s.%(ext)s'
    ydl_opts = {
        'format': 'best/bestvideo+bestaudio',
        'outtmpl': out_template,
        'max_filesize': 50 * 1024 * 1024,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        if not os.path.exists(filename):
            base = os.path.splitext(filename)[0]
            for ext in ['.mp4', '.mkv', '.webm', '.mov']:
                if os.path.exists(base + ext):
                    filename = base + ext
                    break

        title = info.get('title', 'Video')
        return filename, title

# --- 2. MUSIQANING FULL VERSIYASINI QIDIRISH ---
def find_full_audio(url: str):
    out_template = 'downloads/%(id)s_audio.%(ext)s'
    search_query = None

    try:
        with YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                track = info.get('track')
                artist = info.get('artist')
                song = info.get('song')
                title = info.get('title', '')
                description = info.get('description', '')

                if track and artist:
                    search_query = f"ytsearch1:{artist} - {track} full song"
                elif song and artist:
                    search_query = f"ytsearch1:{artist} - {song} full song"
                elif track:
                    search_query = f"ytsearch1:{track} full song"
                else:
                    # Sarlavhadan yoki tavsifdan musiqaga o'xshash qismni qidiramiz
                    clean_title = title
                    for word in ["Video by", "Reel by", "Original audio", "audio by", "IG"]:
                        clean_title = clean_title.replace(word, "")
                    
                    clean_title = clean_title.strip()
                    if len(clean_title) > 2:
                        search_query = f"ytsearch1:{clean_title} full song"
    except Exception as e:
        print(f"Meta qidirishda xatolik: {e}")

    if not search_query:
        search_query = f"ytsearch1:hit music full version"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_template,
        'max_filesize': 50 * 1024 * 1024,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(search_query, download=True)
            if 'entries' in info:
                info = info['entries'][0]
            
            filename = ydl.prepare_filename(info)
            song_title = info.get('title', 'Full Musiqa')
            return filename, song_title
        except Exception:
            return None, None


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 **Assalomu alaykum!**\n\n"
        "Menga Instagram, YouTube yoki TikTok havolasini yuboring.\n"
        "Men videoni va ostida qo'shiqni yuklab olish tugmasini chiqarib beraman! 📥🎵"
    )


@dp.message(F.text.regexp(URL_REGEX))
async def handle_url(message: types.Message):
    url = re.search(URL_REGEX, message.text).group(0)
    status_msg = await message.answer("⏳ *Video yuklanmoqda, kuting...*", parse_mode="Markdown")

    loop = asyncio.get_event_loop()
    bot_info = await bot.get_me()

    try:
        user_links[message.from_user.id] = url
        video_path, video_title = await loop.run_in_executor(None, download_video, url)
        
        if video_path and os.path.exists(video_path):
            video = FSInputFile(video_path)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📥 Qo'shiqni yuklab olish", callback_data="download_song")]
            ])

            await message.answer_video(
                video=video,
                caption=f"🎬 **{video_title[:100]}**\n\n🤖 @{bot_info.username}",
                reply_markup=keyboard
            )
            os.remove(video_path)

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text("⚠️ Xatolik yuz berdi. Havolani tekshirib qaytadan yuboring.")
        print(f"Xatolik: {e}")


@dp.callback_query(F.data == "download_song")
async def callback_download_song(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_links:
        await callback.answer("⚠️ Havola eskirgan. Qaytadan yuboring.", show_alert=True)
        return

    url = user_links[user_id]
    await callback.answer("🎵 Qo'shiq qidirilmoqda...")
    
    wait_msg = await callback.message.answer("🔍 *Musiqaning full versiyasi qidirilmoqda...*", parse_mode="Markdown")
    loop = asyncio.get_event_loop()
    bot_info = await bot.get_me()

    try:
        audio_path, audio_title = await loop.run_in_executor(None, find_full_audio, url)

        if audio_path and os.path.exists(audio_path):
            audio = FSInputFile(audio_path)
            await callback.message.answer_audio(
                audio=audio,
                caption=f"🎵 **{audio_title[:100]} (Full Versiya)**\n\n🤖 @{bot_info.username}"
            )
            os.remove(audio_path)
        else:
            await callback.message.answer("⚠️ Bu musiqani topib bo'lmadi.")

        await wait_msg.delete()

    except Exception as e:
        await wait_msg.edit_text("⚠️ Musiqani yuklab olishda xatolik yuz berdi.")
        print(f"Xatolik: {e}")


@dp.message(F.text)
async def invalid_input(message: types.Message):
    await message.answer("Iltimos, faqat video havolasini yuboring! 🔗")


async def main():
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
