import asyncio
import discord
import threading
import instaloader
import re

# Import the TikTok script
from modules.tiktok_bot import TikTok

# Import the Instagram script
from modules.instagram_bot import *

# Your bot's token
TOKEN = 'MTE0NDE2NDM4ODE1NzI3MjEzNw.G8tkPl.8d3HLrHy0S-7kuk7l0nDl-urBpxzWc2w-4gjWk'

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Instantiate the TikTok class
tiktok = TikTok()


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    tiktok_pattern = r'https?://(?:www\.)?tiktok\.com/.+'
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

                        # Create a File object from the temporary file
                        video_file = discord.File(temp_file.name)
                        tiktok_emote_syntax = "<:tiktok_icon:1144945709645299733>"
                        response = (
                            f"{tiktok_emote_syntax} @{tiktok_video.user}\n\n"
                            f"{tiktok_video.description}"
                        )

                        # Send the response to the user without mentioning them
                        await message.channel.send(response, file=video_file, reference=message, allowed_mentions=discord.AllowedMentions.none())

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

            # Construct the shortened link
            shortened_link = urljoin(url, url.split('?')[0])

            # Combine caption, shortened link, and media files
            caption_message = f"{caption_with_info}\n<{shortened_link}>"

            # Send media files along with caption and shortened link in a single message
            await message.reply(content=caption_message, files=media_files, allowed_mentions=discord.AllowedMentions.none())

            # Delete the original Instagram link message
            await message.delete()


@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')

    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Cake, Juice and Bread"))


def run_discord_bot():
    client.run(TOKEN)


def run_instagram_script():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client.start(TOKEN))


if __name__ == '__main__':
    discord_thread = threading.Thread(target=run_discord_bot)
    instagram_thread = threading.Thread(target=run_instagram_script)

    discord_thread.start()
    instagram_thread.start()

    discord_thread.join()
    instagram_thread.join()
