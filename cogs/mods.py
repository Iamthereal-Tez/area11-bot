# cogs/mod.py
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions, MissingPermissions
import asyncio

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------- Kick -------------------
    @commands.command(name="kick")
    @has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await member.kick(reason=reason)
        await ctx.send(f"✅ Kicked {member.mention} • {reason}")

    # ------------------- Ban -------------------
    @commands.command(name="ban")
    @has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, days: int = 0, *, reason: str = "No reason provided"):
        await member.ban(reason=reason, delete_message_days=days)
        await ctx.send(f"✅ Banned {member.mention} • {reason}")

    # ------------------- Prefix Mute -------------------
    @commands.command(name="mute")
    @has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, duration: int, *, reason: str = "No reason provided"):
        """Mute a member for a given duration in minutes"""
        await self.mute_member(ctx.guild, member, duration*60, reason)
        await ctx.send(f"🔇 Muted {member.mention} for {duration} minutes. Reason: {reason}")

    # ------------------- Mute Helper -------------------
    async def mute_member(self, guild, member: discord.Member, duration_seconds: int, reason: str):
        role = discord.utils.get(guild.roles, name="Muted")
        if role is None:
            role = await guild.create_role(name="Muted", reason="Auto-created for mute")
            for ch in guild.channels:
                try:
                    await ch.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
                except Exception:
                    pass
        await member.add_roles(role, reason=reason)
        try:
            await member.send(f"🔇 You have been muted in **{guild.name}** for {duration_seconds//60} minutes. Reason: {reason}")
        except:
            pass
        await asyncio.sleep(duration_seconds)
        # Remove role after duration
        await member.remove_roles(role, reason="Mute duration expired")

    # ------------------- Warn System -------------------
    @commands.command(name="warn")
    @has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        db = self.bot.db
        warns = await db.add_warn(member.id, ctx.guild.id)

        msg = f"⚠️ {member.mention} has been warned. Reason: {reason} (Warn {warns}/6)"
        await ctx.send(msg)
        try:
            await member.send(f"⚠️ You have been warned in **{ctx.guild.name}**. Reason: {reason} (Warn {warns}/6)")
        except:
            pass

        # Actions based on warn count
        if warns == 3:
            await self.mute_member(ctx.guild, member, duration_seconds=3600, reason="3rd warn")
        elif warns == 4:
            await self.mute_member(ctx.guild, member, duration_seconds=86400, reason="4th warn")
        elif warns == 5:
            await member.kick(reason="5th warn")
            await ctx.send(f"✅ {member.mention} has been kicked due to 5 warns.")
        elif warns >= 6:
            await member.ban(reason="6th warn")
            await ctx.send(f"⛔ {member.mention} has been banned due to 6 warns.")

    # ------------------- Error Handlers -------------------
    @kick.error
    @ban.error
    @warn.error
    async def perm_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        else:
            await ctx.send(f"❌ Error: {error}")

    # ------------------- Slash Commands -------------------
    @app_commands.command(name="warn", description="Warn a member (auto actions at higher warns)")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(member="Member to warn", reason="Reason")
    async def warn_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.defer()
        db = self.bot.db
        warns = await db.add_warn(member.id, interaction.guild.id)
        msg = f"⚠️ {member.mention} has been warned. Reason: {reason} (Warn {warns}/6)"
        await interaction.followup.send(msg)

        try:
            await member.send(f"⚠️ You have been warned in **{interaction.guild.name}**. Reason: {reason} (Warn {warns}/6)")
        except:
            pass

        if warns == 3:
            await self.mute_member(interaction.guild, member, duration_seconds=3600, reason="3rd warn")
        elif warns == 4:
            await self.mute_member(interaction.guild, member, duration_seconds=86400, reason="4th warn")
        elif warns == 5:
            await member.kick(reason="5th warn")
            await interaction.followup.send(f"✅ {member.mention} has been kicked due to 5 warns.")
        elif warns >= 6:
            await member.ban(reason="6th warn")
            await interaction.followup.send(f"⛔ {member.mention} has been banned due to 6 warns.")

    @warn_slash.error
    async def slash_perm_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)

    @app_commands.command(name="mute", description="Mute a member for a duration (in minutes)")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(member="Member to mute", duration="Duration in minutes", reason="Reason")
    async def mute_slash(self, interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "No reason provided"):
        await interaction.response.defer()
        await self.mute_member(interaction.guild, member, duration_seconds=duration*60, reason=reason)
        await interaction.followup.send(f"🔇 Muted {member.mention} for {duration} minutes. Reason: {reason}")

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(member="Member to kick", reason="Reason")
    async def kick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.defer()
        await member.kick(reason=reason)
        await interaction.followup.send(f"✅ Kicked {member.mention} • {reason}")

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(member="Member to ban", days="Delete last X days of messages", reason="Reason")
    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member, days: int = 0, reason: str = "No reason provided"):
        await interaction.response.defer()
        await member.ban(reason=reason, delete_message_days=days)
        await interaction.followup.send(f"✅ Banned {member.mention} • {reason}")

async def setup(bot):
    await bot.add_cog(Mod(bot))
