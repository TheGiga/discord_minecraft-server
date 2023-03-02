import os
import asyncio
import requests
import discord
from dotenv import load_dotenv
from tortoise import connections

load_dotenv()

import config
from src import bot_instance, docker_client, db_init
from src.models.preset import Preset


# from src import db_init


async def main():
    await db_init()
    await bot_instance.start(os.getenv("TOKEN"))


async def stop_running_containers():
    for container in docker_client.containers.list():
        preset = await Preset.get_or_none(name=container.name)
        await preset.shutdown_logic(5.0)

        container.stop()
        print(f'Stopped {container.name}')


@bot_instance.check
async def overall_check(ctx: discord.ApplicationContext):
    return ctx.user.id in bot_instance.config.WHITELIST


if __name__ == "__main__":

    try:
        resp = requests.get(url=f'http://{os.getenv("IP")}:6969')
        print('☑ File server is up!')
    except requests.exceptions.ConnectionError:
        print("❌ Couldn't connect to file server.")

    for cog in config.COGS:
        bot_instance.load_extension(f'cogs.{cog}')
        print(f'☑ Loaded {cog}')

    event_loop = asyncio.get_event_loop_policy().get_event_loop()

    try:
        event_loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        print("🛑 Shutting Down, wait till everything cleans up.")

        event_loop.run_until_complete(stop_running_containers())

        docker_client.containers.prune()
        docker_client.volumes.prune()

        event_loop.run_until_complete(connections.close_all(discard=True))
        event_loop.run_until_complete(bot_instance.close())

        event_loop.stop()
        print("✅ Done!")
