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

        await channel.connect(self_deaf=True, reconnect=True)
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

    @app_commands.command(name="setskipsneededamount")
    async def command_set_skips_needed_amount(self, interaction: discord.Interaction, skips_needed: int):
        """Set the amount of skips needed"""

        await interaction.response.defer()

        self.bot.set_guild_setting(interaction.guild.id, 
                                   PygmyAudio.SETTINGS_ID_SKIP_AMOUNT, 
                                   {True: 1, False: skips_needed} [skips_needed <= 0])  
        
        await interaction.followup.send(f"Set skip amounts needed to: {skips_needed}")


    @app_commands.command(name="play")
    async def play(self, interaction: discord.Interaction, *, url:str):
        """Play or queue audio to the end of the queue"""

        await interaction.response.defer(thinking=True)
        try:
            in_voice = await self.check_user_in_voice(interaction=interaction)
            if in_voice == False:
                await interaction.followup.send(content="You are not in a voice channel.")
                return

            amount_queued: int = await self.guild_audio_players[interaction.guild.id].add_to_queue(url, interaction.user)

            if amount_queued == 0:
                await interaction.followup.send(f"Failed to find audio. Nothing was added to the queue.")
                return
            
            already_playing = self.guild_audio_players[interaction.guild.id].is_playing

            if already_playing == False:
                self.guild_audio_players[interaction.guild.id].try_play()

            if already_playing == True:
                await interaction.followup.send(f"Added {amount_queued} items to queue. Queue is now {len(self.guild_audio_players[interaction.guild.id].queue)-1} long.")
                return
                        
            followup_message:str = ""
            if amount_queued > 1:
                followup_message += f"Added {amount_queued} items to the queue.\n"
            
            followup_message += self.guild_audio_players[interaction.guild.id].get_now_playing_text()
            await interaction.followup.send(followup_message)
        except:
            await interaction.followup.send("Sorry, there was an error.")
            raise
    
    @app_commands.command(name="playnext")
    async def command_play_next(self, interaction: discord.Interaction, *, url:str):
        """Play or queue audio next in the queue"""
        
        await interaction.response.defer(thinking=True)
        try:
            in_voice = await self.check_user_in_voice(interaction=interaction)
            if in_voice == False:
                await interaction.followup.send(content="You are not in a voice channel.")
                return

            amount_queued: int = await self.guild_audio_players[interaction.guild.id].add_to_front_of_queue(url, interaction.user)

            if amount_queued == 0:
                await interaction.followup.send(f"Failed to find audio. Nothing was added to the queue.")
                return
            
            already_playing = self.guild_audio_players[interaction.guild.id].is_playing

            if already_playing == False:
                self.guild_audio_players[interaction.guild.id].try_play()

            if already_playing == True:
                await interaction.followup.send(f"Added {amount_queued} items to the front of the queue. Queue is now {len(self.guild_audio_players[interaction.guild.id].queue)-1} long.")
                return
            
            followup_message:str = ""
            if amount_queued > 1:
                followup_message += f"Added {amount_queued} items to the queue.\n"
            
            followup_message += self.guild_audio_players[interaction.guild.id].get_now_playing_text()
            await interaction.followup.send(followup_message)
        except:
            await interaction.followup.send("Sorry, there was an error.")
            raise
    
            
    @app_commands.command(name="clearqueue")
    async def command_clear_queue(self, interaction: discord.Interaction):
        """Clears the current queue"""

        if interaction.guild.id in self.guild_audio_players:
            self.guild_audio_players[interaction.guild.id].clear_queue()
            await interaction.response.send_message("Queue has been cleared.")
            return
        await interaction.response.send_message("There is no active voice client.")
    
    @app_commands.command(name="queueamount")
    async def command_get_queue_amount(self, interaction: discord.Interaction):
        """Returns the current amount in the queue"""

        if interaction.guild.id in self.guild_audio_players:
            amount = len(self.guild_audio_players[interaction.guild.id].queue) -1
            await interaction.response.send_message(f"Queue is {amount} long.")
            return
        await interaction.response.send_message("There is no active voice client.")

    @app_commands.command(name="pause")
    async def command_pause(self, interaction: discord.Interaction):
        """Pauses the current audio"""

        if interaction.guild.id in self.guild_audio_players:
            self.guild_audio_players[interaction.guild.id].pause()
            await interaction.response.send_message("Audio has been paused.")
            return
        await interaction.response.send_message("There is no active voice client.")

    @app_commands.command(name="unpause")
    async def command_unpause(self, interaction: discord.Interaction):
        """Unpauses the current audio"""

        if interaction.guild.id in self.guild_audio_players:
            self.guild_audio_players[interaction.guild.id].unpause()
            await interaction.response.send_message("Audio has been unpaused.")
            return
        await interaction.response.send_message("There is no active voice client.")

    @app_commands.command(name="shufflequeue")
    async def command_shuffle_queue(self, interaction: discord.Interaction):
        """Shuffle the current queue"""

        if interaction.guild.id in self.guild_audio_players:
            self.guild_audio_players[interaction.guild.id].shuffle_queue()
            await interaction.response.send_message("Queue has been shuffled.")
            return
        await interaction.response.send_message("There is no active voice client.")
            
    @app_commands.command(name="skip")
    async def command_skip(self, interaction: discord.Interaction):
        """Requests to skip the current audio."""

        if interaction.guild.id in self.guild_audio_players:
            await self.guild_audio_players[interaction.guild.id].request_skip(interaction=interaction)
        else:
            await interaction.response.send_message("There is no active voice client.")

    @app_commands.command(name="loopaudio")
    async def command_loop_audio(self, interaction: discord.Interaction, loop: bool):
        """Loop or unloop the current audio"""

        if interaction.guild.id in self.guild_audio_players:
            self.guild_audio_players[interaction.guild.id].loop_audio = loop
            await interaction.response.send_message(f"Loop audio changed: {loop}")
        else:
            await interaction.response.send_message("There is no active voice client.")
    
    @app_commands.command(name="loopqueue")
    async def command_loop_queue(self, interaction: discord.Interaction, loop: bool):
        """Loop or unloop the current queue"""

        if interaction.guild.id in self.guild_audio_players:
            self.guild_audio_players[interaction.guild.id].loop_queue = loop
            await interaction.response.send_message(f"Loop queue changed: {loop}")
        else:
            await interaction.response.send_message("There is no active voice client.")
    
    @app_commands.command(name="nowplaying")
    async def command_now_playing(self, interaction: discord.Interaction):
        """Get the currently playing audio"""

        if interaction.guild.id in self.guild_audio_players:
            await interaction.response.send_message(self.guild_audio_players[interaction.guild.id].get_now_playing_text())
            return
        await interaction.response.send_message("There is no active voice client")
    
    @app_commands.command(name="showqueue")
    async def command_show_queue(self, interaction: discord.Interaction):
        """Print all current items in the queue"""

        if interaction.guild.id in self.guild_audio_players:
            queue_string:str = "**QUEUE**"
            for i in range(0, len(self.guild_audio_players[interaction.guild.id].queue)):
                queue_string += f"\n{i}. {self.guild_audio_players[interaction.guild.id].queue[i].data.get('title')}"
            await interaction.response.send_message(queue_string)
            return
        await interaction.response.send_message("There is no active voice client")

        
    @app_commands.command(name="bump")
    async def command_bump(self, interaction: discord.Interaction):
        """Pause then unpause the audio to bump it incase it stops for any reason"""

        if interaction.guild.id in self.guild_audio_players:
            self.guild_audio_players[interaction.guild.id].pause()
            self.guild_audio_players[interaction.guild.id].unpause()
            await interaction.response.send_message("Bumped.")
            return
        await interaction.response.send_message("There is no active voice client.")

    @app_commands.command(name="removequeueitem")
    async def command_remove_queue_item(self, interaction: discord.Interaction, index:int):
        """Remove an item from the queue at a position. Use /showqueue command to get the position"""
        index = index-1
        if interaction.guild.id in self.guild_audio_players:
            if len(self.guild_audio_players[interaction.guild.id].queue)-1 >= index:
                title = self.guild_audio_players[interaction.guild.id].queue[index].data.get('title')
                self.guild_audio_players[interaction.guild.id].remove_queue_item(index)
                await interaction.response.send_message(f"Removed the item at position: {index+1}")
            else:
                await interaction.response.send_message("There is not that many items in the queue.")
            return
        await interaction.response.send_message("There is no active voice client.")
        
#endregion


#region Guild Music Player

from collections import deque
import time
import asyncio
import random

class GuildAudioPlayer():

    def __init__(self, music_cog:PygmyAudio, guild: discord.Guild):
        self.current_source: YTDLSource = None
        self.music_cog = music_cog
        self.bot = music_cog.bot
        self.guild = guild
        self.loop_audio = False
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
        amount_queued:int = 0

        if 'entries' in data:
            for data_dict in data['entries']:
                audio_instance: GuildAudioInstance = GuildAudioInstance(self, user, data_dict)
                self.queue.append(audio_instance)
                amount_queued += 1
        else:
            audio_instance: GuildAudioInstance = GuildAudioInstance(self, user, data)
            self.queue.append(audio_instance)
            amount_queued += 1
        
        return amount_queued
        
    async def add_to_front_of_queue(self, url:str, user: discord.User):
        data = await YTDLSource.extract_url_data(url=url,event_loop=self.bot.loop, download=False)
        amount_queued:int = 0

        if 'entries' in data:
            if self.is_playing:
                current_playing = self.queue.popleft()
            for data_dict in reversed(data['entries']):
                audio_instance: GuildAudioInstance = GuildAudioInstance(self, user, data_dict)
                self.queue.appendleft(audio_instance)
                amount_queued += 1
            if self.is_playing:
                self.queue.appendleft(current_playing)
        else:
            if self.is_playing:
                current_playing = self.queue.popleft()
            audio_instance: GuildAudioInstance = GuildAudioInstance(self, user, data)
            self.queue.appendleft(audio_instance)
            amount_queued += 1
            if self.is_playing:
                self.queue.appendleft(current_playing)
        
        return amount_queued

    def shutdown(self):
        self.clear_queue()
        self._stop()
    
    def clear_queue(self):
        audio_instance = self.queue.popleft()
        self.queue.clear()
        self.queue.append(audio_instance)
    
    def peek_current_audio(self):
        return self.queue[0]
    
    def peek_recently_added_audio(self):
        return self.queue[-1]
    
    def pause(self):
        self.guild.voice_client.pause()
    
    def remove_queue_item(self, index:int):
        if index == 0:
            self._skip_current()
            return
        
        self.queue.remove(self.queue[index])
    
    def unpause(self):
        if self.guild.voice_client.is_paused():
            self.guild.voice_client.resume()
    
    def shuffle_queue(self):
        if len(self.queue) <= 1:
            return
        
        audio_instance = self.queue.popleft()
        random.shuffle(self.queue)
        self.queue.appendleft(audio_instance)

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
        if self.loop_audio == True:
            if self.loop_queue == False:
                self._clear_current_source()
            else:
                self._requeue_current_source()

        self._stop()
    
    def _stop(self):  
        self.current_source = None
        if self.guild.voice_client.is_playing():
            self.guild.voice_client.stop()
    
    def _clear_current_source(self):
        if self.is_playing == False or len(self.queue) == 0:
            return
        
        audio_instance = self.queue.popleft()
        del audio_instance
        self.is_playing = False
    
    def _requeue_current_source(self):
        if self.is_playing == False or len(self.queue) == 0:
            return
        
        audio_instance = self.queue.popleft()
        self.queue.append(audio_instance)
        
    def _current_source_finished(self, e):
        if not self.guild.voice_client:
            return

        print(f"Current audio has finished. {e if e else ''}")

        if len(self.guild.voice_client.channel.members) <= 1:
            print("audio finished and no one is in the voice channel, evacuating.")
            asyncio.run_coroutine_threadsafe(self.music_cog.disconnect_voice_client(self.guild), self.bot.loop)

        if self.loop_audio == False and self.loop_queue == False:
            self._clear_current_source()
        elif self.loop_audio == False and self.loop_queue == True:
            self._requeue_current_source()

        self.is_playing = False

        print("trying to play next")
        self._try_play_next()
        if self.is_playing == False:
            print("self.isplaying is false, disconnecting")
            asyncio.run_coroutine_threadsafe(self.music_cog.disconnect_voice_client(self.guild), self.bot.loop)

    #region Guild Settings Updates

    def on_guild_settings_changed(self, guild_id:int, settings_id:str, settings_value:object):
        self._on_skip_amount_needed_changed(guild_id, settings_id, settings_value)

    def _on_skip_amount_needed_changed(self, guild_id:int, settings_id:str, settings_value:object):
        if settings_id != PygmyAudio.SETTINGS_ID_SKIP_AMOUNT:
            return
        
        if len(self.users_requesting_skips) >= settings_value:
            self._skip_current()
            return

    #endregion

#endregion

class GuildAudioInstance():
    def __init__(self, guild_audio_player: GuildAudioPlayer, requested_user:discord.User, data: dict):
        self.guild_audio_player = guild_audio_player
        self.requested_user = requested_user
        self.data = data
