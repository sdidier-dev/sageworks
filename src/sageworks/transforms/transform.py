"""Transform: Base Class for all transforms within SageWorks
              Inherited Classes must implement the abstract transform_impl() method"""
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import final
import logging
import awswrangler as wr

# SageWorks Imports
from sageworks.aws_service_broker.aws_sageworks_role_manager import AWSSageWorksRoleManager
from sageworks.utils.sageworks_logging import logging_setup

# Setup Logging
logging_setup()


class TransformInput(Enum):
    """Enumerated Types for SageWorks Transform Inputs"""
    LOCAL_FILE = auto()
    PANDAS_DF = auto()
    SPARK_DF = auto()
    S3_OBJECT = auto()
    DATA_SOURCE = auto()
    FEATURE_SET = auto()
    MODEL = auto()


class TransformOutput(Enum):
    """Enumerated Types for SageWorks Transform Outputs"""
    PANDAS_DF = auto()
    SPARK_DF = auto()
    S3_OBJECT = auto()
    DATA_SOURCE = auto()
    FEATURE_SET = auto()
    MODEL = auto()
    ENDPOINT = auto()


class Transform(ABC):
    def __init__(self, input_uuid: str, output_uuid: str):
        """Transform: Abstract Base Class for all transforms in SageWorks"""

        self.log = logging.getLogger(__name__)
        self.input_type = None
        self.output_type = None
        self.output_tags = list()
        self.output_meta = dict()
        self.input_uuid = input_uuid
        self.output_uuid = output_uuid

        # FIXME: We should have this come from AWS or Config
        self.data_catalog_db = 'sageworks'
        self.data_source_s3_path = 's3://scp-sageworks-artifacts/data-sources'
        self.feature_set_s3_path = 's3://scp-sageworks-artifacts/feature-sets'

        # Grab a SageWorks Role ARN, Boto3, SageMaker Session, and SageMaker Client
        self.sageworks_role_arn = AWSSageWorksRoleManager().sageworks_execution_role_arn()
        self.boto_session = AWSSageWorksRoleManager().boto_session()
        self.sm_session = AWSSageWorksRoleManager().sagemaker_session()
        self.sm_client = self.sm_session.boto_session.client("sagemaker")

        # Make sure the AWS data catalog database exists
        self.ensure_aws_catalog_db()

    @abstractmethod
    def transform_impl(self, **kwargs):
        """Abstract Method: Implement the Transformation from Input to Output"""
        pass

    def pre_transform(self, **kwargs):
        """Perform any Pre-Transform operations"""
        self.log.info('Pre-Transform...')

    def post_transform(self, **kwargs):
        """Perform any Post-Transform operations"""
        self.log.info('Post-Transform...')

    def set_output_tags(self, tags: list | str):
        """Set the tags that will be associated with the output object
           Args:
               tags (list | str): The list of tags or a ':' separated string of tags"""
        if isinstance(tags, list):
            self.output_tags = ':'.join(tags)
        else:
            self.output_tags = tags

    def set_output_meta(self, meta: dict):
        """Set the metadata that will be associated with the output object
           Args:
               meta (dict): A dictionary of metadata"""
        self.output_meta = meta

    @final
    def transform(self, **kwargs):
        """Perform the Transformation from Input to Output with pre_transform() and post_transform() invocations"""
        self.pre_transform(**kwargs)
        self.transform_impl(**kwargs)
        self.post_transform(**kwargs)

    def input_type(self) -> TransformInput:
        """What Input Type does this Transform Consume"""
        return self.input_type

    def output_type(self) -> TransformOutput:
        """What Output Type does this Transform Produce"""
        return self.output_type

    def set_input_uuid(self, input_uuid: str):
        """Set the Input UUID (Name) for this Transform"""
        self.input_uuid = input_uuid

    def set_output_uuid(self, output_uuid: str):
        """Set the Output UUID (Name) for this Transform"""
        self.output_uuid = output_uuid

    def ensure_aws_catalog_db(self):
        """Ensure that the AWS Catalog Database exists"""
        wr.catalog.create_database(self.data_catalog_db, exist_ok=True, boto3_session=self.boto_session)
