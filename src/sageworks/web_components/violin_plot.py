"""A Violin Plot component"""
import plotly.graph_objs
from dash import dcc
import pandas as pd
import math
from plotly.subplots import make_subplots
import plotly.graph_objects as go


def compute_rows_columns(num_plots):
    """Errr... I think this works but happy to be improved"""
    max_columns = 8
    overflow = 1 if num_plots % max_columns != 0 else 0
    num_rows = num_plots // max_columns + overflow
    num_columns = round(num_plots / num_rows + 0.1)
    return num_rows, num_columns

def calculate_height(num_rows):
    # Set the base height and minimum height
    base_height = 300
    min_height = 150

    if num_rows == 1:
        return base_height
    # Calculate the logarithmic height based on the number of rows
    height = base_height - (math.log(num_rows + 1) * 50)
    height = max(height, min_height)  # Ensure the height doesn't go below the minimum height

    return height

# For colormaps see (https://plotly.com/python/discrete-color/#color-sequences-in-plotly-express)
def create_figure(df: pd.DataFrame) -> plotly.graph_objs.Figure:
    """Create a set of Violin Plots for the numeric columns in the dataframe"""

    # Sanity check the dataframe
    if df is None or df.empty or list(df.columns) == ["uuid", "status"]:
        return go.Figure()

    numeric_columns = list(df.select_dtypes("number").columns)
    numeric_columns = [col for col in numeric_columns if len(df[col].unique()) > 1]  # Only columns > 1 unique value
    numeric_columns = [col for col in numeric_columns if col not in ["id", "Id", "ID", "Id_"]]  # Remove id columns
    numeric_columns = numeric_columns[:48]  # Max 48 plots

    # Compute the number of rows and columns
    num_plots = len(numeric_columns)
    num_rows, num_columns = compute_rows_columns(num_plots)
    print(f"Creating {num_plots} violin plots in {num_rows} rows and {num_columns} columns")
    fig = make_subplots(rows=num_rows, cols=num_columns)
    for i, var in enumerate(numeric_columns):
        fig.add_trace(
            go.Violin(y=df[var], name=var, box_visible=True, meanline_visible=True, showlegend=False, points="all"),
            row=i // num_columns + 1,
            col=i % num_columns + 1,
        )
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    fig.update_layout(height=(calculate_height(num_rows)))
    return fig


def create(component_id: str, df: pd.DataFrame) -> dcc.Graph:
    """Create a Violin Plot Graph Component
    Args:
        component_id (str): The ID of the UI component
        df (pd.DataFrame): A dataframe of data
    Returns:
        dcc.Graph: A Dash Graph Component
    """

    # Generate a figure and wrap it in a Dash Graph Component
    return dcc.Graph(id=component_id, figure=create_figure(df))
