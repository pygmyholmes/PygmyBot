import discord
from discord import app_commands
from discord.ext import commands
from YTDLSource import YTDLSource
from queue import Queue

class PygmyMusic(commands.GroupCog, name="pygmusic"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        #self.guildQueues = dict[int, Queue] = {}
        super().__init__()

    async def ensure_voice(self, interaction: discord.Interaction):

        return await self.join_voice_channel(interaction=interaction)
    
    async def join_voice_channel(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel: discord.VoiceChannel = None

        if interaction.user.voice:
            channel = interaction.user.voice.channel
        else:
            return False

        if guild.voice_client is not None:
            if guild.voice_client.channel is channel:
                return True
            
            await guild.voice_client.move_to(channel)
            await guild.change_voice_state(channel=channel,self_deaf=True)
            return True

        await channel.connect(self_deaf=True)
        return True
        

    @app_commands.command(name="disconnect")
    async def disconnect_voice_chat(self, interaction: discord.Interaction):
        """Bot will leave any voice chat it is currently in."""
        
        if interaction.guild.voice_client is not None and interaction.guild.voice_client.channel is not None:
            await interaction.response.send_message("Leaving voice channel.", ephemeral=True)
            await interaction.guild.voice_client.disconnect()

        else:
            await interaction.response.send_message("The bot is not in any voice channel.", ephemeral=True)

    #region Music Commands

    @app_commands.command(name="play")
    async def play(self, interaction: discord.Interaction, *, url:str, loop: bool = None):
        """Plays audio from a URL"""

        ctx:commands.Context = await self.bot.get_context(interaction)
        await interaction.response.defer(thinking=True)

        in_voice = await self.ensure_voice(interaction=interaction)

        if in_voice == False:
            await interaction.followup.send(content="You are not in a voice channel.")
            return

        if ctx.voice_client.is_playing():
            await interaction.followup.send(content="Something is already playing, and I haven't made queues yet. Sorry.")
            return

        player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        
        interaction.guild.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

        await interaction.followup.send(content=f'Now playing: {player.title}')
    #endregion