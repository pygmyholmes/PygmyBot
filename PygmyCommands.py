from discord import app_commands, Client
import discord
import random
from discord.ext import commands 

class PygmyCommands(commands.GroupCog, name="pygcommands"):
    def __init__(self, bot: commands.Bot)-> None:
        self.bot = bot
        super().__init__()

    
    #region Generic Commands
    @app_commands.command(name="set_command_prefix")
    async def set_command_prefix(self, interaction: discord.Interaction, new_prefix:str):
        self.bot.command_prefix = new_prefix
        await interaction.channel.send("command prefix has been changed to '"+new_prefix+"'")

    @app_commands.command(name="guess_the_roll")
    @app_commands.choices(rolls=[
        discord.app_commands.Choice(name='1', value=1),
        discord.app_commands.Choice(name='2', value=2),
        discord.app_commands.Choice(name='3', value=3),
        discord.app_commands.Choice(name='4', value=4),
        discord.app_commands.Choice(name='5', value=5),
        discord.app_commands.Choice(name='6', value=6),
    ])
    async def guess_the_roll(self, interaction: discord.Interaction, rolls: discord.app_commands.Choice[int]):
        ranInt = random.randrange(1, 7)
        if ranInt == rolls.value:
            await interaction.response.send_message(f"Rolled {ranInt}, and you guessed correctly!")
        else:
            await interaction.response.send_message(f"Rolled {ranInt}, and you guessed incorrectly!")
    
    @app_commands.command(name="say_hello")
    @app_commands.choices(choice=[
        discord.app_commands.Choice(name='Private response', value=1),
        discord.app_commands.Choice(name='Public response', value=2),
        discord.app_commands.Choice(name='DM response', value=3),
    ])
    async def say_hello(self, interaction: discord.Interaction, choice: discord.app_commands.Choice[int]):
        match choice.value:
            case 1:
                await interaction.response.send_message("Hello!", ephemeral=True)
            case 2:
                channel = interaction.channel
                await interaction.response.send_message("Publicly saying Hello!", ephemeral=True)
                await channel.send("Hello!")
            case 3:
                channel = await interaction.user.create_dm()
                await channel.send("Hello!")
                await interaction.response.send_message("I sent a dm saying hello!")

    #endregion