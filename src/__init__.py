from .bot import bot_instance, SubclassedBot
from .embed import DefaultEmbed
from .versions import Versions
from .utils import async_wrap_iter, ensure_directory_exists
import docker

docker_client = docker.from_env()
