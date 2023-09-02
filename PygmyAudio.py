import discord
from discord import app_commands
from discord.ext import commands
from YTDLSource import YTDLSource

class PygmyAudio(commands.GroupCog, name="pygaudio"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_audio_players = dict[int, GuildAudioPlayer]()
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
    async def disconnect(self, interaction: discord.Interaction):
        """Bot will leave any voice chat it is currently in."""

        voice_channel_left = self.disconnect_voice_client(interaction.guild)
        
        if voice_channel_left:
            await interaction.response.send_message("Leaving voice channel.", ephemeral=True)
        else:
            await interaction.response.send_message("The bot is not in any voice channel.", ephemeral=True)


    async def disconnect_voice_client(self, guild: discord.Guild):
        if guild.voice_client is not None and guild.voice_client.channel is not None:
            await guild.voice_client.disconnect()
            return True
        return False
    
    @app_commands.command(name="skip")
    async def skip(self, interaction: discord.Interaction):
        if interaction.guild.id in self.guild_audio_players:
            await self.guild_audio_players[interaction.guild.id].request_skip(interaction=interaction)
        else:
            await interaction.response.send_message("There is no active voice client.")

    @app_commands.command(name="set_skips_needed_amount")
    async def set_skips_needed_amount(self, interaction: discord.Interaction, skips_needed: int):
        self.bot.set_guild_setting(interaction.guild.id, 
                                   GuildAudioPlayer.SETTINGS_ID_SKIP_AMOUNT, 
                                   {True: 1, False: skips_needed} [skips_needed == 0])  
        await interaction.response.send_message(f"Set skip amounts needed to: {skips_needed}")
        
        
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

    #region Event Listeners

    #endregion


#region Guild Music Player

from collections import deque

class GuildAudioPlayer():

    SETTINGS_ID_SKIP_AMOUNT = "skip_amount_needed"

    def __init__(self, music_cog:PygmyAudio, guild: discord.Guild):
        self.music_cog = music_cog
        self.guild = guild
        self.skips = 0
        self.users_requesting_skips = list[int]()
        self.queue = deque[GuildAudioInstance]()
        self.bot.event_manager.add_listener(self.bot.EVENT_NAME_GUILD_SETTINGS_CHANGED, self.on_guild_settings_changed)
           
    def __del__(self):
        self.bot.event_manager.remove_listener(self.bot.EVENT_NAME_GUILD_SETTINGS_CHANGED, self.on_guild_settings_changed)
       
    #region Queue Commands

    def add_to_queue(self, interaction: discord.Interaction, *, url:str, loop:bool):
        self.queue.append(url)
    
    def clear_queue(self):
        self.queue.clear()
    
    def add_to_front_of_queue(self, url:str):
        self.queue.appendleft(url)

    async def request_skip(self, interaction: discord.Interaction):
        if interaction.user.id not in self.users_requesting_skips:
            
            self.users_requesting_skips.append(interaction.user.id)
            
            if len(self.users_requesting_skips) >= self.music_cog.bot.guild_settings[
                self.guild.id][GuildAudioPlayer.SETTINGS_ID_SKIP_AMOUNT]:
                self.skip()
                await interaction.response.send_message("Skipping current song!")
                return
            
            await interaction.response.send_message(f"Currently {self.skips}/{GuildAudioPlayer.SETTINGS_ID_SKIP_AMOUNT} skips requested.")
        
        await interaction.response.send_message("You've already requested to skip this song." +
        f" Currently {self.skips}/{GuildAudioPlayer.SETTINGS_ID_SKIP_AMOUNT} skips requested.")

        return

    def skip(self):
        self.skips = 0
        self.queue[-1]
    
    #endregion

    #region Guild Settings Updates

    def on_guild_settings_changed(self, guild_id:int, settings_id:str, settings_value:object):
        self.on_skip_amount_needed_changed(guild_id, settings_id, settings_value)

    def on_skip_amount_needed_changed(self, guild_id:int, settings_id:str, settings_value:object):
        print("Checking skip amount needed guild setting")
        if settings_id != GuildAudioPlayer.SETTINGS_ID_SKIP_AMOUNT:
            return
        
        print("skip amount needed id matched")
        
        if self.skips >= settings_value:
            #todo: skip song.
            return


    #endregion



#endregion

class GuildAudioInstance():
    def __init__(self, guild_audio_player: GuildAudioPlayer, requested_user:discord.User):
        self.guild_audio_player = guild_audio_player
        self.requested_user = requested_user
    
    
