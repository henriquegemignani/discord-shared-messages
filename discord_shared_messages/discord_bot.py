import logging
import typing

import discord


class Bot(discord.Client):
    def __init__(self, token: str, loop, logger: logging.Logger):
        super().__init__(loop=loop)
        self._token = token
        self.logger = logger

    async def runner(self):
        try:
            await self.start(self._token)
        finally:
            if not self.is_closed():
                await self.close()

    @property
    def typed_guilds(self) -> typing.Iterator[discord.Guild]:
        for g in self.guilds:
            yield g

    async def on_ready(self):
        self.logger.info("on_ready!")

        # async for g in self.fetch_guilds():
        #     print(g)
        #     t: discord.Guild = g
        #     for c in await t.fetch_channels():
        #         print(c)

    async def on_message(self, message: discord.Message):
        self.logger.info("Received message: %s", str(message))
