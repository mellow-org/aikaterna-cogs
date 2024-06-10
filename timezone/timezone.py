from datetime import datetime
from typing import Optional

import discord
import pytz
from fuzzywuzzy import fuzz, process
from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import close_menu, menu, DEFAULT_CONTROLS

__version__ = "3.0.0"


class Timezone(commands.Cog):
    """Gets times across the world..."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 278049241001, force_registration=True)
        default_user = {"usertime": None}
        self.config.register_user(**default_user)

    # Function to clear user data (Remove the whole user from db)
    async def clear_user_data(self, user: discord.User):
        await self.config.user(user).clear()

    async def get_usertime(self, user: discord.User):
        tz = None
        usertime = await self.config.user(user).usertime()
        if usertime:
            tz = pytz.timezone(usertime)

        return usertime, tz

    def fuzzy_timezone_search(self, tz: str):
        fuzzy_results = process.extract(tz.replace(" ", "_"), pytz.common_timezones, limit=500,
                                        scorer=fuzz.partial_ratio)
        matches = [x for x in fuzzy_results if x[1] > 98]
        return matches

    async def format_results(self, ctx, tz):
        if not tz:
            incorrect_embed = discord.Embed(
                    title="Error Occurred",
                    description="Incorrect format or no matching timezones found.",
                    color=(await ctx.embed_colour()),
                    timestamp=discord.utils.utcnow(),
                )
            incorrect_embed.add_field(
                name="Correct Usage",
                value="- Format: **`Continent/City`**\n"
                      "- Use correct capitalization or a partial timezone name.",
                inline=False
            )
            incorrect_embed.add_field(
                name="Examples",
                value="- `America/New_York`\n"
                      "- `New York`\n"
                      "- `Asia/Tokyo`",
                inline=False
            )
            await ctx.reply(
                embed=incorrect_embed,
                view=(await self.tzrelated_links())
            )
            return None
        elif len(tz) == 1:
            # command specific response, so don't do anything here
            return tz
        else:
            msg = ""
            for i, timezone in enumerate(tz, start=1):
                msg += f"{i}. {timezone[0]}\n"

            embed_list = []
            for page in pagify(msg, delims=["\n"], page_length=500):
                e = discord.Embed(
                    title=f"{len(tz)} results, please be more specific.",
                    description=page,
                    color=(await ctx.embed_colour()))
                e.set_footer(text="https://en.wikipedia.org/wiki/List_of_tz_database_time_zones")
                embed_list.append(e)
            if len(embed_list) == 1:
                close_control = {"\N{CROSS MARK}": close_menu}
                await menu(ctx, embed_list, close_control)
            else:
                await menu(ctx, embed_list, DEFAULT_CONTROLS)
            return None

    # Function to return a frequently used embed in the cog
    async def tznotset_embed(self, ctx):

        embed_tznotset = discord.Embed(
            title="Timezone Not Set",
            color=(await ctx.embed_colour()),
            description="You haven't set your timezone."
        )

        embed_tznotset.add_field(
            name="How To Set Your Timezone?",
            value=f"Use `{ctx.prefix}time me Continent/City` to set your timezone.",
            inline=False
        )
        embed_tznotset.add_field(
            name="Don't Know Your Timezone?",
            value="- If you don't know your timezone:\n"
                  "  - You can find it by [clicking here](https://whatismyti.me).\n"
                  "- You can see the list of timezones by [clicking here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).",
            inline=False
        )
        embed_tznotset.set_footer(text=f"\"{ctx.prefix}help time\" to view more time related commands!")
        return embed_tznotset

    # Function to return frequently used set of buttons in the cog
    async def tzrelated_links(self):
        view_links = discord.ui.View()
        view_links.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="Find Your Timezone",
            url="https://whatismyti.me")
        )
        view_links.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="Supported Timezones",
            url="https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
        ))
        return view_links

    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def time(self, ctx, member: Optional[discord.Member] = None):
        """
        Checks the time.

        For the list of supported timezones, see here:
        https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
        """
        target = member if member else ctx.author
        usertime, timezone_name = await self.get_usertime(target)

        if not usertime:
            if member:
                await ctx.reply(embed=discord.Embed(
                    description=f"<@{member.id}> hasn't set their timezone.",
                    color=(await ctx.embed_colour()),
                ), allowed_mentions=discord.AllowedMentions(replied_user=False))
            else:
                await ctx.reply(
                    embed=(await self.tznotset_embed(ctx)),
                    view=(await self.tzrelated_links()),
                    allowed_mentions=discord.AllowedMentions(replied_user=False)
                )
            return

        current_time = datetime.now(timezone_name)
        time_str = current_time.strftime("**%I:%M %p** (**%H:%M Hours**) %d-%B-%Y **%Z (UTC %z)**")
        msg = f"**{target.name}'s**" if target != ctx.author else "Your"
        msg += f" current timezone is **{usertime}.**\nThe current time is: {time_str}"
        await ctx.reply(
            content=msg,
            allowed_mentions=discord.AllowedMentions(replied_user=False)
        )

    @time.command()
    async def tz(self, ctx, *, timezone_name: Optional[str] = None):
        """Gets the time in any timezone."""
        if timezone_name is None:
            time = datetime.now()
            fmt = "**%H:%M** %d-%B-%Y"
            await ctx.send(f"Current system time: {time.strftime(fmt)}")
        else:
            tz_results = self.fuzzy_timezone_search(timezone_name)
            tz_resp = await self.format_results(ctx, tz_results)
            if tz_resp:
                time = datetime.now(pytz.timezone(tz_resp[0][0]))
                fmt = "**%H:%M** %d-%B-%Y **%Z (UTC %z)**"
                await ctx.send(time.strftime(fmt))

    @time.command()
    async def iso(self, ctx, *, iso_code=None):
        """Looks up ISO3166 country codes and gives you a supported timezone."""
        if iso_code is None:
            await ctx.send("That doesn't look like a country code!")
        else:
            exist = True if iso_code.upper() in pytz.country_timezones else False
            if exist is True:
                tz = str(pytz.country_timezones(iso_code.upper()))
                msg = (
                    f"Supported timezones for **{iso_code.upper()}:**\n{tz[:-1][1:]}"
                    f"\n**Use** `{ctx.prefix}time tz Continent/City` **to display the current time in that timezone.**"
                )
                await ctx.send(msg)
            else:
                await ctx.send(
                    "That code isn't supported.\nFor a full list, see here: "
                    "<https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes>\n"
                    "Use the two-character code under the `Alpha-2 code` column."
                )

    @time.command()
    async def me(self, ctx, *, timezone_name=None):
        """
        Sets your timezone.
        Usage: [p]time me Continent/City
        Using the command with no timezone will show your current timezone, if any.
        """
        if timezone_name is None:
            usertime, timezone_name = await self.get_usertime(ctx.author)
            if not usertime:
                await ctx.reply(
                    embed=(await self.tznotset_embed(ctx)),
                    view=(await self.tzrelated_links()),
                    allowed_mentions=discord.AllowedMentions(replied_user=False)
                )
            else:
                time = datetime.now(timezone_name)
                time = time.strftime("**%I:%M %p** (**%H:%M**) %d-%B-%Y **%Z (UTC %z)**")
                msg = f"Your current timezone is **{usertime}.**\n" f"The current time is: {time}"
                await ctx.send(msg)
        else:
            tz_results = self.fuzzy_timezone_search(timezone_name)
            tz_resp = await self.format_results(ctx, tz_results)
            if tz_resp:
                await self.config.user(ctx.author).usertime.set(tz_resp[0][0])
                await ctx.reply(embed=discord.Embed(
                    title="Timezone Set!",
                    description=f"Successfully set your timezone to **{tz_resp[0][0]}**.\n",
                    color=(await ctx.embed_colour()),
                    timestamp=discord.utils.utcnow()
                ), allowed_mentions=discord.AllowedMentions(replied_user=False))

    @time.command()
    async def user(self, ctx, user: discord.Member = None):
        """Shows the current time for the specified user."""
        if not user:
            await ctx.send("That isn't a user!")
        else:
            usertime, tz = await self.get_usertime(user)
            if usertime:
                time = datetime.now(tz)
                fmt = "**%H:%M** %d-%B-%Y **%Z (UTC %z)**"
                time = time.strftime(fmt)
                await ctx.send(
                    f"{user.name}'s current timezone is: **{usertime}**\n" f"The current time is: {str(time)}"
                )
            else:
                await ctx.send("That user hasn't set their timezone.")

    @time.command()
    async def compare(self, ctx, user: discord.Member = None):
        """Compare your saved timezone with another user's timezone."""
        if not user:
            return await ctx.send_help()

        usertime, user_tz = await self.get_usertime(ctx.author)
        othertime, other_tz = await self.get_usertime(user)

        if not usertime:
            return await ctx.reply(
                embed=(await self.tznotset_embed(ctx)),
                view=(await self.tzrelated_links()),
                allowed_mentions=discord.AllowedMentions(replied_user=False)
            )

        if not othertime:
            return await ctx.reply(embed=discord.Embed(
                    description=f"<@{user.id}> hasn't set their timezone.",
                    color=(await ctx.embed_colour()),
                ), allowed_mentions=discord.AllowedMentions(replied_user=False))

        user_now = datetime.now(user_tz)
        user_diff = user_now.utcoffset().total_seconds() / 60 / 60
        other_now = datetime.now(other_tz)
        other_diff = other_now.utcoffset().total_seconds() / 60 / 60
        time_diff = abs(user_diff - other_diff)
        time_diff_text = f"{time_diff:g}"
        fmt = "**%H:%M %Z (UTC %z)**"
        other_time = other_now.strftime(fmt)
        plural = "" if time_diff_text == "1" else "s"
        time_amt = "the same time zone as you" if time_diff_text == "0" else f"{time_diff_text} hour{plural}"
        position = "ahead of" if user_diff < other_diff else "behind"
        position_text = "" if time_diff_text == "0" else f" {position} you"

        await ctx.send(f"{user.display_name}'s time is {other_time} which is {time_amt}{position_text}.")

    # Command to clear the user data from the cog config
    @time.command()
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def clear(self, ctx):
        """Clear your time data from the bot."""
        usertime, tz = await self.get_usertime(ctx.author)
        if usertime is None:
            await ctx.reply(embed=discord.Embed(
                title="No User Data Found",
                description="I dont have any timezone data saved on you.",
                color=(await ctx.embed_colour()),
                timestamp=discord.utils.utcnow()
            ), allowed_mentions=discord.AllowedMentions(replied_user=False))
            return
        else:
            try:
                await self.clear_user_data(ctx.author)
            except Exception:
                await ctx.reply(embed=discord.Embed(
                    title="An Error Occurred",
                    description="An error occurred while trying to clear your timezone data.\n"
                                "Please report this issue to the bot owner.",
                    color=(await ctx.embed_colour()),
                    timestamp=discord.utils.utcnow()
                ), allowed_mentions=discord.AllowedMentions(replied_user=False))
            else:
                await ctx.reply(embed=discord.Embed(
                    title="Data Successfully Cleared",
                    description="Successfully cleared your timezone data.\n"
                                f"You can use `{ctx.prefix}time me` to set your timezone again.",
                    color=(await ctx.embed_colour()),
                    timestamp=discord.utils.utcnow()
                ), allowed_mentions=discord.AllowedMentions(replied_user=False))

    @time.command()
    async def version(self, ctx):
        """Show the cog version."""
        await ctx.reply(embed=discord.Embed(
            description=f"Timezone Version: `{__version__}`",
            color=(await ctx.embed_colour())
        ))

    @time.group(invoke_without_command=True)
    @commands.is_owner()
    async def manage(self, ctx):
        """Base command to manage time data of users."""
        await ctx.send_help()
        pass

    @manage.command()
    async def set(self, ctx, user: discord.User, *, timezone_name=None):
        """
        Allows the bot owner to set users' timezones.
        Use a user ID if the user is not present in your server.
        """
        if not user:
            user = ctx.author
        if len(self.bot.users) == 1:
            return await ctx.send("This cog requires Discord's Privileged Gateway Intents to function properly.")
        if user not in self.bot.users:
            return await ctx.send("I can't see that person anywhere.")
        if timezone_name is None:
            return await ctx.send_help()
        else:
            tz_results = self.fuzzy_timezone_search(timezone_name)
            tz_resp = await self.format_results(ctx, tz_results)
            if tz_resp:
                await self.config.user(user).usertime.set(tz_resp[0][0])
                await ctx.send(f"Successfully set {user.name}'s timezone to **{tz_resp[0][0]}**.")

    @manage.command()
    async def delete(self, ctx, user: discord.User):
        """
        Allows the bot owner to delete users' time data.
        Use a user ID if the user is not present in your server.
        """
        if not user:
            user = ctx.author
        if len(self.bot.users) == 1:
            return await ctx.send("This cog requires Discord's Privileged Gateway Intents to function properly.")
        if user not in self.bot.users:
            return await ctx.send("I can't see that person anywhere.")
        else:
            usertime, tz = await self.get_usertime(user)
            if usertime is None:
                await ctx.reply(embed=discord.Embed(
                    title="No User Data Found",
                    description="I dont have any timezone data saved on them.",
                    color=(await ctx.embed_colour()),
                    timestamp=discord.utils.utcnow()
                ), allowed_mentions=discord.AllowedMentions(replied_user=False))
                return
            else:
                try:
                    await self.clear_user_data(user)
                except Exception:
                    await ctx.reply(embed=discord.Embed(
                        title="An Error Occurred",
                        description="An error occurred while trying to clear your timezone data.",
                        color=(await ctx.embed_colour()),
                        timestamp=discord.utils.utcnow()
                    ), allowed_mentions=discord.AllowedMentions(replied_user=False))
                else:
                    await ctx.reply(embed=discord.Embed(
                        title="Data Successfully Cleared",
                        description="Successfully cleared their timezone data.\n"
                                    f"You can use `{ctx.prefix}time manage set` to set their timezone again.",
                        color=(await ctx.embed_colour()),
                        timestamp=discord.utils.utcnow()
                    ), allowed_mentions=discord.AllowedMentions(replied_user=False))

