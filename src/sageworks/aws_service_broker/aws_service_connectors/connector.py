"""Connector: Abstract Base Class for pulling/refreshing AWS Service metadata"""
from abc import ABC, abstractmethod

import logging
from typing import final

# SageWorks Imports
from sageworks.aws_service_broker.aws_account_clamp import AWSAccountClamp
from sageworks.utils.aws_utils import list_tags_with_throttle


class Connector(ABC):
    """Connector: Abstract Base Class for pulling/refreshing AWS Service metadata"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Create a new instance of the class if it doesn't exist, else return the existing instance."""
        if cls._instance is None:
            cls._instance = super(Connector, cls).__new__(cls)
            cls._instance.__initialized = False  # Gets initialized in __init__
        return cls._instance

    def __init__(self):
        """Initialize the ConfigManager as a singleton."""
        if self.__initialized:
            return

        # Initializing class attributes
        self.log = logging.getLogger("sageworks")
        self.aws_account_clamp = AWSAccountClamp()
        self.boto_session = self.aws_account_clamp.boto_session()
        self.sm_session = self.aws_account_clamp.sagemaker_session(self.boto_session)
        self.sm_client = self.aws_account_clamp.sagemaker_client(self.boto_session)
        self.__initialized = True

    @abstractmethod
    def check(self) -> bool:
        """Can we connect to this service?"""
        pass

    @abstractmethod
    def refresh_impl(self):
        """Abstract Method: Implement the AWS Service Data Refresh"""
        pass

    @final
    def refresh(self) -> bool:
        """Refresh data/metadata associated with this service"""
        # We could do something here to refresh the AWS Session or whatever

        # Call the subclass Refresh method
        return self.refresh_impl()

    @abstractmethod
    def aws_meta(self) -> dict:
        """Return ALL the AWS metadata for this AWS Service"""
        pass

    def sageworks_meta_via_arn(self, arn: str) -> dict:
        """Helper: Get the SageWorks specific metadata for this ARN
        Args:
            arn (str): The ARN of the SageMaker resource
        Returns:
            dict: A dictionary of SageWorks specific metadata
        """
        return list_tags_with_throttle(arn, self.sm_session)
