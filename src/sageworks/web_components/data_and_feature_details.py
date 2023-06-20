"""A Component for details/information about DataSources"""
from dash import dcc


def create_markdown(artifact_details: dict) -> str:
    """Create the Markdown for the details/information about the DataSource or the FeatureSet
    Args:
        artifact_details (dict): A dictionary of information about the artifact
    Returns:
        str: A Markdown string
    """

    markdown_template = """
    **Rows:** <<num_rows>>  **Columns:** <<num_columns>>
    <br>**Created/Modified:** <<created>> / <<modified>>
    <br>**Tags:** <<sageworks_tags>>
    <br>**S3:** <<s3_storage_location>>

    #### String Columns
    <<column_details_markdown>>
    """
    details_template = """
    <details>
        <summary><b><<column_name>></b></summary>
        <ul>
        <<bullet_list>>
        </ul>
    </details>
    """

    # Sanity Check for empty data
    if not artifact_details:
        return "No data source details found"

    # Loop through all the details and replace in the template
    for key, value in artifact_details.items():
        # Hack for dates
        if ".000Z" in str(value):
            value = value.replace(".000Z", "").replace("T", " ")
        markdown_template = markdown_template.replace(f"<<{key}>>", str(value))

    # Loop through the column details and create collapsible sections
    details_markdown = ""
    for column_name, value_counts in artifact_details["value_counts"].items():
        bullet_list = ""
        for value, count in value_counts.items():
            bullet_list += f"<li>{value}: {count}</li>"
        details_markdown += details_template.replace("<<column_name>>", column_name).replace(
            "<<bullet_list>>", bullet_list
        )

    # Now actually replace the column details in the markdown
    markdown_template = markdown_template.replace("<<column_details_markdown>>", details_markdown)
    return markdown_template


def create(component_id: str, artifact_details: dict) -> dcc.Markdown:
    """Create a Markdown Component details/information about the DataSource or the FeatureSet
    Args:
        component_id (str): The ID of the UI component
        artifact_details (dict): A dictionary of column information
    Returns:
        dcc.Markdown: A Dash Markdown Component
    """

    # Generate a figure and wrap it in a Dash Graph Component
    return dcc.Markdown(id=component_id, children=create_markdown(artifact_details), dangerously_allow_html=True)