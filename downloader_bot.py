import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from shazamio import Shazam
import yt_dlp

TOKEN = "8995513531:AAGgkoOeJXFKdXoF5oPt25gliipK_ZqlZ14"

bot = Bot(token=TOKEN)
dp = Dispatcher()
shazam = Shazam()

logging.basicConfig(level=logging.INFO)

# Foydalanuvchi qidiruv natijalarini vaqtincha saqlash
user_search_results = {}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "📥 YouTube, Instagram, TikTok havolasini yuboring — videoni yuklab beraman.\n"
        "🎵 Qo'shiq nomini yozing — 10 ta variant chiqaraman (tugmani bosib yuklab olasiz).\n"
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

# 2. Matn orqali musiqa qidirish va tugmalar yaratish
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
            
        text = f"🔎 **{query}** bo'yicha topilgan natijalar:\n\n"
        results = []
        builder = InlineKeyboardBuilder()
        
        for i, entry in enumerate(entries[:10], 1):
            title = entry.get('title', 'Noma\'lum')
            vid_id = entry.get('id')
            url = f"https://www.youtube.com/watch?v={vid_id}"
            results.append((title, url))
            
            # Matn ro'yxati
            text += f"{i}. {title}\n"
            # Har bir qo'shiq uchun raqamli tugma qo'shish
            builder.button(text=str(i), callback_data=f"dl_{i-1}")
            
        user_search_results[message.from_user.id] = results
        
        # Tugmalarni 5 tadan qatorlarga bo'lish
        builder.adjust(5, 5)
        
        text += "\n👇 Yuklab olish uchun pastdagi **raqam tugmasini** bosing!"
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Qidirish xatoligi: {e}")
        await message.answer("⚠️ Qidirishda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()

# 3. Tugma bosilganda musiqani yuklab berish
@dp.callback_query(F.data.startswith("dl_"))
async def callback_download_music(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_search_results:
        await callback.answer("⚠️ Avval qo'shiq qidiring!", show_alert=True)
        return
        
    index = int(callback.data.split("_")[1])
    results = user_search_results[user_id]
    
    if index < 0 or index >= len(results):
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)
        return
        
    title, url = results[index]
    await callback.answer(f"⏳ '{title}' yuklab olinmoqda...")
    processing_msg = await callback.message.answer(f"⏳ *{title}* yuklab olinmoqda, kuting...", parse_mode="Markdown")
    
    # Eski fayllarni tozalash
    for f in os.listdir("."):
        if f.startswith("downloaded_audio"):
            try:
                os.remove(f)
            except:
                pass

    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': 'downloaded_audio.%(ext)s',
        'max_filesize': 50 * 1024 * 1024,
    }
    
    downloaded_file = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            
        if downloaded_file and os.path.exists(downloaded_file):
            audio_input = types.FSInputFile(downloaded_file)
            await callback.message.answer_audio(audio_input, caption=f"🎵 {title}")
        else:
            await callback.message.answer("❌ Musiqani yuklab bo'lmadi.")
    except Exception as e:
        logging.error(f"Audio yuklash xatoligi: {e}")
        await callback.message.answer("⚠️ Musiqani yuklab olishda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except:
                pass

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
        await message.answer("⚠️ Musiqani aniqlashda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()
        if os.path.exists(audio_file_name):
            os.remove(audio_file_name)

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
