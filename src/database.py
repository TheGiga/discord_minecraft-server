import logging

from tortoise import Tortoise


async def db_init():
    await Tortoise.init(
        db_url='sqlite://bot.db?journal_mode=TRUNCATE',
        modules={'models': ['src.models']}
    )

    print("✔ Database initialised!")
    logging.info("Database initialised!")

    await Tortoise.generate_schemas(safe=True)
