import discord
import logging
import requests
from discord.ext import commands
# from events import Events
from registration_form import RegistrationForm
from user_stats import StatScraper
import asyncio
from data import db_session
from data.users import User
from data.regiments import Regiment
import json

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
db_name = "db/thunder_db.sqlite"
db_session.global_init(db_name)
TOKEN = ""


class Commands(commands.Cog):
    def __init__(self, bot_):
        self.bot = bot_

    @commands.command(name='test')
    async def lol(self, ctx, member: discord.Member = None):
        print(help(ctx))
        await ctx.send(ctx.author.roles)

    @commands.command(name='gore')
    async def gore(self, ctx, nickname: str):
        output_ch = filter(lambda chl: chl.id == 978238061446053975,
                           ctx.guild.channels).__next__()
        await output_ch.send(await self.bot.scraper.stats_display(nickname))

    @commands.command(name='rmrole')
    async def my_randint(self, ctx):
        role_guest = filter(lambda role: role.name == "Гость", ctx.author.guild.roles).__next__()
        await ctx.author.remove_roles(role_guest)

    @commands.command(name='stats')
    async def get_stats(self, ctx, user_id: int):
        await ctx.send("Ожидайте...")
        db_sess = db_session.create_session()
        user = db_sess.query(User).get(user_id)
        if not user:
            await ctx.send("Пользователь с таким id не зарегистрирован.")
            return
        self.bot.stats_display(user.nickname)
        await ctx.send(await self.bot.scraper.stats_display(user.nickname))


def init_config():
    file_config = open("config.json", "r")
    _config = json.loads(file_config.read())
    file_config.close()
    return config


def check_regiments(_config):
    regiments = _config["regiments"]
    db_sess = db_session.create_session()
    all_rgt_db = db_sess.query(Regiment.label).all()
    all_rgt_db = list(zip(*all_rgt_db))
    if all_rgt_db:
        all_rgt_db = all_rgt_db[0]
    # print(all_rgt_db)
    # print(regiments)
    for rgt in regiments:
        if not (rgt in all_rgt_db):
            db_sess.add(Regiment(label=rgt))
    db_sess.commit()


if __name__ == "__main__":
    config = init_config()
    check_regiments(config)

    intents = discord.Intents.default()
    intents.members = True
    intents.guilds = True
    intents.message_content = True
    intents.messages = True

    bot = commands.Bot(command_prefix=config["command_prefix"], intents=intents)
    bot.config = config
    bot.add_cog(Commands(bot))
    bot.add_cog(RegistrationForm(bot))
    bot.scraper = StatScraper()
    bot.run(bot.config["bot_token"])
