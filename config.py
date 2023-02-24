import os
from platform import system

COGS = ['basic', 'minecraft']
WHITELIST: list[int] = [352062534469156864, 330731335394000900, 373831081838772224]
HTTP_SERVER_PATH: str = f'{os.getenv("HOME")}/Public'.replace("\\", "/")
DOCKER_VOLUME_PATH: str = f'{os.getenv("HOME")}/Docker/Minecraft'.replace("\\", "/")
