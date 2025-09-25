import os

from quri_parts_oqtopus.backend.config import OqtopusConfig
from quri_parts_oqtopus.rest import (
    ApiClient,
    Configuration,
)


class OqtopusBackendBase:
    """Base class for oqtopus backend.

    Args:
        config: A :class:`OqtopusConfig` for circuit execution.
            If this parameter is ``None`` and both environment variables ``OQTOPUS_URL``
            and ``OQTOPUS_API_TOKEN`` exist, create a :class:`OqtopusConfig` using
            the values of the ``OQTOPUS_URL``, ``OQTOPUS_API_TOKEN``, and
            ``OQTOPUS_PROXY`` environment variables.

            If this parameter is ``None`` and the environment variables do not exist,
            the ``default`` section in the ``~/.oqtopus`` file is read.

    """

    def __init__(self, config: OqtopusConfig | None = None) -> None:
        # set config
        if config is None:
            # if environment variables are set, use their values
            url = os.getenv("OQTOPUS_URL")
            api_token = os.getenv("OQTOPUS_API_TOKEN")
            proxy = os.getenv("OQTOPUS_PROXY")
            if url is not None and api_token is not None:
                config = OqtopusConfig(
                    url=url,
                    api_token=api_token,
                    proxy=proxy,
                )
            # load config from file
            else:
                config = OqtopusConfig.from_file()
        self.config = config

        # construct JobApi
        rest_config = Configuration()
        rest_config.host = self.config.url
        if self.config.proxy:
            rest_config.proxy = self.config.proxy
        self._api_client = ApiClient(
            configuration=rest_config,
            header_name="q-api-token",
            header_value=self.config.api_token,
        )
