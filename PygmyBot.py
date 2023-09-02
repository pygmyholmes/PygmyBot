import discord
from discord.ext import commands
from discord import app_commands
from PygmyCommands import PygmyCommands
from PygmyMusic import PygmyMusic
from Config import Config

#A discord bot implementing discord.Client
#Commands are implemented through commands.cogs

class PygmyBot(commands.Bot):
    def start_bot(self):
        self.run(Config.CONFIG["Discord"]["Token"])

    def __init__(self, command_prefix):
        intents = discord.Intents.all()
        intents.message_content = True
        self.command_prefix = command_prefix
        super().__init__(intents=intents, command_prefix=command_prefix)

    async def on_ready(self):
        print("PygmyBot is ready!")
        await self.register_commands()

    async def register_cogs(self):
        await self.add_cog(PygmyCommands(self))
        await self.add_cog(PygmyMusic(self))
    
    async def register_commands(self):
        print("Registering commands!")
        #await self.add_cog(PygmyCommands(self))
        #await self.add_cog(PygmyMusic(self))
        await self.register_cogs()
        await self.tree.sync()
        
        print("Commands Registered!")
