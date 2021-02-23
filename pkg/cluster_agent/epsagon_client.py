"""
Async Epsagon client
"""
from http import HTTPStatus
from aiohttp.helpers import BasicAuth
from aiohttp.client_exceptions import ClientError
from aiohttp_retry import RetryClient, ExponentialRetry

class EpsagonClientException(Exception):
    pass


class EpsagonClient:
    """
    Async Epsagon client
    """

    DEFAULT_RETRY_ATTEMPTS = 3

    @classmethod
    async def create(cls, epsagon_token, retry_attempts=DEFAULT_RETRY_ATTEMPTS):
        """
        Creates a new EpsagonClient instance
        :param epsagon_token: used for authorization
        """
        self = cls()
        if not epsagon_token:
            raise ValueError("Epsagon token must be given")
        self.epsagon_token = epsagon_token
        retry_options = ExponentialRetry(
            attempts=retry_attempts,
            exceptions=(ClientError,)
        )
        self.client = RetryClient(
            auth=BasicAuth(login=self.epsagon_token),
            headers={
                "Content-Type": "application/json",
            },
            retry_options=retry_options,
            raise_for_status=True
        )
        return self

    async def post(self, url, data):
        """
        Posts data to Epsagon given url.
        :param url: endpoint to post the data to
        :param data: to send
        HTTP status code.
        """
        async with self.client.post(url, data=data):
            pass

    async def close(self):
        """
        Closes the client.
        """
        await self.client.close()
