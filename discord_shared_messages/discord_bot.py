import logging

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

    async def on_ready(self):
        self.logger.info("Discord connection ready")
