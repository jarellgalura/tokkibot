import discord
import requests
import asyncio
import tempfile
from discord.ext import commands
from discord.ui import Button, View
from urllib.parse import urlsplit, urlunsplit, urljoin
import re
import time
# Import the translate function from the mtranslate library
from mtranslate import translate

# Create a bot instance
intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix="hn ", intents=intents)

# Create a variable to store the timestamp when the "Kr/En" button was created
translation_button_created_time = 0

# Create a variable to store the timestamp when the "Jp/En" button was created
jp_translation_button_created_time = 0

# Create a dictionary to store the current translation state by message ID
translation_states = {}


async def fetch_media(url):
    # Determine the file extension based on URL content type
    file_extension = ".jpg" if url.endswith(".jpg") else ".mp4"

    # Modify the URL to use a high-quality format for images
    if file_extension == ".jpg":
        url += "?format=jpg&name=4096x4096"

    # Download the media and create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        temp_file.write(requests.get(url).content)

    return discord.File(temp_file.name)


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")


@bot.command(name="twt", aliases=["x"])
async def hn_tweet_link(ctx, tweet_link):
    # Remove the leading "https://twitter.com/" from the tweet link
    tweet_link = tweet_link.replace("https://twitter.com/", "")

    # Check if the link starts with "x.com/"
    if tweet_link.startswith("x.com/"):
        tweet_link = tweet_link.replace("x.com/", "")

    # Make a request to the tweet data API
    tweet_data_url = f"https://api.vxtwitter.com/{tweet_link}"
    response = requests.get(tweet_data_url)
    if response.status_code == 200:
        tweet_data = response.json()

        # Extract media URLs (images and videos)
        media_urls = tweet_data.get("mediaURLs", [])
        video_urls = tweet_data.get("videoURLs", [])

        # Get the username and date from the tweet data
        username = tweet_data.get("user_screen_name", "UnknownUser")
        date = tweet_data.get("date", "")

        # Format the date (assuming the input is in the format "Fri Sep 08 15:10:07 +0000 2023")
        date_parts = date.split()
        formatted_date = f"{date_parts[2]}/{date_parts[1][:3]}/{date_parts[5][2:]}"

        # Get the caption of the tweet
        tweet_caption = tweet_data.get("text", "No caption provided")

        # Remove the link at the end of the caption (if it exists)
        tweet_caption = tweet_caption.split("https://t.co/")[0]

        x_emote_syntax = "<:x:1149749183755067513>"

        # Combine the username, date, and caption with a Translate button
        full_caption = f"{x_emote_syntax} **@{username}** `{formatted_date}`\n\n {tweet_caption}"

        # Get the original Twitter link without any query parameters
        # Check if the link starts with "x.com/"
        if tweet_link.startswith("x.com/"):
            # If it starts with "x.com/", remove it and create the original_link
            original_link = urljoin(
                "https://twitter.com/", tweet_link.replace('x.com/', ''))
        else:
            # If it starts with "https://twitter.com/", use it directly as the original_link
            original_link = urljoin("https://twitter.com/", tweet_link)

        # Remove query parameters (everything after "?") from the original_link
        original_link = original_link.split("?")[0]

        if media_urls or video_urls:
            # Create a list of media file URLs to download concurrently
            media_files_urls = media_urls + video_urls

            # Use asyncio.gather to download media files concurrently
            media_files = await asyncio.gather(*[fetch_media(url) for url in media_files_urls])

            # Create a view to hold the buttons
            view = View()

            tweet_button = Button(
                style=discord.ButtonStyle.link, label="View Post", url=original_link)

            # Add the "View Post" button to the view
            view.add_item(tweet_button)

            # Create the Translate button conditionally
            translate_button = Button(
                style=discord.ButtonStyle.success, label="Translate Caption")

            # Define a callback function for the Translate button
            async def translate_callback(interaction):
                await interaction.response.defer()
                if ctx.message.id in translation_states:
                    # Toggle the translation state
                    translation_states[ctx.message.id] = not translation_states.get(
                        ctx.message.id, False)
                else:
                    # Initialize the translation state
                    translation_states[ctx.message.id] = True

                if translation_states[ctx.message.id]:
                    # Translate the caption
                    translated_caption = translate(
                        tweet_caption, "en", "auto")
                    new_caption = f"{x_emote_syntax} **@{username}** `{formatted_date}`\n\n{translated_caption}"
                else:
                    # Use the original caption
                    new_caption = f"{x_emote_syntax} **@{username}** `{formatted_date}`\n\n{tweet_caption}"

                await original_caption_message.edit(content=new_caption)

            # Add the callback to the Translate button
            translate_button.callback = translate_callback

            # Add the Translate button to the view
            view.add_item(translate_button)

            # Send the original caption message with buttons as a reply to the user
            original_caption_message = await ctx.send(f"{full_caption.strip()}", files=media_files, view=view, allowed_mentions=discord.AllowedMentions.none())

            # Delete the user's message containing the command
            await ctx.message.delete()

            await asyncio.sleep(600)  # 10 minutes

            # Disable and update the buttons after the specified time
            translate_button.disabled = True
            translate_button.label = "Button Expired"
            await original_caption_message.edit(view=view)

        else:
            # Send an error message if there is no media
            error_message = "There is no media in the tweet link."

            # Send the same error message to the channel
            await ctx.send(error_message)

    else:
        await ctx.send("Failed to fetch tweet data")

# Run the bot with your token
bot.run("MTE0NDE2NDM4ODE1NzI3MjEzNw.G9YrRY.4ZXmExNl6v5mzn5FHPmkEVLiIHWc1zxXVzQufU")
