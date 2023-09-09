import discord
from discord import app_commands
from discord.ext import commands
from YTDLSource import YTDLSource

from Config import Config

class PygmyAudio(commands.Cog):

    SETTINGS_ID_SKIP_AMOUNT = "skip_amount_needed"

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.guild_audio_players = dict[int, GuildAudioPlayer]()
        self.init_event_listeners()
        super().__init__()

    def __del__(self):
        self.cleanup()
    
    def cleanup(self):
        self.cleanup_event_listeners()
    
    def init_event_listeners(self):
        self.bot.event_manager.add_listener(self.bot.EVENT_NAME_GUILD_SETTINGS_CHANGED, self.on_guild_settings_changed)
        self.bot.event_manager.add_listener(self.bot.EVENT_NAME_GUILD_SETTINGS_CREATED, self.on_setup_guilds_settings)

    def cleanup_event_listeners(self):
        self.bot.event_manager.remove_listener(self.bot.EVENT_NAME_GUILD_SETTINGS_CHANGED, self.on_guild_settings_changed)
        self.bot.event_manager.remove_listener(self.bot.EVENT_NAME_GUILD_SETTINGS_CREATED, self.on_setup_guilds_settings)
    
    def on_guild_settings_changed(self, guild_id:int, settings_id:str, settings_value:object):
        if guild_id in self.guild_audio_players:
            self.guild_audio_players[guild_id].on_guild_settings_changed(guild_id, settings_id, settings_value)

    def on_setup_guilds_settings(self, guild_setting_dict: dict[str, object]):
        guild_setting_dict[PygmyAudio.SETTINGS_ID_SKIP_AMOUNT] = int(Config.CONFIG["PygmyAudio"]["Default_Skips_Needed"])

#region Voice Chat 

    async def check_user_in_voice(self, interaction: discord.Interaction):
        
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

        await interaction.response.defer()

        self.bot.set_guild_setting(interaction.guild.id, 
                                   PygmyAudio.SETTINGS_ID_SKIP_AMOUNT, 
                                   {True: 1, False: skips_needed} [skips_needed <= 0])  
        
        await interaction.followup.send(f"Set skip amounts needed to: {skips_needed}")
    
    @app_commands.command(name="simple_play")
    async def command_simple_play(self, interaction: discord.Interaction, url:str):

        print("Simply playing")
        await interaction.response.defer(thinking=True)

        try:
            in_voice = await self.check_user_in_voice(interaction=interaction)

            if in_voice == False:
                await interaction.followup.send(content="You are not in a voice channel.")
                return
        
            if interaction.guild.voice_client.is_playing():
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
            in_voice = await self.check_user_in_voice(interaction=interaction)
            if in_voice == False:
                await interaction.followup.send(content="You are not in a voice channel.")
                return

            queued_values: list = await self.guild_audio_players[interaction.guild.id].add_to_queue(url, interaction.user)

            if len(queued_values) == 0:
                await interaction.followup.send(f"Failed to find audio. Nothing was added to the queue.")
                return
            
            already_playing = self.guild_audio_players[interaction.guild.id].is_playing

            if already_playing == False:
                self.guild_audio_players[interaction.guild.id].try_play()

            if already_playing == True:
                await interaction.followup.send(f"Added {len(queued_values)} items to queue. Queue is now {len(self.guild_audio_players[interaction.guild.id].queue)-1} long.")
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
            return
        await interaction.response.send_message("There is no active voice client")
    
    @app_commands.command(name="stop")
    async def command_stop(self, interaction: discord.Interaction):
        if interaction.guild.id in self.guild_audio_players:
            self.guild_audio_players[interaction.guild.id].shutdown()
            await interaction.response.send_message("Stopped audio.")
            return
        await interaction.response.send_message("There is no active voice client")
        
#endregion


#region Guild Music Player

from collections import deque
import time
import asyncio

class GuildAudioPlayer():

    def __init__(self, music_cog:PygmyAudio, guild: discord.Guild):
        self.current_source: YTDLSource = None
        self.music_cog = music_cog
        self.bot = music_cog.bot
        self.guild = guild
        self.loop_song = False
        self.loop_queue = False
        self.is_playing = False
        self.users_requesting_skips = list[int]()
        self.queue = deque[GuildAudioInstance]()
    
    def cleanup(self):
        return
    
    def try_play(self):
        self._try_play_next()
    
    def _try_play_next(self):
        if len(self.queue) == 0:
            self.is_playing = False
            return False
        
        self.is_playing = True
        
        next_audio_instance = self.peek_current_audio()

        ytdl_source_player = YTDLSource.get_player_from_data(next_audio_instance.data, stream=True)
        self._play_source(ytdl_source_player)
        return True
    
    def _play_source(self, source: YTDLSource):
        self.current_source = source
        self.guild.voice_client.play(source, after=self._current_source_finished)

    def get_now_playing_text(self):
        if self.current_source is not None:
            return f"Now playing: {self.current_source.title}"
        return "Nothing is currently playing."

    async def add_to_queue(self, url:str, user: discord.User):
        data = await YTDLSource.extract_url_data(url=url,event_loop=self.bot.loop, download=False)
        queued_values = list()

        if 'entries' in data:
            for data_dict in data['entries']:
                audio_instance: GuildAudioInstance = GuildAudioInstance(self, user, data_dict)
                self.queue.append(audio_instance)
                queued_values.append(len(self.queue))
        else:
            audio_instance: GuildAudioInstance = GuildAudioInstance(self, user, data)
            self.queue.append(audio_instance)
            queued_values.append(len(self.queue))
        
        return queued_values

    def shutdown(self):
        self.clear_queue()
        self._stop()
    
    def clear_queue(self):
        self.queue.clear()
    
    def add_to_front_of_queue(self, url:str):
        self.queue.appendleft(url)
    
    def peek_current_audio(self):
        return self.queue[0]
    
    def peek_recently_added_audio(self):
        return self.queue[-1]
    
    def pause(self):
        self.guild.voice_client.pause()
    
    def unpause(self):
        if self.guild.voice_client.is_paused():
            self.guild.voice_client.resume()

    async def request_skip(self, interaction: discord.Interaction):
        
        skips_needed: int = self.bot.guild_settings[self.guild.id][PygmyAudio.SETTINGS_ID_SKIP_AMOUNT]

        if len(self.users_requesting_skips) >= skips_needed:
                print("This shouldn't have happened. We shouldn't need to request to skip if the amount is already equal to or past the amount needed")
                self._skip_current()
                if len(self.queue) > 0:
                    await interaction.response.send_message("Skipping current song!")
                else:
                    await interaction.response.send_message("Skipping current song, no other songs in queue.")
                return
        
        if interaction.user.id not in self.users_requesting_skips:
            
            self.users_requesting_skips.append(interaction.user.id)
            
            if len(self.users_requesting_skips) >= skips_needed:
                self._skip_current()
                
                if len(self.queue) > 0:
                    await interaction.response.send_message("Skipping current song!")
                else:
                    await interaction.response.send_message("Skipping current song, no other songs in queue.")
                return
            
            await interaction.response.send_message(f"Skip registered! Currently {len(self.users_requesting_skips)}/{skips_needed} skips requested.")
            return
        
        await interaction.response.send_message("You've already requested to skip this song." +
        f" Currently {len(self.users_requesting_skips)}/{skips_needed} skips requested.")

        return

    def _skip_current(self):
        self.users_requesting_skips.clear()
        self._clear_current_source()
    
    def _stop(self):
        if self.guild.voice_client.is_playing():
            self.guild.voice_client.stop()
        self.current_source = None
    
    def _clear_current_source(self):
        if self.is_playing == False or len(self.queue) == 0:
            return
        
        audio_instance = self.queue.popleft()
        self._stop()
        del audio_instance
        self.is_playing = False
        
    def _current_source_finished(self, e):
        if not self.guild.voice_client:
            return
        print(f"Current audio has finished. {e if e else ''}")
        self._clear_current_source()
        self._try_play_next()
        if self.is_playing == False:
            asyncio.run_coroutine_threadsafe(self.music_cog.disconnect_voice_client(self.guild), self.bot.loop)

    #region Guild Settings Updates

    def on_guild_settings_changed(self, guild_id:int, settings_id:str, settings_value:object):
        self._on_skip_amount_needed_changed(guild_id, settings_id, settings_value)

    def _on_skip_amount_needed_changed(self, guild_id:int, settings_id:str, settings_value:object):
        if settings_id != PygmyAudio.SETTINGS_ID_SKIP_AMOUNT:
            return
        
        if len(self.users_requesting_skips) >= settings_value:
            self._skip_current()
            #TODO: send a message to last command channel saying that the new skip amount is enough to skip, and that its triggered a skip.
            return

    #endregion

#endregion

class GuildAudioInstance():
    def __init__(self, guild_audio_player: GuildAudioPlayer, requested_user:discord.User, data: dict):
        self.guild_audio_player = guild_audio_player
        self.requested_user = requested_user
        self.data = data
