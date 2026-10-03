import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from shazamio import Shazam
import yt_dlp

# Sizning bot tokeningiz kiritildi
TOKEN = "8995513531:AAGgkoOeJXFKdXoF5oPt25gliipK_ZqlZ14"

bot = Bot(token=TOKEN)
dp = Dispatcher()
shazam = Shazam()

logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "📥 Menga YouTube, Instagram yoki TikTok **havolasini** yuboring — videoni yuklab beraman.\n"
        "🎵 Yoki musiqa nomi, audio fayl / ovozli xabar yuboring — Shazam orqali tanib beraman!"
    )

# 1. Havola (Link) orqali video yuklash qismi
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
        'max_filesize': 50 * 1024 * 1024, # 50MB gacha cheklov
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists(output_template):
            video_file = types.FSInputFile(output_template)
            await message.answer_video(video_file, caption="✅ Marhamat, siz so'ragan video!")
        else:
            await message.answer("❌ Videoni yuklab bo'lmadi. Havolani tekshirib ko'ring.")
            
    except Exception as e:
        logging.error(f"Video yuklashda xatolik: {e}")
        await message.answer("⚠️ Videoni yuklab olishda xatolik yuz berdi (hajmi katta bo'lishi mumkin).")
        
    finally:
        await processing_msg.delete()
        if os.path.exists(output_template):
            os.remove(output_template)

# 2. Ovozli xabar yoki audio orqali Shazam'da musiqa tanish qismi
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
            
            await message.answer(
                f"✅ **Topildi!**\n\n"
                f"🎵 Qo'shiq: {title}\n"
                f"🎤 Ijrochi: {artist}"
            )
        else:
            await message.answer("❌ Kechirasiz, bu musiqani aniqlab bo'lmadi.")
            
    except Exception as e:
        logging.error(f"Shazam xatoligi: {e}")
        await message.answer("⚠️ Musiqani aniqlashda xatolik yuz berdi.")
        
    finally:
        await processing_msg.delete()
        if os.path.exists(audio_file_name):
            os.remove(audio_file_name)

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
