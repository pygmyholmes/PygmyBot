import discord
from discord.ext import commands
from discord import app_commands
from PygmyCommands import PygmyCommands
from Config import Config

#A discord bot implementing discord.Client
#Commands are implemented through app_commands.Group's

class PygmyBot(commands.Bot):
    def StartBot(self):
        self.run(Config.CONFIG["Discord"]["Token"])

    def __init__(self, command_prefix):
        intents = discord.Intents.all()
        intents.message_content = True
        self.command_prefix = command_prefix
        super().__init__(intents=intents, command_prefix=command_prefix)

    async def on_ready(self):
        print("PygmyBot is ready!")
        await self.RegisterCommands()
    
    #async def on_message(self, message):
    #    print(f'Message from {message.author}: {message.content}')
    #    await self.process_commands(message)

    async def on_guild_join(self, guild: discord.Guild):
        #guild.create_text_channel() TODO: make a text channel for pygmybot as a test.
        #sync command tree here?
        pass

    @commands.command()
    @commands.guild_only()
    async def sync(self, ctx):
        print("Sync called")
        await ctx.channel.send("Syncing Commands")
        await self.bot.tree.sync()

    async def RegisterCommands(self):
        print("Registering commands!")
        await self.add_cog(PygmyCommands(self))
        await self.tree.sync()
        
        print("Commands Registered!")
