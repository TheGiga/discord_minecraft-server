import asyncio
import threading
from typing import Any

import aiohttp
import discord
import docker.models.containers
from tortoise.models import Model
from tortoise.fields import TextField, IntField, JSONField, CharField

import config
import src
from config import DEFAULT_PRESET_CONFIG
from ..versions import Versions


class Preset(Model):
    id = IntField(pk=True)
    name = CharField(unique=True, max_length=20)

    version = TextField()
    server_type = TextField(default="VANILLA")
    port = IntField(default=25565)

    memory = IntField(default=1280)

    properties = JSONField(default=DEFAULT_PRESET_CONFIG)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    @property
    def running(self) -> bool:
        try:
            return getattr(self, '_running')
        except AttributeError:
            setattr(self, '_running', False)
            return self.running

    @running.setter
    def running(self, x: bool):
        setattr(self, '_running', x)

    @property
    def container(self) -> docker.models.containers.Container:
        try:
            return getattr(self, '_container')
        except AttributeError:
            setattr(self, '_container', None)
            return self.container

    @container.setter
    def container(self, x):
        setattr(self, '_container', x)

    @property
    def webhook(self) -> discord.Webhook:
        try:
            return getattr(self, '_webhook')
        except AttributeError:
            setattr(self, '_webhook', None)
            return self.webhook

    @webhook.setter
    def webhook(self, x):
        setattr(self, '_webhook', x)

    def __repr__(self):
        return f'Preset({self.name=}, {self.version=})'

    async def shutdown_logic(self, wait: float = 15.0):
        await asyncio.sleep(wait)
        try:
            if self.container:
                self.container.stop()
            src.docker_client.containers.prune()
            src.docker_client.volumes.prune()
        finally:
            self.container = None
            self.running = False

            if self.webhook:
                await self.webhook.delete()

            self.webhook = None

    async def run_server(self, logging: bool = False, logging_channel: discord.TextChannel = None):
        if self.running:
            raise src.AlreadyRunning()

        preset = self

        version = preset.version
        java_version = Versions.get_by_version(version).value.flag.java_version

        if java_version is None:
            raise Exception("This version is not declared in the versions enum! Please fix.")

        java_memory = round(preset.memory * 0.75)

        env = [
            "EULA=true",
            f"VERSION={version}",
            f'MEMORY={java_memory}M',
            f'TYPE={preset.server_type}'
        ]

        for var in preset.properties:
            if var == "MOTD":
                env.append(f'{var}="{preset.properties[var]}"')
                continue

            env.append(f'{var}={preset.properties[var]}')

        container = src.docker_client.containers.run(
            image=f'itzg/minecraft-server:{java_version}',
            name=preset.name,
            environment=env,
            ports={f'{preset.port}/tcp': (config.IP, str(preset.port))},
            volumes=[f"{config.DOCKER_VOLUME_PATH}/{preset.name}:/data"],
            mem_limit=f'{preset.memory}m',
            detach=True
        )

        self.running = True
        self.container = container

        if logging:
            webhook = await logging_channel.create_webhook(name=f'{self.name} Logs')

            self.webhook = webhook

            await self.start_logging()

    async def start_logging(self):
        async def logger():
            logs = self.container.logs(stream=True)

            for log in logs:
                if not self.running:
                    break

                log = log.decode('utf-8').rstrip('\n')
                print(log)

                async with aiohttp.ClientSession() as session:
                    await session.post(
                        url=self.webhook.url,
                        data={"content": f'```md\n{log}```'}
                    )

        def starter():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)

            new_loop.run_until_complete(logger())

        thread1 = threading.Thread(target=starter, daemon=True)
        thread1.start()
