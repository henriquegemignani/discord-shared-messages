from typing import Dict

from aiohttp import ClientResponse

from .core import OAuth2Client, UserInfo

__author__ = "Bogdan Gladyshev"
__copyright__ = "Copyright 2017, Bogdan Gladyshev"
__credits__ = ["Bogdan Gladyshev"]
__license__ = "MIT"
__version__ = "0.4.0"
__maintainer__ = "Bogdan Gladyshev"
__email__ = "siredvin.dark@gmail.com"
__status__ = "Production"


class GithubClient(OAuth2Client):
    """Support Github.
    * Dashboard: https://github.com/settings/applications/
    * Docs: http://developer.github.com/v3/#authentication
    * API reference: http://developer.github.com/v3/
    """

    access_token_url = 'https://github.com/login/oauth/access_token'
    authorize_url = 'https://github.com/login/oauth/authorize'
    base_url = 'https://api.github.com'
    name = 'github'
    user_info_url = 'https://api.github.com/user'

    @classmethod
    def user_parse(cls, data) -> UserInfo:
        """Parse information from provider."""
        first_name, _, last_name = (data.get('name') or '').partition(' ')
        location = data.get('location', '')
        city, country = '', ''
        if location:
            split_location = location.split(',')
            country = split_location[0].strip()
            if len(split_location) > 1:
                city = split_location[1].strip()
        return UserInfo(
            id=data.get('id'),
            email=data.get('email'),
            first_name=first_name,
            last_name=last_name,
            username=data.get('login'),
            picture=data.get('avatar_url'),
            link=data.get('html_url'),
            city=city,
            country=country
        )


class DiscordClient(OAuth2Client):
    """Support Discord.
    * Dashboard: https://discordapp.com/developers/applications/me
    * Docs: https://discordapp.com/developers/docs/intro
    * API reference: https://discordapp.com/developers/docs/reference
    """

    name = 'discord'
    access_token_url = 'https://discordapp.com/api/oauth2/token'
    authorize_url = 'https://discordapp.com/api/oauth2/authorize'
    base_url = 'https://discordapp.com/api/'
    user_info_url = 'https://discordapp.com/api/users/@me'

    def __init__(self, *args, **kwargs):
        """Set default scope."""
        super(DiscordClient, self).__init__(*args, **kwargs)
        self.params.setdefault('scope', 'email')

    async def request(
            self, method: str, url: str,
            params: Dict[str, str] = None, headers: Dict[str, str] = None, **aio_kwargs) -> ClientResponse:
        """Request OAuth2 resource."""
        if self.access_token:
            headers = headers or {}
            headers['Authorization'] = "Bearer {}".format(self.access_token)
        return await self.aiohttp_session.request(
            method, url, params=params, headers=headers, **aio_kwargs
        )

    @classmethod
    def user_parse(cls, data) -> UserInfo:
        """Parse information from the provider."""
        return UserInfo(
            id=data.get('id'),
            username=data.get('username'),
            discriminator=data.get('discriminator'),
            avatar=data.get('avatar'),
            verified=data.get('verified'),
            email=data.get('email')
        )
