from PygmyBot import PygmyBot
from Config import Config

client = PygmyBot(command_prefix=Config.CONFIG["Discord"]["Command_Prefix"])
client.start_bot()
