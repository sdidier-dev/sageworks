"""SQL based Outliers: Compute outliers for all the columns in a DataSource using SQL"""
import logging
import pandas as pd

# SageWorks Imports
from sageworks.artifacts.data_sources.data_source_abstract import DataSourceAbstract
from sageworks.utils.sageworks_logging import logging_setup

# Setup Logging
logging_setup()
log = logging.getLogger(__name__)


class Outliers:
    """Outliers: Class to compute outliers for all the columns in a DataSource using SQL"""

    def __init__(self):
        """SQLOutliers Initialization"""
        self.outlier_group = 0

    def compute_outliers(
        self, data_source: DataSourceAbstract, scale: float = 1.7, include_strings: bool = False
    ) -> pd.DataFrame:
        """Compute outliers for all the numeric columns in a DataSource
        Args:
            data_source(DataSource): The DataSource that we're computing outliers on
            scale(float): The scale to use for the IQR outlier calculation (default: 1.7)
            include_strings(bool): Option to include string columns in the outlier calculation (default: False)
        Returns:
            pd.DataFrame: A DataFrame of outliers for this DataSource
        Notes:
            Uses the IQR * 1.7 (~= 3 Sigma) method to compute outliers
            The scale parameter can be adjusted to change the IQR multiplier
        """

        # Compute the numeric outliers
        numeric_outliers_df = self._numeric_outliers(data_source, scale)

        # Compute the string outliers
        if include_strings:
            string_outliers_df = self._string_outliers(data_source)
        else:
            string_outliers_df = None

        # Combine the numeric and string outliers
        if numeric_outliers_df is not None and string_outliers_df is not None:
            all_outliers = pd.concat([numeric_outliers_df, string_outliers_df])
        elif numeric_outliers_df is not None:
            all_outliers = numeric_outliers_df
        elif string_outliers_df is not None:
            all_outliers = string_outliers_df
        else:
            log.warning("No outliers found for this DataSource, returning empty DataFrame")
            all_outliers = pd.DataFrame(columns=data_source.column_names() + ["outlier_group"])

        # Drop duplicates and return the outliers
        return all_outliers.drop_duplicates()

    def _numeric_outliers(self, data_source: DataSourceAbstract, scale: float) -> pd.DataFrame:
        """Internal method to compute outliers for all numeric columns
        Args:
            data_source(DataSource): The DataSource that we're computing outliers on
            scale(float): The scale to use for the IQR outlier calculation
        Returns:
            pd.DataFrame: A DataFrame of all the outliers combined
        """

        # Grab the quartiles for this DataSource
        quartiles = data_source.quartiles()

        # For every column in the data_source that is numeric get the outliers
        log.info("Computing outliers for numeric columns (this may take a while)...")
        outlier_df_list = []
        numeric = ["tinyint", "smallint", "int", "bigint", "float", "double", "decimal"]
        for column, data_type in zip(data_source.column_names(), data_source.column_types()):
            print(column, data_type)
            if data_type in numeric:
                iqr = quartiles[column]["q3"] - quartiles[column]["q1"]

                # Catch cases where IQR is 0
                if iqr == 0:
                    log.info(f"IQR is 0 for column {column}, skipping...")
                    continue

                # Compute dataframes for the lower and upper bounds
                lower_bound = quartiles[column]["q1"] - (iqr * scale)
                upper_bound = quartiles[column]["q3"] + (iqr * scale)
                lower_df, upper_df = self._outlier_dfs(data_source, column, lower_bound, upper_bound)

                # If we have outliers, add them to the list
                for df in [lower_df, upper_df]:
                    if df is not None:
                        # Add the outlier_group identifier
                        df["outlier_group"] = self.outlier_group
                        self.outlier_group += 1

                        # Append the outlier DataFrame to the list
                        log.info(f"Found {len(df)} outliers for column {column}")
                        outlier_df_list.append(df)

        # Return the combined DataFrame
        return pd.concat(outlier_df_list) if outlier_df_list else None

    def _string_outliers(self, data_source: DataSourceAbstract) -> pd.DataFrame:
        """Internal method to compute outliers for all the string columns in a DataSource
        Args:
            data_source(DataSource): The DataSource that we're computing outliers on
        Returns:
            pd.DataFrame: A DataFrame of all the outliers combined
        """

        log.info("Computing outliers for string columns (this may take a while)...")
        outlier_df_list = []
        num_rows = data_source.details()["num_rows"]
        outlier_min_count = max(3, num_rows * 0.001)  # 0.1% of the total rows
        max_unique_values = 40  # 40 is the max number of value counts that are stored in AWS
        value_count_info = data_source.value_counts()
        for column, data_type in zip(data_source.column_names(), data_source.column_types()):
            print(column, data_type)
            # String columns will use the value counts to compute outliers
            if data_type == "string":
                # Skip columns with too many unique values
                if len(value_count_info[column]) >= max_unique_values:
                    log.warning(f"Skipping column {column} too many unique values")
                    continue
                for value, count in value_count_info[column].items():
                    if count < outlier_min_count:
                        log.info(f"Found outlier feature {value} for column {column}")
                        query = f"SELECT * from {data_source.table_name} where {column} = '{value}' limit 3"
                        print(query)
                        df = data_source.query(query)
                        df["outlier_group"] = self.outlier_group
                        self.outlier_group += 1
                        outlier_df_list.append(df)

        # Return the combined DataFrame
        return pd.concat(outlier_df_list) if outlier_df_list else None

    @staticmethod
    def _outlier_dfs(data_source: DataSourceAbstract, column: str, lower_bound: float, upper_bound: float):
        """Internal method to compute outliers for a numeric column
        Args:
            data_source(DataSource): The DataSource that we're computing outliers on
            column(str): The column to compute outliers on
            lower_bound(float): The lower bound for outliers
            upper_bound(float): The upper bound for outliers
        Returns:
            (pd.DataFrame, pd.DataFrame): A DataFrame for lower outliers and a DataFrame for upper outliers
        """

        # Get lower outlier bound
        query = f"SELECT * from {data_source.table_name} where {column} < {lower_bound} order by {column} limit 10"
        lower_df = data_source.query(query)

        # Check for no results
        if lower_df.shape[0] == 0:
            lower_df = None

        # Get upper outlier bound
        query = f"SELECT * from {data_source.table_name} where {column} > {upper_bound} order by {column} desc limit 10"
        upper_df = data_source.query(query)

        # Check for no results
        if upper_df.shape[0] == 0:
            upper_df = None

        # Return the lower and upper outlier DataFrames
        return lower_df, upper_df


if __name__ == "__main__":
    """Exercise the SQL Outliers Functionality"""
    from sageworks.artifacts.data_sources.data_source import DataSource

    # Setup Pandas output options
    pd.set_option("display.max_colwidth", 50)
    pd.set_option("display.max_columns", 15)
    pd.set_option("display.width", 1000)

    # Retrieve a Data Source
    my_data = DataSource("abalone_data")

    # Verify that the Athena Data Source exists
    assert my_data.exists()

    # Create the class and Compute outliers
    my_outliers = Outliers()
    my_outlier_df = my_outliers.compute_outliers(my_data, include_strings=True)
    print("\nOutliers")
    print(my_outlier_df)