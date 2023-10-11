import subprocess
from aiogram.utils import executor
from aiogram.dispatcher import Dispatcher

from create_main_bot import dp
from main_telegram_bot import Admin
from cfg.database import Database

db = Database('cfg/database')


async def shutdown(dispatcher: Dispatcher):
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


def main():

    Admin.register_handler_admin(dp)
    executor.start_polling(dp, on_shutdown=shutdown)


if __name__ == '__main__':
    subprocess.Popen(["/home/str/Tg_magaz2/.venv/bin/python", "/home/str/Tg_magaz2/telegram_bot/monitor.py"])
    main()
