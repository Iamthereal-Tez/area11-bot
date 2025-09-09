import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = None):
        try:
            await member.ban(reason=reason)
            await ctx.send(f"🔨 {member.mention} banned. Reason: {reason or 'No reason provided.'}")
            try:
                await member.send(f"You were banned from {ctx.guild.name}. Reason: {reason or 'No reason provided.'}")
            except discord.Forbidden:
                pass
        except discord.Forbidden:
            await ctx.send("I don't have permission to ban this user.")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = None):
        try:
            await member.kick(reason=reason)
            await ctx.send(f"👢 {member.mention} kicked. Reason: {reason or 'No reason provided.'}")
            try:
                await member.send(f"You were kicked from {ctx.guild.name}. Reason: {reason or 'No reason provided.'}")
            except discord.Forbidden:
                pass
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick this user.")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: str, *, reason: str = None):
        try:
            unit = duration[-1].lower()
            amount = int(duration[:-1])
            if unit == "s":
                delta = timedelta(seconds=amount)
            elif unit == "m":
                delta = timedelta(minutes=amount)
            elif unit == "h":
                delta = timedelta(hours=amount)
            elif unit == "d":
                delta = timedelta(days=amount)
            else:
                return await ctx.send("Invalid duration. Use e.g. `10m`, `2h`, `1d`.")
            until = datetime.now(timezone.utc) + delta
            await member.edit(timed_out_until=until)
            await ctx.send(f"🔇 {member.mention} muted for {duration}. Reason: {reason or 'No reason provided.'}")
            try:
                await member.send(f"You were muted in {ctx.guild.name} for {duration}. Reason: {reason or 'No reason provided.'}")
            except discord.Forbidden:
                pass
        except discord.Forbidden:
            await ctx.send("I don't have permission to timeout this user.")
        except Exception as e:
            await ctx.send(f"Error: {e}")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        try:
            await member.edit(timed_out_until=None)
            await ctx.send(f"🔊 {member.mention} unmuted.")
            try:
                await member.send(f"You were unmuted in {ctx.guild.name}.")
            except discord.Forbidden:
                pass
        except discord.Forbidden:
            await ctx.send("I don't have permission to unmute this user.")

async def setup(bot):
    await bot.add_cog(Mod(bot))