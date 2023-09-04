import discord
from discord.ext import commands
from PygmyCommands import PygmyCommands
from PygmyAudio import PygmyAudio
from EventManager import EventManager
from Config import Config

#A discord bot implementing discord.Client
#Commands are implemented through commands.cogs


##TODO:
#1. add a reference to channel in PygmyBot.py that references the last channel someone has sent a command to and name it bot.command_channel, and use that to send any messages to if not directly responding to an interaction.


class PygmyBot(commands.Bot):
    #region PygmyBot Events

    EVENT_NAME_GUILD_SETTINGS_CHANGED = "guild_settings_changed"

    #endregion
   
    def start_bot(self):
        self.run(Config.CONFIG["Discord"]["Token"])


    def __init__(self, command_prefix):
        intents = discord.Intents.all()
        intents.message_content = True
        self.command_prefix = command_prefix
        self.guild_settings = dict[int, dict[str, object]]()
        self.event_manager = EventManager()
        super().__init__(intents=intents, command_prefix=command_prefix)

    
    async def on_ready(self):
        await self.register_commands()
        print("PygmyBot is set up!")


    async def register_commands(self):
        print("Registering commands!")
        await self.register_cogs()
        await self.tree.sync()
        print("Commands Registered!")

        
    async def register_cogs(self):
        #await self.add_cog(PygmyCommands(self))
        await self.add_cog(PygmyAudio(self))
    
    @EventManager.trigger_event(name=EVENT_NAME_GUILD_SETTINGS_CHANGED)
    def set_guild_setting(self, guild_id:int, settings_id:str, settings_value:object):
        if guild_id not in self.guild_settings:
            self.guild_settings[guild_id] = dict[str,object]()
        
        self.guild_settings[guild_id][settings_id] = settings_value
        print (self.guild_settings[guild_id])
