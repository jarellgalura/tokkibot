import discord
from discord.ext import commands
import sqlite3
intents = discord.Intents.all()
intents.members = True

bot = commands.Bot(command_prefix='$', intents=intents)

# SQLite Database Setup
conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()

greeting_message = "Thank you for boosting! We appreciate your support."
greeting_channel = None  # Store the greeting channel


@bot.group(invoke_without_command=True)
@commands.has_permissions(manage_roles=True, manage_channels=True)
async def greet(ctx):
    """
    Manage greeting settings.
    Usage: $greeting <channel|message>
    """
    await ctx.send("Invalid subcommand. Use `$help greeting` for usage information.")


@greet.command(name="message")
async def set_greeting_message(ctx, *, message):
    if ctx.author.guild_permissions.manage_roles:
        cursor.execute(f"UPDATE guild_{ctx.guild.id} SET greeting_message = ? WHERE guild_id = ?",
                       (message, ctx.guild.id))
        conn.commit()
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
        cursor.execute(f"UPDATE guild_{ctx.guild.id} SET greeting_channel_id = ? WHERE guild_id = ?",
                       (channel.id, ctx.guild.id))
        conn.commit()
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
    Usage: $greettest
    """
    global greeting_message

    booster_role_id = cursor.execute(
        f"SELECT booster_role_id FROM guild_{ctx.guild.id} WHERE guild_id = ?", (ctx.guild.id,)).fetchone()

    if booster_role_id is not None and booster_role_id[0] is not None:
        booster_role = discord.utils.get(
            ctx.guild.roles, id=booster_role_id[0])

        if booster_role in ctx.author.roles:
            greeting_channel_id = cursor.execute(
                f"SELECT greeting_channel_id FROM guild_{ctx.guild.id} WHERE guild_id = ?", (ctx.guild.id,)).fetchone()
            greeting_channel = ctx.guild.get_channel(
                greeting_channel_id[0]) if greeting_channel_id and greeting_channel_id[0] else None

            if greeting_channel:
                greeting_message_plain = greeting_message.replace(
                    "{user}", ctx.author.mention)
                await greeting_channel.send(greeting_message_plain)
                await ctx.send("Greeting message sent for testing.")
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
    embed.set_footer(text="HanniBot - $help for commands",
                     icon_url=bot_avatar_url)
    await ctx.send(embed=embed)


@bot.command()
async def claim(ctx):
    async with ctx.typing():
        print(f"Guild ID: {ctx.guild.id}")  # Debug print

    # Fetch the booster identifier role ID from the database
    booster_identifier_role_id = cursor.execute(
        f"SELECT booster_role_id FROM guild_{ctx.guild.id} WHERE guild_id = ?", (ctx.guild.id,)).fetchone()

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
                custom_role_id = cursor.execute(
                    f"SELECT role_id FROM guild_{ctx.guild.id} WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, ctx.author.id)).fetchone()

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

                    # Assign the role to the user
                    await ctx.author.add_roles(custom_role)

                    # Insert the new row into the database for the user's custom role
                    cursor.execute(f"INSERT INTO guild_{ctx.guild.id} (user_id, role_id, guild_id) VALUES (?, ?, ?)",
                                   (ctx.author.id, custom_role.id, ctx.guild.id))
                    conn.commit()

                    embed = discord.Embed(
                        title="Custom Role Claimed",
                        description=f"You've been granted a custom role: {custom_role.mention}\n\n **Edit your role:**\n **Name:** $role name NewName\n **Color:** $role color #FFFFFF",
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
    embed.set_footer(text="HanniBot - $help for commands",
                     icon_url=bot_avatar_url)

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

            # Fetch banned words and role IDs from the database
            role_ban_data = cursor.execute(
                f"SELECT role_id, ban_words FROM {table_name}").fetchall()

            for role_id, banned_words_str in role_ban_data:
                custom_role = discord.utils.get(ctx.guild.roles, id=role_id)

                if custom_role:
                    if banned_words_str:
                        ban_words = banned_words_str.split(',')
                        for word in ban_words:
                            if word.lower() in new_name.lower():
                                embed = discord.Embed(
                                    title="Role Name Update Failed",
                                    description=f"The role name contains a banned word: {word}.",
                                    color=discord.Color.red()
                                )
                                user_avatar_url = ctx.author.avatar.url
                                embed.set_thumbnail(url=user_avatar_url)
                                bot_avatar_url = bot.user.avatar.url
                                embed.set_footer(text="HanniBot - $help for commands",
                                                 icon_url=bot_avatar_url)
                                await ctx.send(embed=embed)

                                # Log the attempt to change role name to a banned word
                                log_message = f"User {ctx.author.mention} attempted to change their role name to **{new_name}**, which contains a banned word: **{word}**"
                                log_channel_id = cursor.execute(
                                    f"SELECT log_channel_id FROM {table_name} WHERE guild_id = ?", (ctx.guild.id,)).fetchone()
                                log_channel = bot.get_channel(
                                    log_channel_id[0])
                                if log_channel:
                                    await log_channel.send(log_message)

                                return

                    # If no banned words were found, proceed with the role name update
                    await custom_role.edit(name=new_name)

            # Role name updated successfully
            embed = discord.Embed(
                title="Role Name Updated",
                description=f"The role name has been updated successfully.",
                color=discord.Color.pink()
            )
            user_avatar_url = ctx.author.avatar.url
            embed.set_thumbnail(url=user_avatar_url)
            bot_avatar_url = bot.user.avatar.url
            embed.set_footer(text="HanniBot - $help for commands",
                             icon_url=bot_avatar_url)
            await ctx.send(embed=embed)

        elif action == "color":
            role_id = None
            role_id_result = cursor.execute(
                f"SELECT role_id FROM guild_{ctx.guild.id} WHERE user_id = ?", (ctx.author.id,)).fetchone()
            if role_id_result is not None and isinstance(role_id_result[0], int):
                role_id = role_id_result[0]
                custom_role = discord.utils.get(ctx.guild.roles, id=role_id)

            if custom_role is not None:
                try:
                    # Convert hex to int, skip the first character "#"
                    color = discord.Color(int(args[1:], 16))
                    await custom_role.edit(color=color)

                    embed = discord.Embed(
                        title="Role Color Updated",
                        description=f"{custom_role.mention}'s color has been updated successfully.",
                        color=color
                    )
                    user_avatar_url = ctx.author.avatar.url
                    embed.set_thumbnail(url=user_avatar_url)
                    bot_avatar_url = bot.user.avatar.url
                    embed.set_footer(text="HanniBot - $help for commands",
                                     icon_url=bot_avatar_url)
                    await ctx.send(embed=embed)
                except ValueError:
                    embed = discord.Embed(
                        title="Role Color Update Failed",
                        description="Invalid color value. Please provide a valid hexadecimal color value.",
                        color=discord.Color.red()
                    )
                    user_avatar_url = ctx.author.avatar.url
                    embed.set_thumbnail(url=user_avatar_url)
                    bot_avatar_url = bot.user.avatar.url
                    embed.set_footer(text="HanniBot - $help for commands",
                                     icon_url=bot_avatar_url)
                    await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Role Color Update Failed",
                    description="Please provide a valid hexadecimal color value.",
                    color=discord.Color.red()
                )
                user_avatar_url = ctx.author.avatar.url
                embed.set_thumbnail(url=user_avatar_url)
                bot_avatar_url = bot.user.avatar.url
                embed.set_footer(text="HanniBot - $help for commands",
                                 icon_url=bot_avatar_url)
                await ctx.send(embed=embed)

        elif action == "delete":
            role_id = cursor.execute(
                f"SELECT role_id FROM guild_{ctx.guild.id} WHERE user_id = ?", (ctx.author.id,)).fetchone()
            if role_id:
                role_id = role_id[0]
                custom_role = discord.utils.get(ctx.guild.roles, id=role_id)

                try:
                    await custom_role.delete()
                    cursor.execute(f"DELETE FROM guild_{ctx.guild.id} WHERE user_id = ?",
                                   (ctx.author.id,))
                    conn.commit()

                    embed = discord.Embed(
                        title="Custom Role Deleted",
                        description=f"Your role has been deleted.",
                        color=discord.Color.pink()
                    )
                except discord.NotFound:
                    embed = discord.Embed(
                        title="Role Delete Failed",
                        description="Your custom role has already been deleted.",
                        color=discord.Color.red()
                    )
            else:
                embed = discord.Embed(
                    title="Role Delete Failed",
                    description="You don't have a custom role to delete.",
                    color=discord.Color.red()
                )

            user_avatar_url = ctx.author.avatar.url
            embed.set_thumbnail(url=user_avatar_url)
            bot_avatar_url = bot.user.avatar.url
            embed.set_footer(text="HanniBot - $help for commands",
                             icon_url=bot_avatar_url)
            await ctx.send(embed=embed)


@bot.command()
async def addbanword(ctx, *, word):
    if ctx.author.guild_permissions.manage_roles:
        # Fetch existing ban words for the guild
        ban_words_result = cursor.execute(
            f"SELECT ban_words FROM guild_{ctx.guild.id} WHERE guild_id = ?", (ctx.guild.id,)).fetchone()

        existing_ban_words = ban_words_result[0].split(
            ',') if ban_words_result and ban_words_result[0] else []

        # Check if the word is already in the ban words list
        if word.lower() in existing_ban_words:
            embed = discord.Embed(
                title="Banned Word",
                description="This word is already in the ban words list.",
                color=discord.Color.red()
            )
        else:
            # Append the new ban word to the existing list$
            existing_ban_words.append(word.lower())

            # Join the ban words into a single string
            updated_ban_words_str = ','.join(existing_ban_words)

            cursor.execute(
                f"UPDATE guild_{ctx.guild.id} SET ban_words = ? WHERE guild_id = ?", (updated_ban_words_str, ctx.guild.id))
            conn.commit()

            embed = discord.Embed(
                title="Banned Words",
                description=f"**{word}** has been added to the guild's ban words list.",
                color=discord.Color.pink()
            )

        user_avatar_url = ctx.author.avatar.url
        embed.set_thumbnail(url=user_avatar_url)
        bot_avatar_url = bot.user.avatar.url
        embed.set_footer(text="HanniBot - $help for commands",
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
        ban_words_result = cursor.execute(
            f"SELECT ban_words FROM guild_{guild_id} WHERE guild_id = ?", (ctx.guild.id,)).fetchone()

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
                text="HanniBot - $help for commands", icon_url=bot_avatar_url)
            await ctx.send(embed=embed)
            return

        ban_words = ban_words_result[0].split(',')
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
        ban_words_result = cursor.execute(
            f"SELECT ban_words FROM guild_{guild_id}").fetchone()

        embed = discord.Embed(color=discord.Color.red())

        if ban_words_result and ban_words_result[0]:
            ban_words = ban_words_result[0].split(',')
            updated_ban_words = [
                w for w in ban_words if w.strip().lower() != word.lower()]

            if len(updated_ban_words) == len(ban_words):
                embed.title = "Ban Word Removal Failed"
                embed.description = f"{word} is not in the ban words list."
            else:
                updated_ban_words_str = ','.join(updated_ban_words)

                cursor.execute(
                    f"UPDATE guild_{guild_id} SET ban_words = ? WHERE guild_id = ?", (updated_ban_words_str, guild_id))
                conn.commit()

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
        embed.set_footer(text="HanniBot - $help for commands",
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
                cursor.execute(f'''CREATE TABLE IF NOT EXISTS {guild_table_name}
                                (user_id INTEGER, guild_id INTEGER, role_id INTEGER, ban_words TEXT, 
                                booster_role_id INTEGER, greeting_message TEXT, greeting_channel_id INTEGER, log_channel_id INTEGER)''')

                # Insert the booster identifier role into the new table
                cursor.execute(f"INSERT INTO {guild_table_name} (guild_id, booster_role_id) VALUES (?, ?)",
                               (ctx.guild.id, role_mention.id))
                conn.commit()

                embed = discord.Embed(
                    title="Role Set",
                    description=f"The booster role has been set successfully.",
                    color=discord.Color.pink()
                )

                # Add user's avatar as a rounded image beside the title
                user_avatar_url = ctx.author.avatar.url
                embed.set_thumbnail(url=user_avatar_url)
                bot_avatar_url = bot.user.avatar.url
                embed.set_footer(text="HanniBot - $help for commands",
                                 icon_url=bot_avatar_url)
                await ctx.send(embed=embed)
            else:
                await send_error_message(ctx, "Please mention a valid role to be set as the booster role.")
        else:
            await send_error_message(ctx, "Invalid role type. Use `role`, `privaterole`, or `boostrole`.")


@bot.event
async def on_boost(guild, user, ctx):
    global greeting_message

    booster_role_id = cursor.execute(
        f"SELECT booster_role_id FROM guild_{ctx.guild.id} WHERE guild_id = ?", (ctx.guild.id,)).fetchone()

    if booster_role_id is not None and booster_role_id[0] is not None:
        booster_role = discord.utils.get(guild.roles, id=booster_role_id[0])
        if booster_role in user.roles:
            greeting_channel_id = cursor.execute(
                f"SELECT greeting_channel_id FROM guild_{ctx.guild.id} WHERE guild_id = ?", (guild.id,)).fetchone()
            greeting_channel = guild.get_channel(
                greeting_channel_id[0]) if greeting_channel_id and greeting_channel_id[0] else None

            if greeting_channel:
                greeting_message_plain = greeting_message.replace(
                    "{user}", user.mention)
                await greeting_channel.send(greeting_message_plain)


@bot.event
async def on_member_update(before, after):
    if after.guild:
        guild_id = after.guild.id
        guild_table_name = f"guild_{guild_id}"

        try:
            cursor.execute(f"SELECT 1 FROM {guild_table_name} LIMIT 1")
        except sqlite3.OperationalError:
            return  # The table doesn't exist yet

        booster_role_id = cursor.execute(
            f"SELECT booster_role_id FROM {guild_table_name} WHERE guild_id = ?", (guild_id,)).fetchone()

        if booster_role_id is None or booster_role_id[0] is None:
            return  # Booster identifier role not set

        booster_role = discord.utils.get(
            after.guild.roles, id=booster_role_id[0])

        if booster_role in before.roles and booster_role not in after.roles:
            role_id = cursor.execute(
                f"SELECT role_id FROM {guild_table_name} WHERE user_id = ?", (after.id,)).fetchone()

            if role_id:
                custom_role = discord.utils.get(
                    after.guild.roles, id=role_id[0])

                if custom_role:
                    try:
                        await custom_role.delete()
                    except Exception as e:
                        print(
                            f"An error occurred while deleting the custom role: {e}")

                cursor.execute(
                    f"DELETE FROM {guild_table_name} WHERE user_id = ?", (after.id,))
                conn.commit()

        log_channel_id = cursor.execute(
            f"SELECT log_channel_id FROM {guild_table_name} WHERE guild_id = ?", (guild_id,)).fetchone()
        log_channel = bot.get_channel(log_channel_id[0])  # Fetch the channel

        if log_channel:
            ban_words_result = cursor.execute(
                f"SELECT ban_words FROM {guild_table_name} WHERE role_id = ?", (after.id,)).fetchone()

            if ban_words_result and ban_words_result[0]:
                ban_words = ban_words_result[0].split(',')
                for word in ban_words:
                    if word.lower() in after.name.lower():
                        log_message = f"User {after.mention} attempted to change their role name to '{after.name}', which contains a banned word."
                        await log_channel.send(log_message)
                        break  # Stop checking if a banned word is found


@bot.command(name="setlog")
async def set_log_channel(ctx, channel: discord.TextChannel):
    if ctx.author.guild_permissions.manage_roles:
        cursor.execute(f"UPDATE guild_{ctx.guild.id} SET log_channel_id = ? WHERE guild_id = ?",
                       (channel.id, ctx.guild.id))
        conn.commit()
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
        ban_words_result = cursor.execute(
            f"SELECT ban_words FROM guild_{after.guild.id} WHERE role_id = ?", (after.id,)).fetchone()
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
        ("```yaml\n$booster", "to list booster commands.```"),
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
         "$claim\n  ↳ Claim a custom role if you have the booster identifier role.\n"
         "$role name <new_name>\n  ↳ Change the name of your custom role.\n"
         "$role color <#FFFFFF>\n  ↳ Change the color of your custom role.\n"
         "$role delete\n  ↳ Delete your custom role.\n"
         "$addbanword <word>\n  ↳ Add a banned word to your custom role's ban list.\n"
         "$listbanwords\n  ↳ List all banned words in your custom roles' ban lists.\n"
         "$removebanword <word>\n  ↳ Remove a banned word from your custom role's ban list.\n"
         "$server <boostrole> <role_mention>\n  ↳ Set a specific role as the booster identifier role.\n"
         "$greet message\n  ↳ Sets a text greeting message to the boosters.\n"
         "$greet channel <channel>\n  ↳ a channel that will receive the messages.\n"
         "$greet test\n  ↳ Sends a sample greeting message in this channel.\n"
         "$setlog <channel>\n  ↳ a channel that will receive the logs for the role banned words.\n"
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


bot.run('MTE0NDE2NDM4ODE1NzI3MjEzNw.G1r_lp.BxIzRaqOJQ9aRHnEsXd3LRnpkPFHTHh8cwysWw')
