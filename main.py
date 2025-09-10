# main.py
import os, time, asyncio
import discord
from discord.ext import commands
from utils.db import Database

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

BOT_PREFIX = "."
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None)
tree = bot.tree

# Load all cogs
INITIAL_EXTENSIONS = ["cogs.mods", "cogs.levels", "cogs.misc"]

# XP cooldown tracker
_message_cooldowns = {}
XP_PER_MESSAGE = 10
XP_COOLDOWN = 60

# Spam tracker
_spam_tracker = {}
SPAM_THRESHOLD = 5

# ----------------- EVENTS -----------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID:{bot.user.id})")
    
    # Sync slash commands globally
    try:
        synced = await tree.sync()
        print(f"✅ Synced {len(synced)} slash commands globally.")
    except Exception as e:
        print("❌ Sync error:", e)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.guild is None:
        return

    guild_id = message.guild.id
    user_id = message.author.id
    key = (guild_id, user_id)
    content = message.content.lower().strip()

    # ---------------- XP ----------------
    now = time.time()
    last = _message_cooldowns.get(key, 0)
    if now - last >= XP_COOLDOWN:
        try:
            await bot.db.add_xp(user_id, guild_id, XP_PER_MESSAGE)
            
            # Check for level up
            xp = await bot.db.get_user(user_id, guild_id)
            level = bot.db.xp_to_level(xp)
            prev_level = bot.db.xp_to_level(xp - XP_PER_MESSAGE)
            
            if level > prev_level:
                # Level up!
                levels_cog = bot.get_cog("Levels")
                if levels_cog:
                    await levels_cog.send_level_up_message(message.channel, message.author, level)
                    
        except Exception as e:
            print(f"XP Error: {e}")
        _message_cooldowns[key] = now

    # ---------------- Spam ----------------
    last_msg, count = _spam_tracker.get(key, ("", 0))
    if content == last_msg:
        count += 1
    else:
        count = 1
    _spam_tracker[key] = (content, count)

    if count >= SPAM_THRESHOLD:
        try:
            warns = await bot.db.add_warn(user_id, guild_id)
            await message.channel.send(f"⚠️ {message.author.mention} auto-warned for spamming! ({warns}/6)")
            try:
                await message.author.send(f"⚠️ Auto-warned in {message.guild.name}! ({warns}/6)")
            except:
                pass

            mod_cog = bot.get_cog("Mod")
            if mod_cog:
                if warns == 3:
                    await mod_cog.mute_member(message.guild, message.author, 3600, "3rd warn (spam)")
                elif warns == 4:
                    await mod_cog.mute_member(message.guild, message.author, 86400, "4th warn (spam)")
                elif warns == 5:
                    try:
                        await message.author.kick(reason="5th warn (spam)")
                        await message.channel.send(f"✅ {message.author.mention} kicked due to 5 warns.")
                    except discord.Forbidden:
                        await message.channel.send("❌ I don't have permission to kick this user.")
                elif warns >= 6:
                    try:
                        await message.author.ban(reason="6th warn (spam)")
                        await message.channel.send(f"⛔ {message.author.mention} banned due to 6 warns.")
                    except discord.Forbidden:
                        await message.channel.send("❌ I don't have permission to ban this user.")

            _spam_tracker[key] = ("", 0)
        except Exception as e:
            print(f"Spam detection error: {e}")

    await bot.process_commands(message)

# ----------------- EXTENSIONS -----------------
async def load_extensions():
    for ext in INITIAL_EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")

# ----------------- MAIN -----------------
async def main():
    # DB setup
    bot.db = Database()
    await bot.db.connect()
    await bot.db.create_tables()
    print("🔗 Database connected and tables created.")

    await load_extensions()

    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN missing.")
    await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Fatal error: {e}")
