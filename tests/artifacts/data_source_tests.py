"""Tests for the DataSource/AthenaSource functionality"""

# SageWorks Imports
from sageworks.artifacts.data_sources.athena_source import AthenaSource


def test():
    """Tests for the DataSource/AthenaSource functionality"""

    # Retrieve our test Data Source
    my_data = AthenaSource("test_data")

    # Verify that the Athena Data Source exists
    assert my_data.check()

    # What's my SageWorks UUID
    print(f"UUID: {my_data.uuid}")

    # What's my AWS ARN
    print(f"AWS ARN: {my_data.arn()}")

    # Get the S3 Storage for this Data Source
    print(f"S3 Storage: {my_data.s3_storage_location()}")

    # What's the size of the data?
    print(f"Size of Data (MB): {my_data.size()}")

    # When was it created and last modified?
    print(f"Created: {my_data.created()}")
    print(f"Modified: {my_data.modified()}")

    # Get Metadata and tags associated with this Artifact
    print(f"Meta: {my_data.meta()}")
    print(f"Tags: {my_data.sageworks_tags()}")

    # Now delete the AWS artifacts associated with this DataSource
    # print('Deleting SageWorks Data Source...')
    # my_data.delete()


if __name__ == "__main__":
    test()
