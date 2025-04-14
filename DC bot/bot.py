import discord
from discord.ext import commands
from discord import app_commands, Embed, Interaction
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()
intents = discord.Intents.default()
intents.members = True  # Explicitně povolíme intent members
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

timers = {}

class Timer:
    def __init__(self, message: discord.Message, duration: int, starter: discord.User, name: str = "Časovač"):
        self.message = message
        self.total_duration = duration
        self.remaining = duration
        self.starter = starter
        self.running = False
        self.task = None
        self.name = name
        self.last_updater = None

    async def start(self, starter: discord.User):
        self.running = True
        self.last_updater = starter
        self.task = asyncio.create_task(self.run())

    async def run(self):
        while self.remaining > 0:
            await self.update_message()
            await asyncio.sleep(1 if self.remaining <= 60 else 60)
            self.remaining -= 1 if self.remaining <= 60 else 60
        await self.finish()

    async def update_message(self):
        embed = Embed(
            title=f"__**⏳ {self.name}**__",
            description=f"Zbývá: **{self.format_time()}**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Spuštěno", value=self.last_updater.mention if self.last_updater else self.starter.mention, inline=False)
        await self.message.edit(embed=embed)

    async def finish(self):
        embed = Embed(
            title=f"__**✅ {self.name} ready nebo je už 💀 !**__",
            description=f"Čas vypršel.",
            color=discord.Color.green()
        )
        embed.add_field(name="Spustil:", value=self.last_updater.mention if self.last_updater else self.starter.mention, inline=False)
        await self.message.edit(embed=embed)
        self.running = False
        self.remaining = self.total_duration
        self.last_updater = None

    def format_time(self):
        minutes, seconds = divmod(self.remaining, 60)
        return f"{minutes}m {seconds}s" if self.remaining < 60 else f"{minutes}m"

@tree.command(name="settimer", description="Vytvoří nový časovač")
@app_commands.describe(minuty="Délka časovače v minutách", nazev="Volitelný název časovače")
async def settimer(interaction: Interaction, minuty: int, nazev: str = "Časovač"):
    await interaction.response.defer()
    embed = Embed(
        title=f"__**⏳ {nazev} připraven**__",
        description=f"Zbývá: **{minuty}m**",
        color=discord.Color.blue()
    )
    embed.add_field(name="Spustit", value="Klikni na ✅ pro spuštění", inline=False)
    msg = await interaction.followup.send(embed=embed)
    await msg.add_reaction("✅")

    timers[msg.id] = Timer(msg, minuty * 60, interaction.user, nazev)   

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    channel = bot.get_channel(payload.channel_id)
    msg = await channel.fetch_message(payload.message_id)

    if payload.message_id in timers:
        timer = timers[payload.message_id]
        guild = bot.get_guild(payload.guild_id)
        user_who_reacted = guild.get_member(payload.user_id)

        # Odstranění jiných reakcí než ✅
        if str(payload.emoji.name) != "✅":
            try:
                if user_who_reacted:
                    await msg.remove_reaction(payload.emoji, user_who_reacted)
                    print(f"Odstraněna reakce {payload.emoji.name} od uživatele {user_who_reacted}")
            except discord.errors.Forbidden:
                print("Chyba: Bot nemá oprávnění odebírat reakce.")
            except discord.errors.NotFound:
                print("Chyba: Uživatel nebo reakce nebyla nalezena.")
            except discord.errors.HTTPException as e:
                print(f"Chyba při odebírání reakce: {e}")
            return

        # Pokud je reakce ✅ a časovač už běží, odstraníme ji
        if timer.running and str(payload.emoji.name) == "✅":
            try:
                if user_who_reacted:
                    await msg.remove_reaction(payload.emoji, user_who_reacted)
                    print(f"Odstraněna nežádoucí reakce ✅ od běžícího časovače od uživatele {user_who_reacted}")
            except discord.errors.Forbidden:
                print("Chyba: Bot nemá oprávnění odebírat reakce.")
            except discord.errors.NotFound:
                print("Chyba: Uživatel nebo reakce nebyla nalezena.")
            except discord.errors.HTTPException as e:
                print(f"Chyba při odebírání reakce: {e}")
            return

        # Spuštění časovače, pokud neběží a je to reakce ✅
        if not timer.running and str(payload.emoji.name) == "✅":
            print("Vstupuji do bloku pro spuštění časovače")
            if user_who_reacted is not None:
                try:
                    await msg.remove_reaction("✅", user_who_reacted)
                    print("Reakce ✅ od spouštějícího odebrána (pokus)")
                    await timer.start(user_who_reacted)
                    print("Časovač spuštěn (volána metoda timer.start())")

                    # Odstraníme ostatní reakce ✅
                    for reaction in msg.reactions:
                        if str(reaction.emoji) == "✅":
                            async for user in reaction.users():
                                if user != bot.user and user != user_who_reacted:
                                    try:
                                        await msg.remove_reaction("✅", user)
                                        print(f"Odebrána reakce ✅ od uživatele: {user}")
                                    except discord.errors.Forbidden:
                                        print(f"Chyba: Bot nemá oprávnění odebrat reakci ✅ od uživatele: {user}")
                                    except discord.errors.HTTPException as e:
                                        print(f"Chyba při odebírání reakce: {e}")
                except discord.errors.Forbidden:
                    print("Chyba: Bot nemá oprávnění odebírat reakce (uvnitř bloku)")
            else:
                print("Uživatele se stále nepodařilo získat, nemohu odebrat reakci ani spustit časovač.")   

@bot.event
async def on_ready():
    print(f"Bot přihlášen jako {bot.user}")
    try:
        synced = await tree.sync()
        print(f"Slash příkazy synchronizovány: {len(synced)}")
    except Exception as e:
        print(f"Chyba při synchronizaci slash příkazů: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))