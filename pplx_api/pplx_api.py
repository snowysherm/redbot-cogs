from discord import Message
from redbot.core import Config, checks, commands
from typing import List
from perplexipy import PerplexityClient
import re

class PerplexityAPI(commands.Cog):
    """Send messages to Perplexity AI"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=359554929893)
        default_global = {
            "model": "llama-3.1-70b-instruct",
            "max_tokens": 400,
            "mention": True,
            "reply": True,
            "prompt_insert": "",
        }
        self.config.register_global(**default_global)
        self.client = None

    async def perplexity_api_key(self):
        pplx_keys = await self.bot.get_shared_api_tokens("pplx")
        return pplx_keys.get("api_key")

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        config_mention = await self.config.mention()
        config_reply = await self.config.reply()
        if not config_mention and not config_reply:
            return
        ctx: commands.Context = await self.bot.get_context(message)
        to_strip = f"(?m)^(<@!?{self.bot.user.id}>)"
        is_mention = config_mention and re.search(to_strip, message.content)
        is_reply = False
        if config_reply and message.reference and message.reference.resolved:
            author = getattr(message.reference.resolved, "author")
            if author is not None:
                is_reply = message.reference.resolved.author.id == self.bot.user.id and ctx.me in message.mentions
        if is_mention or is_reply:
            await self.do_pplx(ctx)

    @commands.command(aliases=['chat'])
    async def pplx(self, ctx: commands.Context, *, message: str):
        """Send a message to Perplexity AI."""
        await self.do_pplx(ctx, message)

    async def do_pplx(self, ctx: commands.Context, message: str = None):
        await ctx.typing()
        perplexity_api_key = await self.perplexity_api_key()
        if perplexity_api_key is None:
            prefix = ctx.prefix if ctx.prefix else "[p]"
            await ctx.send(f"Perplexity API key not set. Use `{prefix}set api pplx api_key <your_api_key>`.")
            return
        model = await self.config.model()
        max_tokens = await self.config.max_tokens()
        if self.client is None:
            self.client = PerplexityClient(key=perplexity_api_key)
        
        prompt = await self.build_prompt(ctx, message)
        try:
            reply = self.client.query(prompt)
            if len(reply) > 2000:
                reply = reply[:1997] + "..."
            await ctx.send(content=reply, reference=ctx.message)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    async def build_prompt(self, ctx: commands.Context, message: str = None) -> str:
        content = message if message else ctx.message.clean_content
        to_strip = f"(?m)^(<@!?{self.bot.user.id}>)"
        is_mention = re.search(to_strip, ctx.message.content)
        if is_mention:
            content = content[len(ctx.me.display_name) + 2 :]
        if content.startswith('chat '):
            content = content[5:]
        prompt_insert = await self.config.prompt_insert()
        if prompt_insert:
            content = f"{prompt_insert}\n-----------\n{content}"
        return content

    @commands.command()
    @checks.is_owner()
    async def getpplxmodel(self, ctx: commands.Context):
        """Get the model for Perplexity AI."""
        model = await self.config.model()
        await ctx.send(f"Perplexity AI model set to `{model}`")

    @commands.command()
    @checks.is_owner()
    async def setpplxmodel(self, ctx: commands.Context, model: str):
        """Set the model for Perplexity AI."""
        if self.client is None:
            await ctx.send("Client not initialized. Please use the bot once to initialize the client.")
            return
        available_models = self.client.models.keys()
        if model not in available_models:
            await ctx.send(f"Invalid model. Available models: {', '.join(available_models)}")
            return
        await self.config.model.set(model)
        await ctx.send("Perplexity AI model set.")

    @commands.command()
    @checks.is_owner()
    async def getpplxtokens(self, ctx: commands.Context):
        """Get the maximum number of tokens for Perplexity AI to generate."""
        max_tokens = await self.config.max_tokens()
        await ctx.send(f"Perplexity AI maximum number of tokens set to `{max_tokens}`")

    @commands.command()
    @checks.is_owner()
    async def setpplxtokens(self, ctx: commands.Context, number: str):
        """Set the maximum number of tokens for Perplexity AI to generate."""
        try:
            await self.config.max_tokens.set(int(number))
            await ctx.send("Perplexity AI maximum number of tokens set.")
        except ValueError:
            await ctx.send("Invalid numeric value for maximum number of tokens.")

    @commands.command()
    @checks.is_owner()
    async def togglepplxmention(self, ctx: commands.Context):
        """Toggle messages to Perplexity AI on mention.
        Defaults to `True`."""
        mention = not await self.config.mention()
        await self.config.mention.set(mention)
        if mention:
            await ctx.send("Enabled sending messages to Perplexity AI on bot mention.")
        else:
            await ctx.send("Disabled sending messages to Perplexity AI on bot mention.")

    @commands.command()
    @checks.is_owner()
    async def togglepplxreply(self, ctx: commands.Context):
        """Toggle messages to Perplexity AI on reply.
        Defaults to `True`."""
        reply = not await self.config.reply()
        await self.config.reply.set(reply)
        if reply:
            await ctx.send("Enabled sending messages to Perplexity AI on bot reply.")
        else:
            await ctx.send("Disabled sending messages to Perplexity AI on bot reply.")

    @commands.command()
    @checks.is_owner()
    async def getpplxpromptinsert(self, ctx: commands.Context):
        """Get the prompt insertion for Perplexity AI."""
        prompt_insert = await self.config.prompt_insert()
        await ctx.send(f"Perplexity AI prompt insertion is set to: `{prompt_insert}`")

    @commands.command()
    @checks.is_owner()
    async def setpplxpromptinsert(self, ctx: commands.Context, *, prompt_insert: str):
        """Set the prompt insertion for Perplexity AI."""
        await self.config.prompt_insert.set(prompt_insert)
        await ctx.send("Perplexity AI prompt insertion set.")

