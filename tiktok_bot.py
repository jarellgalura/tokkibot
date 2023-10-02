import os
import discord
import re
import aiohttp
from bs4 import BeautifulSoup
import re
from dataclasses import dataclass
from typing import Dict, Tuple
import tempfile
from discord.ui import Button, View

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


class TiktokError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


@dataclass
class TikTokVideo:
    video_url: str
    user: str
    description: str


def error_code_to_message(error_code):
    if error_code == "tiktok":
        return "URL redirected to tiktok home page."
    elif error_code == "Video is private!":
        return "Video is private or unavailable"
    else:
        return error_code


class TikTok:
    BASE_URL: str = "https://musicaldown.com/"

    HEADERS: Dict[str, str] = {
        "Host": "musicaldown.com",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:103.0) Gecko/20100101 Firefox/103.0"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "TE": "trailers",
    }
    EMOJI = "<:tiktok:1050401570090647582>"

    def __init__(self) -> None:
        self.input_element = None

    async def warmup(self, session: aiohttp.ClientSession):
        response = await session.get(self.BASE_URL)
        soup = BeautifulSoup(await response.text(), "lxml")
        self.input_element = soup.findAll("input")

    def generate_post_data(self, url: str):
        if self.input_element is None:
            raise Exception("TikTok downloader was not warmed up!")

        return {
            index.get("name"): url
            if index.get("id") == "link_url"
            else index.get("value")
            for index in self.input_element
        }

    async def download_video(
        self, url: str, session: aiohttp.ClientSession
    ) -> Tuple[str, str, str]:
        async with session.post(
            f"{self.BASE_URL}id/download",
            data=self.generate_post_data(url),
            allow_redirects=True,
        ) as response:
            if response.status == 302:
                raise TiktokError("302 Not Found")

            error_code = response.url.query.get("err")
            if error_code:
                raise TiktokError(error_code_to_message(error_code))

            text = await response.text()

        soup = BeautifulSoup(text, "lxml")

        error_message = re.search(
            r"html: 'Error: (.*)'", soup.findAll("script")[-1].text
        )
        if error_message:
            raise TiktokError(error_message)

        download_link = soup.findAll(
            "a",
            attrs={
                "target": "_blank",
                "class": "btn",
            },
        )
        if not download_link:
            # probably a slideshow with music
            script = soup.findAll("script")[-2].text
            data = re.search(r"data: {\s*data:\s*'(.*?)'",
                             script, flags=re.MULTILINE)
            if data is None:
                raise TiktokError("Internal Error: Unable to scrape POST data")

            async with session.post(
                "https://muscdn.xyz/slider",
                data={"data": data.group(1)},
                headers=self.HEADERS,
            ) as response:
                converted_data = await response.json()
                username = soup.select_one("h2.white-text")
                if username:
                    username = username.text.strip("Download Now: Check out ").strip(
                        "’s video! #TikTok >"
                    )
                else:
                    username = ""
                return converted_data["url"], username, ""

        else:
            username, description = [
                el.text for el in soup.select("h2.white-text")[:2]]
            return download_link[0].get("href"), username, description

    async def get_video(self, url: str) -> TikTokVideo:
        async with aiohttp.ClientSession() as session:
            session.headers.update(self.HEADERS)
            await self.warmup(session)
            return TikTokVideo(*await self.download_video(url, session))

    async def download_video_content(self, url: str, session: aiohttp.ClientSession) -> bytes:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:103.0) Gecko/20100101 Firefox/103.0"
            ),
        }

        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise TiktokError("Failed to fetch video content")

            video_content = await response.read()
            return video_content


tiktok = TikTok()


@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')


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
                        view = View()
                        view.add_item(
                            Button(style=1, label="View Post", url=tiktok_url))

                        # Send the response to the user without mentioning them
                        await message.channel.send(response, file=video_file, view=view, reference=message, allowed_mentions=discord.AllowedMentions.none())
                        await message.delete()
            except Exception as e:
                await message.channel.send(f"An error occurred: {e}")


client.run(
    'MTE0NDgwOTk0NjExOTE0MzUzNQ.GekBmF.vxb8TsdwC5VvlsC5qqK7MvnrtgM5HbBYOqTWYI')
