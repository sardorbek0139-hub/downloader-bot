import logging
import os
import aiohttp
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
        "🔗 YouTube, Instagram, TikTok havolasini yuboring — videoni yuklab beraman.\n"
        "🎵 Qo'shiq nomini yozing — internetdan 10 ta variant topib beraman.\n"
        "🎙 Audio yoki ovozli xabar yuboring — Shazam orqali tanib beraman!"
    )

# 1. Havola orqali video yuklash (YouTube, Instagram, TikTok)
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

# 2. Matn orqali musiqa qidirish (Internet bazasi orqali xatoliksiz)
@dp.message(F.text & ~F.text.startswith("/") & ~F.text.startswith("http"))
async def search_music(message: types.Message):
    query = message.text.strip()
    processing_msg = await message.answer(f"'{query}' internetdan qidirilmoqda...")
    
    try:
        api_url = f"https://saavn.dev/api/search/songs?query={query}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results_data = data.get("data", {}).get("results", [])
                else:
                    results_data = []

        if not results_data:
            await message.answer("Hech narsa topilmadi.")
            await processing_msg.delete()
            return
            
        text = f"🔍 '{query}' bo'yicha topilgan natijalar:\n\n"
        results = []
        kb_builder = ReplyKeyboardBuilder()
        
        for i, song in enumerate(results_data[:10], 1):
            title = song.get('name', 'Noma\'lum')
            artist = song.get('artists', {}).get('primary', [{}])[0].get('name', '')
            full_title = f"{artist} - {title}" if artist else title
            
            download_links = song.get('downloadUrl', [])
            audio_url = download_links[-1].get('url') if download_links else None
            
            if audio_url:
                results.append((full_title, audio_url))
                text += f"{i}. {full_title}\n"
                kb_builder.add(types.KeyboardButton(text=str(i)))
            
        if not results:
            await message.answer("Topilgan qo'shiqlar uchun yuklab olish havolasi topilmadi.")
            await processing_msg.delete()
            return

        user_search_results[message.from_user.id] = results
        
        kb_builder.adjust(5, 5)
        keyboard = kb_builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
        
        text += "\n👇 Yuklab olish uchun pastdagi tugmalardan raqamni tanlang!"
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Qidirish xatoligi: {e}")
        await message.answer("Qidirishda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()

# 3. Raqam yuborilganda musiqani yuborish
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
        
    title, audio_url = results[index]
    processing_msg = await message.answer(f"🎵 '{title}' yuklab olinmoqda, kuting...")
    
    audio_filename = "downloaded_song.mp3"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(audio_url) as resp:
                if resp.status == 200:
                    with open(audio_filename, "wb") as f:
                        f.write(await resp.read())
                        
        if os.path.exists(audio_filename):
            audio_input = types.FSInputFile(audio_filename)
            await message.answer_audio(audio_input, caption=f"🎵 {title}")
        else:
            await message.answer("Musiqani yuklab bo'lmadi.")
    except Exception as e:
        logging.error(f"Audio yuklash xatoligi: {e}")
        await message.answer("Musiqani yuklab olishda xatolik yuz berdi.")
    finally:
        await processing_msg.delete()
        if os.path.exists(audio_filename):
            try:
                os.remove(audio_filename)
            except:
                pass

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
