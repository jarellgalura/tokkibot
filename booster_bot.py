import re  # Import the 're' module for regular expressions
import discord
from discord.ext import commands
import mysql.connector

intents = discord.Intents.all()
intents.members = True

bot = commands.Bot(command_prefix='hn ', intents=intents)

# MySQL Database Setup


def execute_query(query, values=None, fetchone=False, commit=False):
    db_connection = None
    try:
        db_connection = mysql.connector.connect(
            host="containers-us-west-48.railway.app",
            user="root",
            password="K7zECJ9XZBEeWKxMdblM",
            database="railway"
        )
        cursor = db_connection.cursor()

        cursor.execute(query, values)

        if fetchone:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()

        if commit:
            db_connection.commit()  # Commit the changes

        return result
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        if db_connection:
            db_connection.close()


# Helper function for executing SQL queries


greeting_message = "Thank you for boosting! We appreciate your support."
greeting_channel = None  # Store the greeting channel


@bot.group(invoke_without_command=True)
@commands.has_permissions(manage_roles=True, manage_channels=True)
async def greet(ctx):
    """
    Manage greeting settings.
    Usage: hn greeting <channel|message>
    """
    await ctx.send("Invalid subcommand. Use `hn help greeting` for usage information.")


@greet.command(name="message")
async def set_greeting_message(ctx, *, message):
    if ctx.author.guild_permissions.manage_roles:
        execute_query(f"UPDATE guild_{ctx.guild.id} SET greeting_message = %s WHERE guild_id = %s",
                      (message, ctx.guild.id), commit=True)
        await ctx.send("Greeting message has been updated.")
    else:
        # Inform the user that they don't have the required permission
        embed = discord.Embed(
            title="Set Greeting Message",
            description="You don't have permission to use this command. You need the 'Manage Roles' permission.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@greet.command(name="channel")
async def set_greeting_channel(ctx, channel: discord.TextChannel):
    if ctx.author.guild_permissions.manage_roles:
        execute_query(f"UPDATE guild_{ctx.guild.id} SET greeting_channel_id = %s WHERE guild_id = %s",
                      (channel.id, ctx.guild.id), commit=True)
        await ctx.send(f"Greeting channel has been set to {channel.mention}.")
    else:
        # Inform the user that they don't have the required permission
        embed = discord.Embed(
            title="Set Greeting Channel",
            description="You don't have permission to use this command. You need the 'Manage Roles' permission.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@greet.command(name="test")
async def greet_test(ctx):
    """
    Test the greeting message.
    Usage: hn greet test
    """
    global greeting_message

    booster_role_id_result = execute_query(
        f"SELECT booster_role_id FROM guild_{ctx.guild.id} WHERE guild_id = %s", (ctx.guild.id,))

    if booster_role_id_result and booster_role_id_result[0]:
        booster_role_id = booster_role_id_result[0][0]
        booster_role = discord.utils.get(
            ctx.guild.roles, id=booster_role_id)

        if booster_role in ctx.author.roles:
            greeting_channel_id_result = execute_query(
                f"SELECT greeting_channel_id FROM guild_{ctx.guild.id} WHERE guild_id = %s", (ctx.guild.id,))

            if greeting_channel_id_result and greeting_channel_id_result[0]:
                greeting_channel_id = greeting_channel_id_result[0][0]
                greeting_channel = ctx.guild.get_channel(greeting_channel_id)

                if greeting_channel:
                    # Check if a custom greeting message is set
                    greeting_message_result = execute_query(
                        f"SELECT greeting_message FROM guild_{ctx.guild.id} WHERE guild_id = %s", (ctx.guild.id,))

                    if greeting_message_result and greeting_message_result[0]:
                        greeting_message = greeting_message_result[0][0]

                    greeting_message_plain = greeting_message.replace(
                        "{user}", ctx.author.mention)
                    await greeting_channel.send(greeting_message_plain)
                    await ctx.send("Greeting message sent for testing.")
                else:
                    await ctx.send("Greeting channel not set.")
            else:
                await ctx.send("Greeting channel not set.")
        else:
            await ctx.send("You don't have permission to use this command. You need the 'Manage Roles' permission.")
    else:
        await ctx.send("Booster identifier role not set.")


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
    booster_identifier_role_id = execute_query(
        f"SELECT booster_role_id FROM guild_{ctx.guild.id} WHERE guild_id = %s", (ctx.guild.id,), fetchone=True)

    # Debug print
    print(f"Booster Identifier Role ID: {booster_identifier_role_id}")

    if booster_identifier_role_id is not None and booster_identifier_role_id[0] is not None:
        booster_role_id = booster_identifier_role_id[0]
        print(f"Booster Role ID: {booster_role_id}")  # Debug print

        booster_role = discord.utils.get(
            ctx.guild.roles, id=booster_role_id)

        if booster_role:
            print("Booster identifier role found")  # Debug print
            if booster_role in ctx.author.roles:
                custom_role_id = execute_query(
                    f"SELECT role_id FROM guild_{ctx.guild.id} WHERE guild_id = %s AND user_id = %s", (ctx.guild.id, ctx.author.id), fetchone=True)

                print(f"Custom Role ID: {custom_role_id}")

                if custom_role_id is None or not ctx.guild.get_role(custom_role_id[0]):
                    # Create a custom role
                    custom_role = await ctx.guild.create_role(name=f"{ctx.author.name}", color=discord.Color.random())

                    # Find the position of the booster identifier role
                    booster_identifier_position = booster_role.position

                    # Calculate the position for the custom role
                    custom_role_position = max(booster_identifier_position, 1)

                    # Edit the custom role's position
                    await custom_role.edit(position=custom_role_position)

                    # Check for banned words in the role name
                    ban_words_result = execute_query(
                        f"SELECT ban_words FROM guild_{ctx.guild.id} WHERE guild_id = %s", (ctx.guild.id,), fetchone=True)

                    if ban_words_result and ban_words_result[0]:
                        ban_words = ban_words_result[0].split(',')
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
                                log_channel_id_result = execute_query(
                                    f"SELECT log_channel_id FROM guild_{ctx.guild.id} WHERE guild_id = %s", (ctx.guild.id,), fetchone=True)
                                log_channel = bot.get_channel(
                                    log_channel_id_result[0]) if log_channel_id_result else None
                                if log_channel:
                                    await log_channel.send(log_message)

                                return

                    # Assign the role to the user
                    await ctx.author.add_roles(custom_role)

                    # Insert the new row into the database for the user's custom role
                    execute_query(f"INSERT INTO guild_{ctx.guild.id} (user_id, role_id, guild_id) VALUES (%s, %s, %s)",
                                  (ctx.author.id, custom_role.id, ctx.guild.id), commit=True)

                    embed = discord.Embed(
                        title="Custom Role Claimed",
                        description=f"You've been granted a custom role: {custom_role.mention}\n\n **Edit your role:**\n **Name:** `hn role name NewName`\n **Color:** `hn role color #FFFFFF`\n **Icon:** `Request to booster channel.`",
                        color=discord.Color.pink()
                    )
                else:
                    custom_role = ctx.guild.get_role(custom_role_id[0])
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

            # Fetch banned words from the database
            ban_words_result = execute_query(
                f"SELECT ban_words FROM {table_name} WHERE guild_id = %s", (ctx.guild.id,), fetchone=True)

            if ban_words_result and ban_words_result[0]:
                banned_words_str = ban_words_result[0]

                if banned_words_str:
                    ban_words = banned_words_str.split(',')
                    for word in ban_words:
                        # Use re.search to check if the banned word pattern is in the new role name
                        if re.search(fr"{word}", new_name, re.IGNORECASE):
                            embed = discord.Embed(
                                title="Role Name Update Failed",
                                description=f"The role name contains a banned word or pattern: {word}.",
                                color=discord.Color.red()
                            )
                            user_avatar_url = ctx.author.avatar.url
                            embed.set_thumbnail(url=user_avatar_url)
                            bot_avatar_url = bot.user.avatar.url
                            embed.set_footer(text="HanniBot - hn help for commands",
                                             icon_url=bot_avatar_url)
                            await ctx.send(embed=embed)

                            return

            custom_role = discord.utils.get(ctx.guild.roles, name=new_name)

            if custom_role:
                embed = discord.Embed(
                    title="Role Name Update Failed",
                    description="A role with that name already exists.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
            else:
                try:
                    await ctx.author.top_role.edit(name=new_name)

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
                    embed = discord.Embed(
                        title="Role Name Update Failed",
                        description="You don't have permission to edit this role.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)

        elif action == "color":
            role_id = None
            role_id_result = execute_query(
                f"SELECT role_id FROM guild_{ctx.guild.id} WHERE user_id = %s", (
                    ctx.author.id,)
            )

            if isinstance(role_id_result, list) and role_id_result:
                role_id = role_id_result[0][0]
                custom_role = discord.utils.get(ctx.guild.roles, id=role_id)

            if custom_role is not None:
                # Check if the author of the command is the user who has the custom role
                if ctx.author.top_role == custom_role:
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
    if ctx.author.guild_permissions.manage_roles:
        # Fetch existing ban words for the guild
        ban_words_result = execute_query(
            f"SELECT ban_words FROM guild_{ctx.guild.id} WHERE guild_id = %s", (ctx.guild.id,))

        if ban_words_result:
            existing_ban_words = ban_words_result[0][0].split(
                ',') if ban_words_result[0][0] else []
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

            execute_query(
                f"UPDATE guild_{ctx.guild.id} SET ban_words = %s WHERE guild_id = %s", (updated_ban_words_str, ctx.guild.id), commit=True)

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
async def listbanwords(ctx):
    if ctx.author.guild_permissions.manage_roles:
        guild_id = ctx.guild.id
        ban_words_result = execute_query(
            f"SELECT ban_words FROM guild_{guild_id} WHERE guild_id = %s", (ctx.guild.id,))

        if not ban_words_result or not ban_words_result[0]:
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

        ban_words = ban_words_result[0][0].split(',')
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
async def removebanword(ctx, *, word):
    if ctx.author.guild_permissions.manage_roles:
        guild_id = ctx.guild.id
        ban_words_result = execute_query(
            f"SELECT ban_words FROM guild_{guild_id} WHERE guild_id = %s", (guild_id,))

        embed = discord.Embed(color=discord.Color.red())

        if ban_words_result and ban_words_result[0]:
            ban_words = ban_words_result[0][0].split(',')
            updated_ban_words = [
                w for w in ban_words if w.strip().lower() != word.lower()]

            if len(updated_ban_words) == len(ban_words):
                embed.title = "Ban Word Removal Failed"
                embed.description = f"{word} is not in the ban words list."
            else:
                updated_ban_words_str = ','.join(updated_ban_words)

                execute_query(
                    f"UPDATE guild_{guild_id} SET ban_words = %s WHERE guild_id = %s", (updated_ban_words_str, guild_id), commit=True)

                embed.title = "Ban Word Removed"
                embed.description = f"**{word}** has been removed from the ban words list."
                embed.color = discord.Color.pink()
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
async def server(ctx, role_type: str):
    if ctx.author.guild_permissions.manage_roles:
        if role_type.lower() in ["role", "privaterole"]:
            if ctx.message.role_mentions:
                role_mention = ctx.message.role_mentions[0]  # Mentioned role

                # Create a new table for the guild
                guild_table_name = f"guild_{ctx.guild.id}"
                execute_query(f'''CREATE TABLE IF NOT EXISTS {guild_table_name}
                                (user_id BIGINT, guild_id BIGINT, role_id BIGINT, ban_words TEXT, 
                                booster_role_id BIGINT, greeting_message TEXT, greeting_channel_id BIGINT, log_channel_id BIGINT)''')

                # Insert the booster identifier role into the new table
                execute_query(f"INSERT INTO {guild_table_name} (guild_id, booster_role_id) VALUES (%s, %s)",
                              (ctx.guild.id, role_mention.id), commit=True)

                embed = discord.Embed(
                    title="Role Set",
                    description=f"The booster role has been set successfully.",
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
            await send_error_message(ctx, "Invalid role type. Use `role`, `privaterole`, or `boostrole`.")


@bot.event
async def on_boost(guild, user):
    booster_role_id_result = execute_query(
        f"SELECT booster_role_id FROM guild_{guild.id} WHERE guild_id = %s", (guild.id,))

    if booster_role_id_result and booster_role_id_result[0]:
        booster_role_id = booster_role_id_result[0][0]
        booster_role = discord.utils.get(guild.roles, id=booster_role_id)

        if booster_role and booster_role in user.roles:
            greeting_channel_id_result = execute_query(
                f"SELECT greeting_channel_id FROM guild_{guild.id} WHERE guild_id = %s", (guild.id,))

            if greeting_channel_id_result and greeting_channel_id_result[0]:
                greeting_channel_id = greeting_channel_id_result[0][0]
                greeting_channel = guild.get_channel(greeting_channel_id)

                if greeting_channel:
                    # Check if a custom greeting message is set
                    greeting_message_result = execute_query(
                        f"SELECT greeting_message FROM guild_{guild.id} WHERE guild_id = %s", (guild.id,))

                    if greeting_message_result and greeting_message_result[0]:
                        greeting_message = greeting_message_result[0][0]

                    greeting_message_plain = greeting_message.replace(
                        "{user}", user.mention)
                    await greeting_channel.send(greeting_message_plain)


@bot.event
async def on_member_update(before, after):
    if after.guild:
        guild_id = after.guild.id
        guild_table_name = f"guild_{guild_id}"

        try:
            execute_query(f"SELECT 1 FROM {guild_table_name} LIMIT 1")
        except mysql.OperationalError:
            return  # The table doesn't exist yet

        booster_role_id_results = execute_query(
            f"SELECT booster_role_id FROM {guild_table_name} WHERE guild_id = %s", (guild_id,))

        if not booster_role_id_results:
            return  # No result found for booster_role_id

        booster_role_id = booster_role_id_results[0][0]

        if booster_role_id is None:
            return  # Booster identifier role not set

        booster_role = discord.utils.get(
            after.guild.roles, id=booster_role_id)

        if booster_role in before.roles and booster_role not in after.roles:
            role_id_results = execute_query(
                f"SELECT role_id FROM {guild_table_name} WHERE user_id = %s", (after.id,))

            if not role_id_results:
                return  # No result found for role_id

            role_id = role_id_results[0][0]

            if role_id:
                custom_role = discord.utils.get(
                    after.guild.roles, id=role_id)

                if custom_role:
                    try:
                        await custom_role.delete()
                    except Exception as e:
                        print(
                            f"An error occurred while deleting the custom role: {e}")

                # Now, delete the entire row for the user in the database
                execute_query(
                    f"DELETE FROM {guild_table_name} WHERE user_id = %s", (after.id,), commit=True)

                print(
                    f"Deleted role and row for user {after.name} ({after.id})")

        log_channel_id_results = execute_query(
            f"SELECT log_channel_id FROM {guild_table_name} WHERE guild_id = %s", (guild_id,))

        if not log_channel_id_results:
            return  # No result found for log_channel_id

        log_channel_id = log_channel_id_results[0][0]

        log_channel = bot.get_channel(log_channel_id)  # Fetch the channel

        if log_channel:
            ban_words_results = execute_query(
                f"SELECT ban_words FROM {guild_table_name} WHERE role_id = %s", (after.id,))

            if not ban_words_results:
                return  # No result found for ban_words

            ban_words = ban_words_results[0][0].split(',')

            for word in ban_words:
                if word.lower() in after.name.lower():
                    log_message = f"User {after.mention} attempted to change their role name to '{after.name}', which contains a banned word."
                    await log_channel.send(log_message)
                    break  # Stop checking if a banned word is found


@bot.command(name="setlog")
async def set_log_channel(ctx, channel: discord.TextChannel):
    if ctx.author.guild_permissions.manage_roles:
        execute_query(f"UPDATE guild_{ctx.guild.id} SET log_channel_id = %s WHERE guild_id = %s",
                      (channel.id, ctx.guild.id), commit=True)
        await ctx.send(f"Logging channel has been set to {channel.mention}.")
    else:
        # Inform the user that they don't have the required permission
        embed = discord.Embed(
            title="Logs Channel",
            description="You don't have permission to use this command. You need the 'Manage Roles' permission.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@bot.event
async def on_guild_role_update(before, after):
    if before.name != after.name:
        guild_id = after.guild.id
        guild_table_name = f"guild_{guild_id}"

        ban_words_result = execute_query(
            f"SELECT ban_words FROM {guild_table_name} WHERE guild_id = %s", (guild_id,), fetchone=True)

        if ban_words_result and ban_words_result[0]:
            ban_words = ban_words_result[0].split(',')
            for word in ban_words:
                if word.lower() in after.name.lower():
                    await after.edit(name="Filtered_Name")
                    break  # Stop checking if a banned word is found

bot.remove_command("help")


@bot.command()
async def help(ctx):
    help_commands = [
        ("```yaml\nhn booster", "to list booster commands.```"),
    ]

    embed = discord.Embed(
        title="Hanni Bot Commands",
        description="List of available commands\n\n",
        color=discord.Color.pink()
    )

    # Add user's avatar as a rounded image beside the title
    user_avatar_url = ctx.author.avatar.url
    embed.set_author(name=ctx.author.display_name, icon_url=user_avatar_url)

    for command, description in help_commands:
        embed.description += f"{command} - {description}\n"

    # Add bot's avatar as a rounded image beside the footer
    bot_avatar_url = bot.user.avatar.url
    embed.set_footer(text="HanniBot - Created by Pray",
                     icon_url=bot_avatar_url)

    await ctx.send(embed=embed)


@bot.command()
async def booster(ctx):
    spacing_field = ("\n")
    booster_commands = [
        ("🚀 **Booster Commands**",
         "```yaml\n"
         "hn claim\n  ↳ Claim a custom role if you have the booster identifier role.\n"
         "hn role name <new_name>\n  ↳ Change the name of your custom role.\n"
         "hn role color <#FFFFFF>\n  ↳ Change the color of your custom role.\n"
         "hn role delete\n  ↳ Delete your custom role.\n"
         "hn addbanword true <regex>\n  ↳ Add a banned regex to your custom role's ban list.\n"
         "hn listbanwords\n  ↳ List all banned words in your custom roles' ban lists.\n"
         "hn removebanword <word>\n  ↳ Remove a banned word from your custom role's ban list.\n"
         "hn server <boostrole> <role_mention>\n  ↳ Set a specific role as the booster identifier role.\n"
         "hn greet message\n  ↳ Sets a text greeting message to the boosters.\n"
         "hn greet channel <channel>\n  ↳ a channel that will receive the messages.\n"
         "hn greet test\n  ↳ Sends a sample greeting message in this channel.\n"
         "hn setlog <channel>\n  ↳ a channel that will receive the logs for the role banned words.\n"
         "```"),
    ]

    embed = discord.Embed(
        title="Hanni Bot Commands",
        description="List of available commands\n\n",
        color=discord.Color.pink()
    )

    # Add user's avatar as a rounded image beside the title
    user_avatar_url = ctx.author.avatar.url
    embed.set_author(name=ctx.author.display_name, icon_url=user_avatar_url)

    for title, value in booster_commands:
        embed.add_field(name=title, value=value, inline=False)

    # Add a blank field for spacing
    embed.add_field(name=spacing_field, value="\u200b", inline=False)

    # Add bot's avatar as a rounded image beside the footer
    bot_avatar_url = bot.user.avatar.url
    embed.set_footer(text="HanniBot - Created by Pray",
                     icon_url=bot_avatar_url)

    await ctx.send(embed=embed)


@bot.event
async def on_disconnect():
    execute_query.close()


bot.run('MTE0NDE2NDM4ODE1NzI3MjEzNw.G9QUlB.UfLDKULtmSlbrb33YT1mCJ7n1sEb8puQobX_jI')
