import requests
import subprocess
from datetime import datetime

from aiogram.utils import executor
from aiogram.dispatcher import Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from create_main_bot import dp
from cfg.database import Database
from main_telegram_bot import Admin

db = Database('cfg/database')


async def shutdown(dispatcher: Dispatcher):
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


def main():
    Admin.register_handler_admin(dp)

    executor.start_polling(dp, on_shutdown=shutdown)


async def send_m(text_malling):
    all_id_users = db.get_all_user()
    all_token = db.get_bot_token()[0].split("|")
    for token in all_token:
        for id_user in all_id_users:
            try:
                url_req = "https://api.telegram.org/bot" + token + "/sendMessage" + "?chat_id=" + str(id_user[0]) + "&text=" + text_malling
                requests.get(url_req)
            except:
                ...


if __name__ == '__main__':
    subprocess.Popen(["/home/str/Alica/.venv/bin/python", "/home/str/Alica/start_all_bot.py"])

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.start()
    all_malling_info = db.get_all_malling()
    for malling_info in all_malling_info:
        scheduler.add_job(send_m, trigger='cron', hour=malling_info[1][0:2],
                          minute=malling_info[1][3:5],
                          start_date=datetime.now(), kwargs={"text_malling": malling_info[-1]},
                          id=f"{malling_info[0]}")

    main()
