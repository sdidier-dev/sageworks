"""Callbacks/Connections in the Web User Interface"""
from datetime import datetime
import hashlib
from dash import Dash, no_update
from dash.dependencies import Input, Output, State


# SageWorks Imports
from sageworks.views.artifacts_web_view import ArtifactsWebView
from sageworks.web_components import table
from sageworks.utils.pandas_utils import serialize_aws_broker_data, deserialize_aws_broker_data


# Helper functions
def content_hash(serialized_data):
    return hashlib.md5(serialized_data.encode()).hexdigest()


def refresh_data(app: Dash, web_view: ArtifactsWebView, force_refresh=False):
    @app.callback(
        [
            Output("last-updated", "children"),
            Output("aws-broker-data", "data"),
            ],
        Input("main-updater", "n_intervals"),
        State("aws-broker-data", "data")
    )
    def time_updated(n, aws_broker_data):

        # A string of the new time
        new_time = datetime.now().strftime("Last Updated: %Y-%m-%d %H:%M:%S")

        print("Calling ALL Artifact Refresh...")
        web_view.refresh(force_refresh=force_refresh)
        new_broker_data = web_view.view_data()
        serialized_data = serialize_aws_broker_data(new_broker_data)

        # Sanity check our existing data
        if aws_broker_data is None:
            print("No existing data...")
            new_time = new_time + " (Data Update)"
            return [new_time, serialized_data]

        # Check if the data has changed
        if n and content_hash(aws_broker_data) == content_hash(serialized_data):
            return [new_time, no_update]

        # Update the time
        new_time = new_time + " (Data Update)"
        return [new_time, serialized_data]


def update_artifact_tables(app: Dash):
    @app.callback(
        [
            Output("INCOMING_DATA", "columns"),
            Output("INCOMING_DATA", "data"),
        ],
        Input("aws-broker-data", "data"),
    )
    def incoming_data_update(serialized_aws_broker_data):
        aws_broker_data = deserialize_aws_broker_data(serialized_aws_broker_data)
        incoming_data = aws_broker_data["INCOMING_DATA"]
        column_setup_list = table.Table().column_setup(incoming_data, markdown_columns=["Name"])
        return [column_setup_list, incoming_data.to_dict("records")]

    @app.callback(
        [
            Output("GLUE_JOBS", "columns"),
            Output("GLUE_JOBS", "data"),
        ],
        Input("aws-broker-data", "data"),
    )
    def glue_jobs_update(serialized_aws_broker_data):
        aws_broker_data = deserialize_aws_broker_data(serialized_aws_broker_data)
        glue_jobs = aws_broker_data["GLUE_JOBS"]
        column_setup_list = table.Table().column_setup(glue_jobs, markdown_columns=["Name"])
        return [column_setup_list, glue_jobs.to_dict("records")]

    @app.callback(
        [
            Output("DATA_SOURCES", "columns"),
            Output("DATA_SOURCES", "data"),
        ],
        Input("aws-broker-data", "data"),
    )
    def data_sources_update(serialized_aws_broker_data):
        aws_broker_data = deserialize_aws_broker_data(serialized_aws_broker_data)
        data_sources = aws_broker_data["DATA_SOURCES"]
        column_setup_list = table.Table().column_setup(data_sources, markdown_columns=["Name"])
        return [column_setup_list, data_sources.to_dict("records")]

    @app.callback(
        [
            Output("FEATURE_SETS", "columns"),
            Output("FEATURE_SETS", "data"),
        ],
        Input("aws-broker-data", "data"),
    )
    def feature_sets_update(serialized_aws_broker_data):
        aws_broker_data = deserialize_aws_broker_data(serialized_aws_broker_data)
        feature_sets = aws_broker_data["FEATURE_SETS"]
        column_setup_list = table.Table().column_setup(feature_sets, markdown_columns=["Feature Group"])
        return [column_setup_list, feature_sets.to_dict("records")]

    @app.callback(
        [
            Output("MODELS", "columns"),
            Output("MODELS", "data"),
        ],
        Input("aws-broker-data", "data"),
    )
    def models_update(serialized_aws_broker_data):
        aws_broker_data = deserialize_aws_broker_data(serialized_aws_broker_data)
        models = aws_broker_data["MODELS"]
        column_setup_list = table.Table().column_setup(models, markdown_columns=["Model Group"])
        return [column_setup_list, models.to_dict("records")]

    @app.callback(
        [
            Output("ENDPOINTS", "columns"),
            Output("ENDPOINTS", "data"),
        ],
        Input("aws-broker-data", "data"),
    )
    def endpoints_update(serialized_aws_broker_data):
        aws_broker_data = deserialize_aws_broker_data(serialized_aws_broker_data)
        endpoints = aws_broker_data["ENDPOINTS"]
        column_setup_list = table.Table().column_setup(endpoints, markdown_columns=["Name"])
        return [column_setup_list, endpoints.to_dict("records")]


def delete_artifact_callbacks(app: Dash, web_view: ArtifactsWebView):
    @app.callback(Output("modal", "is_open"), Input("DATA_SOURCES", "active_cell"), State("DATA_SOURCES", "data"))
    def delete_data_source(active_cell, table_data):
        global all_data
        if active_cell is None or active_cell["column_id"] != "del":
            print("Delete Cell not pressed...")
            return no_update

        # Get the UUID of the artifact to remove
        uuid = table_data[active_cell["row"]].get("uuid")
        if uuid:
            print(f"Deleting artifact with UUID: {uuid}...")
            web_view.delete_artifact(uuid)
            web_view.refresh(force_refresh=True)
            all_data = web_view.view_data()
            update_artifact_tables(app)
        return no_update
