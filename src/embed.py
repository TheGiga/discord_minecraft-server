import discord


class DefaultEmbed(discord.Embed):
    def __init__(self):
        self.set_footer(text='by gigalegit-#0880')
        super().__init__(colour=discord.Colour.embed_background())
