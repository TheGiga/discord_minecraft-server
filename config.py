import os
from platform import system

COGS = ['basic', 'minecraft']
WHITELIST: list[int] = [352062534469156864, 330731335394000900, 373831081838772224]
CONSOLE_PREFIX = "$"

if system() == "Windows":
    HOME_PATH = os.getenv("UserProfile")
else:
    HOME_PATH = os.getenv("HOME")

HTTP_SERVER_PATH: str = f'{HOME_PATH}/Public'.replace("\\", "/")
DOCKER_VOLUME_PATH: str = f'{HOME_PATH}/Docker/Minecraft'.replace("\\", "/")
