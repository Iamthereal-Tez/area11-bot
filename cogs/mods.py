# cogs/mods.py
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions
import asyncio
import datetime

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------- Kick -------------------
    @commands.command(name="kick")
    @has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        # Check if bot has permission
        if not ctx.guild.me.guild_permissions.kick_members:
            await ctx.send("❌ I don't have permission to kick members.")
            return
            
        # Check if target is higher in hierarchy
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("❌ I can't kick this user because their role is higher than or equal to mine. Secondly, They are White")
            return
            
        try:
            await member.kick(reason=reason)
            await ctx.send(f"✅ Kicked {member.mention} • {reason}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to kick this user.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    # ------------------- Ban -------------------
    @commands.command(name="ban")
    @has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, days: int = 0, *, reason: str = "No reason provided"):
        # Check if bot has permission
        if not ctx.guild.me.guild_permissions.ban_members:
            await ctx.send("❌ I don't have permission to ban members.")
            return
            
        # Check if target is higher in hierarchy
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("❌ I can't ban this user because their role is higher than or equal to mine. Secondly, They are White")
            return
            
        try:
            await member.ban(reason=reason, delete_message_days=days)
            await ctx.send(f"✅ Banned {member.mention} • {reason}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to ban this user.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    # ------------------- Mute System -------------------
    async def mute_member(self, guild, member: discord.Member, duration_seconds: int, reason: str):
        # Check if bot has permission to manage roles
        if not guild.me.guild_permissions.manage_roles:
            return False  # Can't proceed without this permission
            
        # Try to use timeout feature first (Discord.py 2.0+)
        try:
            timeout_until = discord.utils.utcnow() + datetime.timedelta(seconds=duration_seconds)
            await member.timeout(timeout_until, reason=reason)
            print(f"✅ Timeout applied to {member} for {duration_seconds} seconds")
            return True
        except (AttributeError, discord.Forbidden):
            pass  # Fall back to role-based mute
        
        # Role-based mute fallback
        role = discord.utils.get(guild.roles, name="Muted")
        if role is None:
            # Create muted role if it doesn't exist
            try:
                role = await guild.create_role(name="Muted", reason="Auto-created for mute")
                
                # Apply permissions to all channels
                for channel in guild.channels:
                    try:
                        await channel.set_permissions(role, 
                                                    send_messages=False, 
                                                    speak=False, 
                                                    add_reactions=False,
                                                    read_message_history=True)
                    except discord.Forbidden:
                        continue  # Skip if we don't have permission for this channel
            except discord.Forbidden:
                return False  # Can't create role
        
        # Add the role to the member
        try:
            await member.add_roles(role, reason=reason)
            
            # Set a timer to remove the role
            if duration_seconds > 0:
                await asyncio.sleep(duration_seconds)
                if role in member.roles:
                    await member.remove_roles(role, reason="Mute duration expired")
            return True
        except discord.Forbidden:
            return False  # Can't add role to member

    @commands.command(name="mute")
    @has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        """Mute a member for X minutes (e.g., 10m, 1h, 2d)"""
        # Parse duration
        try:
            if duration.endswith('m'):
                seconds = int(duration[:-1]) * 60
            elif duration.endswith('h'):
                seconds = int(duration[:-1]) * 3600
            elif duration.endswith('d'):
                seconds = int(duration[:-1]) * 86400
            else:
                seconds = int(duration) * 60  # Assume minutes if no suffix
        except ValueError:
            await ctx.send("❌ Invalid duration format. Use like: 10m, 1h, 2d")
            return
            
        # Check if bot has permission
        if not ctx.guild.me.guild_permissions.moderate_members and not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("❌ I don't have permission to mute members.")
            return
            
        # Check if target is higher in hierarchy
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("❌ I can't mute this user because their role is higher than or equal to mine. Secondly, They are White")
            return
            
        success = await self.mute_member(ctx.guild, member, seconds, reason)
        if success:
            await ctx.send(f"🔇 Muted {member.mention} for {duration}. Reason: {reason}")
        else:
            await ctx.send("❌ Failed to mute user. Check my permissions.")

    # ------------------- Unmute -------------------
    @commands.command(name="unmute")
    @has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Unmute a member"""
        # Try to remove timeout first
        try:
            await member.timeout(None, reason="Manual unmute")
            await ctx.send(f"✅ Removed timeout from {member.mention}")
            return
        except:
            pass  # Fall back to role removal
            
        # Role-based unmute
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason="Manual unmute")
                await ctx.send(f"✅ Unmuted {member.mention}")
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to unmute this user.")
        else:
            await ctx.send(f"❌ {member.mention} is not muted.")

    # ------------------- Warn System -------------------
    @commands.command(name="warn")
    @has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        # Check if target is higher in hierarchy
        if member.top_role >= ctx.guild.me.top_role:
            await ctx.send("❌ I can't warn this user because their role is higher than or equal to mine. Secondly, They are White")
            return
            
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
            await self.mute_member(ctx.guild, member, 3600, "3rd warn")
        elif warns == 4:
            await self.mute_member(ctx.guild, member, 86400, "4th warn")
        elif warns == 5:
            try:
                await member.kick(reason="5th warn")
                await ctx.send(f"✅ {member.mention} kicked due to 5 warns.")
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to kick this user.")
        elif warns >= 6:
            try:
                await member.ban(reason="6th warn")
                await ctx.send(f"⛔ {member.mention} banned due to 6 warns.")
            except discord.Forbidden:
                await ctx.send("❌ I don't have permission to ban this user.")

    # ------------------- List Warns -------------------
    @commands.command(name="listwarns", aliases=["warns"])
    @has_permissions(manage_messages=True)
    async def listwarns(self, ctx, member: discord.Member):
        """List warns for a member"""
        warns = await self.bot.db.get_warns(member.id, ctx.guild.id)
        embed = discord.Embed(title=f"Warns for {member.display_name}", color=discord.Color.orange())
        embed.add_field(name="Total Warns", value=warns, inline=False)
        
        # Show warn actions
        if warns >= 3:
            action = "1-hour mute" if warns == 3 else "1-day mute" if warns == 4 else "Kick" if warns == 5 else "Ban"
            embed.add_field(name="Next Action", value=action, inline=False)
            
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ------------------- Clear Warns -------------------
    @commands.command(name="clearwarns", aliases=["resetwarns"])
    @has_permissions(manage_messages=True)
    async def clearwarns(self, ctx, member: discord.Member):
        """Clear all warns for a member"""
        await self.bot.db.reset_warns(member.id, ctx.guild.id)
        await ctx.send(f"✅ Cleared all warns for {member.mention}")

    # ------------------- Purge Messages -------------------
    @commands.command(name="purge")
    @has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        """Delete multiple messages"""
        if amount <= 0:
            await ctx.send("❌ Amount must be positive.")
            return
        
        if amount > 100:
            amount = 100
        
        # Delete the command message first
        await ctx.message.delete()
        
        # Delete the specified number of messages
        deleted = await ctx.channel.purge(limit=amount)
        
        # Send confirmation message that auto-deletes
        msg = await ctx.send(f"✅ Deleted {len(deleted)} messages.")
        await asyncio.sleep(5)
        await msg.delete()

    # ------------------- Error Handlers -------------------
    @kick.error
    @ban.error
    @warn.error
    @mute.error
    @unmute.error
    @listwarns.error
    @clearwarns.error
    @purge.error
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
        
        # Check if target is higher in hierarchy
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.followup.send("❌ I can't warn this user because their role is higher than or equal to mine. Secondly, They are White")
            return
            
        db = self.bot.db
        warns = await db.add_warn(member.id, interaction.guild.id)

        msg = f"⚠️ {member.mention} has been warned. Reason: {reason} (Warn {warns}/6)"
        await interaction.followup.send(msg)

        try:
            await member.send(f"⚠️ You have been warned in **{interaction.guild.name}**. Reason: {reason} (Warn {warns}/6)")
        except:
            pass

        if warns == 3:
            await self.mute_member(interaction.guild, member, 3600, "3rd warn")
        elif warns == 4:
            await self.mute_member(interaction.guild, member, 86400, "4th warn")
        elif warns == 5:
            try:
                await member.kick(reason="5th warn")
                await interaction.followup.send(f"✅ {member.mention} kicked due to 5 warns.")
            except discord.Forbidden:
                await interaction.followup.send("❌ I don't have permission to kick this user.")
        elif warns >= 6:
            try:
                await member.ban(reason="6th warn")
                await interaction.followup.send(f"⛔ {member.mention} banned due to 6 warns.")
            except discord.Forbidden:
                await interaction.followup.send("❌ I don't have permission to ban this user.")

    @warn_slash.error
    async def slash_perm_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)

    @app_commands.command(name="mute", description="Mute a member for a duration (e.g., 10m, 1h, 2d)")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(member="Member to mute", duration="Duration (e.g., 10m, 1h, 2d)", reason="Reason")
    async def mute_slash(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "No reason provided"):
        await interaction.response.defer()
        
        # Parse duration
        try:
            if duration.endswith('m'):
                seconds = int(duration[:-1]) * 60
            elif duration.endswith('h'):
                seconds = int(duration[:-1]) * 3600
            elif duration.endswith('d'):
                seconds = int(duration[:-1]) * 86400
            else:
                seconds = int(duration) * 60  # Assume minutes if no suffix
        except ValueError:
            await interaction.followup.send("❌ Invalid duration format. Use like: 10m, 1h, 2d")
            return
            
        # Check if bot has permission
        if not interaction.guild.me.guild_permissions.moderate_members and not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.followup.send("❌ I don't have permission to mute members.")
            return
            
        # Check if target is higher in hierarchy
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.followup.send("❌ I can't mute this user because their role is higher than or equal to mine. Secondly, They are White")
            return
            
        success = await self.mute_member(interaction.guild, member, seconds, reason)
        if success:
            await interaction.followup.send(f"🔇 Muted {member.mention} for {duration}. Reason: {reason}")
        else:
            await interaction.followup.send("❌ Failed to mute user. Check my permissions.")

    @app_commands.command(name="unmute", description="Unmute a member")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(member="Member to unmute")
    async def unmute_slash(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()
        
        # Try to remove timeout first
        try:
            await member.timeout(None, reason="Manual unmute")
            await interaction.followup.send(f"✅ Removed timeout from {member.mention}")
            return
        except:
            pass  # Fall back to role removal
            
        # Role-based unmute
        role = discord.utils.get(interaction.guild.roles, name="Muted")
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason="Manual unmute")
                await interaction.followup.send(f"✅ Unmuted {member.mention}")
            except discord.Forbidden:
                await interaction.followup.send("❌ I don't have permission to unmute this user.")
        else:
            await interaction.followup.send(f"❌ {member.mention} is not muted.")

    @app_commands.command(name="listwarns", description="List warns for a member")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(member="Member to check")
    async def listwarns_slash(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()
        
        warns = await self.bot.db.get_warns(member.id, interaction.guild.id)
        embed = discord.Embed(title=f"Warns for {member.display_name}", color=discord.Color.orange())
        embed.add_field(name="Total Warns", value=warns, inline=False)
        
        # Show warn actions
        if warns >= 3:
            action = "1-hour mute" if warns == 3 else "1-day mute" if warns == 4 else "Kick" if warns == 5 else "Ban"
            embed.add_field(name="Next Action", value=action, inline=False)
            
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="clearwarns", description="Clear all warns for a member")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(member="Member to clear warns for")
    async def clearwarns_slash(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()
        
        await self.bot.db.reset_warns(member.id, interaction.guild.id)
        await interaction.followup.send(f"✅ Cleared all warns for {member.mention}")

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(member="Member to kick", reason="Reason")
    async def kick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.defer()
        
        # Check if bot has permission
        if not interaction.guild.me.guild_permissions.kick_members:
            await interaction.followup.send("❌ I don't have permission to kick members.")
            return
            
        # Check if target is higher in hierarchy
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.followup.send("❌ I can't kick this user because their role is higher than or equal to mine. Secondly, They are White")
            return
            
        try:
            await member.kick(reason=reason)
            await interaction.followup.send(f"✅ Kicked {member.mention} • {reason}")
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to kick this user.")

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(member="Member to ban", days="Delete last X days of messages", reason="Reason")
    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member, days: int = 0, reason: str = "No reason provided"):
        await interaction.response.defer()
        
        # Check if bot has permission
        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.followup.send("❌ I don't have permission to ban members.")
            return
            
        # Check if target is higher in hierarchy
        if member.top_role >= interaction.guild.me.top_role:
            await interaction.followup.send("❌ I can't ban this user because their role is higher than or equal to mine. Secondly, They are White")
            return
            
        try:
            await member.ban(reason=reason, delete_message_days=days)
            await interaction.followup.send(f"✅ Banned {member.mention} • {reason}")
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to ban this user.")

    @app_commands.command(name="purge", description="Delete multiple messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(amount="Number of messages to delete (max 100)")
    async def purge_slash(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer()
        
        if amount <= 0:
            await interaction.followup.send("❌ Amount must be positive.")
            return
        
        if amount > 100:
            amount = 100
        
        # Delete the specified number of messages
        deleted = await interaction.channel.purge(limit=amount)
        
        # Send confirmation message that auto-deletes
        msg = await interaction.followup.send(f"✅ Deleted {len(deleted)} messages.")
        await asyncio.sleep(5)
        await msg.delete()

async def setup(bot):
    await bot.add_cog(Mod(bot))
