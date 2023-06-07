"""FeatureSets Callbacks: Callback within the FeatureSets Web User Interface"""
from datetime import datetime
from dash import Dash
from dash.dependencies import Input, Output

# SageWorks Imports
from sageworks.views.artifacts_web_view import ArtifactsWebView


def update_last_updated(app: Dash):
    @app.callback(
        Output("last-updated-endpoints", "children"),
        Input("endpoints-updater", "n_intervals"),
    )
    def time_updated(n):
        return datetime.now().strftime("Last Updated: %Y-%m-%d %H:%M:%S")


def update_endpoints_table(app: Dash, sageworks_artifacts: ArtifactsWebView):
    @app.callback(Output("ENDPOINTS_DETAILS", "data"), Input("endpoints-updater", "n_intervals"))
    def data_sources_update(n):
        print("Calling FeatureSets Refresh...")
        sageworks_artifacts.refresh()
        endpoints = sageworks_artifacts.endpoints_summary()
        return endpoints.to_dict("records")