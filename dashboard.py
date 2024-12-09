import sys
import os
import dash
import dash_bootstrap_components as dbc
from dash import html, dash_table
import pandas as pd

# Load the CSV data from the specified test folder
def load_data(test_folder):
    csv_filename = os.path.join(test_folder, "test_results.csv")
    if os.path.exists(csv_filename):
        return pd.read_csv(csv_filename)
    else:
        return pd.DataFrame()

# Generate columns for the data table based on the data
def generate_table_columns(data):
    return [{"name": col, "id": col} for col in data.columns]

# Load oscilloscope screenshots from the specified test folder
def load_oscilloscope_screenshots(test_folder):
    return sorted([
        os.path.relpath(os.path.join(test_folder, file), test_folder)
        for file in os.listdir(test_folder)
        if file.startswith("oscilloscope_") and (file.endswith(".png") or file.endswith(".jpg"))
    ])

# Load the setup picture from the specified test folder
def load_setup_picture(test_folder):
    setup_image_path = os.path.join(test_folder, "webcam_image.png")
    if os.path.exists(setup_image_path):
        return os.path.relpath(setup_image_path, test_folder)
    return None

# Generate the layout for the Dash app
def generate_dash_layout(data, oscilloscope_screenshots, setup_picture):
    # Data Table Section

    table_section = html.Div([
        html.H3("Test Data", className="text-center my-4"),
        html.Div(
            dash_table.DataTable(
                id="data-table",
                columns=generate_table_columns(data),
                data=data.to_dict("records"),
                style_table={
                    "width": "560px",  # Total width restricted to fit within 7 inches
                    "margin": "auto",  # Center the table
                    "border": "1px solid lightgray",  # Optional: Add border for clarity
                    "overflowX": "hidden"  # Ensure no horizontal scrolling
                },
                style_header={
                    "backgroundColor": "rgb(230, 230, 230)",
                    "fontWeight": "bold",
                    "fontSize": "9px",  # Reduce header font size for tighter fit
                    "whiteSpace": "normal",  # Allow text wrapping in headers
                    "padding": "2px",  # Reduce header padding
                },
                style_cell={
                    "textAlign": "center",
                    "padding": "2px",  # Minimize cell padding
                    "fontSize": "9px",  # Smaller font size for all cells
                    "maxWidth": "70px",  # Restrict maximum width of each column
                    "whiteSpace": "normal",  # Allow text wrapping in cells
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",  # Truncate if necessary
                },
                style_data={
                    "whiteSpace": "normal",  # Allow text wrapping in data cells
                    "height": "auto",  # Adjust row height dynamically
                },
            ),
            style={"textAlign": "center"}  # Center the entire section
        )
    ])


    # Oscilloscope Screenshots Gallery
    oscilloscope_section = html.Div([
        html.H3("Oscilloscope Screenshots", className="text-center my-4"),
        html.Div([
            html.Div([
                html.Img(src=f"/assets/{img}", style={"width": "100%", "margin": "10px"})
            ], style={"display": "inline-block", "width": "200px"})
            for img in oscilloscope_screenshots
        ]) if oscilloscope_screenshots else html.Div(
            "No oscilloscope screenshots available.",
            className="text-center text-muted my-4"
        ),
    ])

    # Setup Picture Section
    setup_section = html.Div([
        html.H3("Setup Picture", className="text-center my-4"),
        html.Img(src=f"/assets/{setup_picture}", style={"width": "50%", "display": "block", "margin": "auto"}) if setup_picture else
        html.Div("No setup picture available.", className="text-center text-muted my-4"),
    ])

    # Combine all sections
    return dbc.Container([
        html.H1("Oscilloscope Test Dashboard", className="text-center my-4"),
        table_section,
        html.Hr(),
        oscilloscope_section,
        html.Hr(),
        setup_section,
    ], fluid=True)

# Main function to load data and initialize the dashboard
def main(test_folder):
    # Ensure images are served from the assets folder
    assets_folder = os.path.join(test_folder, "assets")
    if not os.path.exists(assets_folder):
        os.makedirs(assets_folder)

    # Copy all image files into the assets folder
    for file in os.listdir(test_folder):
        if file.endswith((".png", ".jpg")):
            src_path = os.path.join(test_folder, file)
            dest_path = os.path.join(assets_folder, file)
            if not os.path.exists(dest_path):
                os.replace(src_path, dest_path)

    # Load data and screenshots
    data = load_data(test_folder)
    oscilloscope_screenshots = load_oscilloscope_screenshots(assets_folder)
    setup_picture = load_setup_picture(assets_folder)

    # Initialize the Dash app
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.title = "Oscilloscope Test Dashboard"
    app.layout = generate_dash_layout(data, oscilloscope_screenshots, setup_picture)

    # Print the URL and run the app
    host = "127.0.0.1"
    port = 8050
    print(f"\nDashboard is running! Open your browser and go to: http://{host}:{port}\n")
    app.run_server(debug=True, host=host, port=port)

# Run the app with the test folder specified as a command-line argument
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dashboard.py <test_folder>")
        sys.exit(1)

    test_folder = sys.argv[1]
    main(test_folder)
