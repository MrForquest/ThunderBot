import discord
import logging
import requests
from discord.ext import commands, tasks
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
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
handler.setFormatter(formatter)
file_handler = logging.FileHandler("log.txt")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(file_handler)

db_name = "db/thunder_db.db"
db_session.global_init(db_name)

TOKEN = ""


def init_config():
    file_config = open("config.json", "r")
    _config = json.loads(file_config.read())
    file_config.close()
    return _config


config = init_config()


class Commands(commands.Cog):
    def __init__(self, bot_):
        self.bot = bot_
        self.update_active_forum.start()

    @commands.command(name='ping')
    async def lol(self, ctx, member: discord.Member = None):
        await ctx.send("pong!")

    @commands.command(name='findme')
    async def find_me(self, ctx, member: discord.Member = None):
        await ctx.reply(ctx.channel)
        await ctx.reply(ctx.channel.id)

    @commands.command(name='forum')
    async def forum_threads(self, ctx):
        forum = self.bot.get_channel(1022934245016092763)
        for thread in forum.threads:
            print(forum.get_thread(thread.id))

    @commands.command(name='stats')
    async def get_stats(self, ctx, member: discord.Member):
        await ctx.send("Ожидайте...")
        db_sess = db_session.create_session()
        user = db_sess.query(User).get(member.id)
        if not user:
            await ctx.send("Пользователь с таким id не зарегистрирован.")
            return
        result = await self.bot.scraper.get_stats(user.nickname)
        if not (result.get("error", 200) == 200):
            await ctx.send(f"Ошибка {result['error']}. Вероятно сайты с информаицей не доступны.")
            return
        text = result["display"]
        await ctx.send(text)

    @commands.command(name='deluser')
    @commands.has_any_role(config["roles"]["allianceOfficerRole"]["roleId"],
                           config["roles"]["careerOfficer"]["roleId"],
                           config["roles"]["technoAdmin"]["roleId"],
                           config["roles"]["officerStudentRole"]["roleId"])
    async def delete_user(self, ctx, member: discord.Member, param=None):
        db_sess = db_session.create_session()
        user = db_sess.query(User).get(member.id)
        if user:
            db_sess.delete(user)
            db_sess.commit()
            user = member
            if not (param is None):
                if param == "-c":
                    await self.clear_roles(ctx, member)
            await ctx.send(f"Пользователь {user.mention} удалён из БД")
        else:
            await ctx.send(f"Пользователь c таким id не найден.")

    @commands.command(name='clearroles')
    @commands.has_any_role(config["roles"]["allianceOfficerRole"]["roleId"],
                           config["roles"]["careerOfficer"]["roleId"],
                           config["roles"]["technoAdmin"]["roleId"])
    async def clear_roles(self, ctx, member: discord.Member):
        user = member
        reserv = ctx.guild.get_role(self.bot.config["roles"]["reservRole"]["roleId"])
        await user.edit(roles=[reserv])
        await ctx.send(f"Роли пользователя {user.mention} очищены.")

    @commands.command(name='cleardb')
    @commands.has_any_role(config["roles"]["adminRole"]["roleId"])
    async def clear_db(self, ctx):
        db_sess = db_session.create_session()
        db_sess.query(User).delete()
        db_sess.commit()
        await ctx.send(f"База данных полностью очищена.")

    @commands.command(name='help')
    async def get_help(self, ctx):
        cmd_pref = self.bot.config['command_prefix']
        text = (f"> **Список команд**\n> Используйте {cmd_pref} в качестве префикса для команд\n"
                f"> `{cmd_pref}reg`: Вызов собственной регистрации\n"
                f"> `{cmd_pref}stats упоминание_пользователя`: Вывод статистики пользователя\n"
                f"> `{cmd_pref}clearroles упоминание_пользователя`: Очищает все роли и добавляет роль резерв\n"
                f"> `{cmd_pref}deluser упоминание_пользователя`: Удаление пользователя из БД\n"
                f"> `{cmd_pref}deluser упоминание_пользователя -c`: То же что deluser и clearroles одновременно.\n"
                f"> `{cmd_pref}cleardb`: Очищает всю БД. Использовать в САМЫХ КРАЙНИХ СЛУЧАЯХ!")
        await ctx.reply(text)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == member.id).first()
        if not (user is None):
            db_sess.delete(user)
            db_sess.commit()

    @tasks.loop(hours=24 * 5)
    async def update_active_forum(self):
        if not self.bot.is_ready():
            return
        guild = self.bot.get_guild(self.bot.config["guild"])
        forum = guild.get_channel(1022934245016092763)

        thread_ids = [rgt["channel1Id"] for rgt in self.bot.config["registration"]["regiments"]]
        update_msgs = list()
        for thread_id in thread_ids:
            thread = forum.get_thread(thread_id)
            if not (thread is None):
                msg = await thread.send("Обновление активности!")
                update_msgs.append(msg)
        for msg in update_msgs:
            await msg.delete()

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(self.bot.config["guild"])
        channel = guild.get_channel(self.bot.config["channels"]["botStatus"])
        await channel.send('Бот работает. Готов к труду и обороне!')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            text = "У вас должна быть одна из следующих ролей:\n"
            names = list()
            for role_id in error.missing_roles:
                role = ctx.guild.get_role(role_id)
                names.append(f"`{role.name}`")
            text += ", ".join(names)
            await ctx.reply(text)
        else:
            raise error


if __name__ == "__main__":
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
