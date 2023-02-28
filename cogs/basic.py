import discord

from src import SubclassedBot


class Basic(discord.Cog):
    def __init__(self, bot):
        self.bot: SubclassedBot = bot

    @discord.slash_command(name='help', description='Bot help')
    async def help_command(self, ctx: discord.ApplicationContext):
        await ctx.respond(embeds=self.bot.help_command())


def setup(bot):
    bot.add_cog(Basic(bot))
