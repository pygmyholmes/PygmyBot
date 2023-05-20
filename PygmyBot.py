import discord
from discord import app_commands
from PygmyCommands import PygmyCommands
from Config import Config

#A discord bot implementing discord.Client
#Commands are implemented through app_commands.Group's

class PygmyBot(discord.Client):
    def StartBot(self):
        self.run(Config.CONFIG["Discord"]["Token"])

    def __init__(self):
        intents = discord.Intents.all()
        intents.message_content = True
        super().__init__(intents=intents)

    async def on_ready(self):
        print("PygmyBot is ready!")
        await self.RegisterCommands()
    
    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')

    async def on_guild_join(self, guild: discord.Guild):
        #guild.create_text_channel() TODO: make a text channel for pygmybot as a test.
        #sync command tree here?
        pass

    async def RegisterCommands(self):
        print("Registering commands!")

        self.tree = app_commands.CommandTree(self)
        self.tree.add_command(PygmyCommands(self.tree, self))

        commands = await self.tree.sync()

        print(f"Commands registered!: \n {commands}")
