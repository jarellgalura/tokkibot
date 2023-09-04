import discord
import aiohttp
import os
import tempfile
import asyncio
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Define cooldown duration (in seconds)
COOLDOWN_DURATION = 5

# Store last link message timestamp per user
user_last_link_time = {}


@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')

    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Cake, Juice and Bread"))


async def get_media_data(session, url):
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()
    except aiohttp.ClientError as e:
        print(f"Error during HTTP request: {e}")
        return None
