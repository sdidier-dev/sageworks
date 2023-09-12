"""FeatureSets Callbacks: Callback within the DataSources Web User Interface"""
from datetime import datetime
import dash
from dash import Dash
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd

# SageWorks Imports
from sageworks.views.data_source_web_view import DataSourceWebView
from sageworks.web_components import table, data_details_markdown, distribution_plots, heatmap
from sageworks.utils.pandas_utils import corr_df_from_artifact_info

# Cheese Sauce (FIXME: TDB)
smart_sample_rows = None


def refresh_data_timer(app: Dash):
    @app.callback(
        Output("last-updated-data-sources", "children"),
        Input("data-sources-updater", "n_intervals"),
    )
    def time_updated(_n):
        return datetime.now().strftime("Last Updated: %Y-%m-%d %H:%M:%S")


def update_data_sources_table(app: Dash, data_source_broker: DataSourceWebView):
    @app.callback(
        Output("data_sources_table", "data"),
        Input("data-sources-updater", "n_intervals"),
        prevent_initial_call=True,
    )
    def data_sources_update(_n):
        """Return the table data as a dictionary"""
        data_source_broker.refresh()
        data_source_rows = data_source_broker.data_sources_summary()
        data_source_rows["id"] = range(len(data_source_rows))
        return data_source_rows.to_dict("records")


# Highlights the selected row in the table
def table_row_select(app: Dash, table_name: str):
    @app.callback(
        Output(table_name, "style_data_conditional"),
        Input(table_name, "derived_viewport_selected_row_ids"),
        prevent_initial_call=True,
    )
    def style_selected_rows(selected_rows):
        print(f"Highlight Selected Rows: {selected_rows}")
        if not selected_rows or selected_rows[0] is None:
            return dash.no_update
        row_style = [
            {
                "if": {"filter_query": "{{id}}={}".format(i)},
                "backgroundColor": "rgb(80, 80, 80)",
            }
            for i in selected_rows
        ]
        return row_style


# Updates the data source details when a new DataSource is selected
def update_data_source_details(app: Dash, data_source_web_view: DataSourceWebView):
    @app.callback(
        [
            Output("data_details_header", "children"),
            Output("data_source_details", "children"),
        ],
        Input("data_sources_table", "derived_viewport_selected_row_ids"),
        prevent_initial_call=True,
    )
    def generate_new_markdown(selected_rows):
        print(f"Data Source Details Selected Rows: {selected_rows}")
        if not selected_rows or selected_rows[0] is None:
            return dash.no_update
        print("Calling DataSource Details...")
        data_details = data_source_web_view.data_source_details(selected_rows[0])
        details_markdown = data_details_markdown.create_markdown(data_details)

        # Name of the data source for the Header
        data_source_name = data_source_web_view.data_source_name(selected_rows[0])
        header = f"Details: {data_source_name}"

        # Return the details/markdown for these data details
        return [header, details_markdown]


def update_data_source_sample_rows(app: Dash, data_source_web_view: DataSourceWebView):
    @app.callback(
        [
            Output("sample_rows_header", "children"),
            Output("data_source_sample_rows", "columns"),
            Output("data_source_sample_rows", "style_data_conditional"),
            Output("data_source_sample_rows", "data", allow_duplicate=True),
        ],
        Input("data_sources_table", "derived_viewport_selected_row_ids"),
        prevent_initial_call=True,
    )
    def sample_rows_update(selected_rows, color_column="outlier_group"):
        global smart_sample_rows
        print(f"Sample Rows Selected Rows: {selected_rows}")
        if not selected_rows or selected_rows[0] is None:
            return dash.no_update
        print("Calling DataSource Sample Rows...")
        smart_sample_rows = data_source_web_view.data_source_smart_sample(selected_rows[0])

        # Name of the data source
        data_source_name = data_source_web_view.data_source_name(selected_rows[0])
        header = f"Sample/Outlier Rows: {data_source_name}"

        # The columns need to be in a special format for the DataTable
        column_setup_list = table.column_setup(smart_sample_rows)

        # We need to update our style_data_conditional to color the outlier groups
        if color_column not in smart_sample_rows.columns:
            style_cells = table.style_data_conditional()
        else:
            unique_categories = smart_sample_rows[color_column].unique().tolist()
            unique_categories = [x for x in unique_categories if x != "sample"]
            style_cells = table.style_data_conditional(color_column, unique_categories)

        # Return the header, columns, style_cell, and the data
        return [header, column_setup_list, style_cells, smart_sample_rows.to_dict("records")]


def update_violin_plots(app: Dash, data_source_web_view: DataSourceWebView):
    """Updates the Violin Plots when a new data source is selected"""

    @app.callback(
        Output("data_source_violin_plot", "figure", allow_duplicate=True),
        Input("data_sources_table", "derived_viewport_selected_row_ids"),
        prevent_initial_call=True,
    )
    def generate_new_violin_plot(selected_rows):
        print(f"Violin Plot Selected Rows: {selected_rows}")
        if not selected_rows or selected_rows[0] is None or smart_sample_rows is None:
            return dash.no_update

        # Get the data source smart sample rows and create the violin plot
        return distribution_plots.create_figure(
            smart_sample_rows,
            plot_type="violin",
            figure_args={
                "box_visible": True,
                "meanline_visible": True,
                "showlegend": False,
                "points": "all",
                "spanmode": "hard",
            },
            max_plots=48,
        )


# Updates the correlation matrix when a new DataSource is selected
def update_correlation_matrix(app: Dash, data_source_web_view: DataSourceWebView):
    @app.callback(
        Output("correlation_matrix", "figure", allow_duplicate=True),
        Input("data_sources_table", "derived_viewport_selected_row_ids"),
        prevent_initial_call=True,
    )
    def generate_new_corr_matrix(selected_rows):
        print(f"Corr Matrix Selected Rows: {selected_rows}")
        if not selected_rows or selected_rows[0] is None:
            return dash.no_update

        # Get the data source smart sample rows and create the correlation matrix
        artifact_info = data_source_web_view.data_source_details(selected_rows[0])

        # Convert the data details to a pandas dataframe
        corr_df = corr_df_from_artifact_info(artifact_info)
        return heatmap.create_figure(corr_df)


#
# The following callbacks are for selections
#


def violin_plot_selection(app: Dash):
    """A selection has occurred on the Violin Plots so highlight the selected points on the plot,
    and send the updated figure to the client"""

    @app.callback(
        Output("data_source_violin_plot", "figure", allow_duplicate=True),
        Input("data_source_violin_plot", "selectedData"),
        State("data_source_violin_plot", "figure"),
        prevent_initial_call=True,
    )
    def update_figure(selected_data, current_figure):
        # Get the selected indices
        if selected_data is None:
            selected_indices = []
        else:
            selected_indices = [point["pointIndex"] for point in selected_data["points"]]
        print("Selected Indices")
        print(selected_indices)

        # Create a figure object so that we can use nice methods like update_traces
        figure = go.Figure(current_figure)

        # Update the selected points
        figure.update_traces(selectedpoints=selected_indices, selector=dict(type="violin"))
        return figure


def get_selection_indices(click_data, df: pd.DataFrame):
    """Get the selection indices from the columns clicked on in the correlation matrix"""

    # First lets get the column names and the correlation
    first_column = click_data["points"][0]["y"].split(":")[0]
    second_column = click_data["points"][0]["x"].split(":")[0]
    correlation = click_data["points"][0]["z"]
    print(f"First Column: {first_column}")
    print(f"Second Column: {second_column}")
    print(f"Correlation: {correlation}")

    # Now grab the indexes for the top 10 value from the first column
    selection_indices = set(df[first_column].nlargest(10).index.tolist())

    # If the correlation is positive, then grab the top 10 values from the
    # second column otherwise grab the bottom 10 values
    if correlation > 0:
        selection_indices = selection_indices.union(set(df[second_column].nlargest(10).index.tolist()))
    elif correlation == 0:
        selection_indices = []
    else:
        selection_indices = selection_indices.union(set(df[second_column].nsmallest(10).index.tolist()))

    # Return the selected indices
    return list(selection_indices)


def select_row_column(figure, click_data):
    """Select a row and column in the correlation matrix based on click data and the dataframe"""

    # Get the columns index from the click_data
    first_column_index = int(click_data["points"][0]["x"].split(":")[1])
    second_column_index = int(click_data["points"][0]["y"].split(":")[1])
    print(f"First Column Index: {first_column_index}")
    print(f"Second Column Index: {second_column_index}")

    # Clear any existing shapes (highlights)
    figure["layout"]["shapes"] = ()

    # Add a rectangle shape to outline the cell
    figure.add_shape(
        type="rect",
        xref="x",
        yref="y",
        x0=first_column_index - 0.5,
        y0=second_column_index - 0.5,
        x1=first_column_index + 0.5,
        y1=second_column_index + 0.5,
        line=dict(color="White"),
    )


def correlation_matrix_selection(app: Dash):
    """A selection has occurred on the Correlation Matrix so highlight the selected box, and also update
    the selections in the violin plot"""

    @app.callback(
        [
            Output("correlation_matrix", "figure", allow_duplicate=True),
            Output("data_source_violin_plot", "figure", allow_duplicate=True),
        ],
        Input("correlation_matrix", "clickData"),
        State("correlation_matrix", "figure"),
        State("data_source_violin_plot", "figure"),
        State("data_source_sample_rows", "data"),
        prevent_initial_call=True,
    )
    def update_figure(click_data, corr_figure, violin_figure, sample_rows):
        # Convert the sample rows to a DataFrame
        sample_rows = pd.DataFrame(sample_rows)

        # Create a selection box in the correlation matrix
        corr_figure = go.Figure(corr_figure)

        # Add a rectangle shape to outline the cell
        select_row_column(corr_figure, click_data)

        # Update the selected points in the violin figure
        if click_data:
            selected_indices = get_selection_indices(click_data, sample_rows)
        else:
            selected_indices = []
        violin_figure = go.Figure(violin_figure)
        violin_figure.update_traces(selectedpoints=selected_indices, selector=dict(type="violin"))
        return [corr_figure, violin_figure]


def reorder_sample_rows(app: Dash):
    """A selection has occurred on the Violin Plots so highlight the selected points on the plot,
    regenerate the figure"""

    @app.callback(
        Output("data_source_sample_rows", "data", allow_duplicate=True),
        Input("data_source_violin_plot", "selectedData"),
        prevent_initial_call=True,
    )
    def reorder_table(selected_data):
        # Convert the current table data back to a DataFrame

        # Get the selected indices from your plot selection
        if not selected_data or smart_sample_rows is None:
            return dash.no_update
        selected_indices = [point["pointIndex"] for point in selected_data["points"]]

        # Separate the selected rows and the rest of the rows
        selected_rows = smart_sample_rows.iloc[selected_indices]
        rest_of_rows = smart_sample_rows.drop(selected_indices)

        # Concatenate them to put the selected rows at the top
        new_df = pd.concat([selected_rows, rest_of_rows], ignore_index=True)

        # Return the new DataFrame as a dictionary
        return new_df.to_dict("records")
