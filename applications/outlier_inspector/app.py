"""DataSources:  A SageWorks Web Interface to view, interact, and manage Data Sources"""
from dash import Dash
from dash_bootstrap_templates import load_figure_template
import dash_bootstrap_components as dbc

# SageWorks Imports
from sageworks.web_components import table, data_and_feature_details, vertical_distribution_plots, scatter_plot
from sageworks.views.data_source_web_view import DataSourceWebView

# Local Imports
from layout import data_sources_layout
import callbacks


# Create our Dash app
app = Dash(
    title="SageWorks: Anomaly Inspector",
    external_stylesheets=[dbc.themes.DARKLY],
)

# Okay feels a bit weird but Dash pages just have a bunch of top level code (no classes/methods)

# Put the components into 'dark' mode
load_figure_template("darkly")

# Grab a view that gives us a summary of the FeatureSets in SageWorks
data_source_broker = DataSourceWebView()
data_source_rows = data_source_broker.data_sources_summary()

# Create a table to display the data sources
data_sources_table = table.create(
    "data_sources_table",
    data_source_rows,
    header_color="rgb(100, 60, 60)",
    row_select="single",
    markdown_columns=["Name"],
)

# Data Source Details
details = data_source_broker.data_source_details(0)
data_details = data_and_feature_details.create("data_source_details", details)

# Grab anomalous rows from the first data source
anomalous_rows = data_source_broker.data_source_anomalies(0)
column_types = details["column_details"] if details is not None else None
data_source_anomalies_rows = table.create(
    "data_source_anomalies_rows",
    anomalous_rows,
    column_types=column_types,
    header_color="rgb(60, 60, 100)",
    max_height="400px",
)

# Create a box plot of all the numeric columns in the sample rows
smart_sample_rows = data_source_broker.data_source_smart_sample(0)
violin = vertical_distribution_plots.create("data_source_violin_plot",
                                    smart_sample_rows,
                                    plot_type="violin",
                                    figure_args={"box_visible": True, "meanline_visible": True, "showlegend": False, "points": "all"},
                                    max_plots=48)

# Create the anomaly cluster plot
cluster_plot = scatter_plot.create("anomaly_scatter_plot", anomalous_rows)

# Create our components
components = {
    "data_sources_table": data_sources_table,
    "data_source_anomalies_rows": data_source_anomalies_rows,
    "anomaly_scatter_plot": cluster_plot,
    "data_source_details": data_details,
    "violin_plot": violin,
}

# Set up our layout (Dash looks for a var called layout)
app.layout = data_sources_layout(**components)

# Refresh our data timer
callbacks.refresh_data_timer(app)

# Periodic update to the data sources summary table
callbacks.update_data_sources_table(app, data_source_broker)

# Callbacks for when a data source is selected
callbacks.table_row_select(app, "data_sources_table")
callbacks.update_data_source_details(app, data_source_broker)
callbacks.update_data_source_anomaly_rows(app, data_source_broker)
callbacks.update_cluster_plot(app, data_source_broker)
callbacks.update_violin_plots(app, data_source_broker)

if __name__ == "__main__":
    """Run our web application in TEST mode"""
    # Note: This 'main' is purely for running/testing locally
    # app.run_server(host="0.0.0.0", port=8080, debug=True)
    app.run_server(host="0.0.0.0", port=8080, debug=True)