from random import shuffle

import discord
from discord.ext import commands

from config import administrator_id

from .functions import check_blocked, get_companion_id, cancel_dialogue
from database import connection, cursor

class ReportModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title = "Отправка сообщения в АнонЧат")
        self.add_item(discord.ui.InputText(
            label = "ID сообщений",
            placeholder = "123, 234, 345",
            style = discord.InputTextStyle.long,
            max_length = 3800
            ))

    async def callback(self, interaction):
        dm = interaction.user.dm_channel
        administrator = await interaction.client.get_or_fetch_user(administrator_id)
        if administrator is not None:
            if administrator.dm_channel is None:
                await administrator.create_dm()
            companion = await interaction.client.get_or_fetch_user(get_companion_id(interaction.user))
            if companion is not None:
                succes_messages = []
                for message_id in self.children[0].value.split(", "):
                    try:
                        message = await interaction.channel.fetch_message(int(message_id))
                        if message.author.bot:
                            files = []
                            for attachment in message.attachments:
                                try:
                                    files.append(await attachment.to_file())
                                except discord.HTTPException:
                                    pass
                            if not succes_messages:
                                await administrator.dm_channel.send(
                                    embed = discord.Embed(
                                        description = f"Ваше Превосходительство, на участника {companion} (`{companion.id}`) подана жалоба. Далее я отправлю объекты нарушения.",
                                        color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                                    ))
                            if not files:
                                await administrator.dm_channel.send(message.content)
                            elif not message.content and files:
                                await administrator.dm_channel.send(files = files)
                            else:
                                await administrator.dm_channel.send(
                                    message.content,
                                    files = files
                                    )
                            succes_messages.append(message_id)
                    except:
                        pass
                return await interaction.respond(
                    embed = discord.Embed(
                        description = f"Жалоба успешно обработана. ID успешно отправленных Разработку сообщений:\n```{'\n'.join(succes_messages) if succes_messages else 'Отсутствуют.'}```",
                        color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                        ),
                    ephemeral = True
                    )

class ReportView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.disable_on_timeout = True
        self.timeout = 15

    @discord.ui.button(
        label = "Подтвердить",
        custom_id = "ApprovedReportButton",
        style = discord.ButtonStyle.danger
        )
    async def approved_report_callbac(self, button, interaction):
        await interaction.response.send_modal(ReportModal())

class DialogueMenuView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.disable_on_timeout = False
        self.timeout = None

    @discord.ui.button(
        emoji = "🤐",
        label = "Закончить разговор",
        custom_id = "CancelDialogueButton"
        )
    async def cancel_callbac(self, button, interaction):
        self.disable_all_items()
        await interaction.edit(view = self)
        await cancel_dialogue(interaction)

    @discord.ui.button(
        emoji = "🛑",
        label = "Пожаловаться",
        custom_id = "ReportDialogueButton",
        style = discord.ButtonStyle.danger
        )
    async def report_callbac(self, button, interaction):
        await interaction.respond(
            embed = discord.Embed(
                description = f"Вы собираетесь подать жалобу. О подаче жалобы собеседник уведомлён не будет.\nПодача жалобы откроет модальное окно, куда вам будет необходимо предоставить ID сообщений через запятую (123, 234, ...). Неверное указанные ID сообщений восприняты Ботом не будут. Ваша жалоба поступит напрямую Разработчику.",
                color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                ),
            view = ReportView(),
            ephemeral = True
            )

class StartDialogueView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.disable_on_timeout = True
        self.timeout = 65

    @discord.ui.button(
        label = "Я согласен с условиями"
        )
    async def callback(self, button, interaction):
        self.disable_all_items()
        await interaction.edit(view = self)
        dm = interaction.user.dm_channel
        if cursor.execute(f"SELECT * FROM privates WHERE second_id IS NULL").fetchone() is None:
            cursor.execute(f"INSERT INTO privates VALUES ({interaction.user.id}, NULL)")
            connection.commit()
            return await dm.send(
                embed = discord.Embed(
                    description = f"Вы встали в очередь на ожидание собеседника в личном анонимном чате.",
                    color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                ))
        list_of_waiters_id = [waiter_id[0] for waiter_id in cursor.execute(f"SELECT * FROM privates WHERE second_id IS NULL AND first_id != {interaction.user.id}").fetchall()]
        while list_of_waiters_id:
            shuffle(list_of_waiters_id)
            companion_member = await interaction.client.get_or_fetch_user(list_of_waiters_id[0])
            if companion_member is not None:
                cursor.execute(f"UPDATE privates SET second_id = {interaction.user.id} WHERE first_id = {companion_member.id}")
                connection.commit()
                try:
                    main_message = await companion_member.dm_channel.send(
                        embed = discord.Embed(
                            description = f"Вы начали диалог с анонимным собеседником.",
                            color = discord.Colour.from_rgb(r = 71, g = 126, b = 128),
                            ),
                        view = DialogueMenuView()
                        )
                    await main_message.pin()
                    main_message = await dm.send(
                        embed = discord.Embed(
                            description = f"Вы начали диалог с анонимным собеседником.",
                            color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                            ),
                        view = DialogueMenuView()
                        )
                    return await main_message.pin()
                except discord.errors.ApplicationCommandInvokeError:
                    pass
            list_of_waiters_id.remove(list_of_waiters_id[0])
            cursor.execute(f"DELETE FROM privates WHERE first_id = {list_of_waiters_id[0]}")
            connection.commit()
        else:
            cursor.execute(f"INSERT INTO privates VALUES ({interaction.user.id}, NULL)")
            connection.commit()
            return await dm.send(
                embed = discord.Embed(
                    description = f"Вы встали в очередь на ожидание собеседника в личном анонимном чате.",
                    color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                ))
        
class AnonPrivate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    anon = discord.SlashCommandGroup("анон")

    @anon.command(name = "поиск", description = "Встать в очередь на анонимное общение.")
    async def message(
        self,
        ctx: discord.ApplicationContext
        ):
        
        if not check_blocked(ctx.author):
            if cursor.execute(f"SELECT * FROM privates WHERE first_id = {ctx.author.id} OR second_id = {ctx.author.id}").fetchone() is not None:
                return await ctx.respond(
                    embed = discord.Embed(
                        description = f"Вы уже встали поиск или находитесь в диалоге с анонимным собеседником.",
                        color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                        ),
                    ephemeral = True
                    )
            dm = ctx.author.dm_channel
            if dm is None:
                try:
                    dm = await ctx.author.create_dm()
                except:
                    return await ctx.respond(
                        embed = discord.Embed(
                            description = f"Не удалось открыть личные сообщения с вами.",
                            color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                            ),
                        ephemeral = True
                        )
            async for message in dm.history(limit = None):
                if message.author.bot:
                    await message.delete()
            try:
                agreement_file = open(file = "соглашение.txt", mode = "r", encoding = "utf-8-sig")
                agreement = agreement_file.read()
                agreement_file.close()
                await dm.send(
                    embed = discord.Embed(
                        description = agreement,
                        color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                        ),
                    view = StartDialogueView()
                    )
            except discord.errors.ApplicationCommandInvokeError:
                return await ctx.respond(
                    embed = discord.Embed(
                        description = f"Не удалось отправить вам личное сообщение.",
                        color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                        ),
                    ephemeral = True
                    )
            return await ctx.respond(   
                embed = discord.Embed(
                    description = f"Для продолжения выполнения команды проверьте личные сообщения.",
                    color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                    ),
                ephemeral = True
                )
        else:
            return await ctx.respond(
                embed = discord.Embed(
                    description = f"Ваш доступ к функциям анонимного чата был ограничен.",
                    color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                    ),
                ephemeral = True
                )

def setup(bot):
    bot.add_cog(AnonPrivate(bot))