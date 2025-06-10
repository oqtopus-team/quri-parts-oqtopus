import json
from datetime import datetime
from typing import Any


class DateTimeEncoder(json.JSONEncoder):
    """JSONEncoder supporting `datetime.datetime`."""

    def default(self, obj: Any) -> Any:  # noqa: ANN401
        """Serialize object.

        Args:
            obj (Any): The object to be serialized

        Returns:
            Any: Serialized object.

        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
