import discord
from tortoise.exceptions import IntegrityError
from discord import SlashCommandGroup

import config
from src import Versions as VersionsEnum, PresetEmbed
from src.models import Preset


async def versions(ctx: discord.AutocompleteContext):
    return [discord.OptionChoice(x.value.name, x.name) for x in VersionsEnum if x.value.name.startswith(ctx.value)]


async def names(ctx: discord.AutocompleteContext):
    return [discord.OptionChoice(x.name) for x in await Preset.all() if x.name.startswith(ctx.value)]


class Presets(discord.Cog):
    def __init__(self, bot):
        self.bot = bot

    preset = SlashCommandGroup(name='preset', description='Manage your server configuration presets.')

    @preset.command(name='create', description='Create configuration preset.')
    async def preset_create(
            self, ctx: discord.ApplicationContext,
            name: discord.Option(
                str, max_length=20, min_length=1, description="Name will be converted to lower text. (Plane -> plane)"
            ),
            version: discord.Option(str, autocomplete=versions),
            server_type: discord.Option(str, choices=config.SERVER_TYPES)
    ):
        name = name.lower()
        version = VersionsEnum[version]

        try:
            created_preset = await Preset.create(name=name, version=version.value.name, server_type=server_type)
        except IntegrityError:
            return await ctx.respond(
                f"❌ Preset with name `{name}` already exists!\n"
                f"- *Use `/preset config {name}` to get more information on that preset.*",
                ephemeral=True
            )

        embed = PresetEmbed(created_preset)

        await ctx.respond(
            content="**Use `/preset config` to change configuration values.**",
            embed=embed
        )

    # For now, since selects in modals aren't a thing yet, spamming discord.Option's is the only actual way.
    @preset.command(
        name='config', description='See/Change information about specific server configuration and properties. '
    )
    async def preset_config(
            self, ctx: discord.ApplicationContext,
            name: discord.Option(
                str, max_length=20, description="Name of the preset you want to change.", autocomplete=names,
                min_length=1
            ),
            pvp: discord.Option(str, choices=['true', 'false']) = None,  # noqa
            mode: discord.Option(str, choices=['survival', 'adventure', 'creative', 'spectator']) = None,  # noqa
            view_distance: discord.Option(int, min_value=2, max_value=64) = None,  # noqa
            spawn_protection: discord.Option(int, min_value=1) = None,  # noqa
            hardcore: discord.Option(str, choices=['true', 'false']) = None,  # noqa
            enable_command_blocks: discord.Option(str, choices=['true', 'false']) = None,  # noqa
            max_players: discord.Option(int, min_value=1) = None,  # noqa
            difficulty: discord.Option(str, choices=['peaceful', 'easy', 'normal', 'hard']) = None,  # noqa
            motd: discord.Option(str, min_length=1) = None,  # noqa

            allocated_memory: discord.Option(  # noqa
                int, min_value=512,
                description="Allocated Memory in megabytes. (75% will be used, 25% reserved for docker)"
            ) = None,

            port: discord.Option(  # noqa
                int, min_value=1, max_value=65535, description="Server port, it must be forwarded"
            ) = None
    ):
        name = name.lower()

        preset = await Preset.get_or_none(name=name)

        if not preset:
            return await ctx.respond(f"❌ There is no preset with name `{name}`", ephemeral=True)

        await ctx.defer()

        properties = preset.properties.copy()
        changed_values: list[str] = []

        for cfg_value in ctx.selected_options:
            if cfg_value.get('name') == "name":
                continue

            if cfg_value.get('name') == 'allocated_memory':
                preset.memory = cfg_value.get('value')
                changed_values.append(cfg_value.get('name'))

            elif cfg_value.get('name') == 'port':
                preset.port = cfg_value.get('value')
                changed_values.append(cfg_value.get('name'))

            else:
                properties[cfg_value.get('name').upper()] = str(cfg_value.get('value'))
                changed_values.append(cfg_value.get('name'))

        preset.properties = properties
        await preset.save()

        content = ''

        for value in changed_values:
            content += f'`{value.upper()}`, '

        await ctx.respond(
            content=f'**Changed values:** {content[:-2]} ({len(changed_values)})',  # Removing last 2 characters - ', '
            embed=PresetEmbed(preset)
        )


def setup(bot):
    bot.add_cog(Presets(bot))
