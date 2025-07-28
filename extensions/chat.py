import aiohttp
import io

import discord
from discord.ext import commands

from config import anon_channel_id

from .functions import check_blocked, get_name, send_anon

class AnonChatMessageModal(discord.ui.Modal):
    def __init__(self, member_id: int, file: discord.Attachment, message_id: str):
        super().__init__(title = "Отправка сообщения в АнонЧат")
        self.member_id = member_id
        self.file = file
        self.message_id = message_id
        self.add_item(discord.ui.InputText(
            label = "Текст",
            style = discord.InputTextStyle.long,
            max_length = 3800
            ))

    async def callback(self, interaction):
        message_embed = discord.Embed(
            description = self.children[0].value,
            color = discord.Colour.from_rgb(r = 71, g = 126, b = 128),
            )
        message_embed.set_author(name = f"Аноним: {get_name(self.member_id)}")
        if self.file is None:
            message = await send_anon(
                interaction = interaction,
                embed = message_embed,
                message_id = self.message_id
                )
        else:
            if self.file.content_type and self.file.content_type.startswith("image/"):
                message_embed.set_image(url = self.file.url)
                message = await send_anon(
                    interaction = interaction,
                    embed = message_embed,
                    message_id = self.message_id
                    )
            async with aiohttp.ClientSession() as session:
                async with session.get(self.file.url) as response:
                    if response.status != 200:
                        message = False
                    else:
                        data = await response.read()
                        memory_file = io.BytesIO(data)
                        memory_file.seek(0)
                        message = await send_anon(
                            interaction = interaction,
                            embed = message_embed,
                            file = discord.File(fp = memory_file, filename = self.file.filename),
                            message_id = self.message_id
                            )
        if message:
            return await interaction.respond(
                embed = discord.Embed(
                    description = f"Анонимное сообщение ({message.jump_url}) успешно отправлено!",
                    color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                    ),
                ephemeral = True
                )
        return await interaction.respond(
            embed = discord.Embed(
                description = f"Не удалось обработать дополнительные аргументы.\n```{self.children[0].value}```",
                color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                ),
            ephemeral = True
            )

class AnonChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    anon = discord.SlashCommandGroup("анон")

    @anon.command(name = "чат", description = "Написать анонимное сообщение в АнонЧат.")
    async def message(
        self,
        ctx: discord.ApplicationContext,
        file: discord.Option(
            discord.Attachment,
            name = "file",
            description = "Прикрепляемый к сообщению файл.",
            required = False
            ),
        message_id: discord.Option(
            str,
            name = "message_id",
            description = "ID сообщения, на которое даётся ответ.",
            required = False
        )):
        
        if not check_blocked(ctx.author):
            async with ctx.guild.get_channel(anon_channel_id).typing():
                await ctx.send_modal(AnonChatMessageModal(ctx.author.id, file, message_id))
        else:
            return await ctx.respond(
                embed = discord.Embed(
                    description = f"Ваш доступ к функциям анонимного чата был ограничен.",
                    color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
                    ),
                ephemeral = True
                )

    @anon.command(name = "имя", description = "Случайно меняет ваше имя в АнонЧате.")
    async def message(
        self,
        ctx: discord.ApplicationContext
        ):

        if not check_blocked(ctx.author):
            return await ctx.respond(
                embed = discord.Embed(
                    description = f"Ваше новое имя в АнонЧате: `{get_name(ctx.author.id, True)}`.",
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
    bot.add_cog(AnonChat(bot))