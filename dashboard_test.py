import os
import sys
import base64
import pandas as pd
from dash import Dash, html, dash_table
import dash_bootstrap_components as dbc

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
        os.path.join(test_folder, file)
        for file in os.listdir(test_folder)
        if file.startswith("oscilloscope_") and (file.endswith(".png") or file.endswith(".jpg"))
    ])

# Encode an image as a base64 string
def encode_image_base64(image_path):
    with open(image_path, "rb") as img_file:
        return f"data:image/png;base64,{base64.b64encode(img_file.read()).decode('utf-8')}"

# Generate oscilloscope gallery with embedded base64 images
def generate_oscilloscope_gallery(screenshots):
    if not screenshots:
        return html.Div("No oscilloscope screenshots available.", className="text-center text-muted my-4")
    return [
        html.Div([html.Img(src=encode_image_base64(screenshot), style={"width": "100%"})],
                 style={"display": "inline-block", "margin": "10px", "width": "200px"})
        for screenshot in screenshots
    ]

# Save the dashboard as a self-contained static HTML file
def save_dashboard_as_html(data, oscilloscope_screenshots, output_path):
    # Build the HTML layout
    data_table_html = dash_table.DataTable(
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
    )

    oscilloscope_gallery_html = generate_oscilloscope_gallery(oscilloscope_screenshots)

    # Write to HTML file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Dashboard</title>
            <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        </head>
        <body>
            <div class="container">
                <h1 class="text-center my-4">Test Dashboard</h1>
                
                <h3 class="text-center my-4">Test Data</h3>
                {data_table_html.to_plotly_json()}
                
                <hr>

                <h3 class="text-center my-4">Oscilloscope 1 Screenshots</h3>
                {"".join([html.Div(child).to_plotly_json() for child in oscilloscope_gallery_html])}

                <hr>
            </div>
        </body>
        </html>
        """)
    print(f"Dashboard saved to {output_path}")

# Main function to load data and initialize the dashboard
def main(test_folder):
    # Load data and screenshots
    data = load_data(test_folder)
    oscilloscope_screenshots = load_oscilloscope_screenshots(test_folder)

    # Initialize Dash app
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
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

    # Save the dashboard as a self-contained HTML file
    output_file = os.path.join(test_folder, "dashboard_export.html")
    save_dashboard_as_html(data, oscilloscope_screenshots, output_file)

    # Run the app
    app.run_server(debug=True)

# Run the app with the test folder specified as a command-line argument
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dashboard.py <test_folder>")
        sys.exit(1)

    test_folder = sys.argv[1]
    main(test_folder)
