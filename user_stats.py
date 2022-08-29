from bs4 import BeautifulSoup
import time
import asyncio
import requests
from data import db_session
from data.users import User


class StatScraper:
    def __init__(self):
        self.stuff_lock = asyncio.Lock()

    async def get_user_stats_thunderskill(self, username, delay=10):
        async with self.stuff_lock:
            base_url = "https://thunderskill.com/ru/stat/"
            url = "https://thunderskill.com/ru/stat/" + username + "/export/json"
            headers = dict()
            headers[
                'User-Agent'] = "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0"
            req = requests.get(url, headers=headers)
            if req.status_code != 200:
                return False
            stats = req.json()
            return stats

    async def stats_display(self, username):
        stats = (await self.get_user_stats_thunderskill(username))
        stats = stats["stats"]["r"]

        return (f"`Игрок: {username}`\n"
                f"`КПД(РБ): {stats['kpd']}`\n"
                f"`КД(РБ): {stats['kd']}`")
