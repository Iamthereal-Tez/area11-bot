import discord
from discord import app_commands
from discord.ext import commands
import random
import aiohttp
from io import BytesIO

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
    @commands.command(name="avatar")
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await ctx.send(member.display_avatar.url)

    @app_commands.command(name="avatar", description="Get a user's avatar")
    async def avatar_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        await interaction.response.send_message(user.display_avatar.url)

    # Userinfo
    @commands.command(name="userinfo")
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"{member}", color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Roles", value=", ".join([r.name for r in member.roles if r.name != "@everyone"]) or "None", inline=False)
        await ctx.send(embed=embed)

    @app_commands.command(name="userinfo", description="Show info about a user")
    async def userinfo_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        embed = discord.Embed(title=f"{user}", color=discord.Color.green())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Account Created", value=user.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Roles", value=", ".join([r.name for r in user.roles if r.name != "@everyone"]) or "None", inline=False)
        await interaction.response.send_message(embed=embed)

    # Server info
    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx):
        g = ctx.guild
        embed = discord.Embed(title=f"{g.name}", description=g.description or "", color=discord.Color.blurple())
        embed.add_field(name="Members", value=g.member_count)
        embed.add_field(name="Owner", value=g.owner)
        embed.add_field(name="Created", value=g.created_at.strftime("%Y-%m-%d"))
        await ctx.send(embed=embed)

    @app_commands.command(name="serverinfo", description="Show server info")
    async def serverinfo_slash(self, interaction: discord.Interaction):
        g = interaction.guild
        embed = discord.Embed(title=f"{g.name}", description=g.description or "", color=discord.Color.blurple())
        embed.add_field(name="Members", value=g.member_count)
        embed.add_field(name="Owner", value=g.owner)
        embed.add_field(name="Created", value=g.created_at.strftime("%Y-%m-%d"))
        await interaction.response.send_message(embed=embed)

    # Coinflip
    @commands.command(name="coinflip")
    async def coinflip(self, ctx):
        res = random.choice(["Heads", "Tails"])
        await ctx.send(f"🪙 {res}")

    @app_commands.command(name="coinflip", description="Flip a coin")
    async def coinflip_slash(self, interaction: discord.Interaction):
        res = random.choice(["Heads", "Tails"])
        await interaction.response.send_message(f"🪙 {res}")

async def setup(bot):
    await bot.add_cog(Misc(bot))
