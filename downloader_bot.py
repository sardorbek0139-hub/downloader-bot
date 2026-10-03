import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from shazamio import Shazam
import yt_dlp


# =========================
# SOZLAMALAR
# =========================

TOKEN = "BU_YERGA_YANGI_BOT_TOKENINGIZNI_YOZING"

bot = Bot(token=TOKEN)
dp = Dispatcher()
shazam = Shazam()

logging.basicConfig(level=logging.INFO)


# Har bir foydalanuvchining qidiruv natijalari
user_search_results = {}


# =========================
# /START
# =========================

@dp.message(Command("start"))
async def start_handler(message: types.Message):

    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "🎵 Qo'shiq nomini yozing — 10 ta variant chiqaraman.\n"
        "🎙 Audio yoki ovozli xabar yuboring — Shazam orqali aniqlayman.\n"
        "🔗 YouTube havolasini yuboring — yuklab beraman."
    )


# =========================
# URL ORQALI VIDEO YUKLASH
# =========================

@dp.message(
    F.text & (
        F.text.startswith("http://") |
        F.text.startswith("https://")
    )
)
async def handle_url(message: types.Message):

    url = message.text.strip()

    processing_msg = await message.answer(
        "⏳ Video yuklab olinmoqda..."
    )

    output_template = "downloaded_video.%(ext)s"

    try:

        ydl_opts = {
            "format": "best[ext=mp4]/best",
            "outtmpl": output_template,
            "noplaylist": True,
            "max_filesize": 50 * 1024 * 1024,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            downloaded_file = ydl.prepare_filename(info)

        if os.path.exists(downloaded_file):

            video_file = types.FSInputFile(downloaded_file)

            await message.answer_video(
                video_file,
                caption="🎬 Marhamat, siz so'ragan video!"
            )

        else:

            await message.answer(
                "❌ Videoni yuklab bo'lmadi."
            )

    except Exception as e:

        logging.exception("Video yuklash xatoligi:")

        await message.answer(
            f"❌ Video yuklashda xatolik:\n\n{str(e)[:1000]}"
        )

    finally:

        try:
            await processing_msg.delete()
        except:
            pass

        # Yuklangan fayllarni tozalash
        for file in os.listdir("."):

            if file.startswith("downloaded_video."):

                try:
                    os.remove(file)
                except:
                    pass


# =========================
# SHAZAM
# =========================

@dp.message(F.voice | F.audio)
async def handle_audio(message: types.Message):

    processing_msg = await message.answer(
        "🎵 Qo'shiq aniqlanmoqda..."
    )

    audio_file_name = "temp_audio.ogg"

    try:

        if message.voice:

            file_id = message.voice.file_id

        else:

            file_id = message.audio.file_id

        file = await bot.get_file(file_id)

        downloaded_file = await bot.download_file(
            file.file_path
        )

        with open(audio_file_name, "wb") as f:

            f.write(downloaded_file.read())

        result = await shazam.recognize(
            audio_file_name
        )

        if result and "track" in result:

            track = result["track"]

            title = track.get(
                "title",
                "Noma'lum"
            )

            artist = track.get(
                "subtitle",
                "Noma'lum artist"
            )

            await message.answer(
                f"🎵 Topildi!\n\n"
                f"Qo'shiq: {title}\n"
                f"👤 Ijrochi: {artist}"
            )

        else:

            await message.answer(
                "❌ Kechirasiz, qo'shiqni aniqlay olmadim."
            )

    except Exception as e:

        logging.exception("Shazam xatoligi:")

        await message.answer(
            f"❌ Shazam xatoligi:\n\n{str(e)[:1000]}"
        )

    finally:

        try:
            await processing_msg.delete()
        except:
            pass

        if os.path.exists(audio_file_name):

            try:
                os.remove(audio_file_name)
            except:
                pass


# =========================
# QO'SHIQ QIDIRISH
# =========================

@dp.message(F.text & ~F.text.startswith("/"))
async def search_music(message: types.Message):

    query = message.text.strip()

    processing_msg = await message.answer(
        f"🔎 '{query}' qidirilmoqda..."
    )

    try:

        ydl_opts = {
            "extract_flat": True,
            "skip_download": True,
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                f"ytsearch10:{query}",
                download=False
            )

        entries = info.get("entries", [])

        if not entries:

            await message.answer(
                "❌ Hech narsa topilmadi."
            )

            return

        text = (
            f"🔍 '{query}' bo'yicha natijalar:\n\n"
        )

        results = []

        keyboard = InlineKeyboardBuilder()

        for i, entry in enumerate(
            entries[:10],
            start=1
        ):

            title = entry.get(
                "title",
                "Noma'lum"
            )

            video_id = entry.get("id")

            url = (
                f"https://www.youtube.com/"
                f"watch?v={video_id}"
            )

            results.append(
                (title, url)
            )

            text += f"{i}. {title}\n"

            keyboard.add(
                types.InlineKeyboardButton(
                    text=str(i),
                    callback_data=f"dl_{i - 1}"
                )
            )

        user_search_results[
            message.from_user.id
        ] = results

        keyboard.adjust(5, 5)

        text += (
            "\n👇 Qo'shiqni yuklab olish "
            "uchun raqamini bosing."
        )

        await message.answer(
            text,
            reply_markup=keyboard.as_markup()
        )

    except Exception as e:

        logging.exception(
            "Qidirish xatoligi:"
        )

        await message.answer(
            f"❌ Qidirishda xatolik:\n\n"
            f"{str(e)[:1000]}"
        )

    finally:

        try:
            await processing_msg.delete()
        except:
            pass


# =========================
# TANLANGAN QO'SHIQNI YUKLASH
# =========================

@dp.callback_query(
    F.data.startswith("dl_")
)
async def download_selected_music(
    callback: types.CallbackQuery
):

    user_id = callback.from_user.id

    if user_id not in user_search_results:

        await callback.answer(
            "Qidiruv eskirgan. Qaytadan qidiring!",
            show_alert=True
        )

        return

    try:

        index = int(
            callback.data.split("_")[1]
        )

    except:

        await callback.answer(
            "Xatolik!",
            show_alert=True
        )

        return

    results = user_search_results[user_id]

    if index < 0 or index >= len(results):

        await callback.answer(
            "Qo'shiq topilmadi.",
            show_alert=True
        )

        return

    title, url = results[index]

    await callback.answer(
        "⏳ Yuklanmoqda..."
    )

    processing_msg = await callback.message.answer(
        f"🎵 {title}\n\n"
        f"⏳ MP3 tayyorlanmoqda..."
    )

    try:

        ydl_opts = {

            "format": "bestaudio/best",

            "outtmpl":
                "downloaded_audio.%(ext)s",

            "noplaylist": True,

            "quiet": False,

            "postprocessors": [

                {
                    "key":
                        "FFmpegExtractAudio",

                    "preferredcodec":
                        "mp3",

                    "preferredquality":
                        "192",
                }

            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            ydl.download([url])

        audio_file = "downloaded_audio.mp3"

        if os.path.exists(audio_file):

            audio = types.FSInputFile(
                audio_file
            )

            await callback.message.answer_audio(
                audio,
                caption=f"🎵 {title}"
            )

        else:

            await callback.message.answer(
                "❌ MP3 fayl yaratilmadi."
            )

    except Exception as e:

        logging.exception(
            "Audio yuklash xatoligi:"
        )

        await callback.message.answer(
            f"❌ Musiqani yuklashda xatolik:\n\n"
            f"{str(e)[:1500]}"
        )

    finally:

        try:
            await processing_msg.delete()
        except:
            pass

        # MP3 ni o'chirish
        if os.path.exists(
            "downloaded_audio.mp3"
        ):

            try:
                os.remove(
                    "downloaded_audio.mp3"
                )
            except:
                pass


# =========================
# BOTNI ISHGA TUSHIRISH
# =========================

async def main():

    print("🤖 Bot ishga tushdi!")

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
