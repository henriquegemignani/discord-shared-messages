from typing import Iterator

import aiohttp
import discord
from sanic import Sanic, response
from sanic.log import logger
from sanic.request import Request
from sanic.response import text
from sanic_session import InMemorySessionInterface
from sanic_wtf import SanicForm
from wtforms import SubmitField, TextAreaField
from wtforms.validators import DataRequired

from discord_shared_messages.discord_bot import Bot
from discord_shared_messages.sanic_oauth.blueprint import oauth_blueprint, login_required

app = Sanic("Discord Shared Messages")
app.blueprint(oauth_blueprint)
app.session_interface = InMemorySessionInterface()
app.config.OAUTH_PROVIDER = 'discord_shared_messages.sanic_oauth.providers.DiscordClient'
app.config.OAUTH_SCOPE = 'identify'


@app.listener('before_server_start')
async def init_aiohttp_session(sanic_app, _loop) -> None:
    sanic_app.async_session = aiohttp.ClientSession()


@app.listener('after_server_stop')
async def close_aiohttp_session(sanic_app, _loop) -> None:
    await sanic_app.async_session.close()


@app.middleware('request')
async def add_session_to_request(request):
    # before each request initialize a session
    # using the client's request
    await request.app.session_interface.open(request)


@app.middleware('response')
async def save_session(request, response):
    # after each request save the session,
    # pass the response to set client cookies
    await request.app.session_interface.save(request, response)


class MessageForm(SanicForm):
    body = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Submit')


def bot() -> Bot:
    return app.bot


def bot_managed_channel(channel: discord.TextChannel, member: discord.Member) -> bool:
    return (channel.topic is not None
            and "#shared-message" in channel.topic
            and channel.permissions_for(member).manage_messages)


def get_relevant_channels(guild_id: int) -> Iterator[discord.TextChannel]:
    guild: discord.Guild = bot().get_guild(guild_id)
    if guild is None:
        return []

    for channel in guild.text_channels:
        if channel.topic is not None and "#shared-message" in channel.topic:
            yield channel


@app.get("/")
async def hello_world(request: Request):
    return text("Hello, world.")


@app.get("/guild/<guild_id:int>")
@login_required
async def guild_index(request: Request, guild_id):
    new_messages = []
    edit_messages = []

    guild: discord.Guild = bot().get_guild(guild_id)
    discord_user: discord.Member = await guild.fetch_member(128619865358467073)

    for channel in guild.text_channels:
        if not bot_managed_channel(channel, discord_user):
            continue

        new_messages.append("<li><a href='{}'>#{}</a></li>".format(
            app.url_for('post_message_form', guild_id=guild_id, channel_id=channel.id, _external=True),
            channel.name,
        ))

        async for message in channel.history(oldest_first=True):
            m: discord.Message = message
            if m.author == bot().user:
                edit_messages.append("<li><a href='{}'>{} in #{}</a>: {}</li>".format(
                    app.url_for('edit_message_form', guild_id=guild_id, channel_id=channel.id,
                                message_id=m.id, _external=True),
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
@login_required
async def post_message(request: Request, user, guild_id, channel_id):
    guild: discord.Guild = bot().get_guild(guild_id)
    channel: discord.TextChannel = guild.get_channel(channel_id)

    if bot_managed_channel(channel, await guild.fetch_member(user.id)):
        result = await channel.send(request.form["body"][0])
        return response.text(f"Thanks for the message: {result}")
    else:
        return response.json({'status': 'not_authorized'}, 403)


@app.get("/message/<guild_id:int>/<channel_id:int>")
@login_required
async def post_message_form(request: Request, user, guild_id, channel_id):
    guild: discord.Guild = bot().get_guild(guild_id)
    channel: discord.TextChannel = guild.get_channel(channel_id)

    if not bot_managed_channel(channel, await guild.fetch_member(user.id)):
        return response.json({'status': 'not_authorized'}, 403)

    form = MessageForm()
    return response.html(f"""
    <h1>Post new message to #{channel.name}</h1>
    <form action="{app.url_for('post_message', guild_id=guild_id,
                               channel_id=channel_id, _external=True)}" method="POST">
      {'<br>'.join(form.body.errors)}
      <br>
      {form.body(size=40, placeholder="Message body")}<br />
      {form.submit}
    </form>
    """)


@app.post("/message/<guild_id:int>/<channel_id:int>/<message_id:int>")
@login_required
async def edit_message(request: Request, user, guild_id, channel_id, message_id):
    guild: discord.Guild = bot().get_guild(guild_id)
    channel: discord.TextChannel = guild.get_channel(channel_id)

    if not bot_managed_channel(channel, await guild.fetch_member(user.id)):
        return response.json({'status': 'not_authorized'}, 403)

    message = await channel.fetch_message(message_id)
    result = await message.edit(content=request.form["body"][0])

    return text(f"The new message: {result}")


@app.get("/message/<guild_id:int>/<channel_id:int>/<message_id:int>")
@login_required
async def edit_message_form(request: Request, user, guild_id, channel_id, message_id):
    guild: discord.Guild = bot().get_guild(guild_id)
    channel: discord.TextChannel = guild.get_channel(channel_id)

    if not bot_managed_channel(channel, await guild.fetch_member(user.id)):
        return response.json({'status': 'not_authorized'}, 403)

    message = await channel.fetch_message(message_id)

    form = MessageForm()
    form.body.data = message.content

    return response.html(f"""
    <h1>Editing message in #{channel.name}</h1>
    <form action="{app.url_for('edit_message', guild_id=guild_id, channel_id=channel_id,
                               message_id=message_id, _external=True)}" method="POST">
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
