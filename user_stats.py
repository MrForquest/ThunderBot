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


# если будет rasberry PI, то сделать pyvirtual Display
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
        options = Options()
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-browser-side-navigation')
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--disable-gpu')
        options.add_argument("--log-level=3")
        driver = uc.Chrome(options=options)
        self.driver = driver
        self.queue = list()
        self.stuff_lock_official = asyncio.Lock()
        self.stuff_lock_thundeskill = asyncio.Lock()

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
                return {"error": 404}
            info = self.parse_element(element)
            winrate = info[3][2]
            deaths = int(info[4][2]) if info[4][2] != "N/A" else 0
            air_kills = int(info[7][2]) if info[7][2] != "N/A" else 0
            earth_kills = int(info[8][2]) if info[8][2] != "N/A" else 0
            water_kills = int(info[9][2]) if info[9][2] != "N/A" else 0
            kills = (air_kills + earth_kills + water_kills)
            kd = str(round(kills / deaths)) if deaths != 0 else "None"
            res = {"kd": kd, "winrate": winrate, "source": "wro"}
            return res

    async def get_user_stats_thunderskill(self, username, delay=10):
        async with self.stuff_lock_thundeskill:
            base_url = "https://thunderskill.com/ru/stat/"
            url = "https://thunderskill.com/ru/stat/" + username + "/export/json"
            headers = dict()
            headers[
                'User-Agent'] = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0"
            req = requests.get(url, headers=headers)
            if req.status_code != 200:
                return {"error": req.status_code}
            stats = req.json()
            stats["source"] = "ts"
            return stats

    async def get_stats(self, username):
        stats = await self.get_user_stats_thunderskill(username)
        if stats.get("error", 200) == 503:
            stats = await self.get_user_stats_official(username)

        return stats

    async def stats_display(self, username):
        stats = (await self.get_user_stats_thunderskill(username))
        if not stats:
            return "Нет доступа к Thunder Skill"
        stats = stats["stats"]["r"]

        return (f"`Игрок: {username}`\n"
                f"`КПД(РБ): {stats['kpd']}`\n"
                f"`КД(РБ): {stats['kd']}`")
