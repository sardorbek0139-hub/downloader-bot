import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
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
        "Assalomu alaykum!\n\n"
        "YouTube, Instagram, TikTok havolasini yuboring — videoni yuklab beraman.\n"
        "Qo'shiq nomini yozing — 10 ta variant chiqaraman.\n"
        "Audio yoki ovozli xabar yuboring — Shazam orqali tanib beraman!"
    )

# 1. Havola orqali video yuklash
@dp.message(F.text & (F.text.startswith("http://") | F.text.startswith("https://")))
async def handle_url(message: types.Message):
    url = message.text.strip()
    processing_msg = await message.answer("Video yuklab olinmoqda, biroz kuting...")
    
    output_template = "downloaded_video.mp4"
    if os.path.exists(output_template):
        os.remove(output_template)
        
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_template,
        'max_filesize': 50 * 1024 * 1024,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists(output_template):
            video_file = types.FSInputFile(output_template)
            await message.answer_video(video_file, caption="Marhamat, siz so'ragan video!")
        else:
            await message.answer("Videoni yuklab bo'lmadi.")
    except Exception as e:
        logging.error(f"Video yuklashda xatolik: {e}")
        await message.answer("Videoni yuklab olishda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()
        if os.path.exists(output_template):
            os.remove(output_template)

# 2. Raqam yuborilganda musiqani yuklab berish (Qidiruvdan oldin tekshiriladi!)
@dp.message(F.text.regexp(r"^(?:[1-9]|10)$"))
async def download_selected_music(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_search_results:
        await message.answer("Avval qo'shiq nomini yozib qidiruv amalga oshiring!")
        return
        
    index = int(message.text) - 1
    results = user_search_results[user_id]
    
    if index < 0 or index >= len(results):
        await message.answer("Iltimos, 1 dan 10 gacha bo'lgan to'g'ri raqamni yuboring.")
        return
        
    title, url = results[index]
    processing_msg = await message.answer(f"{title} yuklab olinmoqda, kuting...")
    
    for f in os.listdir("."):
        if f.startswith("downloaded_audio"):
            try:
                os.remove(f)
            except:
                pass

    # YouTube blokirovkasini aylanib o'tish uchun maxsus sozlama va format
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloaded_audio.%(ext)s',
        'max_filesize': 50 * 1024 * 1024,
        'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
    }
    
    downloaded_file = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            
        if downloaded_file and os.path.exists(downloaded_file):
            audio_input = types.FSInputFile(downloaded_file)
            await message.answer_audio(audio_input, caption=f"🎵 {title}")
        else:
            await message.answer("Musiqani yuklab bo'lmadi.")
    except Exception as e:
        logging.error(f"Audio yuklash xatoligi: {e}")
        await message.answer("Musiqani yuklab olishda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except:
                pass

# 3. Matn orqali musiqa qidirish
@dp.message(F.text & ~F.text.startswith("/") & ~F.text.startswith("http"))
async def search_music(message: types.Message):
    query = message.text.strip()
    processing_msg = await message.answer(f"'{query}' bo'yicha qidirilmoqda...")
    
    ydl_opts = {
        'extract_flat': True,
        'skip_download': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch10:{query}", download=False)
            entries = info.get('entries', [])
            
        if not entries:
            await message.answer("Hech narsa topilmadi.")
            await processing_msg.delete()
            return
            
        text = f"🔍 {query} bo'yicha topilgan natijalar:\n\n"
        results = []
        
        # Oson bosish uchun pastki klaviatura (ReplyKeyboardMarkup) tugmalarini yasash
        kb_builder = ReplyKeyboardBuilder()
        
        for i, entry in enumerate(entries[:10], 1):
            title = entry.get('title', 'Noma\'lum')
            vid_id = entry.get('id')
            url = f"https://www.youtube.com/watch?v={vid_id}"
            results.append((title, url))
            
            text += f"{i}. {title}\n"
            kb_builder.add(types.KeyboardButton(text=str(i)))
            
        user_search_results[message.from_user.id] = results
        
        # Tugmalarni 5 tadan qatorlarga bo'lish
        kb_builder.adjust(5, 5)
        keyboard = kb_builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
        
        text += "\n👇 Yuklab olish uchun pastdagi tugmalardan raqamni tanlang yoki yuboring!"
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Qidirish xatoligi: {e}")
        await message.answer("Qidirishda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()

# 4. Shazam orqali musiqa tanish
@dp.message(F.voice | F.audio)
async def handle_audio(message: types.Message):
    processing_msg = await message.answer("Qo'shiq qidirilmoqda, biroz kuting...")
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
            await message.answer(f"Topildi!\n\nQo'shiq: {title}\nIjrochi: {artist}")
        else:
            await message.answer("Kechirasiz, bu musiqani aniqlab bo'lmadi.")
    except Exception as e:
        logging.error(f"Shazam xatoligi: {e}")
        await message.answer("Musiqani aniqlashda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()
        if os.path.exists(audio_file_name):
            os.remove(audio_file_name)

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
