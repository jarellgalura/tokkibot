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

# Import the TikTok script
from tiktok_bot import TikTok

# Import the Instagram script
from hanniinstagram import *

# Your bot's token
TOKEN = 'MTE0NDE2NDM4ODE1NzI3MjEzNw.G9YrRY.4ZXmExNl6v5mzn5FHPmkEVLiIHWc1zxXVzQufU'

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Instantiate the TikTok class
tiktok = TikTok()
INSTALOADER_SESSION_DIR = os.path.dirname(os.path.abspath(__file__))
INSTAGRAM_USERNAME = "jarellgalura_"  # Replace with your Instagram username

# Create an Instaloader context with the desired session file name
L = instaloader.Instaloader(
    filename_pattern="session-{username}", max_connection_attempts=1)

user_last_link_time = {}  # Define user_last_link_time and COOLDOWN_DURATION here
COOLDOWN_DURATION = 1

# Function to generate a common browser user agent


def generate_browser_user_agent() -> str:
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )

# Function to generate browser headers


def generate_browser_headers() -> Dict[str, Any]:
    headers = {
        'User-Agent': generate_browser_user_agent(),
        'referer': 'https://www.instagram.com/',
        'authority': 'www.instagram.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.5',
        'upgrade-insecure-requests': '1',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': 'Windows',
    }
    return headers


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
        except TwoFactorAuthRequiredException as e:
            L.context.log('Two-factor authentication required.')

            # Check the available 2FA methods
            available_methods = e.available_methods

            if '0' in available_methods:
                # SMS is available as a 2FA method
                phone_number = input('Enter your phone number for SMS 2FA: ')
                L.two_factor_login_sms(phone_number)

            elif '1' in available_methods:
                # Email is available as a 2FA method
                email = input('Enter your email for email 2FA: ')
                L.two_factor_login_email(email)

            elif '3' in available_methods:
                # Authentication app (TOTP) is available as a 2FA method
                otp_code = getpass.getpass(
                    'Enter your authentication app OTP code: ')
                L.two_factor_login_totp(otp_code)

            try:
                L.save_session_to_file()
                L.context.log('Logged in after 2FA.')
            except Exception as e:
                L.context.log(f'Failed to log in after 2FA: {e}')
                time.sleep(5)


async def convert_heic_to_jpg(heic_data):
    with tempfile.NamedTemporaryFile(delete=True, suffix='.jpg') as tmp_file:
        # Open the HEIC data using PIL and save as JPEG
        img = Image.open(io.BytesIO(heic_data))
        img = img.convert("RGB")
        img.save(tmp_file, "JPEG")
        tmp_file.seek(0)
        return tmp_file.read()


async def retrieve_instagram_media(message):
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

    # Use the common browser headers
    headers = generate_browser_headers()

    async with aiohttp.ClientSession(headers=headers) as session:
        # Display typing status while processing
        async with message.channel.typing():
            # Rest of your media retrieval and sending code
            tasks = []
            media_data_results = []

            # Fetch media data concurrently
            for media_url in media_urls:
                tasks.append(get_media_data(session, media_url))
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

            await asyncio.sleep(1)

            # Send media files along with caption and shortened link in a single message
            await message.reply(content=caption_message, files=media_files, view=view, allowed_mentions=discord.AllowedMentions.none())

            # Delete the original Instagram link message
            await message.delete()


@client.event
async def on_message(message):
    if message.author == client.user:
        return

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


def run_discord_bot():
    asyncio.run(client.start(TOKEN))


if __name__ == '__main__':
    asyncio.run(login_instagram())
    run_discord_bot()
