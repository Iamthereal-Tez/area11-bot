import discord
from discord.ext import commands
import math
import io
from PIL import Image, ImageDraw, ImageFont
import aiohttp
from utils import db
import asyncio

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # prevent spam xp: user_id -> last_message_time (seconds)
        self._recent = {}
        self._xp_cooldown = 5  # seconds
        # ensure DB created
        self.bot.loop.create_task(db.init_db())

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return
        # simple cooldown per user to avoid xp spam
        last = self._recent.get((message.guild.id, message.author.id), 0)
        now = asyncio.get_event_loop().time()
        if now - last < self._xp_cooldown:
            return
        self._recent[(message.guild.id, message.author.id)] = now

        xp_gain = 5
        xp, level = await db.add_xp(message.guild.id, message.author.id, xp_gain)
        # compute new level using your formula: level = int(sqrt(xp) // 10)
        new_level = int(math.sqrt(xp) // 10)
        if new_level > level:
            await db.set_level(message.guild.id, message.author.id, new_level)
            embed = discord.Embed(
                title="Level Up!",
                description=f"🎉 {message.author.mention} reached **Level {new_level}**!",
                color=discord.Color.green()
            )
            try:
                await message.channel.send(embed=embed)
            except discord.Forbidden:
                # missing perms; safe to ignore or log
                pass

    @commands.command(aliases=["lvl"])
    async def level(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        row = await db.get_user(ctx.guild.id, member.id)
        if row:
            xp, level = row
            embed = discord.Embed(title=f"{member.display_name}'s Level", color=discord.Color.gold())
            embed.add_field(name="Level", value=str(level), inline=True)
            embed.add_field(name="XP", value=str(xp), inline=True)
        else:
            embed = discord.Embed(description=f"{member.mention} has no XP yet.", color=discord.Color.red())
        await ctx.send(embed=embed)

    @commands.command()
    async def leaderboard(self, ctx, limit: int = 10):
        rows = await db.top_users(ctx.guild.id, limit)
        if not rows:
            return await ctx.send(embed=discord.Embed(description="No data yet.", color=discord.Color.red()))
        embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.blue())
        for i, (user_id, xp, level) in enumerate(rows, start=1):
            member = ctx.guild.get_member(user_id) or await self.bot.fetch_user(user_id)
            name = member.display_name if isinstance(member, discord.Member) else member.name
            embed.add_field(name=f"#{i} — {name}", value=f"Level {level} | {xp} XP", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def profile(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        row = await db.get_user(ctx.guild.id, member.id)
        xp, level = row if row else (0, 0)

        next_level = level + 1
        current_level_xp = (level * 10) ** 2
        next_level_xp = (next_level * 10) ** 2
        xp_into_level = max(0, xp - current_level_xp)
        xp_needed = max(1, next_level_xp - current_level_xp)
        progress = xp_into_level / xp_needed

        # create image
        width, height = 700, 220
        bg_color = (40, 42, 54)
        img = Image.new("RGBA", (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)

        # fonts
        try:
            font_title = ImageFont.truetype("arial.ttf", 28)
            font_small = ImageFont.truetype("arial.ttf", 18)
        except:
            font_title = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # avatar
        avatar_size = 150
        avatar_x, avatar_y = 30, (height - avatar_size) // 2

        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url

        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as resp:
                avatar_bytes = await resp.read()

        avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((avatar_size, avatar_size))
        # circular mask
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        img.paste(avatar, (avatar_x, avatar_y), mask)

        # text
        draw.text((200, 30), f"{member.display_name}", font=font_title, fill=(255,255,255))
        draw.text((200, 75), f"Level: {level}", font=font_small, fill=(200,200,200))
        draw.text((200, 100), f"XP: {xp} / {next_level_xp}", font=font_small, fill=(200,200,200))

        # progress bar
        bar_x, bar_y, bar_w, bar_h = 200, 140, 450, 28
        draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], fill=(60,60,60))
        fill_w = int(bar_w * progress)
        draw.rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], fill=(0,170,255))

        # progress text
        pct = int(progress * 100)
        draw.text((bar_x + bar_w - 60, bar_y + 2), f"{pct}%", font=font_small, fill=(255,255,255))

        with io.BytesIO() as image_binary:
            img.save(image_binary, "PNG")
            image_binary.seek(0)
            file = discord.File(fp=image_binary, filename="profile.png")
            await ctx.send(file=file)

async def setup(bot):
    await bot.add_cog(Levels(bot))