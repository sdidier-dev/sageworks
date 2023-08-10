"""SQL based Quartiles: Compute Quartiles for all the numeric columns in a DataSource using SQL"""
import logging
import pandas as pd

# SageWorks Imports
from sageworks.artifacts.data_sources.data_source_abstract import DataSourceAbstract
from sageworks.utils.sageworks_logging import logging_setup

# Setup Logging
logging_setup()
log = logging.getLogger(__name__)


def sample_rows(data_source: DataSourceAbstract) -> pd.DataFrame:
    """Pull a sample of rows from the DataSource
    Args:
        data_source: The DataSource that we're pulling the sample rows from
    Returns:
        pd.DataFrame: A sample DataFrame from this DataSource
    """

    # Note: Hardcoded to 100 rows so that metadata storage is consistent
    sample_rows = 100
    num_rows = data_source.details()["num_rows"]
    if num_rows > sample_rows:
        # Bernoulli Sampling has reasonable variance, so we're going to +1 the
        # sample percentage and then simply clamp it to 100 rows
        percentage = round(sample_rows * 100.0 / num_rows) + 1
        data_source.log.warning(f"DataSource has {num_rows} rows.. sampling down to {sample_rows}...")
        query = f"SELECT * FROM {data_source.table_name} TABLESAMPLE BERNOULLI({percentage})"
    else:
        query = f"SELECT * FROM {data_source.table_name}"
    sample_df = data_source.query(query).head(sample_rows)

    # Return the sample_df
    return sample_df


if __name__ == "__main__":
    """Exercise the SQL Quartiles Functionality"""
    from sageworks.artifacts.data_sources.data_source import DataSource

    # Setup Pandas output options
    pd.set_option("display.max_colwidth", 50)
    pd.set_option("display.max_columns", 15)
    pd.set_option("display.width", 1000)

    # Retrieve a Data Source
    my_data = DataSource("abalone_data")

    # Verify that the Athena Data Source exists
    assert my_data.exists()

    # What's my SageWorks UUID
    print(f"UUID: {my_data.uuid}")

    # Get sample rows for this DataSource
    my_sample_df = sample_rows(my_data)
    print("\nSample Rows")
    print(my_sample_df)