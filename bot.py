import traceback
import logging
import asyncio
import sys
import discord
from discord.ext import commands
from database_handler import DatabaseHandler
from config_handler import ConfigHandler
from helpers import logger_handlers

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(logger_handlers.get_console_handler())
root_logger.addHandler(logger_handlers.get_file_handler())

config_handler = ConfigHandler()
database_handler = asyncio.get_event_loop().run_until_complete(DatabaseHandler.create())

startup_extensions = ["licenses",
                      "database_debug",
                      "bot_owner_commands",
                      "guild_admin",
                      "bot_information",
                      "cmd_errors"]


async def prefix_callable(bot_client, message):
    try: 
        # TODO: Store this in list or smth so we don't waste calls to db for each message
        return await bot_client.main_db.get_guild_prefix(message.guild.id)
    except Exception as err:
        """
        If fetching prefix from database errors just use the default prefix.
        This is also used in DMs where the guild is None
        """
        default_prefix = config_handler.get_default_prefix()
        root_logger.error(f"Can't get guild {message.guild} prefix. Error:{err}. "
                          f"Using '{default_prefix}' as prefix.")
        return default_prefix


bot = commands.Bot(command_prefix=prefix_callable, description=config_handler.get_description())
bot.config = config_handler
bot.main_db = database_handler

if __name__ == "__main__":
    root_logger.info("Loaded extensions:")
    for extension in startup_extensions:
        cog_path = f"cogs.{extension}"
        try:
            bot.load_extension(cog_path)
            root_logger.info(f"{cog_path}")
        except Exception as e:
            exc = f"{type(e).__name__}: {e}"
            root_logger.error(f"{exc} Failed to load extension {cog_path}")
            root_logger.error(traceback.format_exc())


@bot.event
async def on_connect():
    root_logger.info("Connection to Discord established")


@bot.event
async def on_guild_remove(guild):
    root_logger.info(f"Left guild {guild.name}")


@bot.event
async def on_disconnect():
    root_logger.warning("Connection lost")


@bot.event
async def on_ready():
    root_logger.info(f"Logged in as: {bot.user.name} - {bot.user.id}"
                     f"\tDiscordPy version: {discord.__version__}")
    root_logger.info("Successfully logged in and booted...!")


@bot.event
async def on_error(event: str, *args, **kwargs):
    """
    Called when an EVENT raises an uncaught exception

    This doesn't use the same event system as the rest of events despite being documented as such
    Can only have one and it's gotta be in main file.
    """
    exc_info = sys.exc_info()
    exc_type = exc_info[0].__name__ if exc_info[0] is not None else "<no exception>"
    exc_what = str(exc_info[1]) if exc_info[1] is not None else ""
    root_logger.critical(f"Uncaught {exc_type} in '{event}': {exc_what}")
    root_logger.critical(traceback.format_exc())


bot.run(bot.config.get_token())
