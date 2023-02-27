from .bot import bot_instance, SubclassedBot
from .embed import DefaultEmbed
from .versions import Versions
import docker

docker_client = docker.from_env()
