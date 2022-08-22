import discord
import logging
import requests
from discord.ext import commands
import asyncio
from data import db_session
from data.users import User
from data.regiments import Regiment
import sqlalchemy


class RegistrationForm(commands.Cog):
    registr_table = dict()

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = filter(lambda ch: ch.name == "test", member.guild.text_channels).__next__()
        db_sess = db_session.create_session()
        user_db = db_sess.query(User.id).filter(member.id == User.id).first()
        if user_db:
            await channel.send("Пользователь уже зарегистрирован")
            return

        role_guest = filter(lambda role: role.name == "Гость", member.guild.roles).__next__()
        try:
            await member.add_roles(role_guest)
        except discord.errors.Forbidden:
            await channel.send(
                f"Не удалось присвоить роль гостя человеку {member.mention}\n"
                "Похоже, что этот человек довольно важный.")
        thread = await channel.create_thread(name=f"Регистрация {member.name}",
                                             type=discord.ChannelType.public_thread)
        await thread.send(f"{member.mention}, ваша регистрация будет проходить в этой ветке.")
        self.registr_table[member.id] = dict()
        self.registr_table[member.id]["stage"] = 0
        self.registr_table[member.id]["thread"] = thread
        print(member.name)

        await self.registration(member)
        # thread = filter(lambda th: th.name == "регр", member.guild.threads).__next__()

    @commands.Cog.listener()
    async def on_message_1212313(self, message):
        if message.author != self.bot.user:
            # message.author.roles[1].members
            role_guest = filter(lambda role: role.name == "Гость", message.guild.roles).__next__()
            await self.registration(message.author)

    @commands.command(name='reg')
    async def lol(self, ctx):
        # await self.registration(ctx.message.author)
        await self.on_member_join(ctx.message.author)

    async def stop_registration(self, user):
        await self.registr_table[user.id]["thread"].delete()
        self.registr_table.pop(user.id)

    async def try_timeout(self, user, func, args, expected_exc=(asyncio.TimeoutError,)):
        try:
            return await func(**args)
        except expected_exc:
            await self.registr_table[user.id]["thread"].send(
                'Время ожидания вышло. Регситрация отменена.')
            await self.stop_registration(user)
            return

    async def registration(self, user):
        rules = "ПРАВИЛА"
        if self.registr_table[user.id]["stage"] == 0:
            msg = await self.registr_table[user.id]["thread"].send(
                f"1. Ознакомьтесь с правилами сообщества:\n"
                f"{rules}\nЕсли Вы согласны с этими правилами нажмите на ✅, иначе на ❌")
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check0(reaction_f, user_react):
                if user_react.id == user.id:
                    if reaction_f.message.channel.id == self.registr_table[user_react.id][
                        "thread"].id:
                        return str(reaction_f.emoji) in ['✅', '❌']

            params = {"event": "reaction_add", "timeout": 1 * 60 * 60, "check": check0}
            reaction, user_ = await self.try_timeout(user, self.bot.wait_for, params)
            await msg.channel.send(reaction)
            await msg.clear_reactions()
            if reaction.emoji == "❌":
                await msg.channel.send("Регистрация отменена.")
                await asyncio.sleep(3)
                await self.stop_registration(user)
                return

            self.registr_table[user.id]["stage"] += 1
            await self.registration(user)
            return

        elif self.registr_table[user.id]["stage"] == 1:
            await self.registr_table[user.id]["thread"].send(
                "2. Напишите ваше настоящие имя:")

            def check1(msg_f):
                if msg_f.author.id == user.id:
                    if msg_f.channel.id == self.registr_table[msg_f.author.id]["thread"].id:
                        return self.registr_table[msg_f.author.id]["stage"] == 1
                return False

            params = {"event": "message", "timeout": 1 * 5 * 60, "check": check1}
            real_name = await self.try_timeout(user, self.bot.wait_for, params)
            real_name = real_name.content
            self.registr_table[user.id]["real_name"] = real_name
            self.registr_table[user.id]["stage"] += 1
            await self.registration(user)
            return

        elif self.registr_table[user.id]["stage"] == 2:
            await self.registr_table[user.id]["thread"].send(
                "3. Напишите ваш возраст:")

            def check1(msg_f):
                if msg_f.author.id == user.id:
                    if msg_f.channel.id == self.registr_table[msg_f.author.id]["thread"].id:
                        return self.registr_table[msg_f.author.id]["stage"] == 2
                return False

            params = {"event": "message", "timeout": 1 * 5 * 60, "check": check1}
            age = await self.try_timeout(user, self.bot.wait_for, params)
            try:
                age = int(age.content)
                self.registr_table[user.id]["age"] = age
                self.registr_table[user.id]["stage"] += 1
                await self.registration(user)
                return
            except ValueError:
                self.registr_table[user.id]["num_att-2"] = self.registr_table[user.id].get(
                    "num_att-2",
                    0) + 1
                if self.registr_table[user.id]["num_att-2"] == 3:
                    await self.registr_table[user.id]["thread"].send(
                        "Вы использовали 3 попытки. Просим вас пройти регистрацию через офицера.")
                else:
                    await self.registr_table[user.id]["thread"].send(
                        "Неправильный формат ввода.\nПопробуйте ещё раз.")
                    await self.registration(user)
                    return

        elif self.registr_table[user.id]["stage"] == 3:
            await self.registr_table[user.id]["thread"].send(
                "4. Напишите ваш часовой пояс в формате: `UTC+?` или `UTC-?`\n   "
                "где `?` - это сдвиг по времени относительно Гринвича.\n   "
                "(Для Москвы `UTC+3`)"
            )

            def check2(msg_f):
                if msg_f.author.id == user.id:
                    if msg_f.channel.id == self.registr_table[msg_f.author.id]["thread"].id:
                        return self.registr_table[msg_f.author.id]["stage"] == 3
                return False

            params = {"event": "message", "timeout": 1 * 5 * 60, "check": check2}
            time_zone = await self.try_timeout(user, self.bot.wait_for, params)
            try:
                time_zone = int(time_zone.content.lower().replace("utc", ""))
                self.registr_table[user.id]["time_zone"] = time_zone
                self.registr_table[user.id]["stage"] += 1
                await self.registration(user)
                return
            except ValueError:
                self.registr_table[user.id]["num_att0"] = self.registr_table[user.id].get("num_att0",
                                                                                          0) + 1
                if self.registr_table[user.id]["num_att0"] == 3:
                    await self.registr_table[user.id]["thread"].send(
                        "Вы использовали 3 попытки. Просим вас пройти регистрацию через офицера.")
                else:
                    await self.registr_table[user.id]["thread"].send(
                        "Неправильный формат ввода.\nПопробуйте ещё раз.")
                    await self.registration(user)
                    return

        elif self.registr_table[user.id]["stage"] == 4:
            await self.registr_table[user.id]["thread"].send(
                "5. Напишите ваш ник в игре War Thunder:")

            def check3(msg_f):
                if msg_f.author.id == user.id:
                    if msg_f.channel.id == self.registr_table[msg_f.author.id]["thread"].id:
                        return self.registr_table[msg_f.author.id]["stage"] == 4
                return False

            params = {"event": "message", "timeout": 24 * 60 * 60, "check": check3}
            msg_name = await self.try_timeout(user, self.bot.wait_for, params)
            wt_name = msg_name.content
            await self.registr_table[user.id]["thread"].send("Проверка займёт не больше минуты")
            stats = await self.bot.scraper.get_user_stats_thunderskill(wt_name)
            if not stats:
                await self.registr_table[user.id]["thread"].send(
                    "Не удалось получить информацию об игроке с таким ником.\n"
                    "Попробуйте ещё раз.")
                self.registr_table[user.id]["num_att"] = self.registr_table[user.id].get("num_att",
                                                                                         0) + 1
                if self.registr_table[user.id]["num_att"] == 3:
                    await self.registr_table[user.id]["thread"].send(
                        "Вы использовали 3 попытки. Просим вас пройти регистрацию через офицера.")
                else:
                    await self.registration(user)
                    return
            else:
                print(stats)
                self.registr_table[user.id]["nickname"] = wt_name
                await self.registr_table[user.id]["thread"].send("Отлично!")
                await self.registr_table[user.id]["thread"].send("⠀")
                db_sess = db_session.create_session()
                user_db = User(id=user.id,
                               real_name=self.registr_table[user.id]["real_name"],
                               nickname=self.registr_table[user.id]["nickname"],
                               age=self.registr_table[user.id]["age"],
                               time_zone=self.registr_table[user.id]["time_zone"]
                               )
                try:
                    db_sess.add(user_db)
                    db_sess.commit()
                except sqlalchemy.exc.IntegrityError:
                    self.registr_table[user.id]["thread"].send(
                        "Похоже, что вы уже зарегистрированы.")
                    await asyncio.sleep(3)
                    await self.stop_registration(user)
                    return
                try:
                    await user.edit(nick=f"<{self.registr_table[user.id]['nickname']}> "
                                         f"{self.registr_table[user.id]['real_name']}")
                except discord.errors.Forbidden:
                    await self.registr_table[user.id]["thread"].send(
                        "По всей видимости вы очень высокопоставленный человек на этом сервере.\n"
                        "Поэтому просим вас самостоятельно поменять ваш никнейм на сервере на формат:\n"
                        "`<ник_в_War_Thunder> Настоящие_имя`")
                self.registr_table[user.id]["stage"] += 1
                await self.registration(user)
                return
        elif self.registr_table[user.id]["stage"] == 5:
            msg = await self.registr_table[user.id]["thread"].send(
                "Регистрация почти закончена.\n"
                "6. Вы желаете вступить в полк?"
            )
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check5(reaction_f, user_react):
                if user_react.id == user.id:
                    if reaction_f.message.channel.id == self.registr_table[user_react.id][
                        "thread"].id:
                        return str(reaction_f.emoji) in ['✅', '❌']

            params = {"event": "reaction_add", "timeout": 1 * 60 * 60, "check": check5}
            reaction, user_ = await self.try_timeout(user, self.bot.wait_for, params)
            await msg.channel.send(reaction)
            await msg.clear_reactions()
            if reaction.emoji == "❌":
                await self.registr_table[user.id]["thread"].send(
                    "Поговорите, пожалуйста, с офицером насчёт ваших целей на этом сервере.")
                return
            else:
                self.registr_table[user.id]["stage"] += 1
                await self.registration(user)
                return

        elif self.registr_table[user.id]["stage"] == 6:
            msg = await self.registr_table[user.id]["thread"].send(
                "7. Если вы готовы регулярно участвоать в полковых боях, то предлагаем вам вступить в\n"
                "   полк **WarCA**.\n"
                "   Вы желаете вступить в полк **WarCA**?"
            )
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check4(reaction_f, user_react):
                if user_react.id == user.id:
                    if reaction_f.message.channel.id == self.registr_table[user_react.id][
                        "thread"].id:
                        return str(reaction_f.emoji) in ['✅', '❌']

            params = {"event": "reaction_add", "timeout": 1 * 60 * 60, "check": check4}
            reaction, user_ = await self.try_timeout(user, self.bot.wait_for, params)
            await msg.channel.send(reaction)
            await msg.clear_reactions()
            if reaction.emoji == "❌":
                self.registr_table[user.id]["stage"] += 1
                await self.registration(user)
                return
            else:
                role_guest = filter(lambda role: role.name == "Гость", user.guild.roles).__next__()
                role_rgt = filter(lambda role: role.name == "WarCA", user.guild.roles).__next__()
                try:
                    await user.remove_roles(role_guest)
                    await user.add_roles(role_rgt)
                except discord.errors.Forbidden:
                    await  self.registr_table[user.id]["thread"].send(
                        "Похоже вы очень важный человек на этом сервере,\n"
                        "поэтому не получаестся присвоить вам роли:\n"
                        f"`{role_rgt}`"
                    )
                db_sess = db_session.create_session()
                user_db = db_sess.query(User).filter(User.id == user.id).first()
                rgt_id = db_sess.query(Regiment.id).filter(Regiment.label == "WarCA").first()[0]
                user_db.rgt_id = rgt_id
                db_sess.commit()
                await self.registr_table[user.id]["thread"].send("Добро пожаловать в **WarCA**!")
                await asyncio.sleep(4)
                await self.stop_registration(user)
                return

        elif self.registr_table[user.id]["stage"] == 7:
            db_sess = db_session.create_session()
            all_rgt_db = db_sess.query(Regiment.label).all()
            all_rgt_db = list(zip(*all_rgt_db))
            if all_rgt_db:
                all_rgt_db = list(all_rgt_db[0])
                all_rgt_db.remove("WarCA")
            rgt_text = map(lambda i: f"{i + 1}) {all_rgt_db[i]}", range(len(all_rgt_db)))
            rgt_text = "\n".join(rgt_text)
            await self.registr_table[user.id]["thread"].send(
                "Предлагаем вам вступить в другие полки\n"
                "(для выбора ответа напишите его номер.\n"
                "Номер указан слева от варианта ответа):\n"
                f"{rgt_text}"
            )

            def check5(msg_f):
                if msg_f.author.id == user.id:
                    if msg_f.channel.id == self.registr_table[msg_f.author.id]["thread"].id:
                        return self.registr_table[msg_f.author.id]["stage"] == 7
                return False

            params = {"event": "message", "timeout": 24 * 60 * 60, "check": check5}
            msg_rgt = await self.try_timeout(user, self.bot.wait_for, params)
            try:
                ind_rgt = int(msg_rgt.content) - 1
                if not (ind_rgt in range(len(all_rgt_db))):
                    raise IndexError
                rgt_name = all_rgt_db[ind_rgt]
                self.registr_table[user.id]["stage"] += 1
                role_guest = filter(lambda role: role.name == "Гость", user.guild.roles).__next__()
                role_rgt = filter(lambda role: role.name == rgt_name, user.guild.roles).__next__()
                role_student = filter(lambda role: role.name == "Учебный полк",
                                      user.guild.roles).__next__()
                try:
                    await user.remove_roles(role_guest)
                    await user.add_roles(role_rgt, role_student)
                except discord.errors.Forbidden:
                    await  self.registr_table[user.id]["thread"].send(
                        "Похоже вы очень важный человек на этом сервере,\n"
                        "поэтому не получаестся присвоить вам роли:\n"
                        f"`Учебный полк` и `{rgt_name}`"
                    )
                db_sess = db_session.create_session()
                user_db = db_sess.query(User).filter(User.id == user.id).first()
                rgt_id = db_sess.query(Regiment.id).filter(Regiment.label == rgt_name).first()[0]
                user_db.rgt_id = rgt_id
                db_sess.commit()
                await self.registr_table[user.id]["thread"].send(
                    "**Добро пожаловать к нам сервер!**"
                )
                await asyncio.sleep(4)
                await self.stop_registration(user)
                return
            except (ValueError, IndexError):
                self.registr_table[user.id]["num_att6"] = self.registr_table[user.id].get("num_att6",
                                                                                          0) + 1
                if self.registr_table[user.id]["num_att6"] == 3:
                    await self.registr_table[user.id]["thread"].send(
                        "Вы использовали 3 попытки. Просим вас пройти регистрацию через офицера.")
                else:
                    await self.registr_table[user.id]["thread"].send(
                        "Чел, как здесь можно неправильно написать?\n"
                        "Попробуй ещё раз, но уже без таких приколов")
                    await self.registration(user)
                    return

# reaction, user_ = await self.bot.wait_for('reaction_add', timeout=24 * 60 * 60,
#                                          check=self.check0)
