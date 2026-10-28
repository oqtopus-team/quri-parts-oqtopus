from typing import Any


class OqtopusEstimationResult:
    """A result of a estimation job.

    Args:
        result: A result of dict type.

    Raises:
        ValueError: If ``estimation`` does not exist in result.

    Examples:
        An example of a dict of result is as below:

        .. code-block::

            {
                "estimation": {
                    "exp_value": 2.0,
                    "stds": 1.1
                }
            }

        ``exp_value`` represents the expectation value.
        In the above case, ``exp_value`` is defined as a real number ``2.0``.
        ``stds`` represents the standard deviation value.

    """

    def __init__(
        self,
        result: dict[str, Any],
        mitigation_details: str | None = None,
    ) -> None:
        super().__init__()

        self._result = result
        self._mitigation_details = mitigation_details

    @property
    def exp_value(self) -> float | None:
        """Returns the expectation value."""
        return self._result.get("exp_value")

    @property
    def stds(self) -> float | None:
        """Returns the  standard deviation."""
        return self._result.get("stds")

    @property
    def mitigation_details(self) -> str | None:
        """Returns opaque error-mitigation details encoded as JSON."""
        return self._mitigation_details

    def __repr__(self) -> str:
        """Return a string representation.

        Returns:
            str: A string representation.

        """
        return str(self._result)
