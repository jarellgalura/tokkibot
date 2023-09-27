from datetime import timedelta
import discord
from discord.ext import commands
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timedelta
import pytz
import asyncio

# Discord bot token and Spotify API credentials
TOKEN = 'MTE0NDE2NDM4ODE1NzI3MjEzNw.G9YrRY.4ZXmExNl6v5mzn5FHPmkEVLiIHWc1zxXVzQufU'
SPOTIPY_CLIENT_ID = 'af74290356b04ceaa1d039600b12f93d'
SPOTIPY_CLIENT_SECRET = 'c97a59c90e9c4449b3938cccd40a4f37'
SPOTIPY_REDIRECT_URI = 'https://localhost:5000/callback'

# Create a Discord bot instance
intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='hn ', intents=intents)

# Initialize Spotipy with OAuth2
sp_oauth = SpotifyOAuth(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI,
                        scope='user-library-read user-read-recently-played user-top-read user-read-playback-state')


def get_current_track(user_id=None):
    if user_id is None:
        user_id = 'me'

    # Check if the bot is authorized
    if not sp_oauth.get_cached_token():
        return "Please authorize the bot using !auth"

    # Get the Spotify access token using sp_oauth
    access_token = sp_oauth.get_cached_token()['access_token']

    # Use the access token for making API requests to Spotify
    sp = spotipy.Spotify(auth=access_token)

    # Get the currently playing track
    track = sp.current_playback()

    if track:
        return f"{track['item']['name']} by {', '.join([artist['name'] for artist in track['item']['artists']])}"
    else:
        return "User is not currently listening to Spotify."

# Command to authorize the bot with Spotify


@bot.command()
async def auth(ctx):
    auth_url = sp_oauth.get_authorize_url()

    # Create an embed for the login message
    embed = discord.Embed(
        title="Login to Spotify",
        description=f"Please [Login]({auth_url}) to your Spotify account.",
        color=discord.Color.green()
    )

    await ctx.send(embed=embed)


# Command to get the currently playing track


@bot.command()
async def sf(ctx):
    # Get the currently playing track
    track_info = get_current_track()
    auth_url = sp_oauth.get_authorize_url()

    if "User is not currently listening to Spotify." in track_info:
        await ctx.send(track_info)
        return

    # Create a Spotify client to fetch track details
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        embed = discord.Embed(
            title="Login to Spotify",
            description=f"Please login to your Spotify account by clicking the following link: [Login Here]({auth_url})",
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)
        return
    sp = spotipy.Spotify(auth=token_info['access_token'])

    # Get additional track details
    track = sp.current_playback()
    if not track:
        await ctx.send("User is not currently listening to Spotify.")
        return

    # Extract relevant information
    track_name = track['item']['name']
    artist_name = ", ".join([artist['name']
                            for artist in track['item']['artists']])
    album_name = track['item']['album']['name']
    album_cover_url = track['item']['album']['images'][0]['url']

    # Get Spotify URLs for track, artist, and album
    track_uri = track['item']['external_urls']['spotify']
    artist_uri = track['item']['artists'][0]['external_urls']['spotify']
    album_uri = track['item']['album']['external_urls']['spotify']

    # Get the Discord username of the user who ran the command
    discord_username = ctx.author.display_name

    # Get the current timestamp in the song
    progress_ms = track['progress_ms']
    minutes, seconds = divmod(progress_ms // 1000, 60)
    current_timestamp = f"{minutes}:{seconds:02d}"

    # Get the total duration of the song
    duration_ms = track['item']['duration_ms']
    minutes, seconds = divmod(duration_ms // 1000, 60)
    total_duration = f"{minutes}:{seconds:02d}"

    # Create an embed
    embed = discord.Embed(
        title="Currently Playing on Spotify",
        description=f"{discord_username} is now listening to [{track_name}]({track_uri}) by [{artist_name}]({artist_uri}) from the album [{album_name}]({album_uri})",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=album_cover_url)

    # Add the footer to the embed
    embed.set_footer(
        text=f"Current Timestamp: {current_timestamp} - {total_duration}"
    )

    await ctx.send(embed=embed)


@bot.command()
async def recent(ctx, page: int = 1):
    # Get the user's Spotify access token
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        await ctx.send("Please authorize the bot using !auth")
        return

    discord_username = ctx.author.display_name

    # Create a Spotify client
    sp = spotipy.Spotify(auth=token_info['access_token'])

    # Fetch all recently played tracks
    total_tracks = 50  # Adjust the number as needed
    recently_played = sp.current_user_recently_played(total_tracks)

    if not recently_played['items']:
        await ctx.send("No recently played tracks found.")
        return

    # Sort the tracks by played_at in descending order
    recently_played['items'].sort(key=lambda x: x['played_at'], reverse=True)

    # Calculate the start and end indices for the current page
    items_per_page = 10  # Number of tracks per page
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page

    # Ensure the indices are within bounds
    start_index = max(start_index, 0)
    end_index = min(end_index, len(recently_played['items']))

    # Create a formatted list of tracks for the current page
    track_list = []
    for i, item in enumerate(recently_played['items'][start_index:end_index], start=start_index + 1):
        track = item['track']
        track_name = track['name']
        artist_name = ', '.join([artist['name']
                                for artist in track['artists']])
        track_uri = track['external_urls']['spotify']
        artist_uri = track['artists'][0]['external_urls']['spotify']
        played_at = item['played_at']

        # Convert the played_at timestamp to a datetime object
        played_at_datetime = datetime.fromisoformat(
            played_at[:-1]).replace(tzinfo=pytz.utc)
        current_datetime = datetime.now(pytz.utc)
        time_difference = current_datetime - played_at_datetime

        # Format the time difference
        time_ago = format_timedelta(time_difference)

        track_list.append(
            f"`{i}.` [{track_name}]({track_uri}) by [{artist_name}]({artist_uri}) – {time_ago}")

    # Create or edit an embed for the current page
    if start_index == 0:
        album = sp.album(recently_played['items'][0]['track']['album']['id'])
        album_cover_url = album['images'][0]['url'] if album.get(
            'images') else None
    else:
        album_cover_url = None

    # Create or edit an embed for the current page
    if not hasattr(ctx.bot, 'recent_tracks_message'):
        # Create a new message for the first page
        embed = discord.Embed(
            title=f"{discord_username} Recently Played Tracks",
            description='\n'.join(track_list),
            color=discord.Color.green()
        )
        if album_cover_url:
            # Add album cover as thumbnail
            embed.set_thumbnail(url=album_cover_url)

        # Set the footer with the page number
        embed.set_footer(text=f"Page {page}")
        message = await ctx.send(embed=embed)
        ctx.bot.recent_tracks_message = message
    else:
        # Edit the existing message with the updated embed, including discord_username
        embed = discord.Embed(
            title=f"{discord_username} Recently Played Tracks",
            description='\n'.join(track_list),
            color=discord.Color.green(),
        )
        if album_cover_url:
            # Add album cover as thumbnail
            embed.set_thumbnail(url=album_cover_url)

        # Set the footer with the page number
        embed.set_footer(text=f"Page {page}")
        await ctx.bot.recent_tracks_message.edit(embed=embed)

    # Add pagination react arrows if needed
    if page > 1:
        await ctx.bot.recent_tracks_message.add_reaction("➡️")
    if end_index < len(recently_played['items']):
        await ctx.bot.recent_tracks_message.add_reaction("⬅️")
    if page == 1 and end_index < len(recently_played['items']):
        await ctx.bot.recent_tracks_message.add_reaction("➡️")

    # Function to check if the reaction is from the same user who invoked the command
    def check(reaction, user):
        return user == ctx.author and reaction.message.id == ctx.bot.recent_tracks_message.id

    try:
        reaction, _ = await bot.wait_for('reaction_add', timeout=60.0, check=check)

        # Handle reaction
        if str(reaction.emoji) == "⬅️" and page > 1:
            await recent(ctx, page - 1)
        elif str(reaction.emoji) == "➡️" and end_index < len(recently_played['items']):
            await recent(ctx, page + 1)
    except asyncio.TimeoutError:
        await ctx.bot.recent_tracks_message.clear_reactions()


def format_timedelta(time_difference):
    seconds = time_difference.total_seconds()
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    if days > 0:
        return f"{int(days)}d ago"
    elif hours > 0:
        return f"{int(hours)}h ago"
    elif minutes > 0:
        return f"{int(minutes)}m ago"
    else:
        return f"{int(seconds)}s ago"


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')


# Start the Discord bot
if __name__ == '__main__':
    bot.run(TOKEN)
