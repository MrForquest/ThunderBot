import discord
import logging
import requests
from discord.ext import commands
import asyncio
from data import db_session
from data.users import User
import sqlalchemy


class RegistrationForm(commands.Cog):
    registr_table = dict()

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member, hctx=None):
        reg_ch_id = self.bot.config["registration"]["channelRegistrationId"]
        channel = filter(lambda ch: ch.id == reg_ch_id, member.guild.text_channels).__next__()
        db_sess = db_session.create_session()
        user_db = db_sess.query(User.id).filter(member.id == User.id).first()
        if not (user_db is None):
            if hctx is None:
                await channel.send(f"Пользователь {member.mention}  уже зарегистрирован")
            else:
                await hctx.reply(f"Пользователь {member.mention}  уже зарегистрирован")
            return
        if member.id in self.registr_table.keys():
            await self.stop_registration(member)
        guest_id = self.bot.config["roles"]["guestRole"]["roleId"]
        role_guest = filter(lambda role: role.id == guest_id, member.guild.roles).__next__()
        try:
            await member.add_roles(role_guest)
        except discord.errors.Forbidden:
            await channel.send(
                f"Не удалось присвоить роль гостя человеку {member.mention}\n"
                "Похоже, что этот человек довольно важный.")
        thread = await channel.create_thread(name=f"Регистрация {member.name}",
                                             type=discord.ChannelType.private_thread)
        thread.permissions_for(member)
        thread.permissions_for(
            member.guild.get_role(self.bot.config["roles"]["allianceOfficerRole"]["roleId"]))
        thread.permissions_for(
            member.guild.get_role(self.bot.config["roles"]["careerOfficer"]["roleId"]))
        thread.permissions_for(
            member.guild.get_role(self.bot.config["roles"]["technoAdmin"]["roleId"]))
        await thread.edit(slowmode_delay=3)
        await thread.send(f"{member.mention}, ваша регистрация будет проходить в этой ветке.")
        self.registr_table[member.id] = dict()
        self.registr_table[member.id]["stage"] = 0
        self.registr_table[member.id]["thread"] = thread
        print(member.name)

        await self.registration(member)
        # thread = filter(lambda th: th.name == "регр", member.guild.threads).__next__()

    @commands.command(name='reg')
    async def start_registration(self, ctx):
        if ctx.message.channel.id == self.bot.config["channels"]["flood"]:
            await self.on_member_join(ctx.message.author, ctx)

    @commands.command(name='cleareg')
    async def clear_registration(self, ctx):
        for session in self.registr_table.values():
            try:
                session["thread"].delete()
            except Exception as exc:
                print(exc)
        self.registr_table.clear()

    @commands.command(name='stopreg')
    async def clear_registration(self, ctx, member: discord.Member):
        if member.id in self.registr_table.keys():
            await self.stop_registration(member)
        else:
            await ctx.reply("В данный момент нет регистрации такого пользователя.")

    async def stop_registration(self, user):
        try:
            await self.registr_table[user.id]["thread"].delete()
        except Exception as exc:
            print(exc)
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
        rules = "https://discord.com/channels/256745640011366402/969597794157482014/973867963587379200"
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
                await msg.channel.send("Регистрация отменена.\n"
                                       "Так как вы отказались принимать правила нашего сообщества,\n"
                                       "то вы будете кикнуты с сервера.")
                await asyncio.sleep(3)
                await self.stop_registration(user)
                await user.kick(reason="Надо было согласиться с правилами.")
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
            age_msg = await self.try_timeout(user, self.bot.wait_for, params)
            try:
                age = int(age_msg.content)
                self.registr_table[user.id]["age"] = age
                self.registr_table[user.id]["stage"] += 1
                await self.registration(user)
                return
            except ValueError:
                self.registr_table[user.id]["num_att-2"] = self.registr_table[user.id].get(
                    "num_att-2",
                    0) + 1
                if self.registr_table[user.id]["num_att-2"] == 3:
                    role_officer = user.guild.get_role(
                        self.bot.config["roles"]["officerRole"]["roleId"])
                    role_officer2 = user.guild.get_role(
                        self.bot.config["roles"]["careerOfficer"]["roleId"])
                    await self.registr_table[user.id]["thread"].send(
                        f"Вы использовали 3 попытки. Просим вас пройти регистрацию через {role_officer.mention}"
                        f"и {role_officer2.mention}.")
                else:
                    await self.registr_table[user.id]["thread"].send(
                        "Неправильный формат ввода.\nПопробуйте ещё раз.")
                    await self.registration(user)
                    return

        elif self.registr_table[user.id]["stage"] == 3:
            await self.registr_table[user.id]["thread"].send(
                "4. Напишите ваш ник в игре War Thunder:")

            def check3(msg_f):
                if msg_f.author.id == user.id:
                    if msg_f.channel.id == self.registr_table[msg_f.author.id]["thread"].id:
                        return self.registr_table[msg_f.author.id]["stage"] == 3
                return False

            params = {"event": "message", "timeout": 24 * 60 * 60, "check": check3}
            msg_name = await self.try_timeout(user, self.bot.wait_for, params)
            wt_name = msg_name.content
            await self.registr_table[user.id]["thread"].send("Проверка займёт не больше минуты")
            stats = await self.bot.scraper.get_stats(wt_name)

            if stats.get("error", 200) == 404:
                await self.registr_table[user.id]["thread"].send(
                    "Не удалось получить информацию об игроке с таким ником.\n"
                    "Попробуйте ещё раз.")
                self.registr_table[user.id]["num_att"] = self.registr_table[user.id].get("num_att",
                                                                                         0) + 1
                if self.registr_table[user.id]["num_att"] == 3:
                    # officer_id = self.bot.config["roles"]["officerRole"]["roleId"]
                    role_officer = user.guild.get_role(
                        self.bot.config["roles"]["officerRole"]["roleId"])
                    role_officer2 = user.guild.get_role(
                        self.bot.config["roles"]["careerOfficer"]["roleId"])

                    await self.registr_table[user.id]["thread"].send(
                        f"Вы использовали 3 попытки. Просим вас пройти регистрацию через {role_officer.mention} и"
                        f"{role_officer2.mention}.")
                else:
                    await self.registration(user)
                    return
            else:
                print(stats)
                self.registr_table[user.id]["nickname"] = wt_name
                await self.registr_table[user.id]["thread"].send("Отлично!")
                await self.registr_table[user.id]["thread"].send("⠀")
                output_id = self.bot.config["channels"]["statsOutput"]
                output_ch = filter(lambda chl: chl.id == output_id,
                                   user.guild.channels).__next__()
                text = (f"Пользователь: {user.mention}\n"
                        f"Имя: {self.registr_table[user.id]['real_name']}\n"
                        f"Никнейм(WT): {self.registr_table[user.id]['nickname']}\n"
                        f"Возраст: {self.registr_table[user.id]['age']}\n" + stats["display"])
                stat_msg = await output_ch.send(text)
                self.registr_table[user.id]["stat_msg"] = stat_msg
                db_sess = db_session.create_session()
                user_db = User(id=user.id,
                               real_name=self.registr_table[user.id]["real_name"],
                               nickname=self.registr_table[user.id]["nickname"],
                               age=self.registr_table[user.id]["age"]
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
                    await user.edit(nick=f"<{self.registr_table[user.id]['nickname']}>"
                                         f"({self.registr_table[user.id]['real_name']})")
                except discord.errors.Forbidden:
                    await self.registr_table[user.id]["thread"].send(
                        "По всей видимости вы очень высокопоставленный человек на этом сервере.\n"
                        "Поэтому просим вас самостоятельно поменять ваш никнейм на сервере на формат:\n"
                        "`<ник_в_War_Thunder>(Настоящие_имя)`")
                self.registr_table[user.id]["stage"] += 1
                await self.registration(user)
                return
        elif self.registr_table[user.id]["stage"] == 4:
            msg = await self.registr_table[user.id]["thread"].send(
                "Регистрация почти закончена.\n"
                "5. Вы желаете вступить в полк?"
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
                officer_id = self.bot.config["roles"]["officerRole"]["roleId"]
                role_officer = user.guild.get_role(self.bot.config["roles"]["officerRole"]["roleId"])
                role_officer2 = user.guild.get_role(
                    self.bot.config["roles"]["careerOfficer"]["roleId"])

                await self.registr_table[user.id]["thread"].send(
                    f"Поговорите, пожалуйста, с {role_officer.mention} или с {role_officer2.mention} насчёт ваших целей на этом сервере.")
                # await asyncio.sleep(3 * 24 * 3600)
                # await self.stop_registration(user)
                return
            else:
                self.registr_table[user.id]["stage"] += 1
                await self.registration(user)
                return

        elif self.registr_table[user.id]["stage"] == 5:
            msg = await self.registr_table[user.id]["thread"].send(
                "6. Если вы готовы регулярно участвоать в полковых боях, то предлагаем вам вступить в\n"
                "   полк **WarCA**. Нажмите ✅\n"
                "   Если не готовы, то нажмите на ❌, мы предложим вступить в 'Учебные полки'"
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
                role_id = self.bot.config["roles"]["eliteRole"]["roleId"]
                guest_id = self.bot.config["roles"]["guestRole"]["roleId"]
                role_guest = user.guild.get_role(guest_id)
                role_rgt = user.guild.get_role(role_id)
                role_alliance = user.guild.get_role(self.bot.config["roles"]["alliance"]["roleId"])
                text = self.registr_table[user.id]["stat_msg"].content
                text += f"\n`Полк: {role_rgt.name}`"
                await self.registr_table[user.id]["stat_msg"].edit(content=text)
                try:
                    await user.remove_roles(role_guest)
                    await user.add_roles(role_rgt, role_alliance)
                except discord.errors.Forbidden:
                    await self.registr_table[user.id]["thread"].send(
                        "Похоже вы очень важный человек на этом сервере,\n"
                        "поэтому не получаестся присвоить вам роли:\n"
                        f"`{role_rgt}`"
                    )
                db_sess = db_session.create_session()
                user_db = db_sess.query(User).filter(User.id == user.id).first()
                # rgt_id = db_sess.query(Regiment.id).filter(Regiment.label == "WarCA").first()[0]
                user_db.rgt_id = role_id
                db_sess.commit()
                await self.registr_table[user.id]["thread"].send("Добро пожаловать в **WarCA**!")
                await asyncio.sleep(4)
                await self.stop_registration(user)
                return

        elif self.registr_table[user.id]["stage"] == 6:
            regiments = self.bot.config["registration"]["regiments"]
            rgt_text = "\n".join(
                [str(i + 1) + ". " + rgt["name"] for i, rgt in enumerate(regiments)])
            await self.registr_table[user.id]["thread"].send(
                "Предлагаем вам вступить в другие полки\n"
                "(для выбора ответа напишите его номер.\n"
                "Номер указан слева от варианта ответа):\n"
                f"{rgt_text}"
            )

            def check5(msg_f):
                if msg_f.author.id == user.id:
                    if msg_f.channel.id == self.registr_table[msg_f.author.id]["thread"].id:
                        return self.registr_table[msg_f.author.id]["stage"] == 6
                return False

            params = {"event": "message", "timeout": 24 * 60 * 60, "check": check5}
            msg_rgt = await self.try_timeout(user, self.bot.wait_for, params)
            try:
                ind_rgt = int(msg_rgt.content) - 1
                if not (ind_rgt in range(len(regiments))):
                    raise IndexError

                rgt = regiments[ind_rgt]
                self.registr_table[user.id]["stage"] += 1

                role_guest = user.guild.get_role(self.bot.config["roles"]["guestRole"]["roleId"])
                role_rgt = user.guild.get_role(rgt["roleId"])
                role_student = user.guild.get_role(self.bot.config["roles"]["studentRole"]["roleId"])
                role_alliance = user.guild.get_role(self.bot.config["roles"]["alliance"]["roleId"])
                text = self.registr_table[user.id]["stat_msg"].content
                text += f"\n`Полк: {role_rgt.name}`"
                await self.registr_table[user.id]["stat_msg"].edit(content=text)
                try:
                    await user.remove_roles(role_guest)
                    await user.add_roles(role_rgt, role_student, role_alliance)
                except discord.errors.Forbidden:
                    await self.registr_table[user.id]["thread"].send(
                        "Похоже вы очень важный человек на этом сервере,\n"
                        "поэтому не получаестся присвоить вам роли:\n"
                        f"`{role_student.name}` и `{role_rgt.name}`"
                    )
                db_sess = db_session.create_session()
                user_db = db_sess.query(User).filter(User.id == user.id).first()
                user_db.rgt_id = role_rgt.id
                db_sess.commit()
                await self.registr_table[user.id]["thread"].send(
                    "**Добро пожаловать к нам на сервер!**"
                )
                await asyncio.sleep(4)
                await self.stop_registration(user)
                return
            except (ValueError, IndexError):
                self.registr_table[user.id]["num_att6"] = self.registr_table[user.id].get("num_att6",
                                                                                          0) + 1
                if self.registr_table[user.id]["num_att6"] == 3:
                    role_officer = user.guild.get_role(
                        self.bot.config["roles"]["officerRole"]["roleId"])
                    role_officer2 = user.guild.get_role(
                        self.bot.config["roles"]["careerOfficer"]["roleId"])
                    await self.registr_table[user.id]["thread"].send(
                        f"Вы использовали 3 попытки. Просим вас пройти регистрацию через {role_officer.mention} или "
                        f"{role_officer2.mention}.")
                else:
                    await self.registr_table[user.id]["thread"].send(
                        "Чел, как здесь можно неправильно написать?\n"
                        "Попробуй ещё раз, но уже без таких приколов")
                    await self.registration(user)
                    return

# reaction, user_ = await self.bot.wait_for('reaction_add', timeout=24 * 60 * 60, check=self.check0)
