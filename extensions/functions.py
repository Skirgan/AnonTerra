from random import shuffle, randint

import discord

from database import connection, cursor
from config import anon_channel_id, names

def get_name(member_id: int, reroll: bool = False) -> str:
    if cursor.execute(f"SELECT * FROM names WHERE id = {member_id}").fetchone() and not reroll:
        return cursor.execute(f"SELECT name FROM names WHERE id = {member_id}").fetchone()[0]
    shuffle(names)
    while True:
        some_name = names[0]
        some_name_number = randint(1, 9)
        if not cursor.execute(f"SELECT * FROM names WHERE name = '{some_name}-{some_name_number}'").fetchone():
            if not reroll:
                cursor.execute(f"INSERT INTO names VALUES ({member_id}, '{some_name}-{some_name_number}')")
            else:
                cursor.execute(f"UPDATE names SET name = '{some_name}-{some_name_number}' WHERE id = {member_id}")
            connection.commit()
            return f"{some_name}-{some_name_number}"
        shuffle(names)

async def send_anon(interaction: discord.Interaction, embed: discord.Embed, file: discord.File = None, message_id: str = None) -> discord.Message:
    anon_channel = interaction.guild.get_channel(anon_channel_id)
    if message_id is None:
        if file is None:
            return await anon_channel.send(embed = embed)
        return await anon_channel.send(
            embed = embed,
            file = file
            )
    try:
        reply_message = await anon_channel.fetch_message(int(message_id))
        if file is None:
            return await reply_message.reply(embed = embed)
        return await reply_message.reply(
            embed = embed,
            file = file
            )
    except discord.errors.NotFound:
        return False

def get_companion_id(member: discord.Member):
    if cursor.execute(f"SELECT * FROM privates WHERE first_id = {member.id}").fetchone() is not None:
        return cursor.execute(f"SELECT second_id FROM privates WHERE first_id = {member.id}").fetchone()[0]
    elif cursor.execute(f"SELECT * FROM privates WHERE second_id = {member.id}").fetchone() is not None:
        return cursor.execute(f"SELECT first_id FROM privates WHERE second_id = {member.id}").fetchone()[0]
    return None

async def cancel_dialogue(interaction: discord.Interaction):
    dm = interaction.user.dm_channel
    async for message in dm.history(limit = None):
        if message.author.bot:
            await message.delete()
    await dm.send(
        embed = discord.Embed(
            description = f"Вы завершили диалог.",
            color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
        ))
    companion = await interaction.client.get_or_fetch_user(get_companion_id(interaction.user))
    if companion is not None:
        async for message in companion.dm_channel.history(limit = None):
            if message.author.bot:
                await message.delete()
        await companion.dm_channel.send(
            embed = discord.Embed(
                description = f"К сожалению, ваш собеседник завершил диалог.",
                color = discord.Colour.from_rgb(r = 71, g = 126, b = 128)
            ))
    if cursor.execute(f"SELECT * FROM privates WHERE first_id = {interaction.user.id}").fetchone() is not None:
        cursor.execute(f"DELETE FROM privates WHERE first_id = {interaction.user.id}")
    else:
        cursor.execute(f"DELETE FROM privates WHERE second_id = {interaction.user.id}")
    connection.commit()

def check_blocked(member: discord.Member):
    if cursor.execute(f"SELECT * FROM blacklist WHERE id = {member.id}").fetchone() is not None:
        return True
    return False