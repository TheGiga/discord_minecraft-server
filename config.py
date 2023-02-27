import os
from platform import system
from src import Versions

# You can read more about some of these settings on https://github.com/itzg/docker-minecraft-server

CONSOLE_PREFIX = "$"  # Use this prefix + minecraft command in the channel where you started server
# to send commands to server console
IP = "127.0.0.1"  # Change this to your global ip, if you want to make server accessible to everyone
PORT = "25565"  # The port of the server

# Users from this list will be able to use bot commands and send minecraft server commands to console.
WHITELIST: list[int] = [352062534469156864, 330731335394000900, 373831081838772224]

if system() == "Windows":
    HOME_PATH = os.getenv("UserProfile")
else:
    HOME_PATH = os.getenv("HOME")

VERSIONS = Versions
COGS = ['basic', 'minecraft']
SERVER_TYPES = ['VANILLA', 'SPIGOT', 'PAPER']
DIMENSIONS = ['world', 'world_nether', 'world_the_end']

# The path to your HTTP server directory, worlds from "/extract world" will end-up there
HTTP_SERVER_PATH: str = f'{HOME_PATH}/Public'.replace("\\", "/")
# IP and PORT to your HTTP server, used just to access it, not set it up.
HTTP_SERVER_IP: str = IP
HTTP_SERVER_PORT: str = '6969'

# Path to the directory where you would like to store server files.
DOCKER_VOLUME_PATH: str = f'{HOME_PATH}/Docker/Minecraft'.replace("\\", "/")

ESCAPED_CHARACTERS: dict = {  # Used to prevent people from escaping from minecraft console to bash.
    "-": r"\-",
    "]": r"\]",
    "\\": r"\\",
    "^": r"\^",
    "$": r"\$",
    "*": r"\*",
    ".": r"\.",
    "<": r"\<",
    ">": r"\>",
    "|": r"\|",
    "(": r"\(",
    ")": r"\)",
    "'": r"\'",
    "\"": r"\"",
}
