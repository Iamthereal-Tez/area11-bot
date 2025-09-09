import os
import asyncio
import time
import discord
from discord.ext import commands
from utils.db import Database

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.voice_states = True

BOT_PREFIX = "."

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=commands.DefaultHelpCommand())
tree = bot.tree

# Cogs to load
INITIAL_EXTENSIONS = [
    "cogs.levels",
    "cogs.mod",
    "cogs.misc"
]

# Basic anti-spam/XP cooldown tracker (per user per guild)
_message_cooldowns = {}  # {(guild_id, user_id): last_message_unix}

# XP configuration
XP_PER_MESSAGE = 10
XP_COOLDOWN = 60  # seconds between XP awards for same user/guild

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    # create / sync commands
    try:
        synced = await tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s).")
    except Exception as e:
        print("❌ Failed to sync slash commands:", e)

@bot.event
async def on_connect():
    # initialize DB on connect
    if not hasattr(bot, "db"):
        bot.db = Database()
        await bot.db.connect()
        await bot.db.create_tables()
    print("🔗 Database connected (if available).")

@bot.event
async def on_message(message: discord.Message):
    # ignore bots
    if message.author.bot or message.guild is None:
        return

    # award XP with cooldown
    key = (message.guild.id, message.author.id)
    now = time.time()
    last = _message_cooldowns.get(key, 0)
    if now - last >= XP_COOLDOWN:
        try:
            await bot.db.add_xp(user_id=message.author.id, guild_id=message.guild.id, amount=XP_PER_MESSAGE)
        except Exception as e:
            print("DB XP add error:", e)
        _message_cooldowns[key] = now

    # process commands (prefix)
    await bot.process_commands(message)

async def load_extensions():
    for ext in INITIAL_EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"Loaded extension: {ext}")
        except Exception as e:
            print(f"Failed to load extension {ext}: {e}")

async def main():
    await load_extensions()
    # ensure DB initialized (again) and tables are present
    if not hasattr(bot, "db"):
        bot.db = Database()
        await bot.db.connect()
        await bot.db.create_tables()

    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN environment variable not found. Add it in Railway Variables.")
    await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
