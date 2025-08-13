from abc import abstractmethod


class OqtopusModelBase:
    """A base class for all OQTOPUS models.

    This class provides common functionality for all models in the OQTOPUS framework.
    """

    @abstractmethod
    def refresh(self) -> None:
        """Refresh the model data from the OQTOPUS Cloud.

        This method should be implemented by subclasses to update the model's data
        from the cloud.

        Raises:
            BackendError: If there is an error while refreshing the model data.

        """
        msg = "Subclasses must implement this method."
        raise NotImplementedError(msg)

    @abstractmethod
    def to_json(self) -> str:
        """Convert the model to a JSON string.

        Returns:
            str: The JSON representation of the model.

        """
        msg = "Subclasses must implement this method."
        raise NotImplementedError(msg)
