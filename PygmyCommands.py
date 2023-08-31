from discord import app_commands, Client
import discord
import random
from discord.ext import commands

class PygmyCommands(app_commands.Group, name="pygmybot"):
    def __init__(self, tree: app_commands.CommandTree, client: Client)-> None:
        super().__init__()
        self.tree = tree
        self.client = client
    
    #region Generic Commands

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

    #region Voice Commands
    @app_commands.command(name="connect")
    async def join_voice_chat(self, interaction: discord.Interaction, *, channel: discord.VoiceChannel):
        #Joins a voice channel

        await interaction.response.send_message("Attempting to join the voice channel: " + channel.name, ephemeral=True)

        guild = interaction.guild

        if guild.voice_client is not None:
            await guild.voice_client.move_to(channel)
            await guild.change_voice_state(channel=channel,self_deaf=True)
            return

        await channel.connect(self_deaf=True)

    @app_commands.command(name="disconnect", description="Bot will leave any voice chat it is currently in.")
    async def disconnect_voice_chat(self, interaction: discord.Interaction):
        
        if (interaction.guild.voice_client is not None):
            await interaction.response.send_message("Leaving voice channel.", ephemeral=True)
            await interaction.guild.voice_client.disconnect()
            await interaction.guild.voice_client.cleanup()
        else:
            await interaction.response.send_message("The bot is not in any voice channel.", ephemeral=True)

    #endregion