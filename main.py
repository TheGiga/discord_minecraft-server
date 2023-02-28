import os
import asyncio
import requests
import discord
from dotenv import load_dotenv

load_dotenv()

import config
from src import bot_instance, docker_client


# from src import db_init


async def main():
    # await db_init()
    await bot_instance.start(os.getenv("TOKEN"))


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
        event_loop.run_until_complete(bot_instance.close())
        for container in docker_client.containers.list():
            container.stop()
            print(f'Stopped {container.name}')

        docker_client.containers.prune()
        docker_client.volumes.prune()
        # event_loop.run_until_complete(connections.close_all(discard=True))
        event_loop.stop()
        print("✅ Done!")
