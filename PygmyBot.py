import discord
from discord.ext import commands
from PygmyCommands import PygmyCommands
from PygmyAudio import PygmyAudio, GuildAudioPlayer
from EventManager import EventManager
from Config import Config

#A discord bot implementing discord.Client
#Commands are implemented through commands.cogs


##TODO:
#1. add a reference to channel in PygmyBot.py that references the last channel someone has sent a command to and name it bot.command_channel, and use that to send any messages to if not directly responding to an interaction.


class PygmyBot(commands.Bot):
    #region PygmyBot Events

    EVENT_NAME_GUILD_SETTINGS_CHANGED = "guild_settings_changed"
    EVENT_NAME_GUILD_SETTINGS_CREATED = "guild_settings_setup"

    #endregion
   
    def start_bot(self):
        self.run(Config.CONFIG["Discord"]["Token"])

    def __init__(self, command_prefix):
        intents = discord.Intents.all()
        intents.message_content = True
        self.command_prefix = command_prefix
        self.event_manager = EventManager()
        super().__init__(intents=intents, command_prefix=command_prefix)
 
    async def on_ready(self):
        await self.register_cogs()
        self.initialise_guild_settings()
        await self.register_commands()
        print("PygmyBot is set up!")

    async def on_guild_join(self, guild: discord.Guild):
        self.create_guild_settings(guild.id)

    async def register_commands(self):
        await self.tree.sync()
        print("Commands Registered!")

        
    async def register_cogs(self):
        print("Registering cogs!")
        #await self.add_cog(PygmyCommands(self))
        await self.add_cog(PygmyAudio(self))
    
    def initialise_guild_settings(self):
        self.guild_settings = dict[int, dict[str, object]]()
        for guild in self.guilds:
            self.create_guild_settings(guild)

    def create_guild_settings(self, guild: discord.Guild):
            if guild.id not in self.guild_settings:
                self.guild_settings[guild.id] = dict[str,object]()
                self.setup_guilds_settings(self.guild_settings[guild.id])
    
    @EventManager.trigger_event(name=EVENT_NAME_GUILD_SETTINGS_CREATED)
    def setup_guilds_settings(self, guild_setting_dict: dict[str, object]):
        #if there are any other guild settings, initialise them here with default values.
        #any cog can listen to the event to add their own settings values if needed.
        return
    
    @EventManager.trigger_event(name=EVENT_NAME_GUILD_SETTINGS_CHANGED)
    def set_guild_setting(self, guild_id:int, settings_id:str, settings_value:object):
        if guild_id not in self.guild_settings:
            self.guild_settings[guild_id] = dict[str,object]()
        
        self.guild_settings[guild_id][settings_id] = settings_value
        print (self.guild_settings[guild_id])
