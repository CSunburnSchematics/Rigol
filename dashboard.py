import shutil
import sys
import os
import dash
import dash_bootstrap_components as dbc
from dash import html, dash_table, dcc
import pandas as pd
import plotly.express as px
import plotly.io as pio
import time
from multiprocessing import Process
import webbrowser
import time
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Test Dashboard', border=False, ln=True, align='C')
        self.ln(10)

    def add_section_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, border=False, ln=True, align='L')
        self.ln(5)

    def add_text(self, text):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 10, text)
        self.ln(5)

    def add_image(self, image_path, width=100):
        self.image(image_path, x=None, y=None, w=width)
        self.ln(10)

def generate_pdf(test_folder, test_setup_name, notes, data_by_voltage, oscilloscope1_screenshots, oscilloscope2_screenshots, setup_pictures, osc1_notes, osc2_notes):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Add title and notes
    pdf.add_section_title(f"Test Setup: {test_setup_name}")
    pdf.add_text(f"Notes: {notes}")

    # Add efficiency graph
    efficiency_graph_path = os.path.join("assets", "efficiency_graph.png")
    if os.path.exists(efficiency_graph_path):
        pdf.add_section_title("Efficiency Graph")
        pdf.add_image(efficiency_graph_path, width=150)

    # # Add data tables
    # for voltage, data in data_by_voltage.items():
    #     pdf.add_section_title(f"Test Data for {voltage} V")
    #     table_data = data.to_string(index=False)
    #     pdf.add_text(table_data)

    # Add data tables as images
    for voltage in data_by_voltage.keys():
        png_path = os.path.join(test_folder, f"table_{voltage}.png")
        if os.path.exists(png_path):
            pdf.add_section_title(f"Test Data Table for {voltage} V")
            pdf.add_image(png_path, width=150)


    # Add oscilloscope screenshots
    pdf.add_section_title("Oscilloscope 1 Screenshots")
    pdf.add_text(f"{osc1_notes}")
    for img in oscilloscope1_screenshots:
        img_path = os.path.join(test_folder, img)
        if os.path.exists(img_path):
            pdf.add_image(img_path, width=100)

    pdf.add_section_title("Oscilloscope 2 Screenshots")
    pdf.add_text(f"{osc2_notes}")
    for img in oscilloscope2_screenshots:
        img_path = os.path.join(test_folder, img)
        if os.path.exists(img_path):
            pdf.add_image(img_path, width=100)

    # Add setup pictures
    pdf.add_section_title("Setup Pictures")
    for img in setup_pictures:
        img_path = os.path.join(test_folder, img)
        if os.path.exists(img_path):
            pdf.add_image(img_path, width=100)
            caption = os.path.basename(img).split(".png")[0]
            pdf.add_text(f"{caption}")
            

    # Save PDF
    pdf_output_path = os.path.join(test_folder, "dashboard.pdf")
    pdf.output(pdf_output_path)
    print(f"Dashboard saved as PDF: {pdf_output_path}")







# Load all CSV data from the specified test folder
def load_all_csv_data(test_folder):
    csv_files = [file for file in os.listdir(test_folder) if file.endswith(".csv")]
    data_by_voltage = {}
    for file in csv_files:
        voltage = file.split("_")[-1].replace("V.csv", "")
        file_path = os.path.join(test_folder, file)
        data_by_voltage[voltage] = pd.read_csv(file_path)
    return data_by_voltage

import plotly.graph_objects as go

def save_table_as_png(data, voltage, output_file):
    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=list(data.columns),
                    fill_color="lightgrey",
                    align="center",
                    font=dict(size=10, color="black"),
                ),
                cells=dict(
                    values=[data[col] for col in data.columns],
                    fill_color="white",
                    align="center",
                    font=dict(size=9, color="black"),
                ),
            )
        ]
    )

    # Update layout for better visual output
    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),  # Padding around the table
        height=min(300 + len(data) * 20, 1000),  # Adjust height based on the number of rows
        width=800,  # Fixed width
    )

    # Save the figure as a PNG file
    fig.write_image(output_file)
    print(f"Table for {voltage} V saved as PNG: {output_file}")



def save_dashboard_to_pdf(test_folder, app_url="http://127.0.0.1:8050", wait_time=5):
    pdf_output_path = os.path.join(test_folder, "dashboard.pdf")
    
    # Open the dashboard in the default browser
    webbrowser.open(app_url)

    # Wait for the user to manually print the page as PDF
    print(f"Please print the dashboard as PDF manually. Save it to: {pdf_output_path}")
    time.sleep(wait_time)

def run_dash_server(app, host, port):
    app.run_server(debug=False, host=host, port=port)

# Load oscilloscope screenshots from the assets folder
def load_oscilloscope_screenshots(assets_folder):
    oscilloscope1 = []
    oscilloscope2 = []
    for file in os.listdir(assets_folder):
        if file.endswith((".png", ".jpg")):
            if file.startswith("oscilloscope1"):
                oscilloscope1.append(file)
            elif file.startswith("oscilloscope2"):
                oscilloscope2.append(file)
    return sorted(oscilloscope1), sorted(oscilloscope2)

# Load setup pictures
def load_setup_pictures(assets_folder):
    setup_images = []
    for i in range(1, 3):
        setup_image_path = os.path.join(assets_folder, f"webcam_image_{i}.png")
        if os.path.exists(setup_image_path):
            setup_images.append(f"webcam_image_{i}.png")
    return setup_images

# Generate columns for the data table based on the data
def generate_table_columns(data):
    return [{"name": col, "id": col} for col in data.columns]

# Generate the efficiency graph with multiple lines for each voltage
def generate_efficiency_graph(data_by_voltage, save_path):
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

        fig.update_yaxes(range=[0, 1])

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
        pio.write_image(fig, save_path)
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
        html.Img(src="/assets/efficiency_graph.png", style={"display": "block", "margin": "auto", "width": "600px"})
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

def start_dash_server(app):
    # Start the Dash server
    app.run_server(debug=False, host="127.0.0.1", port=8050)


def main(test_folder, test_setup_name, notes, osc1_notes, osc2_notes):
    # Use the script directory's assets folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_folder = os.path.join(script_dir, "assets")

    # Create the assets folder if it does not exist
    if not os.path.exists(assets_folder):
        os.makedirs(assets_folder)

    # Copy images from test_folder to the assets folder
    for file in os.listdir(test_folder):
        if file.endswith((".png", ".jpg")):
            src_path = os.path.join(test_folder, file)
            dest_path = os.path.join(assets_folder, file)
            shutil.copy(src_path, dest_path)

    # Define the save path for the efficiency graph
    efficiency_graph_path = os.path.join(assets_folder, "efficiency_graph.png")

    # Load CSV data
    data_by_voltage = load_all_csv_data(test_folder)

    # Generate the efficiency graph and save it
    generate_efficiency_graph(data_by_voltage, efficiency_graph_path)

    #generate tables as png
    for voltage, data in data_by_voltage.items():
        table_png_path = os.path.join(test_folder, f"table_{voltage}.png")
        save_table_as_png(data, voltage, table_png_path)


    # Load images for the dashboard
    oscilloscope1_screenshots, oscilloscope2_screenshots = load_oscilloscope_screenshots(assets_folder)
    setup_pictures = load_setup_pictures(assets_folder)

    generate_pdf(test_folder, test_setup_name, notes, data_by_voltage, oscilloscope1_screenshots, oscilloscope2_screenshots, setup_pictures, osc1_notes, osc2_notes)

    # Create the Dash app
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

    # Start the Dash server
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
    osc1_notes = f"Channels: 1) {sys.argv[4].replace('_', ' ')}, 2) {sys.argv[5].replace('_', ' ')}, 3) {sys.argv[6].replace('_', ' ')}, 4) {sys.argv[7].replace('_', ' ')}"
    osc2_notes = f"Channels: 1) {sys.argv[8].replace('_', ' ')}, 2) {sys.argv[9].replace('_', ' ')}, 3) {sys.argv[10].replace('_', ' ')}, 4) {sys.argv[11].replace('_', ' ')}"

    main(test_folder, test_setup_name, notes, osc1_notes, osc2_notes)


