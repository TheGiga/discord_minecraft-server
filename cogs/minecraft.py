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
from discord import SlashCommandGroup
from discord.ext.commands import cooldown, BucketType

import config
from src import docker_client, SubclassedBot, utils, Versions

versions = [
    discord.OptionChoice(x.value.name, x.name)
    for x in config.VERSIONS
]


class Minecraft(discord.Cog):
    def __init__(self, bot):
        self.bot: SubclassedBot = bot
        self.running = False
        self.container = None
        self.console_channel = None

    world = SlashCommandGroup(name='world', description="Commands to work with server world(s)")

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
        if message.channel.id != self.console_channel:
            return

        if not message.content.startswith(config.CONSOLE_PREFIX) or message.author.id not in config.WHITELIST:
            return

        cmd = message.content.removeprefix(config.CONSOLE_PREFIX).strip()
        cmd = cmd.translate(cmd.maketrans(config.ESCAPED_CHARACTERS))

        print(f'{config.CONSOLE_PREFIX} {cmd} - {message.author} [{message.author.id}]')
        response = self.container.exec_run(["mc-send-to-console", f"{cmd}"])

        pretty_response = response.output.decode("utf-8")
        await message.reply(f'Response: `{pretty_response if len(pretty_response) > 0 else "✅"}`')

        if cmd == "stop":
            await self.shutdown_logic()

    @cooldown(1, 60, BucketType.user)
    @world.command(name='download', description='Download server world(s).')
    async def download_world(
            self, ctx: discord.ApplicationContext,
            version_enum_name: discord.Option(str, name='version', choices=versions),
    ):
        if self.running:
            return await ctx.respond("❌ Couldn't download world(s), server is running.", ephemeral=True)

        await ctx.respond('Working on it...')

        version = Versions[version_enum_name].value.name

        directory = f'{uuid.uuid4()}'

        for world in config.DIMENSIONS:
            start_path = f"{config.DOCKER_VOLUME_PATH}/{version}/{world}"
            end_path = f'{config.HTTP_SERVER_PATH}/{directory}/{world}'

            if not os.path.exists(start_path):
                await ctx.channel.send(f"❌ There is no `{world}` on this version.")
                continue

            make_archive(end_path, 'zip', start_path)

        await ctx.send_followup(f'**Result:** http://{os.getenv("IP")}:6969/{directory}/')

    # TODO: Should be refactored.
    @cooldown(1, 60, BucketType.default)
    @world.command(name='upload', description='Upload world(s) to specific server version (it will replace old one!)')
    async def upload_world(
            self, ctx: discord.ApplicationContext,
            url: discord.Option(str),
            version_enum_name: discord.Option(str, name='version', choices=versions),
    ):
        if self.running:
            return await ctx.respond("❌ Couldn't upload world, server is running.", ephemeral=True)

        version = Versions[version_enum_name].value.name

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
        is_world_in_unpacked = os.path.exists(f'{temp_dir}/world')
        is_world_nether_unpacked = os.path.exists(f'{temp_dir}/world_nether')
        is_world_the_end_unpacked = os.path.exists(f'{temp_dir}/world_the_end')

        def delete_and_move(world_name):
            world_path = f'{config.DOCKER_VOLUME_PATH}/{version}/{world_name}'
            if os.path.exists(world_path):
                shutil.rmtree(world_path)
            shutil.move(f'{temp_dir}/{world_name}', world_path)
            if platform.system() == "Linux":
                os.system(f"chown -R 1000:1000 {world_path}")

        worlds_uploaded = 0

        if is_world_in_unpacked:
            delete_and_move("world")
            worlds_uploaded += 1

        if is_world_nether_unpacked:
            delete_and_move("world_nether")
            worlds_uploaded += 1

        if is_world_the_end_unpacked:
            delete_and_move("world_the_end")
            worlds_uploaded += 1

        await message_response.edit(content=f"✅ Unpacking complete! World(s) uploaded: `{worlds_uploaded}`")

        shutil.rmtree(temp_dir)
        os.remove(archive_path)

    @discord.slash_command(name='force-stop', description='Force stop the server. (❌ Data can be lost!)')
    async def force_stop(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        await self.shutdown_logic()
        await ctx.respond("✅ Force-stopped the server.")

    @discord.slash_command(name='start', description='Start minecraft server. (Only one at the time)')
    async def start_server(
            self, ctx: discord.ApplicationContext,
            version_enum_name: discord.Option(str, name='version', choices=versions),
            server_type: discord.Option(str, name='type', choices=config.SERVER_TYPES),
            memory: discord.Option(
                int, default=1024,
                description='🔢 In megabytes. (1024 by default, 75% will be used)'
            ),

            pvp: discord.Option(bool, default=True, description="Enables PVP on server (True)"),
            gamemode: discord.Option(
                str, choices=['survival', 'adventure', 'creative', 'spectator'], default="survival",
                description="Default player gamemode (Survival)"
            ),
            view_distance: discord.Option(
                int, min_value=2, max_value=64, default=10, description="Maximum view distance (10)"
            ),
            spawn_protection: discord.Option(int, min_value=0, default=16, description="Spawn Protection (16)"),
            hardcore: discord.Option(bool, default=False, description="Hardcore Mode (False)"),
            enable_command_blocks: discord.Option(bool, default=True, description="Command Blocks (True)"),
            max_players: discord.Option(
                int, default=20, description="Maximum concurrent player count (20)", min_value=1
            ),
            difficulty: discord.Option(
                str, choices=['peaceful', 'easy', 'normal', 'hard'], default='easy',
                description="In-game difficulty (Easy)"
            ),
            motd: discord.Option(
                str, default='Minecraft server running with discord bot :)', description="Server MOTD"
            ),

            regenerate: discord.Option(bool, default=False, description='❌ All server data will be deleted!')

    ):
        if self.running:
            return await ctx.respond('❌ Already running!', ephemeral=True)

        version = Versions[version_enum_name].value.name
        java_version = Versions[version_enum_name].value.flag.java_version
        memory = round(memory * 0.75)

        initial_response = await ctx.respond('☑ Starting...')

        if regenerate:
            await initial_response.edit_original_response(content="ℹ Regenerating...")
            docker_client.volumes.prune()
            print(os.system(f"rm -rf {self.bot.config.DOCKER_VOLUME_PATH}/{version}/"))

        container = docker_client.containers.run(
            image=f'itzg/minecraft-server:{java_version}',
            name=version,
            environment=[
                "EULA=TRUE",
                f"VERSION={version}",
                f"TYPE={server_type}",
                f'MEMORY={memory}M',
                f'PVP={str(pvp).lower()}',
                f'MODE={gamemode}',
                f'VIEW_DISTANCE={view_distance}',
                f'SPAWN_PROTECTION={spawn_protection}',
                f'HARDCORE={hardcore}',
                f'ENABLE_COMMAND_BLOCK={str(enable_command_blocks).lower()}',
                f'MAX_PLAYERS={max_players}',
                f'DIFFICULTY={difficulty}',
                f'MOTD={motd}',

            ],
            ports={'25565/tcp': (config.IP, config.PORT)},
            volumes=[f"{self.bot.config.DOCKER_VOLUME_PATH}/{version}:/data"],
            mem_limit=f'{memory}m',
            detach=True
        )

        self.running = True
        self.container = container
        self.console_channel = ctx.channel.id

        last_check = None

        initial_response = await initial_response.edit_original_response(
            content=f'✅ **Running...** (Type in `{config.CONSOLE_PREFIX}<command>` to send commands to console)'
        )

        # It's a very rough implementation that, should be improved somehow.
        while self.running:
            logs = container.logs(since=last_check).decode('utf-8')
            last_check = datetime.datetime.utcnow()

            if len(logs) > 0:
                print(logs)
                try:
                    await initial_response.channel.send(f'```md\n{logs}```')
                except discord.HTTPException:
                    await initial_response.channel.send(f'``` * This log cannot be displayed on Discord *```')

            await asyncio.sleep(1.8)


def setup(bot):
    bot.add_cog(Minecraft(bot))
