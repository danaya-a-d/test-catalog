import asyncio
import logging
import os
from io import BytesIO
from pathlib import Path
import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from aiohttp import web
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)
from dotenv import load_dotenv


# загружаем переменные окружения
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

API_URL = os.environ["API_URL"].rstrip("/")
API_KEY = os.environ["INTERNAL_API_KEY"]
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.environ["ADMIN_TELEGRAM_ID"])
WEBAPP_URL = os.environ["WEBAPP_URL"]

BOT_MODE = os.getenv("BOT_MODE", "polling") # способ запуска
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
WEBHOOK_PATH = "/telegram/webhook"
WEBHOOK_PORT = 8081

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")


# создаем диспетчер
dp = Dispatcher()


# обрабатываем команду /start
@dp.message(CommandStart())
async def start_handler(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть каталог 🛍️",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ]
        ]
    )


    text = "Посмотри, какие товары у нас есть 👀"

    if message.from_user and message.from_user.id == ADMIN_ID:
        text += "\n\nДля добавления товара используй /add 📸"

    await message.answer(
        text,
        reply_markup=keyboard
    )



# добавление товара
@dp.message(Command("add"))
async def add_product_handler(message: Message):
    if message.from_user is None:
        return

    if message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для добавления товаров 😔")
        return

    await message.answer("Отправьте фото товара с названием в подписи к изображению 📷")


# получаем фото и название товара
@dp.message(F.photo, F.chat.type == "private")
async def handle_product_photo(message: Message, bot: Bot):
    # проверяем админа
    if message.from_user is None or message.from_user.id != ADMIN_ID:
        await message.answer("У вас нет прав для добавления товаров 😔")
        return

    # получаем и проверяем название из подписи
    name = (message.caption or "").strip()

    if not name or len(name) > 200:
        await message.answer("Добавьте название товара в подпись к фото 📝 (от 1 до 200 символов)")
        return

    # получаем и проверяем фото
    photo = message.photo[-1]
    max_size = 5 * 1024 * 1024

    if photo.file_size is not None and photo.file_size > max_size:
        await message.answer("Фото слишком большое 🤯")
        return

    # скачиваем фото и отправляем в api
    try:
        with BytesIO() as image_buffer: # получаем изображение из telegram по file_id
            await bot.download(
                photo.file_id,
                destination=image_buffer
            )

            # проверка размера
            if image_buffer.getbuffer().nbytes > max_size:
                await message.answer("Фото слишком большое 🤯")
                return

            # создание клиента
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{API_URL}/products",
                    headers={"X-API-Key": API_KEY},
                    data={"name": name},
                    files={
                        "image": (
                            "telegram.jpg",
                            image_buffer,
                            "image/jpeg"
                        )
                    }
                )

    except TelegramAPIError:
        logging.exception("Telegram download failed")
        await message.answer("Не удалось скачать фото ☹️")
        return

    except httpx.RequestError:
        logging.exception("FastAPI request failed")
        await message.answer("Не удалось связаться с сервером 😵")
        return

    # проверка ответа api
    if response.status_code != 201:
        logging.error(
            "API error %s: %s",
            response.status_code,
            response.text
        )
        await message.answer("Ошибка создания товара ☹️")
        return

    # сообщение об успешном создании
    product = response.json()

    await message.answer(
        f"Товар «{product['name']}» успешно создан 👍\n"
#         f"ID: {product['id']}"
    )


# запуск бота

# запуск через polling
async def run_polling():
    async with Bot(token=BOT_TOKEN) as bot:
        await dp.start_polling(bot)


# проверка доступности webhook-сервера
async def health_handler(request: web.Request):
    return web.json_response({"status": "ok"})


# регистрация webhook в telegram
async def on_startup(bot: Bot):
    await bot.set_webhook(
        url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET
    )


# запуск через webhook
def run_webhook():
    if not WEBHOOK_URL or not WEBHOOK_SECRET:
        raise RuntimeError("Webhook settings are not configured")

    bot = Bot(token=BOT_TOKEN)

    dp.startup.register(on_startup)

    app = web.Application()

    app.router.add_get("/health", health_handler)

    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    )

    handler.register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    web.run_app(
        app,
        host="0.0.0.0",
        port=WEBHOOK_PORT
    )


if __name__ == "__main__":
    if BOT_MODE == "webhook":
        run_webhook()
    elif BOT_MODE == "polling":
        asyncio.run(run_polling())
    else:
        raise RuntimeError(f"Unknown BOT_MODE: {BOT_MODE}")

