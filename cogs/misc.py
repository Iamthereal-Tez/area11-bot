# cogs/misc.py
import discord
from discord import app_commands
from discord.ext import commands
import random
import aiohttp
from io import BytesIO
import datetime

class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Ping
    @commands.command(name="ping")
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"🏓 Pong! {latency}ms")

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping_slash(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! {latency}ms")

    # Avatar
    @commands.command(name="avatar", aliases=["av"])
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"{member.display_name}'s Avatar", color=discord.Color.blue())
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @app_commands.command(name="avatar", description="Get a user's avatar")
    async def avatar_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        embed = discord.Embed(title=f"{user.display_name}'s Avatar", color=discord.Color.blue())
        embed.set_image(url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    # Userinfo
    @commands.command(name="userinfo", aliases=["ui"])
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        
        # Get user's XP and warns
        xp = await self.bot.db.get_user(member.id, ctx.guild.id)
        level = self.bot.db.xp_to_level(xp)
        warns = await self.bot.db.get_warns(member.id, ctx.guild.id)
        
        # Get user's rank
        leaderboard = await self.bot.db.get_leaderboard(ctx.guild.id, 1000)
        user_ids = [user_id for user_id, _ in leaderboard]
        try:
            rank = user_ids.index(member.id) + 1
        except ValueError:
            rank = len(user_ids) + 1
        
        embed = discord.Embed(title=f"{member}", color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="Rank", value=f"#{rank}", inline=True)
        embed.add_field(name="XP", value=xp, inline=True)
        embed.add_field(name="Warns", value=warns, inline=True)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
        
        # Show time since joined
        days_since_join = (datetime.datetime.now(datetime.timezone.utc) - member.joined_at).days
        embed.add_field(name="Days in Server", value=days_since_join, inline=True)
        
        # Show booster status
        if member.premium_since:
            boost_days = (datetime.datetime.now(datetime.timezone.utc) - member.premium_since).days
            embed.add_field(name="Boosting Since", value=f"{boost_days} days", inline=True)
        
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        if roles:
            embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles) if len(roles) < 5 else f"{len(roles)} roles", inline=False)
        
        await ctx.send(embed=embed)

    @app_commands.command(name="userinfo", description="Show info about a user")
    async def userinfo_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        
        # Get user's XP and warns
        xp = await self.bot.db.get_user(user.id, interaction.guild.id)
        level = self.bot.db.xp_to_level(xp)
        warns = await self.bot.db.get_warns(user.id, interaction.guild.id)
        
        # Get user's rank
        leaderboard = await self.bot.db.get_leaderboard(interaction.guild.id, 1000)
        user_ids = [user_id for user_id, _ in leaderboard]
        try:
            rank = user_ids.index(user.id) + 1
        except ValueError:
            rank = len(user_ids) + 1
        
        embed = discord.Embed(title=f"{user}", color=discord.Color.green())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="Rank", value=f"#{rank}", inline=True)
        embed.add_field(name="XP", value=xp, inline=True)
        embed.add_field(name="Warns", value=warns, inline=True)
        embed.add_field(name="Account Created", value=user.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d"), inline=True)
        
        # Show time since joined
        days_since_join = (datetime.datetime.now(datetime.timezone.utc) - user.joined_at).days
        embed.add_field(name="Days in Server", value=days_since_join, inline=True)
        
        # Show booster status
        if user.premium_since:
            boost_days = (datetime.datetime.now(datetime.timezone.utc) - user.premium_since).days
            embed.add_field(name="Boosting Since", value=f"{boost_days} days", inline=True)
        
        roles = [r.mention for r in user.roles if r.name != "@everyone"]
        if roles:
            embed.add_field(name=f"Roles ({len(roles)})", value=" ".join(roles) if len(roles) < 5 else f"{len(roles)} roles", inline=False)
        
        await interaction.response.send_message(embed=embed)

    # Server info
    @commands.command(name="serverinfo", aliases=["si"])
    async def serverinfo(self, ctx):
        g = ctx.guild
        
        # Get server stats
        online = len([m for m in g.members if m.status != discord.Status.offline])
        bots = len([m for m in g.members if m.bot])
        
        embed = discord.Embed(title=f"{g.name}", description=g.description or "", color=discord.Color.blurple())
        embed.set_thumbnail(url=g.icon.url if g.icon else None)
        embed.add_field(name="Owner", value=g.owner, inline=True)
        embed.add_field(name="Members", value=f"{g.member_count} ({online} online)", inline=True)
        embed.add_field(name="Bots", value=bots, inline=True)
        embed.add_field(name="Channels", value=f"{len(g.text_channels)} Text | {len(g.voice_channels)} Voice", inline=True)
        embed.add_field(name="Roles", value=len(g.roles), inline=True)
        embed.add_field(name="Emojis", value=len(g.emojis), inline=True)
        embed.add_field(name="Boosts", value=g.premium_subscription_count, inline=True)
        embed.add_field(name="Boost Level", value=g.premium_tier, inline=True)
        embed.add_field(name="Created", value=g.created_at.strftime("%Y-%m-%d"), inline=True)
        
        await ctx.send(embed=embed)

    @app_commands.command(name="serverinfo", description="Show server info")
    async def serverinfo_slash(self, interaction: discord.Interaction):
        g = interaction.guild
        
        # Get server stats
        online = len([m for m in g.members if m.status != discord.Status.offline])
        bots = len([m for m in g.members if m.bot])
        
        embed = discord.Embed(title=f"{g.name}", description=g.description or "", color=discord.Color.blurple())
        embed.set_thumbnail(url=g.icon.url if g.icon else None)
        embed.add_field(name="Owner", value=g.owner, inline=True)
        embed.add_field(name="Members", value=f"{g.member_count} ({online} online)", inline=True)
        embed.add_field(name="Bots", value=bots, inline=True)
        embed.add_field(name="Channels", value=f"{len(g.text_channels)} Text | {len(g.voice_channels)} Voice", inline=True)
        embed.add_field(name="Roles", value=len(g.roles), inline=True)
        embed.add_field(name="Emojis", value=len(g.emojis), inline=True)
        embed.add_field(name="Boosts", value=g.premium_subscription_count, inline=True)
        embed.add_field(name="Boost Level", value=g.premium_tier, inline=True)
        embed.add_field(name="Created", value=g.created_at.strftime("%Y-%m-%d"), inline=True)
        
        await interaction.response.send_message(embed=embed)

    # Coinflip
    @commands.command(name="coinflip", aliases=["flip"])
    async def coinflip(self, ctx):
        res = random.choice(["Heads", "Tails"])
        await ctx.send(f"🪙 {res}")

    @app_commands.command(name="coinflip", description="Flip a coin")
    async def coinflip_slash(self, interaction: discord.Interaction):
        res = random.choice(["Heads", "Tails"])
        await interaction.response.send_message(f"🪙 {res}")

    # 8ball
    @commands.command(name="8ball")
    async def eightball(self, ctx, *, question: str):
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes - definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.",
            "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."
        ]
        answer = random.choice(responses)
        embed = discord.Embed(title="🎱 8Ball", color=discord.Color.purple())
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=answer, inline=False)
        await ctx.send(embed=embed)

    @app_commands.command(name="8ball", description="Ask the magic 8ball a question")
    @app_commands.describe(question="Your question")
    async def eightball_slash(self, interaction: discord.Interaction, question: str):
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes - definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.",
            "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."
        ]
        answer = random.choice(responses)
        embed = discord.Embed(title="🎱 8Ball", color=discord.Color.purple())
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=answer, inline=False)
        await interaction.response.send_message(embed=embed)

    # Help command
    @commands.command(name="help")
    async def help_custom(self, ctx):
        embed = discord.Embed(title="🤖 Bot Help", description=f"Prefix: `{BOT_PREFIX}`", color=discord.Color.blue())
        
        # Level commands
        embed.add_field(
            name="🎮 Level Commands",
            value=f"`{BOT_PREFIX}level [user]` - Show level\n"
                  f"`{BOT_PREFIX}profile [user]` - Show profile card\n"
                  f"`{BOT_PREFIX}leaderboard [limit]` - Show leaderboard",
            inline=False
        )
        
        # Moderation commands
        embed.add_field(
            name="🛡️ Moderation Commands",
            value=f"`{BOT_PREFIX}warn <user> [reason]` - Warn a user\n"
                  f"`{BOT_PREFIX}listwarns <user>` - List warns for a user\n"
                  f"`{BOT_PREFIX}clearwarns <user>` - Clear all warns\n"
                  f"`{BOT_PREFIX}mute <user> <duration> [reason]` - Mute a user\n"
                  f"`{BOT_PREFIX}unmute <user>` - Unmute a user\n"
                  f"`{BOT_PREFIX}kick <user> [reason]` - Kick a user\n"
                  f"`{BOT_PREFIX}ban <user> [days] [reason]` - Ban a user",
            inline=False
        )
        
        # Info commands
        embed.add_field(
            name="ℹ️ Info Commands",
            value=f"`{BOT_PREFIX}userinfo [user]` - User information\n"
                  f"`{BOT_PREFIX}serverinfo` - Server information\n"
                  f"`{BOT_PREFIX}avatar [user]` - Get user avatar\n"
                  f"`{BOT_PREFIX}ping` - Check bot latency",
            inline=False
        )
        
        # Fun commands
        embed.add_field(
            name="🎉 Fun Commands",
            value=f"`{BOT_PREFIX}coinflip` - Flip a coin\n"
                  f"`{BOT_PREFIX}8ball <question>` - Ask the magic 8ball",
            inline=False
        )
        
        embed.set_footer(text="Use slash commands (/) for alternative command interface")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Misc(bot))
