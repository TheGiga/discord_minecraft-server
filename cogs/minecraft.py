import asyncio
import datetime
import os
import uuid
from shutil import make_archive

import discord
from discord.ext.commands import cooldown, BucketType

from src import docker_client, SubclassedBot

versions = {'1.19.3', '1.16.5', '1.12.2', '1.8.9', '1.7.10'}
types = {'VANILLA', 'SPIGOT', 'PAPER'}


class Minecraft(discord.Cog):
    def __init__(self, bot):
        self.bot: SubclassedBot = bot
        self.running = False
        self.container = None
        self.console_channel = None

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id != self.console_channel:
            return

        if not message.content.startswith("$") or message.author.id not in self.bot.config.WHITELIST:
            return

        cmd = message.content.strip("$ ")
        print(f'$ {cmd} - {message.author} [{message.author.id}]')
        response = self.container.exec_run(['mc-send-to-console', f'{cmd}'])

        pretty_response = response.output.decode("utf-8")
        await message.reply(f'Response: `{pretty_response if len(pretty_response) > 0 else "✅"}`')

        if cmd == "stop":
            await asyncio.sleep(10)
            self.container.stop()
            docker_client.containers.prune()
            docker_client.volumes.prune()

            self.running = False
            self.container = None
            self.console_channel = None

    @cooldown(1, 60, BucketType.user)
    @discord.slash_command(name='extract_world')
    async def extract_world(
            self, ctx: discord.ApplicationContext,
            version: discord.Option(str, choices=versions),
    ):
        if self.running:
            return await ctx.respond('❌ Server is already running, cannot extract world(s), stop it.', ephemeral=True)

        await ctx.respond('Working on it...')

        directory = f'{uuid.uuid4()}'

        for world in ['world', 'world_nether', 'world_the_end']:
            start_path = f"{os.getenv('HOME')}/Docker/Minecraft/{version}/{world}"
            end_path = f'{self.bot.config.HTTP_SERVER_PATH}/{directory}/{world}'

            if not os.path.exists(start_path):
                await ctx.channel.send(f"❌ There is no `{world}` on this version.")
                continue

            make_archive(end_path, 'zip', start_path)

        await ctx.send_followup(f'**Result:** http://{os.getenv("IP")}:6969/{directory}/')

    @discord.slash_command(name='start')
    async def start_server(
            self, ctx: discord.ApplicationContext,
            version: discord.Option(str, choices=versions),
            server_type: discord.Option(str, name='type', choices=types),
            regenerate: discord.Option(bool, default=False) = False

    ):
        if self.running:
            return await ctx.respond('❌ Already running!', ephemeral=True)

        await ctx.defer()

        if regenerate:
            docker_client.volumes.prune()
            print(os.system(f"rm -rf /{os.getenv('HOME')}/Docker/Minecraft/{version}/"))

        container = docker_client.containers.run(
            image='itzg/minecraft-server',
            name=version,
            environment=[
                "EULA=TRUE",
                f"VERSION={version}",
                f"TYPE={server_type}"
            ],
            ports={'25565/tcp': (f'{os.getenv("IP")}', '25565')},
            volumes=[f"{os.getenv('HOME')}/Docker/Minecraft/{version}:/data"],
            detach=True
        )
        self.running = True
        self.container = container
        self.console_channel = ctx.channel.id

        last_check = None

        initial_response = await ctx.respond('✅ **Running...**')

        while self.running:
            logs = container.logs(since=last_check).decode('utf-8')
            last_check = datetime.datetime.utcnow()

            if len(logs) > 0:
                print(logs)
                try:
                    await initial_response.channel.send(f'```bash\n{logs}```')
                except discord.HTTPException:
                    await initial_response.channel.send(f'``` * Some weird ass long log. *```')

            await asyncio.sleep(1.5)


def setup(bot):
    bot.add_cog(Minecraft(bot))
