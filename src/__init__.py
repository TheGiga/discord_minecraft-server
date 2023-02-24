from .bot import bot_instance, SubclassedBot
from .embed import DefaultEmbed
import docker

docker_client = docker.from_env()
