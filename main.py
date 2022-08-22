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

    @commands.command(name='addrole')
    async def my_randint(self, ctx):
        role_guest = filter(lambda role: role.name == "Гость", ctx.author.guild.roles).__next__()
        await ctx.author.add_roles(role_guest)

    @commands.command(name='rmrole')
    async def my_randint(self, ctx):
        role_guest = filter(lambda role: role.name == "Гость", ctx.author.guild.roles).__next__()
        await ctx.author.remove_roles(role_guest)

    @commands.command(name='ct')
    async def create_thread(self, ctx):
        channel = filter(lambda ch: ch.name == "test", ctx.guild.text_channels).__next__()
        thread = await channel.create_thread(name=f"Регистрация {ctx.author.name}",
                                             type=discord.ChannelType.public_thread)
        await thread.send(f"{ctx.author.mention}, регистрация будет проходить в этой ветке.")


def init_token():
    file_config = open("config.json", "r")
    config = json.loads(file_config.read())
    token = config["bot_token"]
    file_config.close()
    return token


def check_regiments():
    file_config = open("config.json", "r")
    config = json.loads(file_config.read())
    regiments = config["regiments"]
    file_config.close()
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
    check_regiments()
    TOKEN = init_token()

    intents = discord.Intents.default()
    intents.members = True
    intents.guilds = True
    intents.message_content = True
    intents.messages = True

    bot = commands.Bot(command_prefix='!', intents=intents)
    bot.add_cog(Commands(bot))
    bot.add_cog(RegistrationForm(bot))
    bot.scraper = StatScraper()
    bot.run(TOKEN)
