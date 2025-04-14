import discord
from discord.ext import commands
from discord import app_commands, Embed, Interaction
import asyncio
import os

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

timers = {}

class Timer:
    def __init__(self, message: discord.Message, duration: int, starter: discord.User):
        self.message = message
        self.total_duration = duration
        self.remaining = duration
        self.starter = starter
        self.running = False
        self.task = None

    async def start(self):
        self.running = True
        self.task = asyncio.create_task(self.run())

    async def run(self):
        while self.remaining > 0:
            await self.update_message()
            await asyncio.sleep(1 if self.remaining <= 60 else 60)
            self.remaining -= 1 if self.remaining <= 60 else 60
        await self.finish()

    async def update_message(self):
        embed = Embed(
            title="⏳ Timer",
            description=f"Zbývá: **{self.format_time()}**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Spuštěno", value=self.starter.mention)
        await self.message.edit(embed=embed)

    async def finish(self):
        embed = Embed(
            title="✅ Timer dokončen!",
            description=f"Čas vypršel.",
            color=discord.Color.green()
        )
        embed.add_field(name="Spustil", value=self.starter.mention)
        await self.message.edit(embed=embed)
        self.running = False
        self.remaining = self.total_duration

    def format_time(self):
        minutes, seconds = divmod(self.remaining, 60)
        return f"{minutes}m {seconds}s" if self.remaining < 60 else f"{minutes}m"

@tree.command(name="settimer", description="Vytvoří nový časovač")
@app_commands.describe(minuty="Délka časovače v minutách")
async def settimer(interaction: Interaction, minuty: int):
    await interaction.response.defer()
    embed = Embed(
        title="⏳ Timer připraven",
        description=f"Zbývá: **{minuty}m**",
        color=discord.Color.blue()
    )
    embed.add_field(name="Spustit", value="Klikni na ✅ pro spuštění")
    msg = await interaction.followup.send(embed=embed)
    await msg.add_reaction("✅")

    timers[msg.id] = Timer(msg, minuty * 60, interaction.user)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    if payload.message_id in timers and str(payload.emoji.name) == "✅":
        channel = bot.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)
        timer = timers[payload.message_id]
        if not timer.running:
            await timer.start()

@bot.event
async def on_ready():
    print(f"Bot přihlášen jako {bot.user}")
    try:
        synced = await tree.sync()
        print(f"Slash příkazy synchronizovány: {len(synced)}")
    except Exception as e:
        print(f"Chyba při synchronizaci slash příkazů: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
