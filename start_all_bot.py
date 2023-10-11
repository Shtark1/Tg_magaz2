import os
import sys
import logging
import time

from aiogram import Bot
import requests
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.dispatcher import Dispatcher, FSMContext
import random
from random import randrange
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

from telegram_bot.dop_functional import convert_rub_to_btc, generation_captha
from telegram_bot.messages import MESSAGES
from telegram_bot.KeyboardButton import BUTTON_TYPES
from telegram_bot.utils import StatesUsers
from cfg.database import Database


db = Database('cfg/database')


async def start_bot(dp):
    event_loop.create_task(dp.start_polling())


def bot_init(event_loop, token):
    bot = Bot(token, parse_mode="HTML", disable_web_page_preview=True)
    dp = Dispatcher(bot=bot, storage=MemoryStorage())

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.start()

    # ===================================================
    # ================== СТАРТ КОМАНДА ==================
    # ===================================================
    async def start_command(message: Message):
        await dp.bot.set_my_commands(BUTTON_TYPES["ALL_COMMANDS"])
        if not db.user_exists(message.from_user.id):
            db.add_user(message.from_user.id, message.from_user.username)
            captcha_text = await generation_captha(message)
            with open(f'img/{message.from_user.id}.png', 'rb') as photo:
                await bot.send_photo(chat_id=message.chat.id, photo=photo, caption=MESSAGES["captha"])
            state = dp.current_state(user=message.from_user.id)
            await state.update_data(captha=captcha_text)
            await state.set_state(StatesUsers.all()[0])

        else:
            if message.text == "@@":
                text = MESSAGES["start_3"] % message.from_user.username
            else:
                text = MESSAGES["start"] % message.from_user.username

            all_city_name = db.get_keyboard()
            for city_name in all_city_name:
                city_names = city_name[0]
                id_city = city_name[1]

                text += f"\n➖➖➖\n🏠 {city_names}\n[ Для выбора нажмите 👉 /city_{id_city} ]"

            await bot.send_message(text=text, chat_id=message.from_user.id)
            state = dp.current_state(user=message.from_user.id)
            await state.finish()

    # =================== ВЫБОР ПРОДУКТА ====================
    async def product_task(message: Message):
        id_city = message.text[6:]

        all_products = db.get_keyboard_products(id_city)
        if all_products:
            id_city = all_products[2]
            text = f"🏠 Город: <b>{all_products[1]}</b>\n➖\nВыберите товар:"
            all_products = all_products[0].split("|")
            for idx, products in enumerate(all_products):
                product = products.split("(")
                text += f"\n➖\n<b>🎁 {product[0]}\n💰 Цена: {product[1][:-1]}.</b>\n[ Для покупки нажмите 👉 /item_{id_city}_{idx} ]" \
                        f"\n[ Посмотреть отзывы о данном товаре 👉 /reviews_{id_city}_{idx} ]"
            text += "\n\nЧтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            await bot.send_message(text=text, chat_id=message.from_user.id)
        else:
            await bot.send_message(text=MESSAGES["not_city"] % "Город", chat_id=message.from_user.id)

    # ==================== ВЫБОР РАЙОНА =====================
    async def district_task(message: Message):
        try:
            id_city_item = message.text.split("_")
            all_info_products = db.get_keyboard_products(id_city_item[1])
            if all_info_products[3]:
                info_product = all_info_products[0].split("|")[int(id_city_item[2])].split("(")
                text = f"<b>🏠 Город: {all_info_products[1]}\n🎁 Товар: {info_product[0]}," \
                       f"\n💰 Цена: {info_product[1][:-1]}.</b>\n➖➖➖➖\nВыберите район:"
                for idx, district_info in enumerate(all_info_products[3].split("|")):
                    if id_city_item[2] == district_info[-2]:
                        text += f"\n➖➖➖➖\n🏃 Район: <b>{district_info[:-3]}</b>\n[Для выбора нажмите 👉 /district_{id_city_item[1]}_{id_city_item[2]}_{idx} ]"
                    # else:
                    #     text += "Товар закончился"
                text += "\n\nЧтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                await bot.send_message(text=text, chat_id=message.from_user.id)
            else:
                await bot.send_message(text=MESSAGES["not_city"] % "Продукт", chat_id=message.from_user.id)
        except:
            await bot.send_message(text=MESSAGES["not_city"] % "Продукт", chat_id=message.from_user.id)

    # ==================== ВЫБОР ОПЛАТЫ =====================
    async def input_byu_task(message: Message):
        try:
            id_city_item = message.text.split("_")
            all_info_products = db.get_keyboard_products(id_city_item[1])
            if all_info_products[3]:
                info_product = all_info_products[0].split("|")[int(id_city_item[2])].split("(")
                await bot.send_message(text=MESSAGES["buy_product"] % (
                all_info_products[1], all_info_products[3].split("|")[int(id_city_item[-1])][:-3],
                info_product[0], info_product[1][:-1]), chat_id=message.from_user.id)

                state = dp.current_state(user=message.from_user.id)
                await state.update_data(city=all_info_products[1])
                await state.update_data(district=all_info_products[3].split("|")[int(id_city_item[-1])][:-3])
                await state.update_data(name_product=info_product[0])
                await state.update_data(price_product=info_product[1][:-4])
                await state.set_state(StatesUsers.all()[7])

            else:
                await bot.send_message(text=MESSAGES["not_city"] % "Продукт", chat_id=message.from_user.id)
        except:
            await bot.send_message(text=MESSAGES["not_city"] % "Район", chat_id=message.from_user.id)

    # ================= ПРОЦЕСС ОПЛАТЫ ================
    async def buy_task(message: Message, state: FSMContext):
        data = await state.get_data()
        commission = db.get_all_info("COMMISSION")[0]
        price_rub = int(data["price_product"])
        number_order = random.randint(10000, 99999)
        number_comment = random.randint(100000, 999999)

        if message.text == "/buy1":
            dop_text = convert_rub_to_btc("bitcoin")
            count_pay = (int(price_rub) + int(price_rub)) / int(dop_text)
            num_pay = db.get_all_info("NUMBER_BTC")[0]
            try:
                num_pay = num_pay.split("|")
                num_pay = num_pay[randrange(len(num_pay))]
            except:
                num_pay = num_pay
            await bot.send_message(text=MESSAGES["buy_1_2"], chat_id=message.from_user.id)
            await bot.send_message(
                text=MESSAGES["buy_1"] % (data["city"], data["district"], data["name_product"], data["price_product"],
                                          f"{count_pay:.8f}", num_pay, number_order, number_comment), chat_id=message.from_user.id)
        elif message.text == "/buy2":
            dop_text = convert_rub_to_btc("litecoin")
            count_pay = (int(price_rub) + int(price_rub)) / int(dop_text)
            num_pay = db.get_all_info("NUMBER_LTC")[0]
            try:
                num_pay = num_pay.split("|")
                num_pay = num_pay[randrange(len(num_pay))]
            except:
                num_pay = num_pay
            await bot.send_message(
                text=MESSAGES["buy_11"] % (data["city"], data["district"], data["name_product"], data["price_product"],
                                          f"{count_pay:.8f}", num_pay, number_order, number_comment), chat_id=message.from_user.id)

        elif message.text == "/buy3":
            num_pay = db.get_all_info("NUMBER_CARD")[0]
            try:
                num_pay = num_pay.split("|")
                num_pay = num_pay[randrange(len(num_pay))]
            except:
                num_pay = num_pay
            count_pay = int(price_rub) + (int(price_rub) * commission / 100)
            await bot.send_message(
                text=MESSAGES["buy_2"] % (data["city"], data["district"], data["name_product"], data["price_product"],
                                          int(count_pay), num_pay, number_order, number_comment), chat_id=message.from_user.id)
        elif message.text == "/buy5" or message.text == "/buy4":
            await bot.send_message(text=MESSAGES["buy_4"], chat_id=message.from_user.id)
        elif message.text == "/buy6":
            await bot.send_message(text=MESSAGES["buy_5"], chat_id=message.from_user.id)

        await state.finish()

    # ===================================================
    # ================= ОТЗЫВЫ О ТОВАРЕ =================
    # ===================================================
    async def reviews_product_task(message: Message):
        id_product = message.text.split("_")
        all_info_products = db.get_keyboard_products(id_product[1])
        info_product = all_info_products[0].split("|")[int(id_product[2])].split("(")

        count_reviews = random.randint(1, 9)
        numbers = list(range(1, 31))
        random_reviews = random.sample(numbers, count_reviews)

        reviews_data = (datetime.now() - timedelta(days=random.randint(0, 3))).strftime("%d-%m-%Y")

        text = ""
        for ran_rew in random_reviews:
            text += MESSAGES[f"product_{ran_rew}"] % (info_product[0], reviews_data, "⭐️"*random.randint(4, 5)) + "\n\n➖➖➖\n\n"
        text += "Чтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
        await bot.send_message(text=text, chat_id=message.from_user.id)

    # ===================================================
    # ================ ПРОХОЖДЕНИЕ КАПЧИ ================
    # ===================================================
    async def captha_start(message: Message, state: FSMContext):
        data = await state.get_data()
        if message.text == data["captha"]:
            text = MESSAGES["start"] % message.from_user.username

            all_city_name = db.get_keyboard()
            for city_name in all_city_name:
                city_names = city_name[0]
                id_city = city_name[1]

                text += f"\n➖➖➖\n🏠 {city_names}\n[ Для выбора нажмите 👉 /city_{id_city} ]"
            await bot.send_message(text=text, chat_id=message.from_user.id)
            await state.finish()
        else:
            captcha_text = await generation_captha(message)
            with open(f'img/{message.from_user.id}.png', 'rb') as photo:
                await bot.send_photo(chat_id=message.chat.id, photo=photo, caption=MESSAGES["captha"])
            await state.update_data(captha=captcha_text)
            await state.set_state(StatesUsers.all()[0])

    # ===================================================
    # ================= ОСНОВНЫЕ КОМАНДЫ ================
    # ===================================================
    async def all_task(message: Message):
        await bot.send_message(text=MESSAGES[f"{message.text[1:]}"], chat_id=message.from_user.id)

    # ===================================================
    # ================== СПИСОК ОТЗЫВОВ =================
    # ===================================================
    async def reviews_task(message: Message):
        reviews_1_data = (datetime.now() - timedelta(days=2)).strftime("%d-%m-%Y")
        reviews_2_data = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")
        reviews_3_data = datetime.now().strftime("%d-%m-%Y")
        await bot.send_message(text=MESSAGES[f"{message.text[1:]}1"].replace("%s", reviews_1_data), chat_id=message.from_user.id)
        await bot.send_message(text=MESSAGES[f"{message.text[1:]}2"].replace("%s", reviews_2_data), chat_id=message.from_user.id)
        await bot.send_message(text=MESSAGES[f"{message.text[1:]}3"].replace("%s", reviews_3_data), chat_id=message.from_user.id)

    # ===================================================
    # ================= ПОПОЛНИТЬ БАЛАНС ================
    # ===================================================
    async def add_pay(message: Message):
        min_pay = db.get_all_info("MIN_BALANCE")[0]
        await bot.send_message(text=MESSAGES[f"{message.text[1:]}_1"], chat_id=message.from_user.id)

        if message.text == "/pay1":
            dop_text = convert_rub_to_btc("bitcoin")
            await bot.send_message(text=MESSAGES[f"{message.text[1:]}_2"] % (dop_text, min_pay), chat_id=message.from_user.id)
        elif message.text == "/pay5":
            dop_text = convert_rub_to_btc("litecoin")
            await bot.send_message(text=MESSAGES[f"{message.text[1:]}_2"] % (dop_text, min_pay), chat_id=message.from_user.id)
        elif message.text == "/pay2" or message.text == "/pay3":
            await bot.send_message(text=MESSAGES[f"{message.text[1:]}_2"] % min_pay, chat_id=message.from_user.id)

        state = dp.current_state(user=message.from_user.id)
        await state.update_data(what_pay=message.text)
        await state.update_data(min_p=min_pay)
        await state.set_state(StatesUsers.all()[1])

    # ================= СУММА ПОПОЛНЕНИЯ ================
    async def input_pay(message: Message, state: FSMContext):
        data = await state.get_data()
        if data["what_pay"] != "/pay4":
            if message.text.isnumeric():
                if int(message.text) >= int(data["min_p"]):
                    commission = db.get_all_info("COMMISSION")[0]
                    if data["what_pay"] == "/pay1":
                        dop_text = convert_rub_to_btc("bitcoin")
                        count_pay = (int(message.text) + int(message.text)) / int(dop_text)
                        num_pay = db.get_all_info("NUMBER_BTC")[0]
                        try:
                            num_pay = num_pay.split("|")
                            num_pay = num_pay[randrange(len(num_pay))]
                        except:
                            num_pay = num_pay
                        await bot.send_message(
                            text=MESSAGES[f"{data['what_pay'][1:]}_3"] % (f"{count_pay:.8f}", num_pay),
                            chat_id=message.from_user.id)
                    elif data["what_pay"] == "/pay5":
                        dop_text = convert_rub_to_btc("litecoin")
                        count_pay = (int(message.text) + int(message.text)) / int(dop_text)
                        num_pay = db.get_all_info("NUMBER_LTC")[0]
                        try:
                            num_pay = num_pay.split("|")
                            num_pay = num_pay[randrange(len(num_pay))]
                        except:
                            num_pay = num_pay
                        await bot.send_message(
                            text=MESSAGES[f"{data['what_pay'][1:]}_3"] % (f"{count_pay:.8f}", num_pay),
                            chat_id=message.from_user.id)

                    elif data["what_pay"] == "/pay2" or data["what_pay"] == "/pay3":
                        number_order = random.randint(10000000, 99999999)
                        count_pay = int(message.text) + int(int(message.text) * commission / 100)
                        if data["what_pay"] == "/pay2":
                            type_pay = "банковскую карту"
                            type_pay_db = "банковская карта"
                            what_number_pay = "банковской карты"
                            number_pay = "NUMBER_CARD"
                        else:
                            type_pay = "SIM"
                            type_pay_db = "SIM"
                            what_number_pay = "телефона"
                            number_pay = "NUMBER_SIM"

                        num_pay = db.get_all_info(f"{number_pay}")[0]
                        try:
                            num_pay = num_pay.split("|")
                            num_pay = num_pay[randrange(len(num_pay))]
                        except:
                            num_pay = num_pay
                        await bot.send_message(
                            text=MESSAGES[f"{data['what_pay'][1:]}_3"] % (type_pay, number_order, count_pay,
                                                                          what_number_pay, num_pay, message.text),
                            chat_id=message.from_user.id)
                        text_db = f"{number_order},{datetime.now().strftime('%y.%m.%d %H:%M')},{message.text},{count_pay},{num_pay},{type_pay_db},Пополнение баланса"
                        db.add_trans(message.from_user.id, text_db, "trans")
                    await state.finish()
                else:
                    await bot.send_message(
                        text=MESSAGES["min_count"] % (MESSAGES[f"{data['what_pay'][1:]}_what_pay"], data["min_p"]),
                        chat_id=message.from_user.id)
                    await state.set_state(StatesUsers.all()[1])
            else:
                await bot.send_message(text=MESSAGES["not_count"], chat_id=message.from_user.id)
                await state.finish()
        else:
            await bot.send_message(text=MESSAGES["not_coupon"], chat_id=message.from_user.id)
            await state.finish()

    # ===================================================
    # ============== СПИСОК ЗАЯВОК НА ОБМЕН =============
    # ===================================================
    async def trans_task(message: Message):
        info_trans = db.get_trans(message.from_user.id, "trans")[0]
        if info_trans:
            text = MESSAGES[f"{message.text[1:]}"]
            info_trans = info_trans.split("|")
            info_trans.reverse()
            for idx, trans in enumerate(info_trans):
                trans = trans.split(",")
                text += f"\n➖\n#⃣ Номер заявки: #{trans[0]}\n📆 Дата: {trans[1]}\n💶 К зачислению: {trans[2]}\n💷 К оплате: {trans[3]}\n" \
                        f"💳 Реквизиты: {trans[4]}\n💱 Тип оплаты: {trans[5]}\n💼 Тип процедуры: {trans[6]}"
                if idx == 9:
                    break
            text += "\n\nЧтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            await bot.send_message(text=text, chat_id=message.from_user.id)
        else:
            await bot.send_message(text=MESSAGES[f"{message.text[1:]}_non"], chat_id=message.from_user.id)

    # ===================================================
    # ================== ДОБАВИТЬ БОТА ==================
    # ===================================================
    async def addbot_task(message: Message):
        await bot.send_message(text=MESSAGES[f"{message.text[1:]}"], chat_id=message.from_user.id)
        state = dp.current_state(user=message.from_user.id)
        await state.set_state(StatesUsers.all()[2])

    # ================== ДОБАВИТЬ БОТА ==================
    async def input_token(message: Message, state: FSMContext):
        try:
            r = requests.get(f'https://api.telegram.org/bot{message.text}/getMe').json()["result"]["username"]
            all_token = db.get_bot_token()[0]
            try:
                token = all_token.split("|")
                if message.text in token:
                    await message.answer(MESSAGES["there_is_bot"])
                else:
                    db.add_trans(message.from_user.id, message.text, "my_bot")
                    db.add_admin(f"|{message.text}", "TOKEN")
                    # ЗАПУСК
                    await bot.send_message(text=MESSAGES["success_add_bot"] % r, chat_id=message.from_user.id)
                    time.sleep(2)
                    sys.exit()

            except Exception as ex:
                print(ex)
                db.add_trans(message.from_user.id, message.text, "my_bot")
                db.add_admin(f"|{message.text}", "TOKEN")
                # ЗАПУСК
                await bot.send_message(text=MESSAGES["success_add_bot"] % r, chat_id=message.from_user.id)
                time.sleep(2)
                sys.exit()

        except Exception as ex:
            print(ex)
            await bot.send_message(text=MESSAGES["error_add_bot"], chat_id=message.from_user.id)
        await state.finish()

    # ===================================================
    # =================== СПИСОК БОТОВ ==================
    # ===================================================
    async def mybots_task(message: Message):
        my_bot = db.get_trans(message.from_user.id, "my_bot")[0]
        if my_bot:
            my_bots = my_bot.split("|")
            text = MESSAGES["my_bot_1"]
            for idx, my_bot in enumerate(my_bots):
                username_my_bot = requests.get(f'https://api.telegram.org/bot{my_bot}/getMe').json()["result"][
                    "username"]
                text += f"\n#{idx + 1} 🤖 @{username_my_bot}"
            text += MESSAGES["my_bot_2"]
            await bot.send_message(text=text, chat_id=message.from_user.id)
        else:
            await bot.send_message(text=MESSAGES["not_my_bots"], chat_id=message.from_user.id)

    # ===================================================
    # ================== УДАЛЕНИЕ БОТА ==================
    # ===================================================
    async def removebot_task(message: Message):
        await bot.send_message(text=MESSAGES["removebot"], chat_id=message.from_user.id)
        state = dp.current_state(user=message.from_user.id)
        await state.set_state(StatesUsers.all()[6])

    # ============ ЗАПРОС ТОКЕНА ДЛЯ УДАЛЕНИЯ ===========
    async def input_token_removebot(message: Message, state: FSMContext):
        all_pid = db.get_trans(message.from_user.id, "my_bot")[0]
        try:
            all_pid = all_pid.split("|")
            if len(all_pid) >= int(message.text) > 0:
                my_token = db.get_trans(message.from_user.id, "my_bot")[0].split("|")[int(message.text) - 1]
                db.del_admin(my_token, "TOKEN")
                db.del_my_bot(my_token, "my_bot", message.from_user.id)
                await bot.send_message(text=MESSAGES["success_removebot"], chat_id=message.from_user.id)
                sys.exit()
            else:
                await bot.send_message(text=MESSAGES["not_removebot"], chat_id=message.from_user.id)
        except Exception as ex:
            print(ex)
            await bot.send_message(text=MESSAGES["not_removebot"], chat_id=message.from_user.id)
        await state.finish()

    # ===================================================
    # ================ СОЗДАТЬ ОБРАЩЕНИЕ ================
    # ===================================================
    async def exticket_task(message: Message):
        all_trans = db.get_trans(message.from_user.id, "trans")[0]
        if all_trans:
            await bot.send_message(text=MESSAGES["exticket"], chat_id=message.from_user.id)
            state = dp.current_state(user=message.from_user.id)
            await state.set_state(StatesUsers.all()[3])
        else:
            await bot.send_message(text=MESSAGES["not_exticket"], chat_id=message.from_user.id)

    # ================= ПОЛУЧЕНИЯ НОМЕРА ==================
    async def input_exticket(message: Message, state: FSMContext):
        all_trans = db.get_trans(message.from_user.id, "trans")[0]
        all_extickets = db.get_trans(message.from_user.id, "extickets")[0]
        all_trans = all_trans.split("|")
        test_check = True
        for trans in all_trans:
            trans = trans.split(",")
            if message.text in trans[0]:
                if all_extickets:
                    all_extickets = all_extickets.split("|")
                    for extickets in all_extickets:
                        extickets = extickets.split("////")
                        if message.text in extickets[0]:
                            test_check = False
                            await bot.send_message(text=MESSAGES["exticket_in"], chat_id=message.from_user.id)
                            await state.set_state(StatesUsers.all()[3])
                            break
                        else:
                            test_check = False
                            await bot.send_message(text=MESSAGES["success_exticket"], chat_id=message.from_user.id)
                            await state.update_data(number_exticket=message.text)
                            await state.set_state(StatesUsers.all()[4])
                            break
                else:
                    test_check = False
                    await bot.send_message(text=MESSAGES["success_exticket"], chat_id=message.from_user.id)
                    await state.update_data(number_exticket=message.text)
                    await state.set_state(StatesUsers.all()[4])
                    break
        if test_check:
            await bot.send_message(text=MESSAGES["error_exticket"], chat_id=message.from_user.id)
            await state.set_state(StatesUsers.all()[3])

    # ================= ПОЛУЧЕНИЯ ФОТО ===================
    async def input_photo_exticket(message: Message, state: FSMContext):
        if message.photo:
            await bot.send_message(text=MESSAGES["success_photo"], chat_id=message.from_user.id)
            await state.set_state(StatesUsers.all()[5])
        else:
            await bot.send_message(text=MESSAGES["not_photo"], chat_id=message.from_user.id)
            await state.set_state(StatesUsers.all()[4])

    # ================= СОХРАНЕНИЕ ЗАЯВКИ ===================
    async def save_exticket(message: Message, state: FSMContext):
        await bot.send_message(text=MESSAGES["exticket_send"], chat_id=message.from_user.id)
        data = await state.get_data()
        text = f"{data['number_exticket']}////{message.text}////{datetime.now().strftime('%y.%m.%d %H:%M')}"
        db.add_trans(message.from_user.id, text, "extickets")
        await state.finish()

    # ===================================================
    # ================= СПИСОК ОБРАЩЕНИЙ ================
    # ===================================================
    async def myextickets_task(message: Message):
        all_extickets = db.get_trans(message.from_user.id, "extickets")[0]
        if all_extickets:
            text = ""
            all_extickets = all_extickets.split("|")
            for extickets in all_extickets:
                extickets = extickets.split("////")
                text += f"<b>Обращение по зависшему платежу #{extickets[0]} </b>\n[ Для просмотра 👉 нажмите /myexticket_{extickets[0]} ]\n➖➖➖➖\n"
            text += "\nЧтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
            await bot.send_message(text=text, chat_id=message.from_user.id)
        else:
            await bot.send_message(text=MESSAGES["not_myexticket"], chat_id=message.from_user.id)

    # =================== МОЁ ОБРАЩЕНИЙ ==================
    async def myexticket_task(message: Message):
        num_ticket = message.text[12:]
        all_extickets = db.get_trans(message.from_user.id, "extickets")[0]
        if all_extickets:
            what = True
            all_extickets = all_extickets.split("|")
            for extickets in all_extickets:
                extickets = extickets.split("////")
                if num_ticket == extickets[0]:
                    what = False
                    text = f"<b>⚡️ Обращение по зависшему платежу #{num_ticket}\n➖➖➖\n[Вы]</b>\n{extickets[1]}\n➖➖➖\n" \
                           f"\n📆 Создан {extickets[2]}\nЧтобы вернуться в меню и начать сначала нажмите 👉 /start или @"
                    await bot.send_message(text=text, chat_id=message.from_user.id)
                    break
            if what:
                await bot.send_message(text=MESSAGES["not_myextickets"], chat_id=message.from_user.id)
        else:
            await bot.send_message(text=MESSAGES["not_myextickets"], chat_id=message.from_user.id)

    # ===================================================
    # =============== НЕИЗВЕСТНАЯ КОМАНДА ===============
    # ===================================================
    async def unknown_command(message: Message):
        if not db.user_exists(message.from_user.id):
            db.add_user(message.from_user.id, message.from_user.username)
            captcha_text = await generation_captha(bot)
            with open(f'img/{message.from_user.id}.png', 'rb') as photo:
                await bot.send_photo(chat_id=message.chat.id, photo=photo, caption=MESSAGES["captha"])
            state = dp.current_state(user=message.from_user.id)
            await state.update_data(captha=captcha_text)
            await state.set_state(StatesUsers.all()[2])

        else:
            text = MESSAGES["start"] % message.from_user.username

            all_city_name = db.get_keyboard()
            for city_name in all_city_name:
                city_names = city_name[0]
                id_city = city_name[1]

                text += f"\n➖➖➖\n🏠 {city_names}\n[ Для выбора нажмите 👉 /city_{id_city} ]"
            await bot.send_message(text=text, chat_id=message.from_user.id)
            state = dp.current_state(user=message.from_user.id)
            await state.finish()


    # СТАРТ
    dp.register_message_handler(start_command, lambda message: message.text == '/start' or message.text == '@' or message.text == '@@', state="*")
    dp.register_message_handler(captha_start, state=StatesUsers.STATE_0)

    # ВЫБОР ПРОДУКТА
    dp.register_message_handler(product_task, lambda message: "/city_" in message.text)
    # ВЫБОР РАЙОНА
    dp.register_message_handler(district_task, lambda message: "/item_" in message.text)
    # ВЫБОР ОПЛАТЫ
    dp.register_message_handler(input_byu_task, lambda message: "/district_" in message.text)
    dp.register_message_handler(buy_task, state=StatesUsers.STATE_7)

    # ОТЗЫВЫ О ТОВАРЕ
    dp.register_message_handler(reviews_product_task, lambda message: "/reviews_" in message.text)

    # ОСНОВНЫЕ КОМАНДЫ
    dp.register_message_handler(all_task, commands=BUTTON_TYPES["IZI_COMMANDS"])

    # ПОПОЛНИТЬ БАЛАНС
    dp.register_message_handler(add_pay, commands=["pay1", "pay2", "pay3", "pay4", "pay5"])
    dp.register_message_handler(input_pay, state=StatesUsers.STATE_1)

    # СПИСОК ЗАЯВОК НА ОБМЕН
    dp.register_message_handler(trans_task, commands="trans")

    # СПИСОК ОТЗЫВОВ
    dp.register_message_handler(reviews_task, commands="reviews")

    # ДОБАВИТЬ БОТА
    dp.register_message_handler(addbot_task, commands="addbot")
    dp.register_message_handler(input_token, state=StatesUsers.STATE_2)

    # СПИСОК БОТОВ
    dp.register_message_handler(mybots_task, commands="mybots")

    # УДАЛЕНИЕ БОТА
    dp.register_message_handler(removebot_task, commands="removebot")
    dp.register_message_handler(input_token_removebot, state=StatesUsers.STATE_6)

    # СОЗДАТЬ ОБРАЩЕНИЕ
    dp.register_message_handler(exticket_task, commands="exticket")
    dp.register_message_handler(input_exticket, state=StatesUsers.STATE_3)
    dp.register_message_handler(input_photo_exticket, content_types=["photo", "text"], state=StatesUsers.STATE_4)
    dp.register_message_handler(save_exticket, state=StatesUsers.STATE_5)

    # СПИСОК ОБРАЩЕНИЙ
    dp.register_message_handler(myextickets_task, commands="myextickets")
    dp.register_message_handler(myexticket_task, lambda message: "/myexticket" in message.text)

    # НЕИЗВЕСТНАЯ КОМАНДА
    dp.register_message_handler(unknown_command, content_types=["text"])

    event_loop.run_until_complete(start_bot(dp))


if __name__ == '__main__':
    pid = os.getpid()
    db.update_pid(pid)
    logging.basicConfig(format=u'%(filename)+13s [ LINE:%(lineno)-4s] %(levelname)-8s [%(asctime)s] %(message)s', level=logging.DEBUG)

    tokens = db.get_bot_token()[0].split("|")
    event_loop = asyncio.get_event_loop()

    for idx, token in enumerate(tokens):
        if idx != 0:
            try:
                bot_init(event_loop, token)
            except:
                ...

    event_loop.run_forever()
