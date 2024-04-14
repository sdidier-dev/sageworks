"""Callbacks for the Model Subpage Web User Interface"""

import logging
from dash import Dash, no_update
from dash.dependencies import Input, Output, State

# SageWorks Imports
from sageworks.web_components import table, model_plot, plugin_callbacks
from sageworks.utils.pandas_utils import deserialize_aws_broker_data
from sageworks.api.model import Model

# Get the SageWorks logger
log = logging.getLogger("sageworks")


def update_models_table(app: Dash):
    @app.callback(
        [Output("models_table", "columns"), Output("models_table", "data")],
        Input("aws-broker-data", "data"),
    )
    def models_update(serialized_aws_broker_data):
        """Return the table data for the Models Table"""
        aws_broker_data = deserialize_aws_broker_data(serialized_aws_broker_data)
        models = aws_broker_data["MODELS"]
        models["id"] = range(len(models))
        column_setup_list = table.Table().column_setup(models, markdown_columns=["Model Group"])
        return [column_setup_list, models.to_dict("records")]


# Highlights the selected row in the table
def table_row_select(app: Dash, table_name: str):
    @app.callback(
        Output(table_name, "style_data_conditional"),
        Input(table_name, "derived_viewport_selected_row_ids"),
        prevent_initial_call=True,
    )
    def style_selected_rows(selected_rows):
        if not selected_rows or selected_rows[0] is None:
            return no_update
        row_style = [
            {
                "if": {"filter_query": "{{id}}={}".format(i)},
                "backgroundColor": "rgb(80, 80, 80)",
            }
            for i in selected_rows
        ]
        # Style for symbols
        symbol_style = {"if": {"column_id": "Health"}, "fontSize": 16, "textAlign": "left"}

        # Append the symbol style to the row style
        row_style.append(symbol_style)
        return row_style


# Updates the model plot when a model row is selected
def update_model_plot_component(app: Dash):
    @app.callback(
        Output("model_plot", "figure"),
        Input("model_details-dropdown", "value"),
        [State("models_table", "data"), State("models_table", "derived_viewport_selected_row_ids")],
        prevent_initial_call=True,
    )
    def generate_model_plot_figure(inference_run, table_data, selected_rows):
        # Check for no selected rows
        if not selected_rows or selected_rows[0] is None:
            return no_update

        # Get the selected row data and grab the uuid
        selected_row_data = table_data[selected_rows[0]]
        model_uuid = selected_row_data["uuid"]
        m = Model(model_uuid, legacy=True)

        # Model Details Markdown component
        model_plot_fig = model_plot.ModelPlot().update_properties(m, inference_run)

        # Return the details/markdown for these data details
        return model_plot_fig


# Register the plugin callbacks for the model subpage
def register_plugin_callbacks(plugins):
    # Setup the inputs for the plugins and register the callbacks
    model_inputs = [
        Input("model_details-dropdown", "value"),
        Input("models_table", "derived_viewport_selected_row_ids"),
        State("models_table", "data"),
    ]

    # Sanity check that we have some plugins
    if plugins:
        plugin_callbacks.register_callbacks(plugins, model_inputs, "model")
