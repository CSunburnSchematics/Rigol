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
        return pd.DataFrame(columns=[
            "Current (A)", "Voltage (V)", "Power (W)", "Resistance (Ohms)",
            "Input Voltage (V)", "Input Current (A)", "Input Power (W)", "Efficiency (%)"
        ])

# Load oscilloscope screenshots from the specified test folder
def load_oscilloscope_screenshots(test_folder):
    return sorted([
        f"/{os.path.join(test_folder, file)}"
        for file in os.listdir(test_folder)
        if file.startswith("oscilloscope_") and (file.endswith(".png") or file.endswith(".jpg"))
    ])

# Generate screenshot gallery for oscilloscope
def generate_oscilloscope_gallery(screenshots):
    if not screenshots:
        return html.Div("No oscilloscope screenshots available.", className="text-center text-muted my-4")
    return [
        html.Div([
            html.Img(src=screenshot, style={"width": "100%"})
        ], style={"display": "inline-block", "margin": "10px", "width": "200px"})
        for screenshot in screenshots
    ]

# Main function to load data and initialize the dashboard
def main(test_folder):
    # Load data and screenshots
    data = load_data(test_folder)
    oscilloscope_screenshots = load_oscilloscope_screenshots(test_folder)

    # Initialize the Dash app
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.title = "Oscilloscope Test Dashboard"

    # Layout of the dashboard
    app.layout = dbc.Container([
        html.H1("Oscilloscope Test Dashboard", className="text-center my-4"),

        # Data Table
        html.H3("Test Data", className="text-center my-4"),
        dash_table.DataTable(
            id="data-table",
            columns=[
                {"name": "Output Current (A)", "id": "Current (A)"},
                {"name": "Output Voltage (V)", "id": "Voltage (V)"},
                {"name": "Output Power (W)", "id": "Power (W)"},
                {"name": "Resistance (Ohms)", "id": "Resistance (Ohms)"},
                {"name": "Input Voltage (V)", "id": "Input Voltage (V)"},
                {"name": "Input Current (A)", "id": "Input Current (A)"},
                {"name": "Input Power (W)", "id": "Input Power (W)"},
                {"name": "Efficiency (%)", "id": "Efficiency (%)"},
            ],
            data=data.to_dict("records"),
            style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_cell={'textAlign': 'center'}
        ),

        html.Hr(),

        # Oscilloscope Screenshot Gallery
        html.H3("Oscilloscope Screenshots", className="text-center my-4"),
        html.Div(generate_oscilloscope_gallery(oscilloscope_screenshots)),
    ], fluid=True)

    # Run the app
    app.run_server(debug=True)

# Run the app with the test folder specified as a command-line argument
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dashboard.py <test_folder>")
        sys.exit(1)

    test_folder = sys.argv[1]
    main(test_folder)
