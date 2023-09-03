import discord
from discord.ext import commands


# Define the custom command prefix
intents = discord.Intents.all()
intents.members = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or('$'), intents=intents)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
