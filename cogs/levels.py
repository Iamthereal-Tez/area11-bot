# cogs/levels.py
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import os
import textwrap
import math

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.level_up_channel = None
        
    async def send_level_up_message(self, channel, user, level):
        """Send a level up announcement"""
        embed = discord.Embed(
            title="🎉 Level Up!",
            description=f"GG {user.mention}, you leveled up to **level {level}**!",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        await channel.send(embed=embed)
    
    # ------------------------------------------------------------------
    # Helper: create an Arcane-style profile card
    async def make_profile_card(self, member: discord.Member, xp: int, level: int, rank: int):
        # Create base image
        width, height = 1000, 400
        background = Image.new("RGBA", (width, height), (20, 20, 30, 255))
        draw = ImageDraw.Draw(background)
        
        # Create gradient background
        for y in range(height):
            r = int(20 + (40 * y / height))
            g = int(20 + (30 * y / height))
            b = int(30 + (50 * y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
        
        # Add some visual effects
        for i in range(50):
            x = int(width * 0.7 + width * 0.3 * (i / 50))
            alpha = int(100 * (1 - i / 50))
            draw.ellipse([x-150, -50, x+150, 250], outline=(100, 100, 200, alpha), width=5)
        
        # Fetch avatar
        try:
            avatar_url = member.display_avatar.url
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as resp:
                    avatar_bytes = await resp.read()
            
            # Create circular avatar
            avatar_img = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((250, 250))
            
            # Create circular mask
            mask = Image.new("L", (250, 250), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([(0, 0), (250, 250)], fill=255)
            
            # Apply mask and border
            avatar_with_border = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            avatar_with_border.paste(avatar_img, (3, 3), mask)
            
            # Add glow effect
            glow = avatar_img.filter(ImageFilter.GaussianBlur(10))
            background.paste(glow, (50, 50), glow)
            background.paste(avatar_with_border, (53, 53), avatar_with_border)
            
        except Exception as e:
            print(f"Avatar error: {e}")
        
        # Try to load a font, fallback to default if not available
        try:
            title_font = ImageFont.truetype("arialbd.ttf", 40)
            normal_font = ImageFont.truetype("arial.ttf", 24)
            small_font = ImageFont.truetype("arial.ttf", 20)
        except:
            title_font = ImageFont.load_default()
            normal_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # User info
        username = f"{member.display_name}"
        if len(username) > 15:
            username = username[:15] + "..."
        
        draw.text((320, 60), username, font=title_font, fill=(255, 255, 255, 255))
        
        # Level and rank
        draw.text((320, 120), f"Level: {level}", font=normal_font, fill=(200, 200, 255, 255))
        draw.text((500, 120), f"Rank: #{rank}", font=normal_font, fill=(200, 200, 255, 255))
        
        # XP
        draw.text((320, 160), f"XP: {xp}", font=normal_font, fill=(200, 255, 200, 255))
        
        # Calculate XP progress
        next_level_xp = ((level + 1) / 0.1) ** 2  # Calculate XP needed for next level
        progress = min(1.0, xp / next_level_xp) if next_level_xp > 0 else 0
        
        # XP bar background
        bar_x, bar_y = 320, 210
        bar_w, bar_h = 600, 30
        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=10, fill=(50, 50, 70, 255))
        
        # XP bar fill
        filled = int(bar_w * progress)
        if filled > 0:
            draw.rounded_rectangle([bar_x, bar_y, bar_x + filled, bar_y + bar_h], radius=10, fill=(100, 150, 255, 255))
        
        # XP text on bar
        draw.text((bar_x + 10, bar_y + 5), f"{xp}/{int(next_level_xp)} XP", font=small_font, fill=(255, 255, 255, 255))
        
        # Progress percentage
        draw.text((bar_x + bar_w - 50, bar_y + 5), f"{int(progress*100)}%", font=small_font, fill=(255, 255, 255, 255))
        
        # Server stats
        draw.text((320, 260), f"Server: {member.guild.name}", font=small_font, fill=(200, 200, 200, 255))
        draw.text((320, 290), f"Joined: {member.joined_at.strftime('%Y-%m-%d')}", font=small_font, fill=(200, 200, 200, 255))
        
        # Add some decorative elements
        draw.rectangle([310, 50, 930, 330], outline=(100, 100, 150, 255), width=2)
        
        # Return bytes
        out = BytesIO()
        background.save(out, format="PNG")
        out.seek(0)
        return out

    # --------- Profile command (different from level) ---------
    @commands.command(name="profile")
    async def profile_prefix(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        try:
            xp = await self.bot.db.get_user(member.id, ctx.guild.id)
            level = self.bot.db.xp_to_level(xp)
            
            # Get user's rank
            leaderboard = await self.bot.db.get_leaderboard(ctx.guild.id, 1000)
            user_ids = [user_id for user_id, _ in leaderboard]
            try:
                rank = user_ids.index(member.id) + 1
            except ValueError:
                rank = len(user_ids) + 1
                
            # generate image
            card = await self.make_profile_card(member, xp, level, rank)
            await ctx.reply(file=discord.File(card, filename="profile.png"))
        except Exception as e:
            await ctx.reply(f"Error showing profile: {e}")

    # --------- Level command (simpler than profile) ---------
    @commands.command(name="level", aliases=["lvl", "rank"])
    async def level_prefix(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        try:
            xp = await self.bot.db.get_user(member.id, ctx.guild.id)
            level = self.bot.db.xp_to_level(xp)
            
            # Get user's rank
            leaderboard = await self.bot.db.get_leaderboard(ctx.guild.id, 1000)
            user_ids = [user_id for user_id, _ in leaderboard]
            try:
                rank = user_ids.index(member.id) + 1
            except ValueError:
                rank = len(user_ids) + 1
                
            embed = discord.Embed(title=f"{member.display_name}'s Level", color=discord.Color.blue())
            embed.add_field(name="Level", value=level, inline=True)
            embed.add_field(name="XP", value=xp, inline=True)
            embed.add_field(name="Rank", value=f"#{rank}", inline=True)
            
            # Calculate progress to next level
            next_level_xp = ((level + 1) / 0.1) ** 2  # Calculate XP needed for next level
            progress = min(1.0, xp / next_level_xp) if next_level_xp > 0 else 0
            
            # Progress bar
            bar_length = 20
            filled = int(bar_length * progress)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            embed.add_field(name="Progress", value=f"{bar} {int(progress*100)}%", inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.reply(f"Error showing level: {e}")

    # --------- XP Management Commands (Mods only) ---------
    @commands.command(name="addxp")
    @commands.has_permissions(manage_messages=True)
    async def addxp_prefix(self, ctx, member: discord.Member, amount: int):
        """Add XP to a user"""
        if amount <= 0:
            await ctx.reply("Amount must be positive.")
            return
            
        current_xp = await self.bot.db.get_user(member.id, ctx.guild.id)
        new_xp = current_xp + amount
        await self.bot.db.set_xp(member.id, ctx.guild.id, new_xp)
        
        new_level = self.bot.db.xp_to_level(new_xp)
        await ctx.reply(f"Added {amount} XP to {member.mention}. They are now level {new_level}.")

    @commands.command(name="removexp")
    @commands.has_permissions(manage_messages=True)
    async def removexp_prefix(self, ctx, member: discord.Member, amount: int):
        """Remove XP from a user"""
        if amount <= 0:
            await ctx.reply("Amount must be positive.")
            return
            
        current_xp = await self.bot.db.get_user(member.id, ctx.guild.id)
        new_xp = max(0, current_xp - amount)
        await self.bot.db.set_xp(member.id, ctx.guild.id, new_xp)
        
        new_level = self.bot.db.xp_to_level(new_xp)
        await ctx.reply(f"Removed {amount} XP from {member.mention}. They are now level {new_level}.")

    @commands.command(name="setxp")
    @commands.has_permissions(manage_messages=True)
    async def setxp_prefix(self, ctx, member: discord.Member, amount: int):
        """Set a user's XP to a specific value"""
        if amount < 0:
            await ctx.reply("Amount cannot be negative.")
            return
            
        await self.bot.db.set_xp(member.id, ctx.guild.id, amount)
        
        new_level = self.bot.db.xp_to_level(amount)
        await ctx.reply(f"Set {member.mention}'s XP to {amount}. They are now level {new_level}.")

    @commands.command(name="resetxp")
    @commands.has_permissions(manage_messages=True)
    async def resetxp_prefix(self, ctx, member: discord.Member):
        """Reset a user's XP to 0"""
        await self.bot.db.set_xp(member.id, ctx.guild.id, 0)
        await ctx.reply(f"Reset {member.mention}'s XP. They are now level 1.")

    # Leaderboard with image
    @commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard_prefix(self, ctx, limit: int = 10):
        limit = max(1, min(20, limit))  # Max 20 for image
        try:
            rows = await self.bot.db.get_leaderboard(ctx.guild.id, limit)
            
            # Create leaderboard image
            width, height = 800, 200 + (limit * 80)
            background = Image.new("RGBA", (width, height), (30, 30, 40, 255))
            draw = ImageDraw.Draw(background)
            
            # Title
            try:
                font_large = ImageFont.truetype("arialbd.ttf", 36)
                font_medium = ImageFont.truetype("arial.ttf", 24)
                font_small = ImageFont.truetype("arial.ttf", 20)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
                
            draw.text((width//2, 30), f"🏆 {ctx.guild.name} Leaderboard", font=font_large, 
                     fill=(255, 215, 0, 255), anchor="mm")
            
            y_pos = 100
            for idx, (user_id, xp) in enumerate(rows, start=1):
                member = ctx.guild.get_member(user_id)
                name = member.display_name if member else f"User {user_id}"
                level = self.bot.db.xp_to_level(xp)
                
                # Rank badge
                badge_colors = {
                    1: (255, 215, 0),  # Gold
                    2: (192, 192, 192),  # Silver
                    3: (205, 127, 50)   # Bronze
                }
                
                color = badge_colors.get(idx, (100, 100, 150))
                draw.ellipse([50, y_pos-25, 90, y_pos+15], fill=color + (255,))
                draw.text((70, y_pos-5), str(idx), font=font_medium, fill=(0, 0, 0, 255), anchor="mm")
                
                # User info
                if member:
                    try:
                        avatar_url = member.display_avatar.url
                        async with aiohttp.ClientSession() as session:
                            async with session.get(avatar_url) as resp:
                                avatar_bytes = await resp.read()
                        
                        avatar_img = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((50, 50))
                        mask = Image.new("L", (50, 50), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse([(0, 0), (50, 50)], fill=255)
                        
                        background.paste(avatar_img, (100, y_pos-25), mask)
                    except:
                        pass
                
                # Name and stats
                draw.text((160, y_pos-15), name, font=font_medium, fill=(255, 255, 255, 255))
                draw.text((160, y_pos+10), f"Level {level} | {xp} XP", font=font_small, fill=(200, 200, 200, 255))
                
                # XP bar
                next_level_xp = ((level + 1) / 0.1) ** 2  # Calculate XP needed for next level
                progress = min(1.0, xp / next_level_xp) if next_level_xp > 0 else 0
                bar_width = 300
                draw.rectangle([450, y_pos-5, 450 + bar_width, y_pos+5], fill=(50, 50, 70, 255))
                draw.rectangle([450, y_pos-5, 450 + int(bar_width * progress), y_pos+5], fill=(100, 150, 255, 255))
                
                y_pos += 80
            
            # Save and send
            out = BytesIO()
            background.save(out, format="PNG")
            out.seek(0)
            await ctx.reply(file=discord.File(out, filename="leaderboard.png"))
            
        except Exception as e:
            # Fallback to embed if image fails
            try:
                rows = await self.bot.db.get_leaderboard(ctx.guild.id, limit)
                embed = discord.Embed(title=f"🏆 Leaderboard — Top {limit}", color=discord.Color.blurple())
                desc = ""
                for idx, (user_id, xp) in enumerate(rows, start=1):
                    member = ctx.guild.get_member(user_id)
                    name = member.display_name if member else f"<Left user {user_id}>"
                    level = self.bot.db.xp_to_level(xp)
                    desc += f"**{idx}.** {name} — Level {level} • {xp} XP\n"
                if desc == "":
                    desc = "No data yet."
                embed.description = desc
                await ctx.send(embed=embed)
            except Exception as e2:
                await ctx.send(f"Error loading leaderboard: {e2}")

    # --------- Slash commands ---------
    @app_commands.command(name="profile", description="Show a user's profile card")
    @app_commands.describe(user="User to show (optional)")
    async def profile_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer()
        user = user or interaction.user
        try:
            xp = await self.bot.db.get_user(user.id, interaction.guild.id)
            level = self.bot.db.xp_to_level(xp)
            
            # Get user's rank
            leaderboard = await self.bot.db.get_leaderboard(interaction.guild.id, 1000)
            user_ids = [user_id for user_id, _ in leaderboard]
            try:
                rank = user_ids.index(user.id) + 1
            except ValueError:
                rank = len(user_ids) + 1
                
            card = await self.make_profile_card(user, xp, level, rank)
            await interaction.followup.send(file=discord.File(card, filename="profile.png"))
        except Exception as e:
            await interaction.followup.send(f"Error showing profile: {e}")

    @app_commands.command(name="level", description="Show a user's level and XP")
    @app_commands.describe(user="User to show (optional)")
    async def level_slash(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer()
        user = user or interaction.user
        try:
            xp = await self.bot.db.get_user(user.id, interaction.guild.id)
            level = self.bot.db.xp_to_level(xp)
            
            # Get user's rank
            leaderboard = await self.bot.db.get_leaderboard(interaction.guild.id, 1000)
            user_ids = [user_id for user_id, _ in leaderboard]
            try:
                rank = user_ids.index(user.id) + 1
            except ValueError:
                rank = len(user_ids) + 1
                
            embed = discord.Embed(title=f"{user.display_name}'s Level", color=discord.Color.blue())
            embed.add_field(name="Level", value=level, inline=True)
            embed.add_field(name="XP", value=xp, inline=True)
            embed.add_field(name="Rank", value=f"#{rank}", inline=True)
            
            # Calculate progress to next level
            next_level_xp = ((level + 1) / 0.1) ** 2  # Calculate XP needed for next level
            progress = min(1.0, xp / next_level_xp) if next_level_xp > 0 else 0
            
            # Progress bar
            bar_length = 20
            filled = int(bar_length * progress)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            embed.add_field(name="Progress", value=f"{bar} {int(progress*100)}%", inline=False)
            embed.set_thumbnail(url=user.display_avatar.url)
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"Error showing level: {e}")

    @app_commands.command(name="leaderboard", description="Show the server leaderboard")
    @app_commands.describe(limit="Number of top users to show (max 20)")
    async def leaderboard_slash(self, interaction: discord.Interaction, limit: int = 10):
        await interaction.response.defer()
        limit = max(1, min(20, limit))
        try:
            rows = await self.bot.db.get_leaderboard(interaction.guild.id, limit)
            
            # Create leaderboard image
            width, height = 800, 200 + (limit * 80)
            background = Image.new("RGBA", (width, height), (30, 30, 40, 255))
            draw = ImageDraw.Draw(background)
            
            # Title
            try:
                font_large = ImageFont.truetype("arialbd.ttf", 36)
                font_medium = ImageFont.truetype("arial.ttf", 24)
                font_small = ImageFont.truetype("arial.ttf", 20)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
                
            draw.text((width//2, 30), f"🏆 {interaction.guild.name} Leaderboard", font=font_large, 
                     fill=(255, 215, 0, 255), anchor="mm")
            
            y_pos = 100
            for idx, (user_id, xp) in enumerate(rows, start=1):
                member = interaction.guild.get_member(user_id)
                name = member.display_name if member else f"User {user_id}"
                level = self.bot.db.xp_to_level(xp)
                
                # Rank badge
                badge_colors = {
                    1: (255, 215, 0),  # Gold
                    2: (192, 192, 192),  # Silver
                    3: (205, 127, 50)   # Bronze
                }
                
                color = badge_colors.get(idx, (100, 100, 150))
                draw.ellipse([50, y_pos-25, 90, y_pos+15], fill=color + (255,))
                draw.text((70, y_pos-5), str(idx), font=font_medium, fill=(0, 0, 0, 255), anchor="mm")
                
                # User info
                if member:
                    try:
                        avatar_url = member.display_avatar.url
                        async with aiohttp.ClientSession() as session:
                            async with session.get(avatar_url) as resp:
                                avatar_bytes = await resp.read()
                        
                        avatar_img = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((50, 50))
                        mask = Image.new("L", (50, 50), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse([(0, 0), (50, 50)], fill=255)
                        
                        background.paste(avatar_img, (100, y_pos-25), mask)
                    except:
                        pass
                
                # Name and stats
                draw.text((160, y_pos-15), name, font=font_medium, fill=(255, 255, 255, 255))
                draw.text((160, y_pos+10), f"Level {level} | {xp} XP", font=font_small, fill=(200, 200, 200, 255))
                
                # XP bar
                next_level_xp = ((level + 1) / 0.1) ** 2  # Calculate XP needed for next level
                progress = min(1.0, xp / next_level_xp) if next_level_xp > 0 else 0
                bar_width = 300
                draw.rectangle([450, y_pos-5, 450 + bar_width, y_pos+5], fill=(50, 50, 70, 255))
                draw.rectangle([450, y_pos-5, 450 + int(bar_width * progress), y_pos+5], fill=(100, 150, 255, 255))
                
                y_pos += 80
            
            # Save and send
            out = BytesIO()
            background.save(out, format="PNG")
            out.seek(0)
            await interaction.followup.send(file=discord.File(out, filename="leaderboard.png"))
            
        except Exception as e:
            # Fallback to embed if image fails
            try:
                rows = await self.bot.db.get_leaderboard(interaction.guild.id, limit)
                embed = discord.Embed(title=f"🏆 Leaderboard — Top {limit}", color=discord.Color.blurple())
                desc = ""
                for idx, (user_id, xp) in enumerate(rows, start=1):
                    member = interaction.guild.get_member(user_id)
                    name = member.display_name if member else f"<Left user {user_id}>"
                    level = self.bot.db.xp_to_level(xp)
                    desc += f"**{idx}.** {name} — Level {level} • {xp} XP\n"
                if desc == "":
                    desc = "No data yet."
                embed.description = desc
                await interaction.followup.send(embed=embed)
            except Exception as e2:
                await interaction.followup.send(f"Error loading leaderboard: {e2}")

    # --------- XP Management Slash Commands (Mods only) ---------
    @app_commands.command(name="addxp", description="Add XP to a user")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(user="User to add XP to", amount="Amount of XP to add")
    async def addxp_slash(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        await interaction.response.defer()
        
        if amount <= 0:
            await interaction.followup.send("Amount must be positive.")
            return
            
        current_xp = await self.bot.db.get_user(user.id, interaction.guild.id)
        new_xp = current_xp + amount
        await self.bot.db.set_xp(user.id, interaction.guild.id, new_xp)
        
        new_level = self.bot.db.xp_to_level(new_xp)
        await interaction.followup.send(f"Added {amount} XP to {user.mention}. They are now level {new_level}.")

    @app_commands.command(name="removexp", description="Remove XP from a user")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(user="User to remove XP from", amount="Amount of XP to remove")
    async def removexp_slash(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        await interaction.response.defer()
        
        if amount <= 0:
            await interaction.followup.send("Amount must be positive.")
            return
            
        current_xp = await self.bot.db.get_user(user.id, interaction.guild.id)
        new_xp = max(0, current_xp - amount)
        await self.bot.db.set_xp(user.id, interaction.guild.id, new_xp)
        
        new_level = self.bot.db.xp_to_level(new_xp)
        await interaction.followup.send(f"Removed {amount} XP from {user.mention}. They are now level {new_level}.")

    @app_commands.command(name="setxp", description="Set a user's XP to a specific value")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(user="User to set XP for", amount="Amount of XP to set")
    async def setxp_slash(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        await interaction.response.defer()
        
        if amount < 0:
            await interaction.followup.send("Amount cannot be negative.")
            return
            
        await self.bot.db.set_xp(user.id, interaction.guild.id, amount)
        
        new_level = self.bot.db.xp_to_level(amount)
        await interaction.followup.send(f"Set {user.mention}'s XP to {amount}. They are now level {new_level}.")

    @app_commands.command(name="resetxp", description="Reset a user's XP to 0")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(user="User to reset XP for")
    async def resetxp_slash(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer()
        
        await self.bot.db.set_xp(user.id, interaction.guild.id, 0)
        await interaction.followup.send(f"Reset {user.mention}'s XP. They are now level 1.")

async def setup(bot):
    await bot.add_cog(Levels(bot))
