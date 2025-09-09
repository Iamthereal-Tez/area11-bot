import os, time, asyncio
import discord
from discord.ext import commands
from utils.db import Database

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

BOT_PREFIX = "."
bot = commands.Bot(command_prefix=BOT_PREFIX,intents=intents,help_command=commands.DefaultHelpCommand())
tree = bot.tree

INITIAL_EXTENSIONS = ["cogs.mod"]

# XP cooldown tracker
_message_cooldowns = {}
XP_PER_MESSAGE = 10
XP_COOLDOWN = 60

# Spam tracker
_spam_tracker = {}
SPAM_THRESHOLD = 5

@bot.event
async def on_connect():
    if not hasattr(bot,"db"):
        bot.db = Database()
        await bot.db.connect()
        await bot.db.create_tables()
    print("🔗 Database connected.")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID:{bot.user.id})")
    try:
        synced = await tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print("❌ Sync error:",e)

@bot.event
async def on_message(message:discord.Message):
    if message.author.bot or message.guild is None: return

    guild_id = message.guild.id
    user_id = message.author.id
    key = (guild_id,user_id)
    content = message.content.lower().strip()

    # XP
    now = time.time()
    last = _message_cooldowns.get(key,0)
    if now-last >= XP_COOLDOWN:
        try:
            await bot.db.add_xp(user_id,guild_id,XP_PER_MESSAGE)
        except: pass
        _message_cooldowns[key]=now

    # Spam detection
    last_msg, count = _spam_tracker.get(key, ("",0))
    if content == last_msg:
        count += 1
    else:
        count = 1
    _spam_tracker[key] = (content,count)

    if count >= SPAM_THRESHOLD:
        warns = await bot.db.add_warn(user_id,guild_id)
        await message.channel.send(f"⚠️ {message.author.mention} auto-warned for spamming! ({warns}/6)")
        try: await message.author.send(f"⚠️ Auto-warned in {message.guild.name}! ({warns}/6)")
        except: pass

        # Warn actions
        mod_cog = bot.get_cog("Mod")
        if warns == 3: await mod_cog.mute_member(message.guild,message.author,3600,"3rd warn (spam)")
        elif warns == 4: await mod_cog.mute_member(message.guild,message.author,86400,"4th warn (spam)")
        elif warns == 5:
            await message.author.kick(reason="5th warn (spam)")
            await message.channel.send(f"✅ {message.author.mention} kicked due to 5 warns.")
        elif warns >=6:
            await message.author.ban(reason="6th warn (spam)")
            await message.channel.send(f"⛔ {message.author.mention} banned due to 6 warns.")

        _spam_tracker[key] = ("",0)

    await bot.process_commands(message)

async def load_extensions():
    for ext in INITIAL_EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"Loaded {ext}")
        except Exception as e:
            print(f"Failed to load {ext}: {e}")

async def main():
    await load_extensions()
    if not hasattr(bot,"db"):
        bot.db = Database()
        await bot.db.connect()
        await bot.db.create_tables()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN: raise RuntimeError("DISCORD_TOKEN missing.")
    await bot.start(TOKEN)

if __name__=="__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
