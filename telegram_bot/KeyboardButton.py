from aiogram.types import BotCommand

# ================= КОМАНДНЫЕ КНОПКИ =================
start_command = BotCommand("start", "Главная страница") # ТУТ

poll_command = BotCommand("poll", "Голосования") # ✔️
ref_command = BotCommand("ref", "Реферальная система") # ✔️
balance_command = BotCommand("balance", "Просмотр баланса") # ✔️
check_command = BotCommand("check", "Проверка заказа") # ✔️
help_command = BotCommand("help", "Полчить помощь") # ✔️
connect_command = BotCommand("connect", "Информация о тикетах") # ✔️
reviews_command = BotCommand("reviews", "Список отзывов") # ✔️
addreview_command = BotCommand("addreview", "Добавить отзыв") # ✔️
history_command = BotCommand("history", "История пополнения и расходов") # ✔️
lastorder_command = BotCommand("lastorder", "Просмотр информации о последнем заказе") # ✔️
pay_command = BotCommand("pay", "Пополнить баланс") # ✔️
trans_command = BotCommand("trans", "Список заявок на обмен") # ✔️
issue_command = BotCommand("issue", "Создать заявку на перезаклад") # ✔️
myissues_command = BotCommand("myissues", "Список ваших заявок на перезаклад") # ✔️
exticket_command = BotCommand("exticket", "Создать Обращение по зависшему платежу") # ✔️
myexticket_command = BotCommand("myextickets", "Список Ваших обращений по зависшем платежам") # ✔️
mybots_command = BotCommand("mybots", "Список Ваших персональных ботов") # ️✔️
addbot_command = BotCommand("addbot", "Добавить персонального бота") # ✔️
removebot_command = BotCommand("removebot", "Удаление персонального бота") # ✔️


BUTTON_TYPES = {
    "ALL_COMMANDS": [start_command, poll_command, ref_command, balance_command, check_command, help_command, connect_command,
                     reviews_command, addreview_command, history_command, lastorder_command, pay_command,
                     trans_command, issue_command, myissues_command, exticket_command,
                     myexticket_command, mybots_command, addbot_command, removebot_command,],
    "IZI_COMMANDS": ["poll", "ref", "balance", "check", "help", "connect", "addreview", "history", "lastorder", "issue",
                     "myissues", "pay",]
}
