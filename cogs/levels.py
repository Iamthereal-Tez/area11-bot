import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Use a default font that works on Railway
        try:
            self.font = ImageFont.truetype("arial.ttf", 40)
            self.small_font = ImageFont.truetype("arial.ttf", 24)
        except:
            # Fallback to default font
            self.font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()

    # ------------------------------------------------------------------
    # Helper: create a simple profile card image (avatar + xp bar)
    async def make_profile_card(self, member: discord.Member, xp: int, level: int):
        width, height = 800, 250
        background = Image.new("RGBA", (width, height), (30, 30, 30, 255))
        draw = ImageDraw.Draw(background)

        # Fetch avatar
        avatar_bytes = None
        try:
            avatar = member.display_avatar.url
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar) as resp:
                    avatar_bytes = await resp.read()

            avatar_img = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((200, 200))
            background.paste(avatar_img, (25, 25), avatar_img)
        except:
            # If avatar fails, just continue without it
            pass

        # Text
        draw.text((250, 40), f"{member.display_name}", font=self.font, fill=(255,255,255,255))
        draw.text((250, 90), f"Level: {level}  •  XP: {xp}", font=self.small_font, fill=(200,200,200,255))

        # XP bar background
        bar_x, bar_y = 250, 150
        bar_w, bar_h = 500, 30
        draw.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), fill=(60,60,60,255))

        # Calculate XP progress
        next_level_xp = (level + 1) * 100  # Simple formula
        progress = min(1.0, xp / next_level_xp) if next_level_xp > 0 else 0
        filled = int(bar_w * progress)
        draw.rectangle((bar_x, bar_y, bar_x + filled, bar_y + bar_h), fill=(0, 200, 100, 255))

        # Return bytes
        out = BytesIO()
        background.save(out, format="PNG")
        out.seek(0)
        return out

    # --------- Prefix command
    @commands.command(name="level", aliases=["lvl", "rank"])
    async def level_prefix(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        try:
            xp = await self.bot.db.get_user(member.id, ctx.guild.id)
            level = self.bot.db.xp_to_level(xp)
            # generate image
            card = await self.make_profile_card(member, xp, level)
            await ctx.reply(file=discord.File(card, filename="profile.png"))
        except Exception as e:
            await ctx.reply(f"Error showing level: {e}")

    # --------- Slash command
    @app_commands.command(name="level", description="Show a user's level and XP")
    @app_commands.describe(user="User to show (optional)")
    async def level(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer()
        user = user or interaction.user
        try:
            xp = await self.bot.db.get_user(user.id, interaction.guild.id)
            level = self.bot.db.xp_to_level(xp)
            card = await self.make_profile_card(user, xp, level)
            await interaction.followup.send(file=discord.File(card, filename="profile.png"))
        except Exception as e:
            await interaction.followup.send(f"Error showing level: {e}")

    # Leaderboard (prefix)
    @commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard_prefix(self, ctx, limit: int = 10):
        limit = max(1, min(25, limit))
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
        except Exception as e:
            await ctx.send(f"Error loading leaderboard: {e}")

    # Leaderboard (slash)
    @app_commands.command(name="leaderboard", description="Show the server leaderboard")
    @app_commands.describe(limit="Number of top users to show (max 25)")
    async def leaderboard(self, interaction: discord.Interaction, limit: int = 10):
        await interaction.response.defer()
        limit = max(1, min(25, limit))
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
        except Exception as e:
            await interaction.followup.send(f"Error loading leaderboard: {e}")

async def setup(bot):
    await bot.add_cog(Levels(bot))
