import os
from platform import system

COGS = ['basic', 'minecraft']
WHITELIST: list[int] = [352062534469156864, 330731335394000900, 373831081838772224]
CONSOLE_PREFIX = "$"
VERSIONS = {'1.19.3', '1.19.2', '1.18.2', '1.17.1', '1.16.5', '1.15.2', '1.14.4', '1.13.2', '1.12.2', '1.8.9', '1.7.10'}
SERVER_TYPES = {'VANILLA', 'SPIGOT', 'PAPER'}
DIMENSIONS = {'world', 'world_nether', 'world_the_end'}


if system() == "Windows":
    HOME_PATH = os.getenv("UserProfile")
else:
    HOME_PATH = os.getenv("HOME")

HTTP_SERVER_PATH: str = f'{HOME_PATH}/Public'.replace("\\", "/")
DOCKER_VOLUME_PATH: str = f'{HOME_PATH}/Docker/Minecraft'.replace("\\", "/")

ESCAPED_CHARACTERS: dict = {
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
