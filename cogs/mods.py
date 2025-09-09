import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------------- Kick (prefix)
    @commands.command(name="kick")
    @has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await member.kick(reason=reason)
        await ctx.send(f"✅ Kicked {member.mention} • {reason}")

    # -------------- Ban (prefix)
    @commands.command(name="ban")
    @has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, days: int = 0, *, reason: str = "No reason provided"):
        await member.ban(reason=reason, delete_message_days=days)
        await ctx.send(f"✅ Banned {member.mention} • {reason}")

    # -------------- Slash Kick
    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(member="Member to kick", reason="Reason")
    async def kick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.defer()
        await member.kick(reason=reason)
        await interaction.followup.send(f"✅ Kicked {member.mention} • {reason}")

    # -------------- Slash Ban
    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(member="Member to ban", days="Delete last X days of messages", reason="Reason")
    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member, days: int = 0, reason: str = "No reason provided"):
        await interaction.response.defer()
        await member.ban(reason=reason, delete_message_days=days)
        await interaction.followup.send(f"✅ Banned {member.mention} • {reason}")

    # -------------- Mute (simple role-based mute)
    @commands.command(name="mute")
    @has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if role is None:
            # create muted role
            role = await ctx.guild.create_role(name="Muted", reason="Auto-created by bot for mute command")
            for ch in ctx.guild.channels:
                try:
                    await ch.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
                except Exception:
                    pass
        await member.add_roles(role, reason=reason)
        await ctx.send(f"🔇 Muted {member.mention} • {reason}")

    @app_commands.command(name="mute", description="Mute a member (creates Muted role if needed)")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def mute_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.defer()
        role = discord.utils.get(interaction.guild.roles, name="Muted")
        if role is None:
            role = await interaction.guild.create_role(name="Muted", reason="Auto-created by bot for mute command")
            for ch in interaction.guild.channels:
                try:
                    await ch.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
                except Exception:
                    pass
        await member.add_roles(role, reason=reason)
        await interaction.followup.send(f"🔇 Muted {member.mention} • {reason}")

    # Error handlers
    @kick.error
    @ban.error
    @mute.error
    async def perm_error(self, ctx, error):
        if isinstance(error, MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        else:
            await ctx.send(f"❌ Error: {error}")

    @kick_slash.error
    @ban_slash.error
    @mute_slash.error
    async def slash_perm_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Mod(bot))
