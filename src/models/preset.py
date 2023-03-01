import discord
from tortoise.models import Model
from tortoise.fields import TextField, IntField, JSONField, CharField
from config import DEFAULT_PRESET_CONFIG


class Preset(Model):
    id = IntField(pk=True)
    name = CharField(unique=True, max_length=20)

    version = TextField()
    server_type = TextField(default="VANILLA")
    port = IntField(default=25565)

    memory = IntField(default=1280)

    properties = JSONField(default=DEFAULT_PRESET_CONFIG)

    def __repr__(self):
        return f'Preset({self.name=}, {self.version=})'

    async def run_server(self, logging_channel: discord.TextChannel, container_name: str = None):
        raise NotImplementedError




