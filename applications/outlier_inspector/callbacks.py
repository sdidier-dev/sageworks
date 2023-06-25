"""Callbacks for the FeatureSets Subpage Web User Interface"""
from datetime import datetime
import dash
from dash import Dash
from dash.dependencies import Input, Output

# SageWorks Imports
from sageworks.views.data_source_web_view import DataSourceWebView
from sageworks.web_components import (
    table,
    data_and_feature_details,
    distribution_plots,
    scatter_plot,
)


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
    )
    def data_sources_update(_n):
        """Return the table data as a dictionary"""
        data_source_broker.refresh()
        data_source_rows = data_source_broker.data_sources_summary()
        data_source_rows["id"] = data_source_rows.index
        return data_source_rows.to_dict("records")


# Highlights the selected row in the table
def table_row_select(app: Dash, table_name: str):
    @app.callback(
        Output(table_name, "style_data_conditional"),
        Input(table_name, "derived_viewport_selected_row_ids"),
    )
    def style_selected_rows(selected_rows):
        print(f"Selected Rows: {selected_rows}")
        if not selected_rows or selected_rows[0] is None:
            return dash.no_update
        row_style = [
            {
                "if": {"filter_query": "{{id}} ={}".format(i)},
                "backgroundColor": "rgb(80, 80, 80)",
            }
            for i in selected_rows
        ]
        return row_style


# Updates the data source details when a row is selected in the summary
def update_data_source_details(app: Dash, data_source_web_view: DataSourceWebView):
    @app.callback(
        [
            Output("data_source_details_header", "children"),
            Output("data_source_details", "children"),
        ],
        Input("data_sources_table", "derived_viewport_selected_row_ids"),
    )
    def generate_new_markdown(selected_rows):
        print(f"Selected Rows: {selected_rows}")
        if not selected_rows or selected_rows[0] is None:
            return dash.no_update
        print("Calling DataSource Details...")
        data_source_details = data_source_web_view.data_source_details(selected_rows[0])
        data_source_details_markdown = data_and_feature_details.create_markdown(
            data_source_details
        )

        # Name of the data source for the Header
        data_source_name = data_source_web_view.data_source_name(selected_rows[0])
        header = f"Details: {data_source_name}"

        # Return the details/markdown for these data details
        return [header, data_source_details_markdown]


def update_data_source_outlier_rows(app: Dash, data_source_web_view: DataSourceWebView):
    @app.callback(
        [
            Output("data_source_outlier_rows_header", "children"),
            Output("data_source_outlier_rows", "columns"),
            Output("data_source_outlier_rows", "data"),
        ],
        Input("data_sources_table", "derived_viewport_selected_row_ids"),
        prevent_initial_call=True,
    )
    def sample_rows_update(selected_rows):
        print(f"Selected Rows: {selected_rows}")
        if not selected_rows or selected_rows[0] is None:
            return dash.no_update
        print("Calling DataSource Sample Rows...")
        sample_rows = data_source_web_view.data_source_outliers(selected_rows[0])

        # Name of the data source
        data_source_name = data_source_web_view.data_source_name(selected_rows[0])
        header = f"Anomalous Rows: {data_source_name}"

        # The columns need to be in a special format for the DataTable
        column_setup_list = table.column_setup(sample_rows)

        # Return the columns and the data
        return [header, column_setup_list, sample_rows.to_dict("records")]


def update_cluster_plot(app: Dash, data_source_web_view: DataSourceWebView):
    """Updates the Cluster Plot when a new feature set is selected"""

    @app.callback(
        Output("outlier_scatter_plot", "figure"),
        Input("data_sources_table", "derived_viewport_selected_row_ids"),
        prevent_initial_call=True,
    )
    def generate_new_cluster_plot(selected_rows):
        print(f"Selected Rows: {selected_rows}")
        if not selected_rows or selected_rows[0] is None:
            return dash.no_update
        outlier_rows = data_source_web_view.data_source_outliers(selected_rows[0])
        return scatter_plot.create_figure(outlier_rows)


def update_violin_plots(app: Dash, data_source_web_view: DataSourceWebView):
    """Updates the Violin Plots when a new feature set is selected"""

    @app.callback(
        Output("data_source_violin_plot", "figure"),
        Input("data_sources_table", "derived_viewport_selected_row_ids"),
        prevent_initial_call=True,
    )
    def generate_new_violin_plot(selected_rows):
        print(f"Selected Rows: {selected_rows}")
        if not selected_rows or selected_rows[0] is None:
            return dash.no_update
        smart_sample_rows = data_source_web_view.data_source_smart_sample(
            selected_rows[0]
        )
        return distribution_plots.create_figure(
            smart_sample_rows,
            plot_type="violin",
            figure_args={
                "box_visible": True,
                "meanline_visible": True,
                "showlegend": False,
                "points": "all",
            },
            max_plots=48,
        )
