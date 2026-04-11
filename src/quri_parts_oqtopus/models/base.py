from abc import abstractmethod


class OqtopusModelBase:
    """A base class for all OQTOPUS models.

    This class provides common functionality.
    """

    def __init__(self) -> None:
        pass

    @abstractmethod
    def refresh(self) -> None:
        """Retrieve the latest information from OQTOPUS Cloud.

        This method should be implemented by subclasses to retrieve the latest
        information from OQTOPUS Cloud.

        Raises:
            BackendError: If there is an error while refreshing the model data.

        """
        msg = "Subclasses must implement this method."
        raise NotImplementedError(msg)

    @abstractmethod
    def to_json(self) -> str:
        """Convert the model to a JSON string.

        This method should be implemented by subclasses to convert the model's data
        to a JSON string.

        Returns:
            str: The JSON representation of the model.

        """
        msg = "Subclasses must implement this method."
        raise NotImplementedError(msg)
