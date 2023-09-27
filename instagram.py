import discord
from discord.ext import commands
import instaloader
import requests

# Set your Discord bot token
TOKEN = 'MTE0NDgwOTk0NjExOTE0MzUzNQ.GekBmF.vxb8TsdwC5VvlsC5qqK7MvnrtgM5HbBYOqTWYI'

# Instagram credentials
INSTAGRAM_USERNAME = 'ja.dmp_'
INSTAGRAM_PASSWORD = 'jcdg120899'

# Create a Discord bot instance
intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix="hn ", intents=intents)

# Initialize the Instaloader instance for authentication
instagram_loader = instaloader.Instaloader()


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')


@bot.command()
async def instagram(ctx, post_url):
    try:
        # Construct the Instagram post URL
        if not post_url.startswith('https://www.instagram.com/p/'):
            await ctx.send('Invalid Instagram post URL.')
            return

        # Extract the shortcode from the URL
        shortcode = post_url.split('/')[-2]

        # Login to Instagram (You can handle login exceptions here)
        instagram_loader.load_session_from_file(INSTAGRAM_USERNAME)

        # Fetch post information using Instaloader
        post = instaloader.Post.from_shortcode(
            instagram_loader.context, shortcode)

        if post:
            # Extract image and video URLs
            image_urls = []
            video_urls = []

            if post.is_video:
                video_urls.append(post.url)
            else:
                image_urls.append(post.url)

            # Send the URLs to the Discord channel
            if image_urls:
                await ctx.send(f'Image URLs from the Instagram post:\n' + '\n'.join(image_urls))
            if video_urls:
                await ctx.send(f'Video URLs from the Instagram post:\n' + '\n'.join(video_urls))
        else:
            # If Instaloader fails to fetch data, use the original method
            api_url = f'{post_url}?__a=1&__d=dis'
            response = requests.get(api_url)

            # Check if the response status code is 200 (OK)
            if response.status_code == 200:
                data = response.json()

                if 'graphql' in data and 'shortcode_media' in data['graphql']:
                    media_data = data['graphql']['shortcode_media']

                    # Extract image and video URLs
                    image_urls = []
                    video_urls = []

                    if 'edge_sidecar_to_children' in media_data:
                        # If it's a carousel post with multiple images/videos
                        carousel_media = media_data['edge_sidecar_to_children']['edges']
                        for edge in carousel_media:
                            if 'node' in edge and 'is_video' in edge['node']:
                                video_urls.append(edge['node']['video_url'])
                            elif 'node' in edge and 'display_url' in edge['node']:
                                image_urls.append(edge['node']['display_url'])
                    elif 'is_video' in media_data and media_data['is_video']:
                        # If it's a video
                        video_urls.append(media_data['video_url'])
                    elif 'display_url' in media_data:
                        # If it's a single image
                        image_urls.append(media_data['display_url'])

                    # Send the URLs to the Discord channel
                    if image_urls:
                        await ctx.send(f'Image URLs from the Instagram post:\n' + '\n'.join(image_urls))
                    if video_urls:
                        await ctx.send(f'Video URLs from the Instagram post:\n' + '\n'.join(video_urls))
                else:
                    await ctx.send('Unable to fetch data for the Instagram post.')
            else:
                await ctx.send(f'Failed to fetch data. Status Code: {response.status_code}')
    except Exception as e:
        await ctx.send(f'Error: {str(e)}')

# Run the bot
bot.run(TOKEN)
