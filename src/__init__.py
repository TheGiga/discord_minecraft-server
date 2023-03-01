from .bot import bot_instance, SubclassedBot
from .embed import DefaultEmbed, PresetEmbed
from .versions import Versions
from .utils import async_wrap_iter, ensure_directory_exists
from .database import db_init
import docker

docker_client = docker.from_env()
