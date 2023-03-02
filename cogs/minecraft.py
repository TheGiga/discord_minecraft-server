import asyncio
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
from src import SubclassedBot, utils
from src.models import Preset
from .presets import names

versions = [
    discord.OptionChoice(x.value.name, x.name)
    for x in config.VERSIONS
]


class Minecraft(discord.Cog):
    def __init__(self, bot):
        self.bot: SubclassedBot = bot
        self.running = False
        self.preset = None
        self.container = None
        self.console_channel = None

    world = SlashCommandGroup(name='world', description="Commands to work with server world(s)")

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id != self.console_channel:
            return

        if not message.content.startswith(config.CONSOLE_PREFIX) or message.author.id not in config.WHITELIST:
            return

        cmd = message.content.removeprefix(config.CONSOLE_PREFIX).strip()
        cmd = cmd.translate(cmd.maketrans(config.ESCAPED_CHARACTERS))

        print(f'{config.CONSOLE_PREFIX} {cmd}  ({message.author} [{message.author.id}])')
        response = self.container.exec_run(["mc-send-to-console", f"{cmd}"])

        pretty_response = response.output.decode("utf-8")
        await message.reply(f'Response: `{pretty_response if len(pretty_response) > 0 else "✅"}`')

        if cmd == "stop" and self.running:
            await self.preset.shutdown_logic()
            self.running = False
            self.preset = None
            self.container = None
            self.console_channel = None

    @cooldown(1, 10, BucketType.default)
    @world.command(name='download', description='Download server world(s).')
    async def download_world(
            self, ctx: discord.ApplicationContext,
            preset: discord.Option(
                max_length=20, autocomplete=names, description='Name of a preset you want to download from'
            ),
    ):
        if self.running:
            return await ctx.respond("❌ Couldn't download world(s), server is running.", ephemeral=True)

        await ctx.respond('Working on it...')

        name = preset.lower()
        preset = await Preset.get_or_none(name=name)

        if not preset:
            return await ctx.respond(
                f"❌ There is no preset with name `{name}`, create one by running `/preset create`", ephemeral=True
            )

        directory = f'{uuid.uuid4()}'

        for world in config.DIMENSIONS:
            start_path = f"{config.DOCKER_VOLUME_PATH}/{preset.name}/{world}"
            end_path = f'{config.HTTP_SERVER_PATH}/{directory}/{world}'

            if not os.path.exists(start_path):
                await ctx.channel.send(f"❌ There is no `{world}` on this version.")
                continue

            make_archive(end_path, 'zip', start_path)

        await ctx.send_followup(f'**Result:** http://{os.getenv("IP")}:6969/{directory}/')

    # TODO: Should be refactored.
    @cooldown(1, 15, BucketType.default)
    @world.command(name='upload', description='Upload world(s) to specific server version (it will replace old one!)')
    async def upload_world(
            self, ctx: discord.ApplicationContext,
            url: discord.Option(str),
            preset: discord.Option(
                max_length=20, autocomplete=names, description='Name of a preset you want to download from'
            ),
    ):
        if self.running:
            return await ctx.respond("❌ Couldn't upload world, server is running.", ephemeral=True)

        name = preset.lower()
        preset = await Preset.get_or_none(name=name)

        if not preset:
            return await ctx.respond(
                f"❌ There is no preset with name `{name}`, create one by running `/preset create`", ephemeral=True
            )

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

        temp_dir = f'{config.DOCKER_VOLUME_PATH}/{preset.name}/Temp'.replace("\\", "/")
        temp_dir = utils.ensure_directory_exists(temp_dir)

        shutil.unpack_archive(archive_path, temp_dir)
        is_world_in_unpacked = os.path.exists(f'{temp_dir}/world')
        is_world_nether_unpacked = os.path.exists(f'{temp_dir}/world_nether')
        is_world_the_end_unpacked = os.path.exists(f'{temp_dir}/world_the_end')

        def delete_and_move(world_name):
            world_path = f'{config.DOCKER_VOLUME_PATH}/{preset.name}/{world_name}'
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

    @cooldown(1, 10, BucketType.default)
    @discord.slash_command(name='force-stop', description='Force stop the server. (❌ Data can be lost!)')
    async def force_stop(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        await self.preset.shutdown_logic()

        self.running = False
        self.preset = None
        self.container = None
        self.console_channel = None

        await ctx.respond("✅ Force-stopped the server.")

    @cooldown(1, 10, BucketType.default)
    @discord.slash_command(name='start', description='Start minecraft server. (Only one at the time)')
    async def start_server(
            self, ctx: discord.ApplicationContext,
            preset: discord.Option(str, autocomplete=names, description="Name of the preset to use."),
    ):
        name = preset.lower()
        preset = await Preset.get_or_none(name=name)

        if not preset:
            return await ctx.respond(
                f"❌ There is no preset with name `{name}`, create one by running `/preset create`", ephemeral=True
            )

        if self.running:
            return await ctx.respond(
                '❌ Server is already running!', ephemeral=True
            )

        initial_response = await ctx.respond("🔃 Starting...")

        await preset.run_server(logging=True, logging_channel=ctx.channel)

        self.running = True
        self.preset = preset
        self.container = preset.container
        self.console_channel = ctx.channel.id

        await initial_response.edit_original_response(
            content=f'✅ **Running...** (Type in `{config.CONSOLE_PREFIX}<command>` to send commands to console)'
        )


def setup(bot):
    bot.add_cog(Minecraft(bot))
