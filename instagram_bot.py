import discord
import instaloader
import aiohttp
import os
import tempfile
import asyncio
from datetime import datetime, timedelta
from urllib.parse import urlparse
from io import BytesIO

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


async def get_media_data(session, url):
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()
    except aiohttp.ClientError as e:
        print(f"Error during HTTP request: {e}")
        return None


@client.event
async def on_message(message):
    if message.author == client.user:
        return

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


async def retrieve_instagram_media(message):
    url = message.content.split()[0]
    shortcode = url.split('/')[-2]

    L = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(L.context, shortcode)

    username = post.owner_username
    post_date = post.date.strftime('%Y-%m-%d %H:%M:%S')
    caption = post.caption if post.caption else "No caption available."
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
    caption_with_info = f"{instagram_emote_syntax} **@{username}** {post_date}\n\n{caption}"

    async with aiohttp.ClientSession() as session:
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

                with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
                    tmp_file.write(media_data)
                    tmp_file.seek(0)
                    temp_path = os.path.join(tempfile.gettempdir(),
                                             f'{index:02d}{os.path.splitext(urlparse(media_urls[index - 1]).path)[1]}')
                    with open(temp_path, 'wb') as f:
                        f.write(tmp_file.read())
                    media_files.append(discord.File(temp_path))

            # Combine caption and URL with media files
            caption_message = f"{caption_with_info}\n<{url}>"

            # Send media files along with caption and URL in a single message
            await message.channel.send(content=caption_message, files=media_files)

            # Delete the original Instagram link message
            await message.delete()

client.run(
    'MTE0NDE2NDM4ODE1NzI3MjEzNw.Gqo5qS.4RhfKd6jUnB7NML-igAL50W7pRlXPAkQZn-jkg')
