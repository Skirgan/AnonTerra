import discord
from discord.ext import commands

from extensions.functions import get_companion_id

from database import connection, cursor
        
class AnonPrivateEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None and not message.author.bot:
            if get_companion_id(message.author) is not None:
                companion = await self.bot.get_or_fetch_user(get_companion_id(message.author))
                if companion is not None:
                    if companion.dm_channel is None:
                        await companion.create_dm()
                    files = []
                    for attachment in message.attachments:
                        try:
                            files.append(await attachment.to_file())
                        except discord.HTTPException:
                            pass
                    if not files:
                        return await companion.dm_channel.send(message.content)
                    if not message.content and files:
                        return await companion.dm_channel.send(files = files)
                    return await companion.dm_channel.send(
                        message.content,
                        files = files
                        )
            await message.add_reaction("❌")

def setup(bot):
    bot.add_cog(AnonPrivateEvents(bot))