import mtranslate
import asyncio
import discord
import instaloader
import re
import os
from PIL import Image
import io
from instaloader.exceptions import TwoFactorAuthRequiredException, BadCredentialsException
import getpass
import time
import random
import string
import tempfile
import uuid
from urllib.parse import urlparse, urljoin
from typing import Dict, Any
from discord.ui import Button, View
import aiohttp
from datetime import datetime, timedelta
import sqlite3
import itertools

# Import the TikTok script
from tiktok_bot import TikTok

# Import the Instagram script
from hanniinstagram import *

# Your bot's token
TOKEN = 'MTE0NDE2NDM4ODE1NzI3MjEzNw.G9YrRY.4ZXmExNl6v5mzn5FHPmkEVLiIHWc1zxXVzQufU'

intents = discord.Intents.all()
intents.message_content = True
client = discord.Client(intents=intents)

# Connect to the SQLite database (create it if it doesn't exist)
conn = sqlite3.connect('message_data.db')
cursor = conn.cursor()

# Create a table to store message data if it doesn't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY,
                    channel_id INTEGER,
                    content TEXT
                )''')
conn.commit()

# Instantiate the TikTok class
tiktok = TikTok()
INSTALOADER_SESSION_DIR = os.path.dirname(os.path.abspath(__file__))
INSTAGRAM_USERNAME = "praychandesu_"

# Create an Instaloader context with the desired session file name
L = instaloader.Instaloader(
    filename_pattern="session-{username}", max_connection_attempts=1)

user_last_link_time = {}  # Define user_last_link_time and COOLDOWN_DURATION here
COOLDOWN_DURATION = 1
message_dict = {}


COMMAND_PREFIX = "hn "


async def say_command(message):
    # Check if the user has the "Manage Channels" permission
    if not message.author.guild_permissions.manage_channels:
        await message.channel.send("You do not have permission to use this command.")
        return

    # Extract the content of the message after the "hn say" prefix
    input_text = message.content[len(COMMAND_PREFIX):].strip()

    # Check if the user has specified a target channel
    if input_text.startswith("<#"):
        # Find the channel mention
        channel_mention = input_text.split()[0].strip()

        # Remove the channel mention from the input text
        input_text = input_text[len(channel_mention):].strip()

        # Get the target channel from the mention
        channel_id = int(channel_mention[2:-1])  # Extract the channel ID
        target_channel = message.guild.get_channel(channel_id)

        if target_channel:
            # Send the message to the specified channel
            sent_message = await target_channel.send(input_text)
            await message.channel.send(f"Message sent to {target_channel.mention}.")

            # Store the messageId in the dictionary
            message_dict[message.id] = sent_message
            return
        else:
            # Send an error message if the specified channel does not exist
            await message.channel.send("Error: The specified channel does not exist.")
            return

    # If no channel is specified or not found, send the message to the current channel
    sent_message = await message.channel.send(input_text)
    await message.channel.send("Message sent to this channel.")

    # Store the messageId in the dictionary
    message_dict[message.id] = sent_message


# Function to generate a common browser user agent

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15"
]

user_agent_iterator = itertools.cycle(user_agents)


def generate_random_user_agent():
    return next(user_agent_iterator)

# Function to generate browser headers


def generate_browser_headers() -> Dict[str, Any]:
    headers = {
        'User-Agent': generate_random_user_agent(),
        'Referer': 'https://www.instagram.com/',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    }
    return headers


# Persistent session handling


async def login_instagram():
    # Load or create a session
    session_file_path = os.path.join(
        INSTALOADER_SESSION_DIR, f"session-{INSTAGRAM_USERNAME}")
    try:
        L.load_session_from_file(
            INSTAGRAM_USERNAME, filename=session_file_path)
    except (FileNotFoundError, BadCredentialsException):
        try:
            L.context.log('Logging in with provided credentials.')
            L.context.log("Session file does not exist yet - Logging in.")
            L.context.log(
                "If you have not logged in yet, you will be asked for your Instagram credentials.")
            L.context.log(
                "If you have chosen the 'Remember me' option while logging in, the session file will be created and you won't have to log in again next time.")
            pass
        except Exception as e:
            L.context.log(f'Failed to log in: {e}')

# Add a random delay between requests


async def random_request_delay():
    await asyncio.sleep(random.uniform(2, 5))


async def convert_heic_to_jpg(heic_data):
    with tempfile.NamedTemporaryFile(delete=True, suffix='.jpg') as tmp_file:
        # Open the HEIC data using PIL and save as JPEG
        img = Image.open(io.BytesIO(heic_data))
        img = img.convert("RGB")
        img.save(tmp_file, "JPEG")
        tmp_file.seek(0)
        return tmp_file.read()


async def retrieve_instagram_media(message):
    try:
        url = message.content.split()[0]
        shortcode = url.split('/')[-2]

        post = instaloader.Post.from_shortcode(L.context, shortcode)

        username = post.owner_username
        post_date = post.date.strftime('%Y-%m-%d')
        caption = post.caption if post.caption else "No caption available."

        # Remove hashtags from the caption
        caption_without_hashtags = re.sub(r'#\w+', '', caption).strip()

        media_urls = []

        if post.typename == 'GraphImage':
            media_urls.append(post.url)
        elif post.typename == 'GraphVideo':
            media_urls.append(post.video_url)
        elif post.typename == 'GraphSidecar':
            for media in post.get_sidecar_nodes():
                if media.is_video:
                    media_urls.append(media.video_url)
                else:
                    media_urls.append(media.display_url)
        elif post.typename in ['GraphStoryImage', 'GraphStoryVideo']:
            media_urls.append(post.url)
        elif post.typename == 'GraphReel':
            if post.is_video:
                media_urls.append(post.video_url)
            else:
                media_urls.append(post.url)

        instagram_emote_syntax = "<:instagram_icon:1144223792466513950>"
        caption_with_info = f"{instagram_emote_syntax} **@{username}** `{post_date}`\n\n{caption_without_hashtags}"

        headers = generate_browser_headers()

        async with aiohttp.ClientSession(headers=headers) as session:
            # Display typing status while processing
            async with message.channel.typing():
                # Check if there is Korean text in the caption
                translation_button = Button(
                    style=discord.ButtonStyle.success, label="Translate Caption")

                # Define a mutable list to store the 'translated' flag
                translated = [False]

                # Define a callback function for the Translate button
                async def translate_callback(interaction):
                    await interaction.response.defer()

                    # Toggle the translation state
                    translated[0] = not translated[0]

                    if translated[0]:
                        # Translate the caption
                        translated_caption = mtranslate.translate(
                            caption_without_hashtags, "en", "auto")
                    else:
                        # Use the original caption
                        translated_caption = caption_without_hashtags

                    # Create a new caption with the translated or original text
                    new_caption = f"{instagram_emote_syntax} **@{username}** `{post_date}`\n\n{translated_caption}"

                    # Update the message content and button label
                    await original_message.edit(content=new_caption)
                    translation_button.label = "Original" if translated[0] else "Kr/En"

                # Add the callback to the Translation button
                translation_button.callback = translate_callback

                # Rest of your media retrieval and sending code
                tasks = []
                media_data_results = []

                # Fetch media data concurrently
                for media_url in media_urls:
                    tasks.append(get_media_data(session, media_url))
                    await random_request_delay()
                media_data_results = await asyncio.gather(*tasks)

                media_files = []
                for index, media_data in enumerate(media_data_results, start=1):
                    if media_data is None:
                        await message.channel.send("An error occurred while retrieving media.")
                        return

                    # Convert HEIC to JPEG if the media is in HEIC format
                    if os.path.splitext(urlparse(media_urls[index - 1]).path)[1].lower() == '.heic':
                        media_data = await convert_heic_to_jpg(media_data)
                        # Update the media URL to use the new JPEG format
                        media_urls[index - 1] = media_urls[index -
                                                           1].replace('.heic', '.jpg')

                    with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
                        tmp_file.write(media_data)
                        tmp_file.seek(0)
                        temp_path = os.path.join(tempfile.gettempdir(
                        ), f'{index:02d}{os.path.splitext(urlparse(media_urls[index - 1]).path)[1]}')
                        with open(temp_path, 'wb') as f:
                            f.write(tmp_file.read())
                        media_files.append(discord.File(temp_path))

                # Construct the shortened link
                shortened_link = urljoin(url, url.split('?')[0])

                # Combine caption, shortened link, and media files
                caption_message = f"{caption_with_info}"

                view = View()
                ig_button = Button(
                    style=discord.ButtonStyle.link, label="View Post", url=shortened_link)  # Use discord.ButtonStyle.link
                view.add_item(ig_button)

                if translation_button:
                    view.add_item(translation_button)

                # Send media files along with caption and shortened link in a single message
                original_message = await message.reply(content=caption_message, files=media_files, view=view, allowed_mentions=discord.AllowedMentions.none())

                # Delete the original Instagram link message
                await message.delete()

                # Disable and update the buttons after the specified time
                translation_button.disabled = True

    except instaloader.HTTPException as e:
        await message.channel.send(f"An error occurred: {e}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith(COMMAND_PREFIX):
        command = message.content[len(COMMAND_PREFIX):].strip()

        if command.startswith("say "):
            command_args = command[len("say "):].strip()

            if command_args:
                # Check if there are any attachments (images) in the message
                if message.attachments:
                    # If there are attachments, send only the attached images
                    channel_mention = command_args.split(' ', 1)[0]
                    if channel_mention.startswith("<#") and channel_mention.endswith(">"):
                        channel_id = int(channel_mention[2:-1])
                        target_channel = message.guild.get_channel(channel_id)
                        if target_channel:
                            sent_messages = []
                            for attachment in message.attachments:
                                sent_message = await target_channel.send(file=await attachment.to_file())
                                sent_messages.append(sent_message)
                            await message.channel.send(f"Image(s) sent to {target_channel.mention}.")
                        else:
                            await message.channel.send("Error: The specified channel does not exist.")
                    else:
                        await message.channel.send("Error: Invalid channel mention format.")
                else:
                    # If no attachments, send only the text
                    command_parts = command_args.split(' ', 1)
                    if len(command_parts) == 2:
                        channel_mention, message_content = command_parts
                        if channel_mention.startswith("<#") and channel_mention.endswith(">"):
                            channel_id = int(channel_mention[2:-1])
                            target_channel = message.guild.get_channel(
                                channel_id)
                            if target_channel:
                                sent_message = await target_channel.send(message_content)
                                await message.channel.send(f"Message sent to {target_channel.mention}.")
                                cursor.execute("INSERT INTO messages (message_id, channel_id, content) VALUES (?, ?, ?)",
                                               (sent_message.id, channel_id, message_content))
                                conn.commit()
                            else:
                                await message.channel.send("Error: The specified channel does not exist.")
                        else:
                            await message.channel.send("Error: Invalid channel mention format.")
                    else:
                        await message.channel.send("Error: Invalid command format. Use `hn say <#channel_mention> <message>`.")
            else:
                await message.channel.send("Error: Invalid command format. Use `hn say <#channel_mention> <message>` or attach an image.")

            return
        elif command.startswith("edit "):
            command_args = command[len("edit "):].strip().split(' ', 1)

            if len(command_args) == 2:
                message_id, new_content = command_args
                try:
                    message_id = int(message_id)
                except ValueError:
                    await message.channel.send("Error: Invalid message ID format.")
                    return

                # Check if the message exists in the database
                cursor.execute(
                    "SELECT channel_id FROM messages WHERE message_id=?", (message_id,))
                result = cursor.fetchone()

                if result:
                    channel_id = result[0]
                    target_channel = message.guild.get_channel(channel_id)
                    if target_channel:
                        # Edit the message using the message ID
                        edited_message = await target_channel.fetch_message(message_id)
                        await edited_message.edit(content=new_content)
                        await message.channel.send(f"Message with ID {message_id} edited.")

                        # Update the message content in the database
                        cursor.execute(
                            "UPDATE messages SET content=? WHERE message_id=?", (new_content, message_id))
                        conn.commit()
                    else:
                        await message.channel.send("Error: The specified channel does not exist.")
                else:
                    await message.channel.send("Error: Message with that ID not found.")
            else:
                await message.channel.send("Error: Invalid command format. Use `hn edit <messageId> <new_content>`.")
        else:
            # Handle other commands here if needed
            pass

    # Check if the raw content of the message contains a TikTok URL that starts with '<' and ends with '>'
    if re.search(r'<https?://(?:www\.|vm\.)?(?:tiktok\.com|vt\.tiktok\.com)/[^ ]+>', message.content):
        return

    # Modified regex pattern
    tiktok_pattern = r'https?://(?:www\.|vm\.)?(?:tiktok\.com|vt\.tiktok\.com)/[^<> ]+'
    tiktok_urls = re.findall(tiktok_pattern, message.content)

    async with aiohttp.ClientSession() as session:
        for tiktok_url in tiktok_urls:
            try:
                tiktok_video = await tiktok.get_video(tiktok_url)
                video_content = await tiktok.download_video_content(tiktok_video.video_url, session)
                async with message.channel.typing():
                    # Create a temporary file using tempfile.NamedTemporaryFile
                    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
                        temp_file.write(video_content)
                        temp_file.seek(0)

                        # Remove hashtags from the description
                        description_without_hashtags = re.sub(
                            r'#\w+', '', tiktok_video.description)

                        # Create a File object from the temporary file
                        video_file = discord.File(temp_file.name)
                        tiktok_emote_syntax = "<:tiktok_icon:1144945709645299733>"
                        response = (
                            f"{tiktok_emote_syntax} **@{tiktok_video.user}**\n\n"
                            f"{description_without_hashtags}"
                        )

                        # Send the response to the user without mentioning them
                        await message.channel.send(response, file=video_file, reference=message, allowed_mentions=discord.AllowedMentions.none())
                        await message.edit(suppress=True)
            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")

    if 'instagram.com/p/' in message.content or 'instagram.com/reel/' in message.content:
        user_id = message.author.id
        current_time = datetime.now()

        if user_id in user_last_link_time:
            time_since_last_link = current_time - user_last_link_time[user_id]
            if time_since_last_link < timedelta(seconds=COOLDOWN_DURATION):
                await message.channel.send("Please wait before sending another link.")
                return

        user_last_link_time[user_id] = current_time
        await retrieve_instagram_media(message)


@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')

    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Cake, Juice and Bread"))


@client.event
async def on_disconnect():
    conn.close()


def run_discord_bot():
    asyncio.run(client.start(TOKEN))


if __name__ == '__main__':
    asyncio.run(login_instagram())
    run_discord_bot()
