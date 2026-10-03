import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from shazamio import Shazam
import yt_dlp

TOKEN = "8995513531:AAGgkoOeJXFKdXoF5oPt25gliipK_ZqlZ14"

bot = Bot(token=TOKEN)
dp = Dispatcher()
shazam = Shazam()

logging.basicConfig(level=logging.INFO)

user_search_results = {}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "📥 YouTube, Instagram, TikTok havolasini yuboring — videoni yuklab beraman.\n"
        "🎵 Qo'shiq nomini yozing — 10 ta variant chiqaraman.\n"
        "🎙 Audio yoki ovozli xabar yuboring — Shazam orqali tanib beraman!"
    )

# 1. Havola (Link) orqali video yuklash
@dp.message(F.text & (F.text.startswith("http://") | F.text.startswith("https://")))
async def handle_url(message: types.Message):
    url = message.text.strip()
    processing_msg = await message.answer("⏳ Video yuklab olinmoqda, biroz kuting...")
    
    output_template = "downloaded_video.mp4"
    if os.path.exists(output_template):
        os.remove(output_template)
        
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_template,
        'max_filesize': 50 * 1024 * 1024,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists(output_template):
            video_file = types.FSInputFile(output_template)
            await message.answer_video(video_file, caption="✅ Marhamat, siz so'ragan video!")
        else:
            await message.answer("❌ Videoni yuklab bo'lmadi.")
    except Exception as e:
        logging.error(f"Video yuklashda xatolik: {e}")
        await message.answer("⚠️ Videoni yuklab olishda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()
        if os.path.exists(output_template):
            os.remove(output_template)

# 2. Matn orqali musiqa qidirish
@dp.message(F.text & ~F.text.startswith("/") & ~F.text.startswith("http"))
async def search_music(message: types.Message):
    query = message.text.strip()
    processing_msg = await message.answer(f"🔍 '{query}' bo'yicha qidirilmoqda...")
    
    ydl_opts = {
        'extract_flat': True,
        'skip_download': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch10:{query}", download=False)
            entries = info.get('entries', [])
            
        if not entries:
            await message.answer("❌ Hech narsa topilmadi.")
            await processing_msg.delete()
            return
            
        text = f"🔎 **'{query}'** bo'yicha topilgan natijalar:\n\n"
        results = []
        for i, entry in enumerate(entries[:10], 1):
            title = entry.get('title', 'Noma\'lum')
            vid_id = entry.get('id')
            url = f"https://www.youtube.com/watch?v={vid_id}"
            results.append((title, url))
            text += f"{i}. {title}\n"
            
        user_search_results[message.from_user.id] = results
        text += "\n👇 Yuklab olish uchun **1 dan 10 gacha bo'lgan raqamni** yuboring!"
        
        await message.answer(text)
    except Exception as e:
        logging.error(f"Qidirish xatoligi: {e}")
        await message.answer("⚠️️ Qidirishda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()

# 3. Raqam yuborilganda musiqani yuklab berish
@dp.message(F.text.isdigit())
async def download_selected_music(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_search_results:
        await message.answer("⚠️ Avval qo'shiq nomini yozib, qidiruv amalga oshiring!")
        return
        
    index = int(message.text) - 1
    results = user_search_results[user_id]
    
    if index < 0 or index >= len(results):
        await message.answer("❌ Iltimos, 1 dan 10 gacha bo'lgan to'g'ri raqamni tanlang.")
        return
        
    title, url = results[index]
    processing_msg = await message.answer(f"⏳ **{title}** yuklab olinmoqda, kuting...")
    
    output_audio = "audio.mp3"
    if os.path.exists(output_audio):
        os.remove(output_audio)
        
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'audio',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
        'max_filesize': 50 * 1024 * 1024,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        # Topilgan mp3 faylni topish
        final_file = "audio.mp3"
        if os.path.exists(final_file):
            audio_input = types.FSInputFile(final_file)
            await message.answer_audio(audio_input, caption=f"🎵 {title}")
        else:
            await message.answer("❌ Musiqani yuklab bo'lmadi.")
    except Exception as e:
        logging.error(f"Audio yuklash xatoligi: {e}")
        await message.answer("⚠️ Musiqani yuklab olishda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()
        if os.path.exists("audio.mp3"):
            os.remove("audio.mp3")

# 4. Shazam orqali musiqa tanish
@dp.message(F.voice | F.audio)
async def handle_audio(message: types.Message):
    processing_msg = await message.answer("🔍 Qo'shiq qidirilmoqda, biroz kuting...")
    audio_file_name = "temp_audio.ogg"
    
    try:
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        downloaded_file_bytes = await bot.download_file(file_path)
        with open(audio_file_name, "wb") as f:
            f.write(downloaded_file_bytes.read())
            
        out = await shazam.recognize(audio_file_name)
        
        if out and "track" in out:
            track = out["track"]
            title = track.get("title", "Noma'lum")
            artist = track.get("subtitle", "Noma'lum artist")
            await message.answer(f"✅ **Topildi!**\n\n🎵 Qo'shiq: {title}\n🎤 Ijrochi: {artist}")
        else:
            await message.answer("❌ Kechirasiz, bu musiqani aniqlab bo'lmadi.")
    except Exception as e:
        logging.error(f"Shazam xatoligi: {e}")
        await message.answer("⚠️️ Musiqani aniqlashda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()
        if os.path.exists(audio_file_name):
            os.remove(audio_file_name)

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
