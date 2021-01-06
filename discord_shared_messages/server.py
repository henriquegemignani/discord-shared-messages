from typing import Iterator

import discord
from sanic import Sanic, response
from sanic.log import logger
from sanic.request import Request
from sanic.response import text
from sanic_wtf import SanicForm
from wtforms import SubmitField, TextAreaField
from wtforms.validators import DataRequired

from discord_shared_messages.discord_bot import Bot

app = Sanic("Discord Shared Messages")


class MessageForm(SanicForm):
    body = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Submit')


def bot() -> Bot:
    return app.bot


def get_relevant_channels(guild_id: int) -> Iterator[discord.TextChannel]:
    guild: discord.Guild = bot().get_guild(guild_id)
    if guild is None:
        return []

    for channel in guild.text_channels:
        if channel.topic is not None and "#shared-message" in channel.topic:
            yield channel


@app.get("/")
async def hello_world(request):
    return text("Hello, world.")


@app.get("/guild/<guild_id:int>")
async def guild_index(request: Request, guild_id):
    new_messages = []
    edit_messages = []

    for channel in get_relevant_channels(guild_id):
        new_messages.append("<li><a href='{}'>#{}</a></li>".format(
            app.url_for('post_message_form', guild_id=guild_id, channel_id=channel.id),
            channel.name,
        ))

        async for message in channel.history(oldest_first=True):
            m: discord.Message = message
            if m.author == bot().user:
                edit_messages.append("<li><a href='{}'>{} in #{}</a>: {}</li>".format(
                    app.url_for('edit_message_form', guild_id=guild_id, channel_id=channel.id, message_id=m.id),
                    m.id,
                    channel.name,
                    m.content[:50],
                ))

    return response.html(f"""
    <h1>Post new message to...</h1>
    <ul>{''.join(new_messages)}</ul>
    <h1>Existing messages to edit:</h1>
    <ul>{''.join(edit_messages)}</ul>
    """)


@app.post("/message/<guild_id:int>/<channel_id:int>")
async def post_message(request: Request, guild_id, channel_id):
    guild: discord.Guild = bot().get_guild(guild_id)
    channel: discord.TextChannel = guild.get_channel(channel_id)
    result = await channel.send(request.form["body"][0])

    return text(f"Thanks for the message: {result}")


@app.get("/message/<guild_id:int>/<channel_id:int>")
async def post_message_form(request: Request, guild_id, channel_id):
    guild: discord.Guild = bot().get_guild(guild_id)
    channel: discord.TextChannel = guild.get_channel(channel_id)

    form = MessageForm()
    return response.html(f"""
    <h1>Post new message to #{channel.name}</h1>
    <form action="{app.url_for('post_message', guild_id=guild_id, channel_id=channel_id)}" method="POST">
      {'<br>'.join(form.body.errors)}
      <br>
      {form.body(size=40, placeholder="Message body")}<br />
      {form.submit}
    </form>
    """)


@app.post("/message/<guild_id:int>/<channel_id:int>/<message_id:int>")
async def edit_message(request: Request, guild_id, channel_id, message_id):
    guild: discord.Guild = bot().get_guild(guild_id)
    channel: discord.TextChannel = guild.get_channel(channel_id)
    message = await channel.fetch_message(message_id)
    result = await message.edit(content=request.form["body"][0])

    return text(f"The new message: {result}")


@app.get("/message/<guild_id:int>/<channel_id:int>/<message_id:int>")
async def edit_message_form(request: Request, guild_id, channel_id, message_id):
    guild: discord.Guild = bot().get_guild(guild_id)
    channel: discord.TextChannel = guild.get_channel(channel_id)
    message = await channel.fetch_message(message_id)

    form = MessageForm()
    form.body.data = message.content

    return response.html(f"""
    <h1>Editing message in #{channel.name}</h1>
    <form action="{app.url_for('edit_message', guild_id=guild_id, channel_id=channel_id,
                               message_id=message_id)}" method="POST">
      {'<br>'.join(form.body.errors)}
      <br>
      {form.body(size=40)}<br />
      {form.submit}
    </form>
    """)


@app.listener('before_server_start')
async def setup(app_: Sanic, loop):
    logger.info('Starting discord bot')

    app.bot = Bot(app.config["DISCORD_TOKEN"], loop, logger)
    app.add_task(app.bot.runner())


if __name__ == '__main__':
    app.run(port=8000, debug=True)
