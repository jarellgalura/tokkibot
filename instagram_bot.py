import discord
import instaloader
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

    # Register application commands for all guilds
    for guild in client.guilds:
        commands = [
            {
                "name": "retrieve_instagram",
                "description": "Retrieve media from an Instagram link",
                "type": 1,  # Slash command
                "options": [
                    {
                        "name": "url",
                        "description": "The Instagram link",
                        "type": 3,  # String type
                        "required": True
                    },
                    {
                        "name": "include_caption",
                        "description": "Include caption? (yes/no)",
                        "type": 3,  # String type
                        "required": False
                    }
                ]
            }
        ]

        await client.http.bulk_upsert_guild_commands(client.user.id, guild.id, commands)


@client.event
async def on_interaction(interaction):
    if isinstance(interaction, discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:
            command = interaction.data["name"]

            if command == "retrieve_instagram":
                await interaction.response.defer()

                url = interaction.data["options"][0]["value"]
                include_caption_option = interaction.data["options"][1] if len(
                    interaction.data["options"]) > 1 else None

                await retrieve_instagram_media(interaction, url, include_caption_option)


async def retrieve_instagram_media(interaction, url, include_caption_option):
    shortcode = url.split('/')[-2]
    L = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(L.context, shortcode)

    username = post.owner_username
    post_date = post.date.strftime('%Y-%m-%d %H:%M:%S')
    caption = post.caption if post.caption else "No caption available."

    if include_caption_option and include_caption_option["value"].lower() == "no":
        caption = ""

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
        async with interaction.channel.typing():
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
                    await interaction.followup.send("An error occurred while retrieving media.")
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
            if include_caption_option and include_caption_option["value"].lower() == "yes":
                caption_message = f"{caption_with_info}\n\n{shortened_link}"
            else:
                caption_message = f"{caption_with_info}"

            # Send media files along with caption and shortened link in a single message
            await interaction.followup.send(content=caption_message, files=media_files, allowed_mentions=discord.AllowedMentions.none())


async def get_media_data(session, url):
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()
    except aiohttp.ClientError as e:
        print(f"Error during HTTP request: {e}")
        return None

client.run(
    "MTE0NDE2NDM4ODE1NzI3MjEzNw.G8tkPl.8d3HLrHy0S-7kuk7l0nDl-urBpxzWc2w-4gjWk")
