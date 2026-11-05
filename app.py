import os
import threading
import asyncio
from flask import Flask
import bot

app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running"

@app.route('/health')
def health():
    return "OK"

def run_bot():
    # Создаем новый цикл событий для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Запускаем бота
    loop.run_until_complete(bot.dp.start_polling(bot.bot))

if __name == "__main__":
    # Запускаем бота в фоновом потоке
    threading.Thread(target=run_bot, daemon=True).start()
    # Запускаем Flask для Render
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
