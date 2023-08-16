"""SQL based Column Statistics: Compute Column Statistics for a DataSource using SQL"""
import logging
import pandas as pd

# SageWorks Imports
from sageworks.artifacts.data_sources.data_source_abstract import DataSourceAbstract
from sageworks.utils.sageworks_logging import logging_setup

# Setup Logging
logging_setup()
log = logging.getLogger(__name__)


def count_distinct_query(columns: list[str], table_name: str):
    """Build a query to compute the count of distinct values for the given columns
       Args:
           columns(list(str)): The columns to compute distinct counts on
           table_name(str): The database table
       Returns:
           str: The query to compute the distinct values count for the given columns
    """
    distinct_counts = [f'COUNT(DISTINCT {column}) AS {column}' for column in columns]
    sql_query = f'SELECT  {", ".join(distinct_counts)} FROM {table_name};'
    return sql_query


def count_nulls_query(columns: list[str], table_name: str) -> str:
    """Build a query to compute the counts of null values for the given columns
       Args:
           columns(list[str]): The columns to compute null counts on
           table_name(str): The database table
       Returns:
           str: The query to compute the null values counts for the given columns
    """
    null_counts = [f'COUNT(CASE WHEN {column} IS NULL THEN 1 END) AS {column}' for column in columns]
    sql_query = f'SELECT  {", ".join(null_counts)} FROM {table_name};'
    return sql_query


def count_zeros_query(columns: list[str], table_name: str) -> str:
    """Build a query to compute the counts of zero values for the given columns
       Args:
           columns(list[str]): The columns to compute zero counts on
           table_name(str): The database table
       Returns:
           str: The query to compute the zero values counts for the given columns
    """
    zero_counts = [f'COUNT(CASE WHEN {column} = 0 THEN 1 END) AS zero_values_{column}' for column in columns]
    sql_query = f'SELECT  {", ".join(zero_counts)} FROM {table_name};'
    return sql_query


def column_stats(data_source: DataSourceAbstract) -> dict[dict]:
    """SQL based Column Statistics: Compute Column Statistics for a DataSource using SQL
    Args:
        data_source(DataSource): The DataSource that we're computing column stats on
    Returns:
        dict(dict): A dictionary of stats for each column this format
        NB: String columns will have value_counts but NOT have num_zeros and quartiles
             {'col1': {'dtype': 'string', 'unique': 4321, 'nulls': 12, 'value_counts': {...}},
              'col2': {'dtype': 'int', 'unique': 4321, 'nulls': 12, 'num_zeros': 100, 'quartiles': {...}},
              ...}
    """
    data_source.log.info("Computing Column Statistics for all columns...")

    #
    # This first section is just aggregating data that we've already computed
    #

    # Get the column names and types from the DataSource
    column_data = {name: {"dtype": dtype} for name, dtype in data_source.column_details().items()}

    # Now add quartiles to the column stats
    quartiles = data_source.quartiles()
    for column, quartile_info in quartiles.items():
        column_data[column]["quartiles"] = quartile_info

    # Now add value_counts to the column stats
    value_counts = data_source.value_counts()
    for column, count_info in value_counts.items():
        column_data[column]["value_counts"] = count_info

    # Now add correlations to the column stats
    correlations = data_source.correlations()
    for column, correlation_info in correlations.items():
        column_data[column]["correlations"] = correlation_info

    #
    # This second section is computing uniques, nulls/nans, and num_zeros
    #

    # Figure out which columns are numeric
    num_type = ["double", "float", "int", "bigint", "smallint", "tinyint"]
    details = data_source.column_details()
    numeric = [column for column, data_type in details.items() if data_type in num_type]
    non_numeric = [column for column, data_type in details.items() if data_type not in num_type]
    all_columns = numeric + non_numeric

    # Now call the queries to compute the counts of distinct, nulls, and zeros
    data_source.log.info("Computing Unique values...")
    distinct_counts = data_source.query(count_distinct_query(all_columns, data_source.table_name))
    data_source.log.info("Computing Null values...")
    null_counts = data_source.query(count_nulls_query(all_columns, data_source.table_name))
    data_source.log.info("Computing Zero values...")
    zero_counts = data_source.query(count_zeros_query(numeric, data_source.table_name))

    # Okay now we take the results of the queries and add them to the column_data
    for column in all_columns:
        column_data[column]["unique"] = distinct_counts.iloc[0][column]
        column_data[column]["nulls"] = null_counts.iloc[0][column]
        if column in numeric:
            column_data[column]["num_zeros"] = zero_counts.iloc[0][f"zero_values_{column}"]

    # Return the column stats data
    return column_data


if __name__ == "__main__":
    """Exercise the SQL Quartiles Functionality"""
    from pprint import pprint
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

    # Get column stats for all columns
    my_column_stats = column_stats(my_data)
    print("\nColumn Stats:")
    pprint(my_column_stats)
