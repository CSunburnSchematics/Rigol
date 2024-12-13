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

# Load setup pictures
def load_setup_pictures(test_folder):
    setup_images = []
    for i in range(1, 3):
        setup_image_path = os.path.join(test_folder, f"webcam_image_{i}.png")
        if os.path.exists(setup_image_path):
            setup_images.append(os.path.relpath(setup_image_path, test_folder))
    return setup_images

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
            width=600,
            legend=dict(
                title="Input Voltage",
                orientation="h",
                x=0.5,
                xanchor="center",
                y=-0.2,
            ),
        )
        return html.Div(
            dcc.Graph(figure=fig),
            style={"display": "flex", "justifyContent": "center"},
        )
    else:
        return html.Div(
            "Efficiency graph cannot be displayed. Required data is missing.",
            className="text-center text-muted my-4",
        )

# Generate the layout for the Dash app
def generate_dash_layout(test_setup_name, notes, data_by_voltage, oscilloscope1_screenshots, oscilloscope2_screenshots, setup_pictures, osc1_notes, osc2_notes):
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
        print(f"Creating captioned image for: {img_path}")  # Debugging
        file_name = os.path.basename(img_path).split(".png")[0]
        return html.Div([
            html.Img(src=f"/assets/{img_path}", style={"width": "100%", "margin": "10px"}),
            html.P(file_name, className="text-center text-muted", style={"fontSize": "12px"})
        ], style={"display": "inline-block", "width": "200px"})

    def group_screenshots_by_voltage(screenshots):
        grouped = {}
        for img_path in screenshots:
            parts = os.path.basename(img_path).split("_")
            if len(parts) > 1 and "V" in parts[1]:
                voltage = parts[1].replace("V", "")
                if voltage not in grouped:
                    grouped[voltage] = []
                grouped[voltage].append(img_path)
        return grouped

    def generate_oscilloscope_section(title, grouped_screenshots, notes):
        sections = []
        sections.append(html.Div([
            html.P(notes, className="text-center text-muted my-3")
        ]))
        for voltage, images in sorted(grouped_screenshots.items()):
            sections.append(html.Div([
                html.H4(f"{title} for {voltage} V", className="text-center my-3"),
                html.Div([
                    create_image_with_caption(img)
                    for img in images
                ], style={"textAlign": "center"})
            ]))
        return html.Div(sections)

    oscilloscope1_grouped = group_screenshots_by_voltage(oscilloscope1_screenshots)
    oscilloscope1_section = html.Div([
        html.H3("Oscilloscope 1 Screenshots", className="text-center my-4"),
        generate_oscilloscope_section("Oscilloscope 1 Screenshots", oscilloscope1_grouped, osc1_notes)
    ])

    oscilloscope2_grouped = group_screenshots_by_voltage(oscilloscope2_screenshots)
    oscilloscope2_section = html.Div([
        html.H3("Oscilloscope 2 Screenshots", className="text-center my-4"),
        generate_oscilloscope_section("Oscilloscope 2 Screenshots", oscilloscope2_grouped, osc2_notes)
    ])

    setup_section = html.Div([
        html.H3("Setup Pictures", className="text-center my-4"),
        html.Div([
            create_image_with_caption(img)
            for img in setup_pictures
        ], style={"textAlign": "center"})
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


def main(test_folder, test_setup_name, notes, osc1_notes, osc2_notes):
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
    setup_pictures = load_setup_pictures(assets_folder)

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.title = test_setup_name

    app.layout = generate_dash_layout(
        test_setup_name,
        notes,
        data_by_voltage,
        oscilloscope1_screenshots,
        oscilloscope2_screenshots,
        setup_pictures,
        osc1_notes,
        osc2_notes
    )

    host = "127.0.0.1"
    port = 8050
    print(f"\nDashboard is running! Open your browser and go to: http://{host}:{port}\n")
    app.run_server(debug=True, host=host, port=port)


if __name__ == "__main__":
    if len(sys.argv) < 12:
        print("Usage: python dashboard.py <test_folder> <test_setup_name> <notes> <osc1_ch1> <osc1_ch2> <osc1_ch3> <osc1_ch4> <osc2_ch1> <osc2_ch2> <osc2_ch3> <osc2_ch4>")
        sys.exit(1)

    test_folder = sys.argv[1]
    test_setup_name = sys.argv[2]
    notes = sys.argv[3].replace("_", " ")
    osc1_notes = f"Channels: 1) {sys.argv[4].replace("_", " ")}, 2) {sys.argv[5].replace("_", " ")}, 3) {sys.argv[6].replace("_", " ")}, 4) {sys.argv[7].replace("_", " ")}"
    osc2_notes = f"Channels: 1) {sys.argv[8].replace("_", " ")}, 2) {sys.argv[9].replace("_", " ")}, 3) {sys.argv[10].replace("_", " ")}, 4) {sys.argv[11].replace("_", " ")}"

    main(test_folder, test_setup_name, notes, osc1_notes, osc2_notes)
