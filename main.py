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

    @commands.command(name='stats')
    async def get_stats(self, ctx, user_id: int):
        await ctx.send("Ожидайте...")
        db_sess = db_session.create_session()
        user = db_sess.query(User).get(user_id)
        if not user:
            await ctx.send("Пользователь с таким id не зарегистрирован.")
            return
        await ctx.send(await self.bot.scraper.stats_display(user.nickname))

    @commands.command(name='deluser')
    async def get_stats(self, ctx, user_id: int):
        db_sess = db_session.create_session()
        user = db_sess.query(User).get(user_id)
        if user:
            db_sess.delete(user)
            db_sess.commit()
            user = discord.utils.get(bot.get_all_members(), id=user_id)
            await ctx.send(f"Пользователь {user.mention} удалён из БД")
        else:
            await ctx.send(f"Пользователь c таким id не найден.")

    @commands.command(name='help')
    async def get_help(self, ctx):
        text = ("> **Список команд**\n> Используйте ! в качестве префикса для команд\n"
                "> `!reg`: Вызов собственной регистрации\n"
                "> `!deluser id_пользователя`: Удаление пользователя из БД\n"
                "> `!stats id_пользователя`: Вывод статистики пользователя")
        await ctx.reply(text)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == member.id).first()
        if not (user is None):
            db_sess.delete(user)
            db_sess.commit()


def init_config():
    file_config = open("config.json", "r")
    _config = json.loads(file_config.read())
    file_config.close()
    return _config


if __name__ == "__main__":
    config = init_config()
    intents = discord.Intents.default()
    intents.members = True
    intents.guilds = True
    intents.message_content = True
    intents.messages = True

    bot = commands.Bot(command_prefix=config["command_prefix"], intents=intents)
    bot.config = config
    bot.remove_command('help')
    bot.add_cog(Commands(bot))
    bot.add_cog(RegistrationForm(bot))
    bot.scraper = StatScraper()
    bot.run(bot.config["bot_token"])
