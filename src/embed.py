import discord
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Preset


class DefaultEmbed(discord.Embed):
    def __init__(self):
        self.set_footer(text='by gigalegit-#0880')
        super().__init__(colour=discord.Colour.embed_background())


class PresetEmbed(discord.Embed):
    def __init__(self, preset: 'Preset'):
        super().__init__()

        self.colour = discord.Colour.green()
        self.title = preset.name

        self.description = f"🔢 **Allocated Memory:** `{preset.memory}M`\n" \
                           f"🎯 **Version:** `{preset.version}`\n" \
                           f"🔨 **Server Type:** `{preset.server_type}`\n\n" \
                           f"**Properties:**"

        for key in preset.properties:
            self.add_field(name=key, value=f'`{preset.properties[key].upper()}`')

        self.set_footer(text=f"Preset ID: {preset.id}")
