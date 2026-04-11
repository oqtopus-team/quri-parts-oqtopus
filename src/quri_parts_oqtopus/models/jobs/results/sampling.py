from collections import Counter
from typing import Any

from quri_parts.backend import (
    SamplingCounts,
    SamplingResult,
)


class OqtopusSamplingResult(SamplingResult):
    """A result of a sampling job.

    Args:
        result: A result of dict type.
            This dict should have the key ``counts``.
            The value of ``counts`` is the dict input for the counts.
            Where the keys represent a measured classical value
            and the value is an integer the number of shots with that result.

            If the keys of ``counts`` is expressed as a bit string,
            then ``properties`` is a mapping from the index of bit string
            to the index of the quantum circuit.

    Raises:
        ValueError: If ``counts`` does not exist in result.

    Examples:
        An example of a dict of result is as below:

        .. code-block::

            {
                "counts": {
                    "0": 600,
                    "1": 300,
                    "3": 100,
                }
            }

        In the above case, the bit string representation of 0, 1, and 3
        in the keys of ``counts`` is "00", "01", and "11" respectively.
        The LSB (Least Significant Bit) of the bit string representation is
        ``classical index``=0.

    """

    def __init__(self, result: dict[str, Any]) -> None:
        super().__init__()

        if "counts" not in result:
            msg = "'counts' does not exist in result"
            raise ValueError(msg)

        self._result = result
        self._counts: SamplingCounts = Counter(result.get("counts"))
        self._divided_counts: dict[str, SamplingCounts] | None = None
        if result.get("divided_counts"):
            self._divided_counts = {
                index: Counter({
                    int(bits): count
                    for bits, count in result["divided_counts"][index].items()
                })
                for index in result["divided_counts"]
            }

    @property
    def counts(self) -> SamplingCounts:
        """Returns the dict input for the counts."""
        return self._counts

    @property
    def divided_counts(self) -> dict | None:
        """Returns divided_counts."""
        return self._divided_counts

    def __repr__(self) -> str:
        """Return a string representation.

        Returns:
            str: A string representation.

        """
        return str(self._result)
