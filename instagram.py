import asyncio
import discord
import instaloader
import os
import tempfile
from urllib.parse import urljoin
from typing import Dict, Any
from discord.ui import Button, View
from discord import File
from datetime import datetime, timedelta
import sqlite3
import subprocess

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

INSTALOADER_SESSION_DIR = os.path.dirname(os.path.abspath(__file__))
INSTAGRAM_USERNAME = "ja.dmp_"
L = None

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


async def login_instagram():
    global L  # Make L a global variable to reuse the session

    try:
        if L is None:
            # Create a new Instaloader instance if not already created
            L = instaloader.Instaloader(
                filename_pattern="session-{username}", max_connection_attempts=1)

        # Load or create a session
        session_file_path = os.path.join(
            INSTALOADER_SESSION_DIR, f"session-{INSTAGRAM_USERNAME}")
        L.load_session_from_file(
            INSTAGRAM_USERNAME, filename=session_file_path)

        # Set custom browser headers
        L.context.headers = generate_browser_headers()

    except (FileNotFoundError, instaloader.exceptions.BadCredentialsException):
        try:
            L.context.log('Logging in with provided credentials.')
            L.context.log("Session file does not exist yet - Logging in.")
            L.context.log(
                "If you have not logged in yet, you will be asked for your Instagram credentials.")
            L.context.log(
                "If you have chosen the 'Remember me' option while logging in, the session file will be created and you won't have to log in again next time.")
        except Exception as e:
            L.context.log(f'Failed to log in: {e}')

    return L


def generate_browser_headers() -> Dict[str, Any]:
    headers = {
        'User-Agent': (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:103.0) Gecko/20100101 Firefox/103.0"
        ),
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


async def download_instagram_reel(url):
    try:
        # Create a temporary directory to save the downloaded file
        temp_dir = tempfile.mkdtemp()

        # Use subprocess to run gallery-dl with the specified options
        command = ['gallery-dl', '--cookies',
                   './cookies-instagram-com.txt', '--directory', temp_dir, url]
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, error_output = process.communicate()

        # Check if gallery-dl succeeded
        if process.returncode == 0:
            # Gallery-dl should have downloaded the file to the temporary directory
            downloaded_files = [f for f in os.listdir(
                temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
            if downloaded_files:
                # Assuming the downloaded file is the first one in the list
                downloaded_file = os.path.join(temp_dir, downloaded_files[0])
                return downloaded_file
            else:
                return None
        else:
            return None
    except Exception as e:
        print(f"Error downloading Instagram reel: {e}")
        return None


async def download_instagram_reel_with_caption(message):
    try:
        # Extract the Instagram reel URL from the message content
        url = message.content.split()[0]

        async with message.channel.typing():

            # Download the Instagram reel using gallery-dl
            downloaded_file = await download_instagram_reel(url)

            if downloaded_file:

                # Create a discord.File object from the downloaded video file
                video_file = discord.File(downloaded_file)
                post = instaloader.Post.from_shortcode(
                    L.context, url.split('/')[-2])
                username = post.owner_username  # Get the username of the post owner
                post_date = post.date.strftime('%Y-%m-%d')

                instagram_emote_syntax = "<:instagram_icon:1144223792466513950>"

                # Create a formatted message with username and caption
                formatted_message = f"{instagram_emote_syntax} **@{username}** `{post_date}`"
                shortened_link = urljoin(url, url.split('?')[0])
                view = View()
                ig_button = Button(
                    style=discord.ButtonStyle.link, label="View Post", url=shortened_link)  # Use discord.ButtonStyle.link
                view.add_item(ig_button)

                # Send the formatted message along with the video file as one message
                await message.reply(content=formatted_message, file=video_file, view=view, allowed_mentions=discord.AllowedMentions.none())

                await message.delete()
            else:
                await message.channel.send("Meta! blocked me again.")
    except Exception as e:
        await message.channel.send(f"An error occurred: {e}")


async def send_file_to_discord_channel(channel, file_path):
    if file_path is not None:
        with open(file_path, 'rb') as file:
            discord_file = discord.File(file)
            await channel.send(file=discord_file)
        os.remove(file_path)


async def download_instagram_media_with_gallery_dl(url):
    try:
        # Create a temporary directory to save the downloaded files
        temp_dir = tempfile.mkdtemp()

        # Use subprocess to run gallery-dl with the specified options
        command = ['gallery-dl', '--cookies',
                   './cookies-instagram-com.txt', '--directory', temp_dir, url]
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, error_output = process.communicate()

        # Check if gallery-dl succeeded
        if process.returncode == 0:
            # Gallery-dl should have downloaded the files to the temporary directory
            downloaded_files = [os.path.join(temp_dir, f) for f in os.listdir(
                temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]

            return downloaded_files
        else:
            return None
    except Exception as e:
        print(f"Error downloading Instagram media: {e}")
        return None


async def retrieve_instagram_media(message):
    try:
        url = message.content.split()[0]

        # Show the "bot typing" indicator
        async with message.channel.typing():
            # Download all Instagram media using gallery-dl
            downloaded_files = await download_instagram_media_with_gallery_dl(url)

            if downloaded_files:
                # Fetch the Instagram post using Instaloader
                post = instaloader.Post.from_shortcode(
                    L.context, url.split('/')[-2])
                username = post.owner_username  # Get the username of the post owner
                post_date = post.date.strftime('%Y-%m-%d')

                media_files = [File(media_file_path)
                               for media_file_path in downloaded_files]

                # Create a shortened link to the original post
                shortened_link = urljoin(url, url.split('?')[0])
                instagram_emote_syntax = "<:instagram_icon:1144223792466513950>"

                # Create a message with the media files, username, and a link to the original post
                response_message = f"{instagram_emote_syntax} **@{username}** `{post_date}`"
                view = View()
                view.add_item(
                    Button(style=1, label="View Post", url=shortened_link))

                # Send all media files in one message along with the message and shortened link
                await message.reply(content=response_message, files=media_files, view=view, allowed_mentions=discord.AllowedMentions.none())

                # Delete the original Instagram link message
                await message.delete()
            else:
                await message.channel.send("Failed to download Instagram media.")
    except Exception as e:
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

    if message.content.startswith("<") and message.content.endswith(">"):
        return

    if message.content.strip() and not message.content.startswith('http'):
        return

    if 'instagram.com/reel/' in message.content:
        # Call the updated download_instagram_reel_with_caption function
        await download_instagram_reel_with_caption(message)

    elif 'instagram.com/p/' in message.content:
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
