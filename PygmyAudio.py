import discord
from discord import app_commands
from discord.ext import commands
from YTDLSource import YTDLSource

class PygmyAudio(commands.GroupCog, name="pygaudio"):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.skips = 0
        self.guild_audio_players = dict[int, GuildAudioPlayer]()
        super().__init__()


#region Voice Chat 

    async def try_ensure_voice(self, interaction: discord.Interaction):
        
        channel: discord.VoiceChannel = None

        if interaction.user.voice:
            channel = interaction.user.voice.channel
        else:
            return False

        await self.join_voice_channel(interaction.guild, channel)
        return True
    

    async def join_voice_channel(self, guild: discord.Guild, channel: discord.VoiceChannel):

        if guild.voice_client is not None:
            if guild.voice_client.channel is channel:
                return
            
            #await guild.voice_client.move_to(channel)
            await guild.change_voice_state(channel=channel,self_deaf=True)
            return

        await channel.connect(self_deaf=True)
        self.guild_audio_players[guild.id] = GuildAudioPlayer(self, guild)
        

    async def disconnect_voice_client(self, guild: discord.Guild):
        
        if guild.id in self.guild_audio_players:
            self.guild_audio_players[guild.id].cleanup()
            del self.guild_audio_players[guild.id]

        if guild.voice_client is not None and guild.voice_client.channel is not None:
            await guild.voice_client.disconnect()
            return True
        return False

#endregion

#region Commands

    @app_commands.command(name="disconnect")
    async def command_disconnect(self, interaction: discord.Interaction):
        """Bot will leave any voice chat it is currently in."""

        voice_channel_left = await self.disconnect_voice_client(interaction.guild)
        
        if voice_channel_left:
            await interaction.response.send_message("Leaving voice channel.", ephemeral=True)
        else:
            await interaction.response.send_message("The bot is not in any voice channel.", ephemeral=True)

    @app_commands.command(name="set_skips_needed_amount")
    async def command_set_skips_needed_amount(self, interaction: discord.Interaction, skips_needed: int):
        """Set the amount of skips needed"""

        self.bot.set_guild_setting(interaction.guild.id, 
                                   GuildAudioPlayer.SETTINGS_ID_SKIP_AMOUNT, 
                                   {True: 1, False: skips_needed} [skips_needed == 0])  
        
        await interaction.response.send_message(f"Set skip amounts needed to: {skips_needed}")
    
    @app_commands.command(name="simple_play")
    async def command_simple_play(self, interaction: discord.Interaction, url:str):

        print("Simply playing")
        await interaction.response.defer(thinking=True)

        try:
            in_voice = await self.try_ensure_voice(interaction=interaction)

            if in_voice == False:
                await interaction.followup.send(content="You are not in a voice channel.")
                return
        
            if interaction.guild.voice_client.is_playing():
                print("currently playing something, stopping it")
                interaction.guild.voice_client.stop()

            player = await YTDLSource.play_from_url(url, loop=self.bot.loop, stream=True)
        
            interaction.guild.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

            await interaction.followup.send(content=f'Now playing: {player.title}')
        except:
            await interaction.followup.send("Sorry, there was an error.")


    @app_commands.command(name="play")
    async def play(self, interaction: discord.Interaction, *, url:str):
        """Plays audio from a URL, or queues if something is already playing"""

        await interaction.response.defer(thinking=True)
        try:
            in_voice = await self.try_ensure_voice(interaction=interaction)
            if in_voice == False:
                await interaction.followup.send(content="You are not in a voice channel.")
                return

            queued_values: list = await self.guild_audio_players[interaction.guild.id].add_to_queue(url, interaction.user)
            is_playing = self.guild_audio_players[interaction.guild.id].try_play_next()
            if is_playing == False:
                await interaction.followup.send(f"Added {len(queued_values)} items to queue. Queue is now {len(self.guild_audio_players[interaction.guild.id].queue)} long.")
                return
            await interaction.followup.send(self.guild_audio_players[interaction.guild.id].get_now_playing_text())
        except:
            await interaction.followup.send("Sorry, there was an error.")
            raise
            
    
    
    @app_commands.command(name="clear_queue")
    async def command_clear_queue(self, interaction: discord.Interaction):
        if interaction.guild.id in self.guild_audio_players:
            self.guild_audio_players[interaction.guild.id].clear_queue()
            await interaction.response.send_message("Queue has been cleared.")
            return
        await interaction.response.send_message("There is no active voice client.")
            
    
    @app_commands.command(name="skip")
    async def command_skip(self, interaction: discord.Interaction):
        """Requests to skip the current audio."""

        if interaction.guild.id in self.guild_audio_players:
            await self.guild_audio_players[interaction.guild.id].request_skip(interaction=interaction)
        else:
            await interaction.response.send_message("There is no active voice client.")

    @app_commands.command(name="loop")
    async def command_loop(self, interaction: discord.Interaction, loop: bool):
        if interaction.guild.id in self.guild_audio_players:
            self.guild_audio_players[interaction.guild.id].loop = loop
            await interaction.response.send_message(f"Loop audio changed: {loop}")
        else:
            await interaction.response.send_message("There is no active voice client.")
    
    @app_commands.command(name="now_playing")
    async def command_now_playing(self, interaction: discord.Interaction):
        if interaction.guild.id in self.guild_audio_players:
            await interaction.response.send_message(self.guild_audio_players[interaction.guild.id].get_now_playing_text())
        await interaction.response.send_message("There is no active voice client")
    
    @app_commands.command(name="stop")
    async def command_stop(self, interaction: discord.Interaction):
        if interaction.guild.id in self.guild_audio_players:
            self.guild_audio_players[interaction.guild.id].stop()
            await interaction.response.send_message("Stopped audio.")
            return
        await interaction.response.send_message("There is no active voice client")
        
#endregion


#region Guild Music Player

from collections import deque

class GuildAudioPlayer():

    SETTINGS_ID_SKIP_AMOUNT = "skip_amount_needed"

    def __init__(self, music_cog:PygmyAudio, guild: discord.Guild):
        self.current_source: YTDLSource = None
        self.music_cog = music_cog
        self.bot = music_cog.bot
        self.guild = guild
        self.skips = 0
        self.loop = False
        self.users_requesting_skips = list[int]()
        self.queue = deque[GuildAudioInstance]()
        self.bot.event_manager.add_listener(self.bot.EVENT_NAME_GUILD_SETTINGS_CHANGED, self.on_guild_settings_changed)
           
    def __del__(self):
        self.cleanup()
    
    def cleanup(self):
        self.bot.event_manager.remove_listener(self.bot.EVENT_NAME_GUILD_SETTINGS_CHANGED, self.on_guild_settings_changed)
    
    def try_play_next(self, forceSkip: bool = False):
        if self.guild.voice_client.is_playing():
            if forceSkip == False:
                return False
            self.skip_current()
        
        next_audio_instance = self.peek_next_audio()

        ytdl_source_player = YTDLSource.get_player_from_data(next_audio_instance.data, stream=True)
        self._play_source(ytdl_source_player)
        return True
    
    def _play_source(self, source: YTDLSource):
        self.current_source = source
        self.guild.voice_client.play(source, 
                                     after=lambda e: 
                                     print(f'Player error: {e}') if e else None
                                     )
        #todo: self.send_now_playing_message()
    
    #async def send_now_playing_message(self):
        #await self.bot.command_channel.send_message(self.get_now_playing_text())

    def get_now_playing_text(self):
        if self.current_source is not None:
            return f"Now playing: {self.current_source.title}"
        return "Nothing is currently playing."

    async def add_to_queue(self, url:str, user: discord.User):
        data = await YTDLSource.extract_url_data(url=url,event_loop=self.bot.loop, download=False)
        queued_values = list()

        if 'entries' in data:
            for key in data["entries"]:
                print (f"\n\n Key: {key}")
                audio_instance: GuildAudioInstance = GuildAudioInstance(self, user, data[key])
                self.queue.append(audio_instance)
                queued_values.append(len(self.queue))
        else:
            audio_instance: GuildAudioInstance = GuildAudioInstance(self, user, data)
            self.queue.append(audio_instance)
        
        return queued_values

    def clear_queue(self):
        self.queue.clear()
    
    def add_to_front_of_queue(self, url:str):
        self.queue.appendleft(url)
    
    def peek_next_audio(self):
        return self.queue[0]
    
    def peek_recently_added_audio(self):
        return self.queue[-1]
    
    def pause(self):
        self.guild.voice_client.pause()
    
    def unpause(self):
        if self.guild.voice_client.is_paused():
            self.guild.voice_client.resume()

    async def request_skip(self, interaction: discord.Interaction):
        if interaction.user.id not in self.users_requesting_skips:
            
            self.users_requesting_skips.append(interaction.user.id)
            
            if len(self.users_requesting_skips) >= self.bot.guild_settings[
                self.guild.id][GuildAudioPlayer.SETTINGS_ID_SKIP_AMOUNT]:
                self.skip_current()
                is_playing = await self.try_play_next()
                if is_playing:
                    await interaction.response.send_message("Skipping current song!")
                else:
                    await interaction.response.send_message("Skipping current song, no other songs in queue.")
                return
            
            await interaction.response.send_message(f"Currently {self.skips}/{GuildAudioPlayer.SETTINGS_ID_SKIP_AMOUNT} skips requested.")
        
        await interaction.response.send_message("You've already requested to skip this song." +
        f" Currently {self.skips}/{GuildAudioPlayer.SETTINGS_ID_SKIP_AMOUNT} skips requested.")

        return

    def skip_current(self):
        self.skips = 0
        audio_instance = self.queue.popleft()
        self.stop()
        del audio_instance
    
    def current_audio_finished():
        print("Current audio has finished.")
    
    def stop(self):
        if self.guild.voice_client.is_playing():
            self.guild.voice_client.stop()
        self.current_source = None

    #region Guild Settings Updates

    def on_guild_settings_changed(self, guild_id:int, settings_id:str, settings_value:object):
        self.on_skip_amount_needed_changed(guild_id, settings_id, settings_value)

    def on_skip_amount_needed_changed(self, guild_id:int, settings_id:str, settings_value:object):
        print("Checking skip amount needed guild setting")
        if settings_id != GuildAudioPlayer.SETTINGS_ID_SKIP_AMOUNT:
            return
        
        print("skip amount needed id matched")
        
        if self.skips >= settings_value:
            #TODO: skip song.
            return


    #endregion

#endregion

class GuildAudioInstance():
    def __init__(self, guild_audio_player: GuildAudioPlayer, requested_user:discord.User, data: dict):
        self.guild_audio_player = guild_audio_player
        self.requested_user = requested_user
        self.data = data
