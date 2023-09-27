import re  # Import the 're' module for regular expressions
import discord
from discord.ext import commands
import asyncpg
import asyncio
intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='hn ', intents=intents)

# PostgreSQL Database Setup


async def create_pg_pool():
    return await asyncpg.create_pool(
        user='postgres',
        password='cO2V2oj3kPDUDTkONl5W',
        database='railway',
        host='containers-us-west-81.railway.app',
        port=5779
    )


async def create_guild_table(guild_id, pool):
    async with pool.acquire() as conn:
        await conn.execute(f'''
            CREATE TABLE IF NOT EXISTS guild_{guild_id} (
                user_id BIGINT,
                guild_id BIGINT,
                role_id BIGINT,
                ban_words TEXT,
                booster_role_id BIGINT,
                greeting_message TEXT,
                greeting_channel_id BIGINT,
                log_channel_id BIGINT
            )
        ''')

# Define an asynchronous function to initialize the bot


async def initialize_bot():
    pool = await create_pg_pool()
    bot.pool = pool


async def send_error_message(ctx, message):
    embed = discord.Embed(
        title="Error", description=message, color=discord.Color.red())
    user_avatar_url = ctx.author.avatar.url
    embed.set_thumbnail(url=user_avatar_url)
    bot_avatar_url = bot.user.avatar.url
    embed.set_footer(text="HanniBot - hn help for commands",
                     icon_url=bot_avatar_url)
    await ctx.send(embed=embed)


@bot.command()
async def claim(ctx):
    async with ctx.typing():
        print(f"Guild ID: {ctx.guild.id}")  # Debug print

    # Fetch the booster identifier role ID from the database
    query = f"SELECT booster_role_id FROM guild_{ctx.guild.id} WHERE guild_id = $1"
    booster_identifier_role_id_result = await bot.pool.fetchval(query, ctx.guild.id)

    # Debug print
    print(f"Booster Identifier Role ID: {booster_identifier_role_id_result}")

    if booster_identifier_role_id_result is not None:
        booster_role_id = booster_identifier_role_id_result
        print(f"Booster Role ID: {booster_role_id}")  # Debug print

        booster_role = discord.utils.get(
            ctx.guild.roles, id=booster_role_id)

        if booster_role:
            print("Booster identifier role found")  # Debug print
            if booster_role in ctx.author.roles:
                query = f"SELECT role_id FROM guild_{ctx.guild.id} WHERE guild_id = $1 AND user_id = $2"
                custom_role_id_result = await bot.pool.fetchval(query, ctx.guild.id, ctx.author.id)

                print(f"Custom Role ID: {custom_role_id_result}")

                if custom_role_id_result is None or not ctx.guild.get_role(custom_role_id_result):
                    # Create a custom role
                    custom_role = await ctx.guild.create_role(name=f"{ctx.author.name}", color=discord.Color.random())

                    # Find the position of the booster identifier role
                    booster_identifier_position = booster_role.position

                    # Calculate the position for the custom role (just above booster identifier)
                    custom_role_position = booster_identifier_position - 1

                    # Edit the custom role's position
                    await custom_role.edit(position=custom_role_position)

                    # Check for banned words in the role name
                    query = f"SELECT ban_words FROM guild_{ctx.guild.id} WHERE guild_id = $1"
                    ban_words_result = await bot.pool.fetchval(query, ctx.guild.id)

                    if ban_words_result:
                        ban_words = ban_words_result.split(',')
                        for word in ban_words:
                            if word.lower() in custom_role.name.lower():
                                await custom_role.delete()
                                embed = discord.Embed(
                                    title="Custom Role Claim Failed",
                                    description=f"The role name contains a banned word or pattern: {word}.",
                                    color=discord.Color.red()
                                )
                                user_avatar_url = ctx.author.avatar.url
                                embed.set_thumbnail(url=user_avatar_url)
                                bot_avatar_url = bot.user.avatar.url
                                embed.set_footer(text="HanniBot - hn help for commands",
                                                 icon_url=bot_avatar_url)
                                await ctx.send(embed=embed)

                                # Log the attempt to change role name to a banned word or pattern
                                log_message = f"User {ctx.author.mention} attempted to change their role name to **{custom_role.name}**, which contains a banned word or pattern: **{word}**"
                                query = f"SELECT log_channel_id FROM guild_{ctx.guild.id} WHERE guild_id = $1"
                                log_channel_id_result = await bot.pool.fetchval(query, ctx.guild.id)
                                if log_channel_id_result:
                                    log_channel = bot.get_channel(
                                        log_channel_id_result) if log_channel_id_result else None
                                    if log_channel:
                                        await log_channel.send(log_message)

                                return

                    # Assign the role to the user
                    await ctx.author.add_roles(custom_role)

                    # Reorder roles to ensure custom role is above booster identifier
                    roles = ctx.guild.roles
                    roles = sorted(
                        roles, key=lambda x: x.position, reverse=True)
                    custom_role_index = roles.index(custom_role)
                    await ctx.guild.edit_role_positions(positions={custom_role: custom_role_index})

                    # Insert the new row into the database for the user's custom role
                    query = f"INSERT INTO guild_{ctx.guild.id} (user_id, role_id, guild_id) VALUES ($1, $2, $3)"
                    await bot.pool.execute(query, ctx.author.id, custom_role.id, ctx.guild.id)

                    embed = discord.Embed(
                        title="Custom Role Claimed",
                        description=f"You've been granted a custom role: {custom_role.mention}\n\n **Edit your role:**\n **Name:** `hn role name NewName`\n **Color:** `hn role color #FFFFFF`\n **Icon:** `Request to booster channel.`",
                        color=discord.Color.pink()
                    )
                else:
                    custom_role = ctx.guild.get_role(custom_role_id_result)
                    embed = discord.Embed(
                        title="Role Claim Failed",
                        description=f"You already have a custom role: {custom_role.mention}",
                        color=discord.Color.red()
                    )
            else:
                embed = discord.Embed(
                    title="Role Claim Failed",
                    description="You need to have the booster identifier role to claim your custom role.",
                    color=discord.Color.red()
                )
        else:
            embed = discord.Embed(
                title="Role Claim Failed",
                description="Booster identifier role not found.",
                color=discord.Color.red()
            )
    else:
        embed = discord.Embed(
            title="Role Claim Failed",
            description="Booster identifier role not set.",
            color=discord.Color.red()
        )

    user_avatar_url = ctx.author.avatar.url
    embed.set_thumbnail(url=user_avatar_url)
    bot_avatar_url = bot.user.avatar.url
    embed.set_footer(
        text="HanniBot - hn help for commands", icon_url=bot_avatar_url)

    # Send the embed as the message
    await ctx.send(embed=embed)


@bot.command()
async def role(ctx, action, *, args=""):
    async with ctx.typing():
        if action == "name":
            new_name = args
            user_id = ctx.author.id

            # Choose the appropriate table name based on guild ID
            table_name = f"guild_{ctx.guild.id}"

            # Initialize banned_words_str with an empty string
            banned_words_str = ""

            # Fetch banned words from the database
            query = f"SELECT ban_words FROM {table_name} WHERE guild_id = $1"
            banned_words_result = await bot.pool.fetchval(query, ctx.guild.id)

            if banned_words_result:
                banned_words_str = banned_words_result

            if banned_words_str:
                ban_words = banned_words_str.split(',')
                for word in ban_words:
                    # Use re.search to check if the banned word pattern is in the new role name
                    if re.search(fr"{word}", new_name, re.IGNORECASE):
                        embed = discord.Embed(
                            title="Role Name Change Attempt",
                            description=f"User {ctx.author.mention} attempted to change their role name to a name containing a banned word.",
                            color=discord.Color.red()
                        )
                        embed.add_field(
                            name="User", value=ctx.author.mention, inline=False)
                        embed.add_field(name="Attempted Role Name",
                                        value=new_name, inline=False)
                        embed.add_field(name="Banned Word",
                                        value=word, inline=False)

                        # Add the profile of the user who attempted the change
                        embed.set_author(name=ctx.author.name,
                                         icon_url=ctx.author.avatar.url)

                        query = f"SELECT log_channel_id FROM {table_name} WHERE guild_id = $1"
                        log_channel_id = await bot.pool.fetchval(query, ctx.guild.id)

                        if log_channel_id:
                            log_channel = bot.get_channel(
                                log_channel_id) if log_channel_id else None
                            if log_channel:
                                await log_channel.send(embed=embed)

                        error_embed = discord.Embed(
                            title="Role Name Update Failed",
                            description=f"The role name contains a banned word: `{word}`.",
                            color=discord.Color.red()
                        )
                        user_avatar_url = ctx.author.avatar.url
                        error_embed.set_thumbnail(url=user_avatar_url)
                        bot_avatar_url = bot.user.avatar.url
                        error_embed.set_footer(
                            text="HanniBot - hn help for commands", icon_url=bot_avatar_url)
                        await ctx.send(embed=error_embed)
                        return

            # Fetch the role_id from the database
            query = f"SELECT role_id FROM {table_name} WHERE user_id = $1"
            role_id = await bot.pool.fetchval(query, ctx.author.id)

            if not role_id:
                await send_error_message(ctx, "You don't have a custom role to edit.")
                return

            # Check if the custom role exists and if it's the author's top role
            custom_role = discord.utils.get(ctx.author.roles, id=role_id)

            if custom_role:
                try:
                    await custom_role.edit(name=new_name)

                    embed = discord.Embed(
                        title="Role Name Updated",
                        description=f"The role name has been updated successfully.",
                        color=discord.Color.pink()
                    )
                    user_avatar_url = ctx.author.avatar.url
                    embed.set_thumbnail(url=user_avatar_url)
                    bot_avatar_url = bot.user.avatar.url
                    embed.set_footer(
                        text="HanniBot - hn help for commands", icon_url=bot_avatar_url)
                    await ctx.send(embed=embed)
                except discord.Forbidden:
                    await send_error_message(ctx, "You don't have permission to edit this role.")
            else:
                await send_error_message(ctx, "The specified custom role does not exist.")

        elif action == "color":
            query = f"SELECT role_id FROM {table_name} WHERE user_id = $1"
            custom_role_id = await bot.pool.fetchval(query, ctx.author.id)

            if custom_role_id:
                custom_role = discord.utils.get(
                    ctx.author.roles, id=custom_role_id)

                if custom_role:
                    try:
                        # Convert hex to int, skip the first character "#"
                        color = discord.Color(int(args[1:], 16))
                        await custom_role.edit(color=color)

                        embed = discord.Embed(
                            title="Role Color Updated",
                            description=f"{custom_role.mention}'s color has been updated successfully.",
                            color=color,
                        )
                        user_avatar_url = ctx.author.avatar.url
                        embed.set_thumbnail(url=user_avatar_url)
                        bot_avatar_url = bot.user.avatar.url
                        embed.set_footer(
                            text="HanniBot - hn help for commands", icon_url=bot_avatar_url)
                        await ctx.send(embed=embed)
                    except ValueError:
                        embed = discord.Embed(
                            title="Role Color Update Failed",
                            description="Invalid color value. Please provide a valid hexadecimal color value.",
                            color=discord.Color.red(),
                        )
                        user_avatar_url = ctx.author.avatar.url
                        embed.set_thumbnail(url=user_avatar_url)
                        bot_avatar_url = bot.user.avatar.url
                        embed.set_footer(
                            text="HanniBot - hn help for commands", icon_url=bot_avatar_url)
                        await ctx.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title="Role Color Update Failed",
                        description="You don't have permission to edit this role. Only the user with the role can edit it.",
                        color=discord.Color.red(),
                    )
                    await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Role Color Update Failed",
                    description="You don't have a custom role to edit.",
                    color=discord.Color.red(),
                )
                await ctx.send(embed=embed)


@bot.command()
async def addbanword(ctx, regex: bool = False, *, word):
    async with ctx.typing():
        if ctx.author.guild_permissions.manage_roles:
            guild_id = ctx.guild.id
            guild_table_name = f"guild_{guild_id}"

            # Fetch existing ban words for the guild
            query = f"SELECT ban_words FROM {guild_table_name} WHERE guild_id = $1"
            existing_ban_words = await bot.pool.fetchval(query, guild_id)

            if existing_ban_words:
                existing_ban_words = existing_ban_words.split(
                    ',') if existing_ban_words else []
            else:
                existing_ban_words = []

            # Check if the word is already in the ban words list
            if word.lower() in existing_ban_words:
                embed = discord.Embed(
                    title="Banned Word",
                    description="This word is already in the ban words list.",
                    color=discord.Color.red()
                )
            else:
                if regex:
                    try:
                        # Attempt to compile the word as a regex pattern
                        re.compile(word)
                        existing_ban_words.append(word)
                    except re.error:
                        # Invalid regex pattern
                        embed = discord.Embed(
                            title="Invalid Regular Expression",
                            description="The provided regular expression pattern is invalid.",
                            color=discord.Color.red()
                        )
                        await ctx.send(embed=embed)
                        return
                else:
                    # Append the new ban word to the existing list as a plain word
                    existing_ban_words.append(word.lower())

                # Join the ban words into a single string
                updated_ban_words_str = ','.join(existing_ban_words)

                query = f"UPDATE {guild_table_name} SET ban_words = $1 WHERE guild_id = $2"
                await bot.pool.execute(query, updated_ban_words_str, guild_id)

                embed = discord.Embed(
                    title="Banned Words",
                    description=f"{'Regex ' if regex else ''}**{word}** has been added to the guild's ban words list.",
                    color=discord.Color.pink()
                )

            user_avatar_url = ctx.author.avatar.url
            embed.set_thumbnail(url=user_avatar_url)
            bot_avatar_url = bot.user.avatar.url
            embed.set_footer(text="HanniBot - hn help for commands",
                             icon_url=bot_avatar_url)
            await ctx.send(embed=embed)
        else:
            # Inform the user that they don't have the required permission
            embed = discord.Embed(
                title="Add Banned Word",
                description="You don't have permission to use this command. You need the 'Manage Roles' permission.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)


@bot.command()
async def removebanword(ctx, *, word):
    async with ctx.typing():
        if ctx.author.guild_permissions.manage_roles:
            guild_id = ctx.guild.id
            guild_table_name = f"guild_{guild_id}"

            # Fetch existing ban words for the guild
            query = f"SELECT ban_words FROM {guild_table_name} WHERE guild_id = $1"
            ban_words_result = await bot.pool.fetchval(query, guild_id)

            embed = discord.Embed(color=discord.Color.red())

            if ban_words_result:
                ban_words = ban_words_result.split(
                    ',') if ban_words_result else []

                # Check if the input is a number
                if word.isdigit():
                    word_index = int(word) - 1  # Convert to 0-based index
                    if 0 <= word_index < len(ban_words):
                        removed_word = ban_words.pop(word_index)

                        updated_ban_words_str = ','.join(ban_words)
                        query = f"UPDATE {guild_table_name} SET ban_words = $1 WHERE guild_id = $2"
                        await bot.pool.execute(query, updated_ban_words_str, guild_id)

                        embed.title = "Ban Word Removed"
                        embed.description = f"**{removed_word}** has been removed from the ban words list."
                        embed.color = discord.Color.pink()
                    else:
                        embed.title = "Invalid Index"
                        embed.description = "The specified index is out of range."
                elif word.lower() in [w.strip().lower() for w in ban_words]:
                    updated_ban_words = [
                        w for w in ban_words if w.strip().lower() != word.lower()]

                    updated_ban_words_str = ','.join(updated_ban_words)
                    query = f"UPDATE {guild_table_name} SET ban_words = $1 WHERE guild_id = $2"
                    await bot.pool.execute(query, updated_ban_words_str, guild_id)

                    embed.title = "Ban Word Removed"
                    embed.description = f"**{word}** has been removed from the ban words list."
                    embed.color = discord.Color.pink()
                else:
                    embed.title = "Ban Word Removal Failed"
                    embed.description = f"{word} is not in the ban words list."
            else:
                embed.title = "No Ban Words Found"
                embed.description = "No ban words found for this guild."
                embed.color = discord.Color.blue()

            user_avatar_url = ctx.author.avatar.url
            embed.set_thumbnail(url=user_avatar_url)
            bot_avatar_url = bot.user.avatar.url
            embed.set_footer(text="HanniBot - hn help for commands",
                             icon_url=bot_avatar_url)

            await ctx.send(embed=embed)
        else:
            # Inform the user that they don't have the required permission
            embed = discord.Embed(
                title="Remove Ban Word",
                description="You don't have permission to use this command. You need the 'Manage Roles' permission.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)


@bot.command()
async def listbanwords(ctx):
    async with ctx.typing():
        if ctx.author.guild_permissions.manage_roles:
            guild_id = ctx.guild.id
            guild_table_name = f"guild_{guild_id}"

            # Fetch existing ban words for the guild
            query = f"SELECT ban_words FROM {guild_table_name} WHERE guild_id = $1"
            ban_words_result = await bot.pool.fetchval(query, guild_id)

            if not ban_words_result:
                embed = discord.Embed(
                    title="Banned Words List",
                    description="No banned words are currently set for this guild.",
                    color=discord.Color.blue()
                )
                user_avatar_url = ctx.author.avatar.url
                embed.set_thumbnail(url=user_avatar_url)
                bot_avatar_url = bot.user.avatar.url
                embed.set_footer(
                    text="HanniBot - hn help for commands", icon_url=bot_avatar_url)
                await ctx.send(embed=embed)
                return

            ban_words = ban_words_result.split(',') if ban_words_result else []
            total_ban_words = len(ban_words)

            # Split and enumerate the banned words
            formatted_ban_words = "\n".join(
                [f"{i+1}. {word}" for i, word in enumerate(ban_words)])

            # Split the formatted banned words into chunks of 10 items
            items_per_page = 10
            formatted_ban_words_list = formatted_ban_words.split('\n')
            formatted_ban_words_chunks = [
                formatted_ban_words_list[i:i + items_per_page] for i in range(0, len(formatted_ban_words_list), items_per_page)]

            embeds = []
            for i, chunk in enumerate(formatted_ban_words_chunks):
                embed = discord.Embed(
                    title=f"Banned Words List - (Total: {total_ban_words})",
                    description='\n'.join(chunk),
                    color=discord.Color.pink()
                )
                embed.set_thumbnail(url=bot.user.avatar.url)
                embed.set_footer(
                    text=f"Page {i+1}/{len(formatted_ban_words_chunks)}")
                embeds.append(embed)

            current_page = 0
            msg = await ctx.send(embed=embeds[current_page])
            await msg.add_reaction("⬅️")
            await msg.add_reaction("➡️")

            def check(reaction, user):
                return user == ctx.author and reaction.message == msg and str(reaction.emoji) in ["⬅️", "➡️"]

            while True:
                try:
                    reaction, user = await bot.wait_for("reaction_add", timeout=60, check=check)

                    if str(reaction.emoji) == "➡️" and current_page < len(embeds) - 1:
                        current_page += 1
                    elif str(reaction.emoji) == "⬅️" and current_page > 0:
                        current_page -= 1

                    await msg.edit(embed=embeds[current_page])
                    await msg.remove_reaction(reaction, user)
                except TimeoutError:
                    break

            await msg.clear_reactions()
        else:
            # Inform the user that they don't have the required permission
            embed = discord.Embed(
                title="List Banned Words",
                description="You don't have permission to use this command. You need the 'Manage Roles' permission.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)


@bot.command()
async def server(ctx, role_type: str):
    if ctx.author.guild_permissions.manage_roles:
        if role_type.lower() in ["role", "privaterole"]:
            if ctx.message.role_mentions:
                role_mention = ctx.message.role_mentions[0]  # Mentioned role

                guild_id = ctx.guild.id
                guild_table_name = f"guild_{guild_id}"

                # Check if the table exists in the database
                query = f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)"
                table_exists = await bot.pool.fetchval(query, guild_table_name)

                if not table_exists:
                    # Create a new table for the guild if it doesn't exist
                    query = f'''CREATE TABLE IF NOT EXISTS {guild_table_name}
                               (user_id BIGINT, guild_id BIGINT, role_id BIGINT, ban_words TEXT, 
                               booster_role_id BIGINT, greeting_message TEXT, greeting_channel_id BIGINT, log_channel_id BIGINT)'''
                    await bot.pool.execute(query)

                # Insert the booster identifier role into the new table
                query = f"INSERT INTO {guild_table_name} (guild_id, booster_role_id) VALUES ($1, $2)"
                await bot.pool.execute(query, guild_id, role_mention.id)

                embed = discord.Embed(
                    title="Role Set",
                    description=f"The {role_type} has been set successfully.",
                    color=discord.Color.pink()
                )

                # Add user's avatar as a rounded image beside the title
                user_avatar_url = ctx.author.avatar.url
                embed.set_thumbnail(url=user_avatar_url)
                bot_avatar_url = bot.user.avatar.url
                embed.set_footer(text="HanniBot - hn help for commands",
                                 icon_url=bot_avatar_url)
                await ctx.send(embed=embed)
            else:
                await send_error_message(ctx, "Please mention a valid role to be set as the booster role.")
        else:
            await send_error_message(ctx, "Invalid role type. Use `role` or `privaterole`.")
    else:
        await send_error_message(ctx, "You don't have permission to use this command. You need the 'Manage Roles' permission.")


@bot.event
async def on_boost(guild, user):
    guild_id = guild.id
    guild_table_name = f"guild_{guild_id}"

    # Check if the table exists in the database
    query = f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)"
    table_exists = await bot.pool.fetchval(query, guild_table_name)

    if not table_exists:
        return  # The table doesn't exist yet

    # Fetch the booster role ID from the database
    query = f"SELECT booster_role_id FROM {guild_table_name} WHERE guild_id = $1"
    booster_role_id = await bot.pool.fetchval(query, guild.id)

    if booster_role_id:
        booster_role = discord.utils.get(guild.roles, id=booster_role_id)

        if booster_role and booster_role in user.roles:
            # Fetch the greeting channel ID from the database
            query = f"SELECT greeting_channel_id FROM {guild_table_name} WHERE guild_id = $1"
            greeting_channel_id = await bot.pool.fetchval(query, guild.id)

            if greeting_channel_id:
                greeting_channel = guild.get_channel(greeting_channel_id)

                if greeting_channel:
                    # Check if a custom greeting message is set
                    query = f"SELECT greeting_message FROM {guild_table_name} WHERE guild_id = $1"
                    greeting_message = await bot.pool.fetchval(query, guild.id)

                    if greeting_message:
                        greeting_message_plain = greeting_message.replace(
                            "{user}", user.mention)
                        await greeting_channel.send(greeting_message_plain)


async def on_member_update(before, after):
    if after.guild:
        guild_id = after.guild.id
        guild_table_name = f"guild_{guild_id}"

        # Check if the table exists in the database
        query = f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)"
        table_exists = await bot.pool.fetchval(query, guild_table_name)

        if not table_exists:
            return  # The table doesn't exist yet

        # Fetch the booster role ID from the database
        query = f"SELECT booster_role_id FROM {guild_table_name} WHERE guild_id = $1"
        booster_role_id = await bot.pool.fetchval(query, guild_id)

        if not booster_role_id:
            return  # No result found for booster_role_id

        if booster_role_id is None:
            return  # Booster identifier role not set

        booster_role = discord.utils.get(after.guild.roles, id=booster_role_id)

        if booster_role in before.roles and booster_role not in after.roles:
            # Fetch the role_id from the database
            query = f"SELECT role_id FROM {guild_table_name} WHERE user_id = $1"
            role_id = await bot.pool.fetchval(query, after.id)

            if role_id:
                custom_role = discord.utils.get(after.guild.roles, id=role_id)

                if custom_role:
                    # Check if the user still has the booster identifier role
                    if booster_role in after.roles:
                        return  # User still has the booster identifier role, do nothing

                    try:
                        # Remove the custom role from the user
                        await after.remove_roles(custom_role)
                    except discord.Forbidden:
                        print(
                            f"Bot does not have permission to remove the custom role.")
                    except Exception as e:
                        print(
                            f"An error occurred while removing the custom role: {e}")

                    # Now, delete the entire row for the user in the database
                    query = f"DELETE FROM {guild_table_name} WHERE user_id = $1"
                    await bot.pool.execute(query, after.id)

                    print(
                        f"Removed custom role and row for user {after.name} ({after.id})")

        # Fetch the log channel ID from the database
        query = f"SELECT log_channel_id FROM {guild_table_name} WHERE guild_id = $1"
        log_channel_id = await bot.pool.fetchval(query, guild_id)

        if log_channel_id:
            log_channel = discord.utils.get(
                after.guild.channels, id=log_channel_id)

            if log_channel:
                # Fetch the ban words for the user from the database
                query = f"SELECT ban_words FROM {guild_table_name} WHERE role_id = $1"
                ban_words_str = await bot.pool.fetchval(query, after.id)

                if ban_words_str:
                    ban_words = ban_words_str.split(',')

                    for word in ban_words:
                        if word.lower() in after.name.lower():
                            log_message = f"User {after.mention} attempted to change their role name to '{after.name}', which contains a banned word."
                            await log_channel.send(log_message)
                            break  # Stop checking if a banned word is found


async def on_guild_role_update(before, after):
    if before.name != after.name:
        guild_id = after.guild.id
        guild_table_name = f"guild_{guild_id}"

        # Check if the table exists in the database
        query = f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)"
        table_exists = await bot.pool.fetchval(query, guild_table_name)

        if not table_exists:
            return  # The table doesn't exist yet

        # Fetch the ban words for the guild from the database
        query = f"SELECT ban_words FROM {guild_table_name} WHERE guild_id = $1"
        ban_words_str = await bot.pool.fetchval(query, guild_id)

        if ban_words_str:
            ban_words = ban_words_str.split(',')

            for word in ban_words:
                if word.lower() in after.name.lower():
                    # Modify the role name to "Filtered_Name" in the database
                    query = f"UPDATE {guild_table_name} SET role_name = $1 WHERE role_id = $2"
                    await bot.pool.execute(query, "Filtered_Name", after.id)

                    # Modify the role's name
                    await after.edit(name="Filtered_Name")
                    break  # Stop checking if a banned word is found


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')


async def initialize_bot():
    pool = await create_pg_pool()
    bot.pool = pool
    await bot.start('MTE0NDgwOTk0NjExOTE0MzUzNQ.GekBmF.vxb8TsdwC5VvlsC5qqK7MvnrtgM5HbBYOqTWYI')

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(initialize_bot())
