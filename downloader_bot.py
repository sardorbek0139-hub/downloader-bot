import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import yt_dlp

TOKEN = "8995513531:AAGgkoOeJXFKdXoF5oPt25gliipK_ZqlZ14"

bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "Assalomu alaykum!\n\n"
        "🔗 Menga YouTube, Instagram yoki TikTok havolasini yuboring — men sizga videoni yuklab beraman!"
    )

# Havola (URL) orqali video yuklash
@dp.message(F.text & (F.text.startswith("http://") | F.text.startswith("https://")))
async def handle_url(message: types.Message):
    url = message.text.strip()
    processing_msg = await message.answer("Video yuklab olinmoqda, iltimos biroz kuting...")
    
    output_template = "downloaded_video.mp4"
    if os.path.exists(output_template):
        os.remove(output_template)
        
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_template,
        'max_filesize': 50 * 1024 * 1024, # 50 MB gacha bo'lgan videolar uchun
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists(output_template):
            video_file = types.FSInputFile(output_template)
            await message.answer_video(video_file, caption="Marhamat, siz so'ragan video! 🎬")
        else:
            await message.answer("Kechirasiz, videoni yuklab bo'lmadi.")
    except Exception as e:
        logging.error(f"Video yuklashda xatolik: {e}")
        await message.answer("Videoni yuklab olishda xatolik yuz berdi. Havola to'g'riligiga ishonch hosil qiling.")
    finally:
        await processing_msg.delete()
        if os.path.exists(output_template):
            try:
                os.remove(output_template)
            except:
                pass

# Boshqa turdagi xabarlar uchun ogohlantirish
@dp.message()
async def other_messages(message: types.Message):
    await message.answer("Iltimos, faqat video havolasini (URL) yuboring!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
