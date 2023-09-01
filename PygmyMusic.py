import discord
import youtube_dl
import asyncio
import time
from discord import app_commands
from discord.ext import commands



# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


#region Voice Commands

class PygmyMusic(commands.GroupCog, name="pygmusic"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()
    
    async def join_voice_channel(self, interaction: discord.Interaction):
        
        print("joining voice chat")
        guild = interaction.guild
        channel: discord.VoiceChannel = None

        print("guild gathered")

        if interaction.user.voice:
            print("author is in voice")
            channel = interaction.user.voice.channel
        else:
            print("author is not in voice")
            await interaction.response.send_message("You are not connected to a voice channel")
            return False

        if guild.voice_client is not None:

            if guild.voice_client.channel is channel:
                print("already in the correct voice channel")
                return True
            
            print("transferring to a different channel")
            await guild.voice_client.move_to(channel)
            await guild.change_voice_state(channel=channel,self_deaf=True)
            return True

        print(f"connecting to channel {channel.name}")
        await channel.connect(self_deaf=True)
        return True
        

    @app_commands.command(name="disconnect", description="Bot will leave any voice chat it is currently in.")
    async def disconnect_voice_chat(self, interaction: discord.Interaction):
        
        if interaction.guild.voice_client is not None and interaction.guild.voice_client.channel is not None:
            await interaction.response.send_message("Leaving voice channel.", ephemeral=True)
            await interaction.guild.voice_client.disconnect()
            await interaction.guild.voice_client.cleanup()
        else:
            await interaction.response.send_message("The bot is not in any voice channel.", ephemeral=True)

    #endregion


    #region Music Commands

    @app_commands.command(name="play")
    async def play(self, interaction: discord.Interaction, *, url:str):
        """Plays from a url (almost anything youtube_dl supports)"""
        
        print("Attempting to ensure in voice chat")
        in_voice = await self.ensure_voice(interaction=interaction)

        if in_voice == False:
            print("Leaving, user is not in voice chat")
            return
        print("Should be present in voice chat")
        time.sleep(0.5)

        async with interaction.channel.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
        
        interaction.guild.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

        await interaction.response.send_message(f'Now playing: {player.title}')
    #endregion

    async def ensure_voice(self, interaction: discord.Interaction):

        return await self.join_voice_channel(interaction=interaction)