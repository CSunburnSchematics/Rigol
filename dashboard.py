import sys
import os
import dash
import dash_bootstrap_components as dbc
from dash import html, dash_table, dcc
import pandas as pd
import plotly.express as px

# Load all CSV data from the specified test folder
def load_all_csv_data(test_folder):
    csv_files = [file for file in os.listdir(test_folder) if file.endswith(".csv")]
    data_by_voltage = {}
    for file in csv_files:
        voltage = file.split("_")[-1].replace("V.csv", "")
        file_path = os.path.join(test_folder, file)
        data_by_voltage[voltage] = pd.read_csv(file_path)
    return data_by_voltage

# Load oscilloscope screenshots from the specified test folder
def load_oscilloscope_screenshots(test_folder):
    oscilloscope1 = []
    oscilloscope2 = []
    for file in os.listdir(test_folder):
        if file.endswith((".png", ".jpg")):
            if file.startswith("oscilloscope1"):
                oscilloscope1.append(os.path.relpath(os.path.join(test_folder, file), test_folder))
            elif file.startswith("oscilloscope2"):
                oscilloscope2.append(os.path.relpath(os.path.join(test_folder, file), test_folder))
    return sorted(oscilloscope1), sorted(oscilloscope2)

def load_setup_picture(test_folder):
    setup_image_path = os.path.join(test_folder, "webcam_image.png")
    if os.path.exists(setup_image_path):
        return os.path.relpath(setup_image_path, test_folder)
    return None

# Generate columns for the data table based on the data
def generate_table_columns(data):
    return [{"name": col, "id": col} for col in data.columns]

# Generate the efficiency graph with multiple lines for each voltage
def generate_efficiency_graph(data_by_voltage):
    graph_data = []
    for voltage, data in data_by_voltage.items():
        if "Current (A)" in data.columns and "Efficiency (%)" in data.columns:
            temp_df = data[["Current (A)", "Efficiency (%)"]].copy()
            temp_df["Voltage (V)"] = voltage
            graph_data.append(temp_df)

    if graph_data:
        combined_df = pd.concat(graph_data)
        fig = px.line(
            combined_df,
            x="Current (A)",
            y="Efficiency (%)",
            color="Voltage (V)",
            markers=True,
            title="Efficiency vs. Input Current for Each Voltage",
            labels={"Current (A)": "Input Current (A)", "Efficiency (%)": "Efficiency (%)"},
        )
        fig.update_layout(
            margin={"l": 40, "r": 40, "t": 40, "b": 40},
            height=400,
            legend=dict(
                title="Input Voltage",
                orientation="h",  # Horizontal legend
                x=0.5,  # Center the legend
                xanchor="center",
                y=-0.2,  # Place below the chart
            ),
        )
        return dcc.Graph(figure=fig)
    else:
        return html.Div(
            "Efficiency graph cannot be displayed. Required data is missing.",
            className="text-center text-muted my-4",
        )
    


# Generate the layout for the Dash app
def generate_dash_layout(test_setup_name, notes, data_by_voltage, oscilloscope1_screenshots, oscilloscope2_screenshots, setup_picture):
    title_section = html.Div([
        html.H1(test_setup_name, className="text-center my-4"),
        html.H4("Notes:", className="text-center my-2"),
        html.P(notes, className="text-center my-2 text-muted")
    ])

    table_sections = []
    for voltage, data in data_by_voltage.items():
        table_sections.append(html.Div([
            html.H3(f"Test Data for {voltage} V", className="text-center my-4"),
            html.Div(
                dash_table.DataTable(
                    id=f"data-table-{voltage}",
                    columns=generate_table_columns(data),
                    data=data.to_dict("records"),
                    style_table={"width": "560px", "margin": "auto", "border": "1px solid lightgray", "overflowX": "hidden"},
                    style_header={"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold", "fontSize": "9px", "whiteSpace": "normal", "padding": "2px"},
                    style_cell={"textAlign": "center", "padding": "2px", "fontSize": "9px", "maxWidth": "70px", "whiteSpace": "normal", "overflow": "hidden", "textOverflow": "ellipsis"},
                    style_data={"whiteSpace": "normal", "height": "auto"},
                ),
                style={"textAlign": "center"}
            )
        ]))

    efficiency_graph_section = html.Div([
        html.H3("Efficiency Graph", className="text-center my-4"),
        generate_efficiency_graph(data_by_voltage)
    ])

    def create_image_with_caption(img_path):
        file_name = os.path.basename(img_path).split(".png")[0]
        return html.Div([
            html.Img(src=f"/assets/{img_path}", style={"width": "100%", "margin": "10px"}),
            html.P(file_name, className="text-center text-muted", style={"fontSize": "12px"})
        ], style={"display": "inline-block", "width": "200px"})
    
    def group_screenshots_by_voltage(screenshots):
        grouped = {}
        for img_path in screenshots:
            # Extract voltage from the filename (e.g., "oscilloscope1_48.00V_0.50A.png")
            parts = os.path.basename(img_path).split("_")
            if len(parts) > 1 and "V" in parts[1]:
                voltage = parts[1].replace("V", "")
                if voltage not in grouped:
                    grouped[voltage] = []
                grouped[voltage].append(img_path)
        return grouped

# Updated oscilloscope section generation
    def generate_oscilloscope_section(title, grouped_screenshots):
        sections = []
        for voltage, images in sorted(grouped_screenshots.items()):
            sections.append(html.Div([
                html.H4(f"{title} for {voltage} V", className="text-center my-3"),
                html.Div([
                    create_image_with_caption(img)
                    for img in images
                ], style={"textAlign": "center"})
            ]))
        return html.Div(sections)

    # oscilloscope1_section = html.Div([
    #     html.H3("Oscilloscope 1 Screenshots", className="text-center my-4"),
    #     html.Div([
    #         create_image_with_caption(img) for img in oscilloscope1_screenshots
    #     ]) if oscilloscope1_screenshots else html.Div("No screenshots available for Oscilloscope 1.", className="text-center text-muted my-4"),
    # ])

    # oscilloscope2_section = html.Div([
    #     html.H3("Oscilloscope 2 Screenshots", className="text-center my-4"),
    #     html.Div([
    #         create_image_with_caption(img) for img in oscilloscope2_screenshots
    #     ]) if oscilloscope2_screenshots else html.Div("No screenshots available for Oscilloscope 2.", className="text-center text-muted my-4"),
    # ])

    oscilloscope1_grouped = group_screenshots_by_voltage(oscilloscope1_screenshots)
    oscilloscope1_section = html.Div([
        html.H3("Oscilloscope 1 Screenshots", className="text-center my-4"),
        generate_oscilloscope_section("Oscilloscope 1 Screenshots", oscilloscope1_grouped)
    ])

    oscilloscope2_grouped = group_screenshots_by_voltage(oscilloscope2_screenshots)
    oscilloscope2_section = html.Div([
        html.H3("Oscilloscope 2 Screenshots", className="text-center my-4"),
        generate_oscilloscope_section("Oscilloscope 2 Screenshots", oscilloscope2_grouped)
    ])


    setup_section = html.Div([
        html.H3("Setup Picture", className="text-center my-4"),
        html.Img(src=f"/assets/{setup_picture}", style={"width": "50%", "display": "block", "margin": "auto"}) if setup_picture else
        html.Div("No setup picture available.", className="text-center text-muted my-4"),
    ])

    return dbc.Container([
        title_section,
        *table_sections,
        efficiency_graph_section,
        html.Hr(),
        oscilloscope1_section,
        html.Hr(),
        oscilloscope2_section,
        html.Hr(),
        setup_section,
    ], fluid=True)

def main(test_folder, test_setup_name, notes):
    assets_folder = os.path.join(test_folder, "assets")
    if not os.path.exists(assets_folder):
        os.makedirs(assets_folder)

    for file in os.listdir(test_folder):
        if file.endswith((".png", ".jpg")):
            src_path = os.path.join(test_folder, file)
            dest_path = os.path.join(assets_folder, file)
            if not os.path.exists(dest_path):
                os.replace(src_path, dest_path)

    data_by_voltage = load_all_csv_data(test_folder)
    oscilloscope1_screenshots, oscilloscope2_screenshots = load_oscilloscope_screenshots(assets_folder)
    setup_picture = load_setup_picture(assets_folder)

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.title = test_setup_name
    app.layout = generate_dash_layout(test_setup_name, notes, data_by_voltage, oscilloscope1_screenshots, oscilloscope2_screenshots, setup_picture)

    host = "127.0.0.1"
    port = 8050
    print(f"\nDashboard is running! Open your browser and go to: http://{host}:{port}\n")
    app.run_server(debug=True, host=host, port=port)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python dashboard.py <test_folder> <test_setup_name> <notes>")
        sys.exit(1)

    test_folder = sys.argv[1]
    test_setup_name = sys.argv[2]
    notes = " ".join(sys.argv[3:])
    main(test_folder, test_setup_name, notes)
