# ---------------- WARN SYSTEM ----------------

# in-memory warn storage (you can later move to DB if needed)
self.warns = {}  # {guild_id: {user_id: warn_count}}

# ---------- Prefix warn command ----------
@commands.command(name="warn")
@has_permissions(kick_members=True, ban_members=True, manage_messages=True)
async def warn(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
    guild_warns = self.warns.setdefault(ctx.guild.id, {})
    guild_warns[member.id] = guild_warns.get(member.id, 0) + 1
    count = guild_warns[member.id]

    # send warn message in channel
    await ctx.send(f"⚠️ {member.mention} has been warned. Reason: {reason} (Warn {count})")
    try:
        await member.send(f"⚠️ You received a warning in {ctx.guild.name}. Reason: {reason} (Warn {count})")
    except:
        pass  # user has DMs closed

    # escalate actions based on warn count
    await self.handle_warn_escalation(ctx.guild, member, count)

# ---------- Slash warn command ----------
@app_commands.command(name="warn", description="Warn a member")
@app_commands.checks.has_permissions(kick_members=True, ban_members=True, manage_messages=True)
@app_commands.describe(member="Member to warn", reason="Reason")
async def warn_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    guild_warns = self.warns.setdefault(interaction.guild.id, {})
    guild_warns[member.id] = guild_warns.get(member.id, 0) + 1
    count = guild_warns[member.id]

    await interaction.response.send_message(f"⚠️ {member.mention} has been warned. Reason: {reason} (Warn {count})")
    try:
        await member.send(f"⚠️ You received a warning in {interaction.guild.name}. Reason: {reason} (Warn {count})")
    except:
        pass

    await self.handle_warn_escalation(interaction.guild, member, count)

# ---------- Escalation handler ----------
async def handle_warn_escalation(self, guild: discord.Guild, member: discord.Member, count: int):
    role = discord.utils.get(guild.roles, name="Muted")
    if count == 3:
        if not role:
            role = await guild.create_role(name="Muted", reason="Auto-created for warn system")
            for ch in guild.channels:
                try:
                    await ch.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
                except:
                    pass
        await member.add_roles(role, reason="3rd warning - auto mute 1 hour")
        await member.send("🔇 You have been muted for 1 hour due to 3 warnings.")
        # auto remove mute after 1 hour
        asyncio.create_task(self.remove_role_after(member, role, 3600))
    elif count == 4:
        if not role:
            role = await guild.create_role(name="Muted", reason="Auto-created for warn system")
            for ch in guild.channels:
                try:
                    await ch.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
                except:
                    pass
        await member.add_roles(role, reason="4th warning - auto mute 24 hours")
        await member.send("🔇 You have been muted for 24 hours due to 4 warnings.")
        asyncio.create_task(self.remove_role_after(member, role, 86400))
    elif count == 5:
        await member.kick(reason="5th warning - auto kick")
    elif count >= 6:
        await member.ban(reason="6th warning - auto ban")

# helper to remove role after delay
async def remove_role_after(self, member: discord.Member, role: discord.Role, delay: int):
    await asyncio.sleep(delay)
    if role in member.roles:
        try:
            await member.remove_roles(role, reason="Temporary mute expired")
        except:
            pass

# ---------------- ANTI-SPAM ----------------
# track last messages
self.user_messages = {}  # {(guild_id, user_id): [last 5 messages content]}

@commands.Cog.listener()
async def on_message(self, message: discord.Message):
    if message.author.bot or message.guild is None:
        return

    key = (message.guild.id, message.author.id)
    msgs = self.user_messages.setdefault(key, [])
    msgs.append(message.content.lower())
    if len(msgs) > 5:
        msgs.pop(0)

    # check spam (same message 5 times)
    if len(msgs) == 5 and all(m == msgs[0] for m in msgs):
        guild_warns = self.warns.setdefault(message.guild.id, {})
        guild_warns[message.author.id] = guild_warns.get(message.author.id, 0) + 1
        count = guild_warns[message.author.id]
        await message.channel.send(f"⚠️ {message.author.mention} warned for spamming. (Warn {count})")
        try:
            await message.author.send(f"⚠️ You received a warning in {message.guild.name} for spamming. (Warn {count})")
        except:
            pass
        await self.handle_warn_escalation(message.guild, message.author, count)
        self.user_messages[key] = []  # reset messages after spam warn
