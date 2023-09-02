import discord
from discord.ext import commands
from mtranslate import translate

# Define the custom command prefix
intents = discord.Intents.all()
intents.members = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or('$'), intents=intents)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')


@bot.event
async def on_message(message):
    # Avoid responding to the bot's own messages to prevent loops
    if message.author == bot.user:
        return

    # Check if the bot was mentioned in the message
    if bot.user.mentioned_in(message):
        # Extract the text after the mention
        mentioned_text = message.content.replace(bot.user.mention, '').strip()

        # Translate text using the 'mtranslate' library
        translated_text = mtranslate(mentioned_text)

        # Send the translation
        await message.channel.send(f'{translated_text}')

    # Process commands
    await bot.process_commands(message)

# Function to perform translation using the 'mtranslate' library


def mtranslate(text):
    translated_text = translate(text, 'en', 'auto')
    return translated_text


# Run the bot with your Discord token
bot.run('MTE0NDE2NDM4ODE1NzI3MjEzNw.G1r_lp.BxIzRaqOJQ9aRHnEsXd3LRnpkPFHTHh8cwysWw')
