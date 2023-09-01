import asyncio
import discord
import instaloader
import re
from PIL import Image
import io
import os
import tempfile
import asyncio
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
import aiohttp

# Import the TikTok script
from tiktok_bot import TikTok


# Your bot's token
TOKEN = 'MTE0NDE2NDM4ODE1NzI3MjEzNw.G1r_lp.BxIzRaqOJQ9aRHnEsXd3LRnpkPFHTHh8cwysWw'

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Instantiate the TikTok class
tiktok = TikTok()
L = instaloader.Instaloader()
# Define cooldown duration (in seconds)
COOLDOWN_DURATION = 5

# Store last link message timestamp per user
user_last_link_time = {}


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    tiktok_pattern = r'https?://(?:www\.|vm\.)?(?:tiktok\.com|vt\.tiktok\.com)/.+'
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
                            f"{tiktok_emote_syntax} @{tiktok_video.user}\n\n"
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
    post_date = post.date.strftime('%Y-%m-%d %H:%M:%S')
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
    caption_with_info = f"{instagram_emote_syntax} **@{username}** {post_date}\n\n{caption_without_hashtags}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        # Display typing status while processing
        async with message.channel.typing():
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
                    temp_path = os.path.join(tempfile.gettempdir(),
                                             f'{index:02d}{os.path.splitext(urlparse(media_urls[index - 1]).path)[1]}')
                    with open(temp_path, 'wb') as f:
                        f.write(tmp_file.read())
                    media_files.append(discord.File(temp_path))

            # Construct the shortened link
            shortened_link = urljoin(url, url.split('?')[0])

            # Combine caption, shortened link, and media files
            caption_message = f"{caption_with_info}\n<{shortened_link}>"

            # Send media files along with caption and shortened link in a single message
            await message.reply(content=caption_message, files=media_files, allowed_mentions=discord.AllowedMentions.none())

            # Delete the original Instagram link message
            await message.delete()


INSTALOADER_SESSION_DIR = os.path.dirname(os.path.abspath(__file__))
INSTAGRAM_USERNAME = "jarellgalura"  # Replace with your Instagram username

# Create an Instaloader context with the desired session file name
L = instaloader.Instaloader(
    filename_pattern="session-{username}", max_connection_attempts=1)


async def get_media_data(session, url):
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()
    except aiohttp.ClientError as e:
        print(f"Error during HTTP request: {e}")
        return None


@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')

    # Load or create a session
    session_file_path = os.path.join(
        INSTALOADER_SESSION_DIR, f"session-{INSTAGRAM_USERNAME}")
    try:
        L.load_session_from_file(
            INSTAGRAM_USERNAME, filename=session_file_path)
    except FileNotFoundError:
        L.context.log("Session file does not exist yet - Logging in.")
        L.context.log(
            "If you have not logged in yet, you will be asked for your Instagram credentials.")
        L.context.log(
            "If you have chosen the 'Remember me' option while logging in, the session file will be created and you won't have to log in again next time.")
        pass
    except Exception as e:
        L.context.log(f"Error while loading session: {e}")
        pass

    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Cake, Juice and Bread"))


def run_discord_bot():
    asyncio.run(client.start(TOKEN))


if __name__ == '__main__':
    run_discord_bot()
