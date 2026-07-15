import asyncio
import os
import threading
import discord
from discord.ext import commands
from config import DISCORD_BOT_TOKEN
from modules.request_queue import submit
from modules.persistence import append_entry
from modules.tts import synthesize_sentence

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

_loop = None
_voice_client = None

@bot.event
async def on_ready():
    global _loop
    _loop = asyncio.get_running_loop()
    await bot.tree.sync()
    print(f"[discord] logged in as {bot.user}")

@bot.tree.command(name="join", description="Bring NAI into your voice channel")
async def join(interaction: discord.Interaction):
    global _voice_client
    if not interaction.user.voice:
        await interaction.response.send_message("You're not in a voice channel.")
        return
    _voice_client = await interaction.user.voice.channel.connect()
    await interaction.response.send_message("Joined.")

@bot.tree.command(name="leave", description="Disconnect NAI from voice")
async def leave(interaction: discord.Interaction):
    global _voice_client
    if _voice_client:
        await _voice_client.disconnect()
        _voice_client = None
        await interaction.response.send_message("Left.")
    else:
        await interaction.response.send_message("Not in a voice channel.")

def _speak_in_vc(text):
    if _voice_client is None or not _voice_client.is_connected():
        return
    try:
        path, _, _ = synthesize_sentence(text)
    except Exception as e:
        print(f"[discord] tts synth failed: {e}")
        return

    async def _play():
        while _voice_client.is_playing():
            await asyncio.sleep(0.1)
        _voice_client.play(discord.FFmpegPCMAudio(path),
                            after=lambda e: os.path.exists(path) and os.remove(path))

    asyncio.run_coroutine_threadsafe(_play(), _loop)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if bot.user not in message.mentions:
        await bot.process_commands(message)
        return

    text = message.content.replace(f"<@{bot.user.id}>", "").strip()
    if not text:
        return
    append_entry("user", text, source="discord")

    def on_sentence(sentence):
        _speak_in_vc(sentence)

    def on_done(full_reply):
        append_entry("ai", full_reply, source="discord")
        asyncio.run_coroutine_threadsafe(message.channel.send(full_reply), _loop)

    def on_error(e):
        asyncio.run_coroutine_threadsafe(message.channel.send(f"Error: {e}"), _loop)

    submit(text, "discord", on_sentence, on_done, on_error)
    await bot.process_commands(message)

def start_bot():
    threading.Thread(target=lambda: bot.run(DISCORD_BOT_TOKEN), daemon=True).start()