from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import asyncio
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests


# from pyvirtualdisplay import Display

# display = Display(visible=0, size=(60, 40))
# display.start()


class AsyncWebDriverWait(WebDriverWait):
    async def async_until(self, method, message: str = ""):
        screen = None
        stacktrace = None
        end_time = time.monotonic() + self._timeout
        while True:
            try:
                value = method(self._driver)
                if value:
                    return value
            except self._ignored_exceptions as exc:
                screen = getattr(exc, 'screen', None)
                stacktrace = getattr(exc, 'stacktrace', None)
            await asyncio.sleep(self._poll)
            if time.monotonic() > end_time:
                break
        raise TimeoutException(message, screen, stacktrace)


class StatScraper:
    def __init__(self):
        pass
        # options = Options()
        # options.add_argument('--disable-infobars')
        # options.add_argument('--disable-dev-shm-usage')
        # options.add_argument('--disable-browser-side-navigation')
        # options.add_argument("--remote-debugging-port=9222")
        # options.add_argument('--ignore-certificate-errors')
        # options.add_argument('--ignore-ssl-errors')
        # options.add_argument('--disable-gpu')
        # options.add_argument("--log-level=3")
        # options.add_argument('--disable-features=VizDisplayCompositor')
        # options.add_argument('--no-sandbox')
        # driver = uc.Chrome(options=options,
        #                    driver_executable_path="/usr/lib/chromium-browser/chromedriver")
        # self.driver = driver
        # self.queue = list()
        # self.stuff_lock_official = asyncio.Lock()
        # self.stuff_lock_thundeskill = asyncio.Lock()

    def parse_element(self, element):
        table = BeautifulSoup(element.get_attribute('innerHTML'), "html.parser")
        stats = list()
        for col in table.select("ul"):
            stats.append(list())
            for row in col.select("li"):
                stats[-1].append(row.text)
        new_stats = list()
        for i in range(len(stats[0])):
            new_stats.append(list())
            for j in range(len(stats)):
                new_stats[-1].append(stats[j][i])
        return new_stats

    async def get_user_stats_official(self, username, delay=10):
        print(username, "OF start")
        # username = "UN1Y_SATAN1ST"
        # https://warthunder.ru/ru/community/claninfo/War%20Clown%20Association для ЛПР
        async with self.stuff_lock_official:
            url = f'https://warthunder.ru/ru/community/userinfo/?nick={username}'
            self.driver.get(url)
            self.driver.maximize_window()
            try:
                element = await AsyncWebDriverWait(self.driver, delay).async_until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".user-stat__list-row--with-head")))
            except TimeoutException:
                print(username, "OF Error")
                return {"error": 404}
            info = self.parse_element(element)
            winrate = info[3][2]
            deaths = int(info[4][2].replace(",", "")) if info[4][2] != "N/A" else 0
            air_kills = int(info[7][2].replace(",", "")) if info[7][2] != "N/A" else 0
            earth_kills = int(info[8][2].replace(",", "")) if info[8][2] != "N/A" else 0
            water_kills = int(info[9][2].replace(",", "")) if info[9][2] != "N/A" else 0
            kills = (air_kills + earth_kills + water_kills)
            kd = str(round(kills / deaths, 2)) if deaths != 0 else "None"
            res = {"kd": kd, "winrate": winrate, "source": "wro", "error": 200}
            res["display"] = (f"`Игрок: {username}`\n"
                              f"`Винрейт(РБ): {res['winrate']}`\n"
                              f"`КД(РБ): {res['kd']}`")
            return res

    async def get_user_stats_thunderskill(self, username, delay=10):
        async with self.stuff_lock_thundeskill:
            print(username, "TS start")
            base_url = "https://thunderskill.com/ru/stat/"
            url = base_url + username + "/export/json"
            headers = dict()
            headers[
                'User-Agent'] = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0"
            try:
                req = requests.get(url, headers=headers, timeout=7)
                if req.status_code != 200:
                    print(username, f"TS Error {req.status_code}")
                    return {"error": req.status_code}
                stats = req.json()['stats']['r']
                stats["source"] = "ts"
                stats["display"] = (f"`Игрок: {username}`\n"
                                    f"`КПД(РБ): {stats['kpd']}`\n"
                                    f"`КД(РБ): {stats['kd']}`")
                print(username, "TS start")
                return stats
            except requests.exceptions.Timeout:
                print(username, "TS Error")
                return {"error": 502}

    async def get_stats(self, username):
        return {"error":404}
        stats = await self.get_user_stats_official(username)
        if stats.get("error", 200) in range(400, 505):
            stats = await self.get_user_stats_thunderskill(username)

        return stats
