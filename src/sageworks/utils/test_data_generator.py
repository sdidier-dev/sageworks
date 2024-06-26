"""A Test Data Generator Class"""

import logging
import pandas as pd
import numpy as np
from sklearn.datasets import make_classification, make_regression


class TestDataGenerator:
    """A Test Data Generator Class
    Usage:
         test_data = TestDataGenerator()
         df = test_data.generate(columns=10, rows=100)
    """

    def __init__(self):
        """TestDataGenerator Initialization"""
        self.log = logging.getLogger("sageworks")

    def ml_data(self, n_samples: int = 1000, n_features: int = 4, target_type: str = "regression") -> pd.DataFrame:
        """Generate a Pandas DataFrame with random data

        Args:
            n_samples: number of samples (default: 1000)
            n_features: number of features (default: 4)
            target_type: type of target regression or classification (default: regression)

        Returns:
            pd.DataFrame: DataFrame with random data
        """
        if target_type == "regression":
            X, y = make_regression(n_samples=n_samples, n_features=n_features, n_informative=n_features - 2)
        elif target_type == "classification":
            X, y = make_classification(n_samples=n_samples, n_features=n_features, n_informative=n_features - 2)
        else:
            self.log.critical(f"Unknown target_type: {target_type}")
            raise ValueError(f"Unknown target_type: {target_type}")

        # Convert the data to a Pandas DataFrame
        df = pd.DataFrame(X)
        df["target"] = y
        return df

    @staticmethod
    def regression_with_varying_noise(n_samples: int = 1000, n_features: int = 4) -> pd.DataFrame:
        """Generate a Pandas DataFrame with regression data and varying noise

        Args:
            n_samples: number of samples (default: 1000)
            n_features: number of features (default: 4)

        Returns:
            pd.DataFrame: DataFrame with regression data and varying noise
        """

        # Generate a simple regression dataset with one feature and one target
        # Both the feature and the target vary from 0 to 100, the target is the feature plus 10% noise
        feature = np.float32(range(0, 1000))
        target = [x + 1000.0 + x * np.random.uniform(-0.1, 0.1) for x in feature]

        # Create a DataFrame
        df = pd.DataFrame({"feature": feature, "target": target})
        return df

        """
        # Generate basic synthetic data
        X, y = make_regression(n_samples=n_samples, n_features=n_features, n_informative=n_features,
                               noise=0.0, random_state=42)

        # Normalize target values to the range [0, 100]
        y = (y - y.min()) / (y.max() - y.min()) * 100


        # Introduce varying noise
        def add_varying_noise(y, max_noise_percentage=0.5):
            noise_level = (max_noise_percentage / 100) * y  # noise is a percentage of the target value
            noisy_y = y + noise_level * np.random.randn(len(y))
            return noisy_y

        # Apply varying noise to the target values
        y_noisy = add_varying_noise(y, max_noise_percentage=50.0)

        # Create a DataFrame
        feature_columns = [f'feature_{i + 1}' for i in range(n_features)]
        df = pd.DataFrame(X, columns=feature_columns)
        df['target'] = y

        # Return the DataFrame
        return df
        """

    def person_data(self, rows: int = 100) -> pd.DataFrame:
        """Generate a Pandas DataFrame of Person Data
        Args:
            rows(int): number of rows (default: 100)
        Returns:
            pd.DataFrame: DataFrame of Person Data
        """
        df = pd.DataFrame()
        df["Id"] = range(1, rows + 1)
        df["Name"] = ["Person " + str(i) for i in range(1, rows + 1)]

        # Height will be normally distributed with mean 68 and std 4
        df["Height"] = np.random.normal(68, 4, rows)

        # Weight is loosely correlated with height
        df["Weight"] = self.generate_correlated_series(df["Height"], 0.2, 100, 300)

        # Salary ranges from 80k to 200k and is correlated with height
        df["Salary"] = self.generate_correlated_series(df["Height"], 0.95, 80000, 200000)

        # Create a few salary outliers
        # Select 4 highest salaries and set them to a random value between 200k and 230k
        salary_outliers = df.sort_values("Salary", ascending=False)[:4]
        df.loc[salary_outliers.index, "Salary"] = np.random.randint(200000, 230000, len(salary_outliers))

        # Age is loosely correlated with salary
        df["Age"] = self.generate_correlated_series(df["Salary"], 0.5, 20, 80)

        # IQ Scores range from 100 to 150 and are negatively correlated with salary :)
        df["IQ_Score"] = self.generate_correlated_series(df["Salary"], -0.6, 100, 150)

        # Food will be correlated with salary
        food_list = "pizza, tacos, steak, sushi".split(", ")
        df["Food"] = self.generate_correlated_series(df["Salary"], 0.8, -1.5, 4.4)

        # Round to nearest integer
        df["Food"] = df["Food"].round().astype(int).clip(0, len(food_list) - 1)

        # Convert integers to food strings
        df["Food"] = df["Food"].apply(lambda x: food_list[x])

        # Randomly apply some NaNs to the Food column
        df["Food"] = df["Food"].apply(lambda x: np.nan if np.random.random() < 0.1 else x)

        # Boolean column for liking dogs (correlated to IQ)
        df["Likes_Dogs"] = self.generate_correlated_series(df["IQ_Score"], 0.75, -0.5, 1.5)
        df["Likes_Dogs"] = df["Likes_Dogs"].round().astype(int).clip(0, 1)
        df["Likes_Dogs"] = df["Likes_Dogs"].apply(lambda x: True if x == 1 else False)

        # Date is a random date between 1/1/2022 and 12/31/2022
        df["Date"] = pd.date_range(start="1/1/2022", end="12/31/2022", periods=rows, tz="US/Mountain")

        # Get less bloated types for the columns
        df = df.astype(
            {
                "Id": "int32",
                "Age": "int32",
                "Height": "float32",
                "Weight": "float32",
                "Salary": "float32",
                "IQ_Score": "float32",
                "Likes_Dogs": "boolean",
            }
        )

        # Return the DataFrame
        return df

    @staticmethod
    def pearson_correlation(x: pd.Series, y: pd.Series) -> float:
        """Calculate Pearson's correlation coefficient between two series.
        Args:
            x(pd.Series): First series.
            y(pd.Series): Second series.
        Returns:
            float: Pearson's correlation coefficient.
        """
        return np.corrcoef(x, y)[0, 1]

    @staticmethod
    def generate_correlated_series(series: pd.Series, target_corr: float, min_val: float, max_val: float) -> pd.Series:
        """Generates a new Pandas Series that has a Pearson's correlation close to the desired
           value with the original Series.
        Args:
            series(pd.Series): Original Pandas Series.
            target_corr(float): Target correlation value (between -1 and 1).
            min_val(float): Minimum value for the new Series.
            max_val(float): Maximum value for the new Series.
        Returns:
            pd.Series: New Pandas Series correlated with the original Series.
        """

        # Fudging with the target correlation to make it work better
        target_corr = target_corr * 0.8

        # Random noise with normal distribution, with mean and std of series
        random_noise = np.random.normal(loc=np.mean(series), scale=np.std(series), size=series.size)

        # Create an array with a target correlation to the series
        correlated_series = target_corr * series + (1 - abs(target_corr)) * random_noise

        # Rescale the correlated series to be within the min-max range
        min_orig = np.min(correlated_series)
        max_orig = np.max(correlated_series)
        scaled_series = min_val + (correlated_series - min_orig) * (max_val - min_val) / (max_orig - min_orig)

        return pd.Series(scaled_series)


if __name__ == "__main__":
    """Exercise the TestDataGenerator class"""

    # Create a TestDataGenerator
    test_data = TestDataGenerator()
    df = test_data.ml_data(10, 100, "regression")
    print(df.head())

    df = test_data.ml_data(10, 100, "classification")
    print(df.head())

    df = test_data.regression_with_varying_noise(100, 4)
    print(df.head())

    df = test_data.person_data(100)
    print(df.head())
