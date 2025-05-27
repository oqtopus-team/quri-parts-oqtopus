import configparser
import os
from pathlib import Path


class OqtopusConfig:
    """A configuration information class for using OQTOPUS backend.

    Args:
        url: Base URL for OQTOPUS Cloud.
        api_token: API token for OQTOPUS Cloud.

    Raises:
        ValueError: If ``url`` or ``api_token`` is None.

    """

    def __init__(self, url: str, api_token: str, proxy: str | None = None) -> None:
        super().__init__()

        if url is None:
            msg = "url should not be None."
            raise ValueError(msg)
        self._url: str = url

        if api_token is None:
            msg = "api_token should not be None."
            raise ValueError(msg)
        self._api_token: str = api_token

        self._proxy: str | None = proxy

    @property
    def url(self) -> str:
        """Return the url.

        Returns:
            str: the url to access OCTOPUS Cloud.

        """
        return self._url

    @property
    def api_token(self) -> str:
        """Return the API token.

        Returns:
            str: the API token to access OCTOPUS Cloud.

        """
        return self._api_token

    @property
    def proxy(self) -> str | None:
        """Return the proxy.

        Returns:
            str | None: the proxy to access OCTOPUS Cloud.

        """
        return self._proxy

    @staticmethod
    def from_file(
        section: str | None = "default", path: str | None = "~/.oqtopus"
    ) -> "OqtopusConfig":
        """Read configuration information from a file.

        Args:
            section: A :class:`OqtopusConfig` for circuit execution.
            path: A path for config file.

        Returns:
            Configuration information :class:`OqtopusConfig` .

        Raises:
        ValueError: If ``path`` is None.

        Examples:
            The OQTOPUS configuration file describes configuration information for each
            section. A section has a header in the form ``[section]``.
            The default file path is ``~/.oqtopus`` and the default section name is
            ``default``. Each section describes a setting in the format ``key=value``.
            An example of a configuration file description is as below:

            .. code-block::

                [default]
                url=<base URL>
                api_token=<API token>

                [sectionA]
                url=<base URL>
                api_token=<API token>

                [sectioB]
                url=<base URL>
                api_token=<API token>
                proxy=http://<proxy>:<port>

            If ``sectionA`` settings are to be used, initialize
            ``OqtopusSamplingBackend`` as follows

            .. code-block::

                backend = OqtopusSamplingBackend(OqtopusConfig.from_file("sectionA"))

        """
        if os.getenv("OQTOPUS_ENV") == "sse_container":
            # This section is only for inside SSE container.
            # Config is not needed in the container.
            return OqtopusConfig(url="", api_token="")
        if path is None:
            msg = "path should not be None."
            raise ValueError(msg)
        if section is None:
            msg = "section should not be None."
            raise ValueError(msg)
        expanded = os.path.expandvars(path)
        path_expanded = Path(expanded)
        pat_expanduser = Path.expanduser(path_expanded)
        parser = configparser.ConfigParser()
        parser.read(pat_expanduser, encoding="utf-8")
        return OqtopusConfig(
            url=parser[section]["url"],
            api_token=parser[section]["api_token"],
            proxy=parser[section].get("proxy", None),
        )
