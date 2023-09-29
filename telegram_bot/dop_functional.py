import requests
import random
from captcha.image import ImageCaptcha


# ===================================================
# =============== ПОЛУЧЕНИЕ КУРСА BTC ===============
# ===================================================
def convert_rub_to_btc(coin):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": f"{coin}",
            "vs_currencies": "rub"
        }

        response = requests.get(url, params=params, verify=False).json()[coin]["rub"]
        return response
    except Exception as ex:
        print(ex)
        return "Не удалось получить курс обмена"


# ===================================================
# ================== СОЗДАНИЕ КАПЧИ =================
# ===================================================
async def generation_captha(message):
    image = ImageCaptcha(width=250, height=100)

    random_numbers = []
    for _ in range(5):
        random_number = random.randint(0, 9)
        random_numbers.append(str(random_number))
    captcha_text = ''.join(random_numbers)

    image.write(captcha_text, f'img/{message.from_user.id}.png')
    return captcha_text
