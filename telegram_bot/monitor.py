import subprocess

if __name__ == '__main__':
    while True:
        try:
            subprocess.run(["/home/str/Tg_magaz2/.venv/bin/python", "/home/str/Tg_magaz2/start_all_bot.py"])
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Ошибка: {e}")
