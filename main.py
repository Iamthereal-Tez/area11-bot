import os
import discord
from discord.ext import commands
import asyncio

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.voice_states = True

# Prefix (you can make this per-guild later)
BOT_PREFIX = "."

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=commands.DefaultHelpCommand())

# Load cogs
INITIAL_EXTENSIONS = [
    "cogs.levels",
    "cogs.mod"
]

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("Loaded cogs:", INITIAL_EXTENSIONS)

async def load_extensions():
    for ext in INITIAL_EXTENSIONS:
        try:
            bot.load_extension(ext)
            print(f"Loaded extension {ext}")
        except Exception as e:
            print(f"Failed to load extension {ext}: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(load_extensions())

    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError("❌ DISCORD_TOKEN environment variable not found. Add it in Railway Variables.")
    bot.run(TOKEN)
