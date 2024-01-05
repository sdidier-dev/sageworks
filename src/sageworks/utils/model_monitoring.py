"""ModelMonitoring class for monitoring SageMaker endpoints"""
import logging
import json
from io import StringIO
import pandas as pd
from sagemaker import Predictor
from sagemaker.model_monitor import (
    CronExpressionGenerator,
    DataCaptureConfig,
    DefaultModelMonitor,
    DatasetFormat,
)
import awswrangler as wr

# SageWorks Imports
from sageworks.core.artifacts.endpoint_core import EndpointCore
from sageworks.aws_service_broker.aws_account_clamp import AWSAccountClamp
from sageworks.utils.s3_utils import read_s3_file
from sageworks.utils import endpoint_utils


class ModelMonitoring:
    def __init__(self, endpoint_name, instance_type="ml.t3.large"):
        """ExtractModelArtifact Class
        Args:
            endpoint_name (str): Name of the endpoint to set up monitoring for
            instance_type (str): Instance type to use for monitoring. Defaults to "ml.t3.large".
                                 Other options: ml.m5.large, ml.m5.xlarge, ml.m5.2xlarge, ml.m5.4xlarge, ...
        """
        self.log = logging.getLogger("sageworks")
        self.endpoint_name = endpoint_name
        self.endpoint = EndpointCore(self.endpoint_name)

        # Initialize Class Attributes
        self.sagemaker_session = self.endpoint.sm_session
        self.sagemaker_client = self.endpoint.sm_client
        self.data_capture_path = self.endpoint.endpoint_data_capture_path
        self.monitoring_path = self.endpoint.endpoint_monitoring_path
        self.instance_type = instance_type
        self.monitoring_schedule_name = f"{self.endpoint_name}-monitoring-schedule"
        self.monitoring_output_path = f"{self.monitoring_path}/monitoring_reports"
        self.baseline_dir = f"{self.monitoring_path}/baseline"
        self.baseline_csv_file = f"{self.baseline_dir}/baseline.csv"
        self.constraints_json_file = f"{self.baseline_dir}/constraints.json"
        self.statistics_json_file = f"{self.baseline_dir}/statistics.json"

        # Initialize the DefaultModelMonitor
        self.sageworks_role = AWSAccountClamp().sageworks_execution_role_arn()
        self.model_monitor = DefaultModelMonitor(role=self.sageworks_role, instance_type=self.instance_type)

    def add_data_capture(self, capture_percentage=100):
        """
        Add data capture configuration for the SageMaker endpoint.

        Args:
            capture_percentage (int): Percentage of data to capture. Defaults to 100.
        """

        # Check if this endpoint is a serverless endpoint
        if self.endpoint.is_serverless():
            self.log.warning("Data capture is not currently supported for serverless endpoints.")
            return

        # Check if the endpoint already has data capture configured
        if self.is_data_capture_configured(capture_percentage):
            self.log.important(f"Data capture {capture_percentage} already configured for {self.endpoint_name}.")
            return

        # Get the current endpoint configuration name
        current_endpoint_config_name = self.endpoint.endpoint_config_name()

        # Log the data capture path
        self.log.important(f"Adding Data Capture to {self.endpoint_name} --> {self.data_capture_path}")
        self.log.important("This normally redeploys the endpoint...")

        # Setup data capture config
        data_capture_config = DataCaptureConfig(
            enable_capture=True,
            sampling_percentage=capture_percentage,
            destination_s3_uri=self.data_capture_path,
            capture_options=["Input", "Output"],
            csv_content_types=["text/csv"],
        )

        # Create a Predictor instance and update data capture configuration
        predictor = Predictor(self.endpoint_name, sagemaker_session=self.sagemaker_session)
        predictor.update_data_capture_config(data_capture_config=data_capture_config)

        # Delete the old endpoint configuration
        self.log.important(f"Deleting old endpoint configuration: {current_endpoint_config_name}")
        self.sagemaker_client.delete_endpoint_config(EndpointConfigName=current_endpoint_config_name)

    def is_data_capture_configured(self, capture_percentage):
        """
        Check if data capture is already configured on the endpoint.
        Args:
            capture_percentage (int): Expected data capture percentage.
        Returns:
            bool: True if data capture is already configured, False otherwise.
        """
        try:
            endpoint_config_name = self.endpoint.endpoint_config_name()
            endpoint_config = self.sagemaker_client.describe_endpoint_config(EndpointConfigName=endpoint_config_name)
            data_capture_config = endpoint_config.get("DataCaptureConfig", {})

            # Check if data capture is enabled and the percentage matches
            is_enabled = data_capture_config.get("EnableCapture", False)
            current_percentage = data_capture_config.get("InitialSamplingPercentage", 0)
            return is_enabled and current_percentage == capture_percentage
        except Exception as e:
            self.log.error(f"Error checking data capture configuration: {e}")
            return False

    def get_latest_data_capture(self) -> (pd.DataFrame, pd.DataFrame):
        """
        Get the latest data capture from S3.

        Returns:
            DataFrame (input), DataFrame(output): Flattened and processed DataFrames for input and output data.
        """
        # List files in the specified S3 path
        files = wr.s3.list_objects(self.data_capture_path)

        if files:
            print(f"Found {len(files)} files in {self.data_capture_path}. Reading the most recent file.")

            # Read the most recent file into a DataFrame
            df = wr.s3.read_json(path=files[-1], lines=True)  # Reads the last file assuming it's the most recent one

            # Process the captured data and return the input and output DataFrames
            return self.process_captured_data(df)
        else:
            print(f"No data capture files found in {self.data_capture_path}.")
            return None, None

    @staticmethod
    def process_captured_data(df: pd.DataFrame) -> (pd.DataFrame, pd.DataFrame):
        """
        Process the captured data DataFrame to extract and flatten the nested data.

        Args:
            df (DataFrame): DataFrame with captured data.

        Returns:
            DataFrame (input), DataFrame(output): Flattened and processed DataFrames for input and output data.
        """
        processed_records = []

        # Phase1: Process the AWS Data Capture format into a flatter DataFrame
        for _, row in df.iterrows():
            # Extract data from captureData dictionary
            capture_data = row["captureData"]
            input_data = capture_data["endpointInput"]
            output_data = capture_data["endpointOutput"]

            # Process input and output, both meta and actual data
            record = {
                "input_content_type": input_data.get("observedContentType"),
                "input_encoding": input_data.get("encoding"),
                "input": input_data.get("data"),
                "output_content_type": output_data.get("observedContentType"),
                "output_encoding": output_data.get("encoding"),
                "output": output_data.get("data"),
            }
            processed_records.append(record)
        processed_df = pd.DataFrame(processed_records)

        # Phase2: Process the input and output 'data' columns into separate DataFrames
        input_df_list = []
        output_df_list = []
        for _, row in processed_df.iterrows():
            input_df = pd.read_csv(StringIO(row["input"]))
            input_df_list.append(input_df)
            output_df = pd.read_csv(StringIO(row["output"]))
            output_df_list.append(output_df)

        # Return the input and output DataFrames
        return pd.concat(input_df_list), pd.concat(output_df_list)

    def baseline_exists(self) -> bool:
        """
        Check if baseline files exist in S3.

        Returns:
            bool: True if all files exist, False otherwise.
        """

        files = [self.baseline_csv_file, self.constraints_json_file, self.statistics_json_file]
        return all(wr.s3.does_object_exist(file) for file in files)

    def create_baseline(self, recreate: bool = False):
        """Code to create a baseline for monitoring
        Args:
            recreate (bool): If True, recreate the baseline even if it already exists
        Notes:
            This will create/write three files to the baseline_dir:
            - baseline.csv
            - constraints.json
            - statistics.json
        """
        if not self.baseline_exists() or recreate:
            # Create a baseline for monitoring (training data from the FeatureSet)
            baseline_df = endpoint_utils.fs_training_data(self.endpoint)
            wr.s3.to_csv(baseline_df, self.baseline_csv_file, index=False)

            self.log.important(f"Creating baseline files for {self.endpoint_name} --> {self.baseline_dir}")
            self.model_monitor.suggest_baseline(
                baseline_dataset=self.baseline_csv_file,
                dataset_format=DatasetFormat.csv(header=True),
                output_s3_uri=self.baseline_dir,
            )
        else:
            self.log.important(f"Baseline already exists for {self.endpoint_name}")

    def get_baseline(self) -> pd.DataFrame:
        """Code to get the baseline CSV from the S3 baseline directory

        Returns:
            pd.DataFrame: The baseline CSV from the baseline (baseline.csv)
        """
        # Read the monitoring data from S3
        if not wr.s3.does_object_exist(path=self.baseline_csv_file):
            self.log.warning("baseline.csv data does not exist in S3.")
        else:
            return wr.s3.read_csv(self.baseline_csv_file)

    def get_constraints(self) -> pd.DataFrame:
        """Code to get the constraints from the baseline

        Returns:
            pd.DataFrame: The constraints from the baseline (constraints.json)
        """
        return self._get_monitor_json_data(self.constraints_json_file)

    def get_statistics(self) -> pd.DataFrame:
        """Code to get the statistics from the baseline

        Returns:
            pd.DataFrame: The statistics from the baseline (statistics.json)
        """
        return self._get_monitor_json_data(self.statistics_json_file)

    def _get_monitor_json_data(self, s3_path: str) -> pd.DataFrame:
        """Internal: Convert the JSON monitoring data into a DataFrame
        Args:
            s3_path(str): The S3 path to the monitoring data
        Returns:
            pd.DataFrame: Monitoring data in DataFrame form
        """
        # Read the monitoring data from S3
        if not wr.s3.does_object_exist(path=s3_path):
            self.log.warning("Monitoring data does not exist in S3.")
        else:
            raw_json = read_s3_file(s3_path=s3_path)
            monitoring_data = json.loads(raw_json)
            monitoring_df = pd.json_normalize(monitoring_data["features"])
            return monitoring_df

    def setup_monitoring_schedule(self, schedule: str = "hourly", recreate: bool = False):
        """
        Sets up the monitoring schedule for the model endpoint.
        Args:
            schedule (str): The schedule for the monitoring job (hourly or daily, defaults to hourly).
            recreate (bool): If True, recreate the monitoring schedule even if it already exists.
        """

        # Set up the monitoring schedule, name, and output path
        if schedule == "daily":
            schedule = CronExpressionGenerator.daily()
        else:
            schedule = CronExpressionGenerator.hourly()

        # Check if the baseline exists
        if not self.baseline_exists():
            self.log.warning(f"Baseline does not exist for {self.endpoint_name}. Call create_baseline() first...")
            return

        # Check if monitoring schedule already exists
        if self.monitoring_schedule_exists() and not recreate:
            return

        # Setup monitoring schedule
        self.model_monitor.create_monitoring_schedule(
            monitor_schedule_name=self.monitoring_schedule_name,
            endpoint_input=self.endpoint_name,
            output_s3_uri=self.monitoring_output_path,
            statistics=self.statistics_json_file,
            constraints=self.constraints_json_file,
            schedule_cron_expression=schedule,
        )
        self.log.important(f"Monitoring schedule created for {self.endpoint_name}.")

    def setup_alerts(self):
        """Code to set up alerts based on monitoring results"""
        pass

    def monitoring_schedule_exists(self):
        """Code to get the status of the monitoring schedule"""
        existing_schedules = self.sagemaker_client.list_monitoring_schedules(MaxResults=100).get(
            "MonitoringScheduleSummaries", []
        )
        if any(schedule["MonitoringScheduleName"] == self.monitoring_schedule_name for schedule in existing_schedules):
            self.log.info(f"Monitoring schedule already exists for {self.endpoint_name}.")
            return True
        else:
            self.log.info(f"Could not find a Monitoring schedule for {self.endpoint_name}.")
            return False


if __name__ == "__main__":
    """Exercise the ModelMonitoring class"""

    # Set options for actually seeing the dataframe
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)

    # Create the Class and test it out
    endpoint_name = "abalone-regression-end-rt"
    my_endpoint = EndpointCore(endpoint_name)
    if not my_endpoint.exists():
        print(f"Endpoint {endpoint_name} does not exist.")
        exit(1)
    mm = ModelMonitoring(endpoint_name)
    mm.add_data_capture()

    # Create a baseline for monitoring
    mm.create_baseline()

    # Check the baseline outputs
    base_df = mm.get_baseline()
    print(base_df.head())
    constraints_df = mm.get_constraints()
    print(constraints_df.head())
    statistics_df = mm.get_statistics()
    print(statistics_df.head())

    # Set up the monitoring schedule (if it doesn't already exist)
    mm.setup_monitoring_schedule()

    #
    # Test the data capture by running some predictions
    #

    # Make predictions on the Endpoint
    pred_df = endpoint_utils.fs_predictions(my_endpoint)
    print(pred_df.head())

    # Check that data capture is working
    input_df, output_df = mm.get_latest_data_capture()
    if input_df is None:
        print("No data capture files found, for a new endpoint it may take a few minutes to start capturing data")
    else:
        print("Found data capture files")
        print("Input")
        print(input_df.head())
        print("Output")
        print(output_df.head())
