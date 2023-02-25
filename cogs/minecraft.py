import asyncio
import datetime
import os
import platform
import shutil
import uuid
from shutil import make_archive

import aiofiles
import aiohttp
import discord
from discord.ext.commands import cooldown, BucketType

from src import docker_client, SubclassedBot, utils

versions = {'1.19.3', '1.19.2', '1.18.2', '1.17.1', '1.16.5', '1.15.2', '1.14.4', '1.13.2', '1.12.2', '1.8.9', '1.7.10'}
types = {'VANILLA', 'SPIGOT', 'PAPER'}
dimensions = {'world', 'world_nether', 'world_the_end'}


class Minecraft(discord.Cog):
    def __init__(self, bot):
        self.bot: SubclassedBot = bot
        self.running = False
        self.container = None
        self.console_channel = None

    async def shutdown_logic(self):
        await asyncio.sleep(10)
        self.container.stop()
        docker_client.containers.prune()
        docker_client.volumes.prune()

        self.container = None
        self.console_channel = None
        self.running = False

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        config = self.bot.config

        if message.channel.id != self.console_channel:
            return

        if not message.content.startswith(config.CONSOLE_PREFIX) or message.author.id not in config.WHITELIST:
            return

        cmd = message.content[len(config.CONSOLE_PREFIX):].strip()
        cmd = cmd.replace('"', '\\"')
        cmd = cmd.replace("'", "\\'")

        print(f'$ {cmd} - {message.author} [{message.author.id}]')
        response = self.container.exec_run(["mc-send-to-console", f"{cmd}"]) # echo "{cmd}" > /tmp/minecraft-console-in

        print(response)

        pretty_response = response.output.decode("utf-8")
        await message.reply(f'Response: `{pretty_response if len(pretty_response) > 0 else "✅"}`')

        if cmd == "stop":
            await self.shutdown_logic()

    @cooldown(1, 60, BucketType.user)
    @discord.slash_command(name='extract_world')
    async def extract_world(
            self, ctx: discord.ApplicationContext,
            version: discord.Option(str, choices=versions),
    ):
        config = self.bot.config

        if self.running:
            return await ctx.respond("❌ Couldn't extract world(s), server is running.", ephemeral=True)

        await ctx.respond('Working on it...')

        directory = f'{uuid.uuid4()}'

        for world in dimensions:
            start_path = f"{config.DOCKER_VOLUME_PATH}/{version}/{world}"
            end_path = f'{config.HTTP_SERVER_PATH}/{directory}/{world}'

            if not os.path.exists(start_path):
                await ctx.channel.send(f"❌ There is no `{world}` on this version.")
                continue

            make_archive(end_path, 'zip', start_path)

        await ctx.send_followup(f'**Result:** http://{os.getenv("IP")}:6969/{directory}/')

    # TODO: Should be refactored.
    @cooldown(1, 60, BucketType.default)
    @discord.slash_command(name='upload_world')
    async def upload_world(
            self, ctx: discord.ApplicationContext,
            url: discord.Option(str),
            version: discord.Option(str, choices=versions),
    ):
        config = self.bot.config

        if self.running:
            return await ctx.respond("❌ Couldn't upload world, server is running.", ephemeral=True)

        archive_types: list = [".zip", ".bz2", ".gz"]
        archive_type_index: int = -1

        for archive_type in archive_types:
            if url.endswith(archive_type):
                archive_type_index = archive_types.index(archive_type)
                break

        if archive_type_index == -1:
            return await ctx.respond(
                f'❌ Unsupported archive type. Supported archive types: {", ".join(archive_types)}',
                ephemeral=True
            )

        await ctx.defer()
        archive_name = f'{uuid.uuid4()}{archive_types[archive_type_index]}'
        archive_path = f'{utils.ensure_directory_exists(f"{os.getcwd()}/temp")}/{archive_name}'.replace("\\", "/")

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return await ctx.respond(
                        f'❌ Got {response.status}, make sure you provide a valid url.', ephemeral=True
                    )

                message_response = await ctx.send_followup("🚀 Downloading file")
                async with aiofiles.open(archive_path, 'wb') as file:
                    await file.write(await response.read())
                    await file.close()
                    await message_response.edit(content="ℹ Download complete, unpacking...")

        temp_dir = f'{config.DOCKER_VOLUME_PATH}/{version}/Temp'.replace("\\", "/")
        temp_dir = utils.ensure_directory_exists(temp_dir)

        shutil.unpack_archive(archive_path, temp_dir)
        is_world_in_archive = os.path.exists(f'{temp_dir}/world')
        is_world_nether_in_archive = os.path.exists(f'{temp_dir}/world_nether')
        is_world_the_end_in_archive = os.path.exists(f'{temp_dir}/world_the_end')

        def delete_and_move(world_name):
            world_path = f'{config.DOCKER_VOLUME_PATH}/{version}/{world_name}'
            if os.path.exists(world_path):
                shutil.rmtree(world_path)
            shutil.move(f'{temp_dir}/{world_name}', world_path)
            if platform.system() == "Linux":
                os.system(f"chown -R 1000:1000 {world_path}")

        worlds_uploaded = 0

        if is_world_in_archive:
            delete_and_move("world")
            worlds_uploaded += 1

        if is_world_nether_in_archive:
            delete_and_move("world_nether")
            worlds_uploaded += 1

        if is_world_the_end_in_archive:
            delete_and_move("world_the_end")
            worlds_uploaded += 1

        await message_response.edit(content=f"✅ Unpacking complete! World(s) uploaded: `{worlds_uploaded}`")

        shutil.rmtree(temp_dir)
        os.remove(archive_path)

    @discord.slash_command(name='force-stop', description='Data can be lost!')
    async def force_stop(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        await self.shutdown_logic()
        await ctx.respond("✅ Force-stopped the server.")

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
            print(os.system(f"rm -rf {self.bot.config.DOCKER_VOLUME_PATH}/{version}/"))

        container = docker_client.containers.run(
            image='itzg/minecraft-server',
            name=version,
            environment=[
                "EULA=TRUE",
                f"VERSION={version}",
                f"TYPE={server_type}"
            ],
            ports={'25565/tcp': (f'{os.getenv("IP")}', '25565')},
            volumes=[f"{self.bot.config.DOCKER_VOLUME_PATH}/{version}:/data"],
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
