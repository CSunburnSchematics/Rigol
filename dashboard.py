import re
import shutil
import sys
import os
import dash
import dash_bootstrap_components as dbc
from dash import html, dash_table, dcc
import pandas as pd
import plotly.express as px
import plotly.io as pio
from plotly.io import write_image
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
        self.cell(0, 10, title, border=False, ln=True, align='C')
        self.ln(5)

    def add_text(self, text):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 10, text, align = 'C')
        self.ln(5)

    def add_image(self, image_path, x_start = None, y_start = None, width=100):
        self.image(image_path, x=x_start, y=y_start, w=width)
        self.ln(10)

def generate_pdf(test_folder, test_setup_name, notes, data_by_voltage, oscilloscope1_screenshots, oscilloscope2_screenshots, oscilloscope3_screenshots, oscilloscope_graphs_folder, setup_pictures, osc1_notes, osc2_notes, osc3_notes):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    

    # Add title and notes
    pdf.add_section_title(f"Test Setup: {test_setup_name}")
    pdf.add_text(f"{notes}")

    # Add data tables as images
    for voltage in data_by_voltage.keys():
        png_path = os.path.join(test_folder, f"table_{voltage}.png")
        if os.path.exists(png_path):
            pdf.add_section_title(f"Test Data Table for {voltage} V")
            pdf.add_image(png_path, None, None, width=150)


    # Add efficiency graph
    efficiency_graph_path = os.path.join("assets", "efficiency_graph.png")
    if os.path.exists(efficiency_graph_path):
        pdf.add_section_title("Efficiency Graph")
        pdf.add_image(efficiency_graph_path, None, None, width=150)



    pdf.add_section_title("Oscilloscope Screenshots")
    pdf.add_text(f"{osc1_notes}\n{osc2_notes}\n{osc3_notes}")

    # Define constants for grid layout
    cell_width = 60
    cell_height = 65  # Includes space for the image and caption
    spacing = 10  # Spacing between cells
    columns_per_row = 3  # Number of columns in each row
    max_y = 250  # Maximum Y position before triggering a new page

    # Flatten all screenshots into one grid
    grid = []
    for i in range(max(len(oscilloscope1_screenshots), len(oscilloscope2_screenshots), len(oscilloscope3_screenshots))):
        grid.append(oscilloscope1_screenshots[i] if i < len(oscilloscope1_screenshots) else None)
        grid.append(oscilloscope2_screenshots[i] if i < len(oscilloscope2_screenshots) else None)
        grid.append(oscilloscope3_screenshots[i] if i < len(oscilloscope3_screenshots) else None)

    # Starting Y position for the grid
    start_y = pdf.get_y()
    current_y = start_y  # Track the Y position for rows

    # Iterate through the grid and place images
    for idx, img_name in enumerate(grid):
        col = idx % columns_per_row  # Current column (0, 1, 2 for each row)

        # Calculate X and Y positions
        x_pos = 10 + col * (cell_width + spacing)  # Start X at 10 with spacing between columns

        # Check if the current row exceeds the page limit
        if current_y + cell_height > max_y:
            pdf.add_page()  # Add a new page
            current_y = 20  # Reset Y position for the new page

        # Add an empty cell if no image is present
        if img_name is None:
            continue

        # Load the image path
        img_path = os.path.join(test_folder, img_name)

        # Add image and caption if the file exists
        if os.path.exists(img_path):
            pdf.image(img_path, x=x_pos, y=current_y, w=cell_width)
            pdf.set_y(current_y + cell_width/2 + 6)  # Move below the image
            pdf.set_x(x_pos)
            pdf.cell(cell_width, 5, os.path.splitext(img_name)[0], align='C')

        # Move to the next row after completing all columns in a row
        if col == columns_per_row - 1:
            current_y += cell_height  # Update Y position for the next row

    # Move the cursor to the next section after the grid
    pdf.ln(cell_height)


    # Add oscilloscope graphs section
    pdf.add_section_title("Oscilloscope Graphs")
    for graph_file in sorted(os.listdir(oscilloscope_graphs_folder)):
        graph_path = os.path.join(oscilloscope_graphs_folder, graph_file)
        if os.path.exists(graph_path) and graph_file.endswith("V.png"):
            pdf.add_image(graph_path, None, None, width=150)
            
            
    # Add setup pictures
    pdf.add_section_title("Setup Pictures")
    for img in setup_pictures:
        img_path = os.path.join(test_folder, img)
        if os.path.exists(img_path):
            pdf.add_image(img_path, None, None, width=100)
            caption = os.path.basename(img).split(".png")[0]
            pdf.add_text(f"{caption}")
            

    # Save PDF
    pdf_output_path = os.path.join(test_folder, f"{test_setup_name}.pdf")
    pdf.output(pdf_output_path)
    print(f"Dashboard saved as PDF: {pdf_output_path}")


def copy_test_folder_to_shared_drive(test_folder, destination_folder):
    """
    Copy the test_folder and its contents to the shared drive destination.
    
    :param test_folder: Path to the folder containing test data.
    :param destination_folder: Destination folder path on the shared drive.
    """
    try:
        # Ensure the destination folder exists
        os.makedirs(destination_folder, exist_ok=True)
        
        # Define the destination path for the copied folder
        destination_path = os.path.join(destination_folder, os.path.basename(test_folder))
        
        # Copy the folder and its contents
        shutil.copytree(test_folder, destination_path, dirs_exist_ok=True)
        print(f"Test folder successfully copied to: {destination_path}")
    except Exception as e:
        print(f"Failed to copy test folder to shared drive: {e}")

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
    filtered_data = data.loc[:, : "Efficiency (%)"]
    num_columns = len(filtered_data.columns)
    

    # Determine the green header styling based on the number of columns
    header_fill_colors = []
    if num_columns == 10:
        header_fill_colors = [
            "#b0bfc2" if 0 <= i < 6 else "#b0c2b2" if i == num_columns - 1 else "#dbbfc9"
            for i in range(num_columns)
        ]
    elif num_columns == 7:
        header_fill_colors = [
            "#b0bfc2" if 0 <= i < 3 else "#b0c2b2" if i == num_columns - 1 else "#dbbfc9"
            for i in range(num_columns)
        ]
    else:
        header_fill_colors = ["#dbbfc9"] * num_columns  # Default styling for other cases

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=list(filtered_data.columns),
                    fill_color=header_fill_colors,
                    align="center",
                    font=dict(size=10, color=["white" if color == "green" else "black" for color in header_fill_colors]),
                ),
                cells=dict(
                    values=[filtered_data[col] for col in filtered_data.columns],
                    fill_color="white",
                    align="center",
                    font=dict(size=9, color="black"),
                ),
            )
        ]
    )

    fig.write_image(output_file)


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
    oscilloscope3 = []
    for file in os.listdir(assets_folder):
        if file.endswith((".png", ".jpg")):
            if file.startswith("oscilloscope1"):
                oscilloscope1.append(file)
            if file.startswith("oscilloscope2"):
                oscilloscope2.append(file)
            elif file.startswith("oscilloscope3"):
                oscilloscope3.append(file)
    return sorted(oscilloscope1), sorted(oscilloscope2), sorted(oscilloscope3)

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

def generate_oscilloscope_graphs(data_by_voltage, save_path):
    oscilloscope_graphs = []

    # Trace colors for specific channels
    trace_colors = {
        "CH 1": "yellow",
        "CH 2": "cyan",
        "CH 3": "magenta",
        "CH 4": "blue",
    }

    # Loop through each voltage dataset
    for voltage, data in data_by_voltage.items():
        if "Load Current (A)" not in data.columns:
            continue

        # Identify oscilloscope columns dynamically
        osc_measurements = {}
        for column in data.columns:
            match = re.match(r"(Osc\d+) CH_(\d+) (negative )?(VMax|VMin)", column, re.IGNORECASE)
            if match:
                osc_name, channel, is_negative, measurement = match.groups()
                if osc_name not in osc_measurements:
                    osc_measurements[osc_name] = []
                osc_measurements[osc_name].append((channel, measurement, column, bool(is_negative)))

        # Generate graphs for each oscilloscope, combining VMax and VMin
        for osc_name, measurements in osc_measurements.items():
            fig = go.Figure()

            # Add traces for each channel
            for channel, measurement, column, is_negative in measurements:
                color = trace_colors.get(f"CH {channel}", "black")  # Default to black if channel not in colors
                fig.add_trace(go.Scatter(
                    x=data["Load Current (A)"],
                    y=data[column],
                    mode="lines+markers",
                    name=f"CH {channel} {'Negative ' if is_negative else ''}{measurement}",
                    line=dict(color=color)
                ))

            # Update layout
            fig.update_layout(
                title=f"{osc_name} Measurements vs Load Current for {voltage} V",
                xaxis_title="Load Current (A)",
                yaxis_title="Voltage",
                legend_title="Channel & Measurement",
                height=400,
                width=800,
                margin={"l": 40, "r": 40, "t": 40, "b": 40},
            )

            # Save the graph as a PNG file
            png_filename = f"{osc_name}_{voltage}V.png"
            png_path = os.path.join(save_path, png_filename)
            write_image(fig, png_path)

            # Append to the layout
            oscilloscope_graphs.append(html.Div([
                html.H3(f"{osc_name} Measurements for {voltage} V", className="text-center my-4"),
                html.Div(
                    dcc.Graph(figure=fig),
                    style={"display": "flex", "justifyContent": "center"}  # Center the graph
                )
            ]))

    return oscilloscope_graphs



# Generate the efficiency graph with multiple lines for each voltage
def generate_efficiency_graph(data_by_voltage, save_path):
    graph_data = []
    for voltage, data in data_by_voltage.items():
        if "Load Current (A)" in data.columns and "Efficiency (%)" in data.columns:
            temp_df = data[["Load Current (A)", "Efficiency (%)"]].copy()
            temp_df["Voltage (V)"] = voltage
            graph_data.append(temp_df)

    if graph_data:
        combined_df = pd.concat(graph_data)
        fig = px.line(
            combined_df,
            x="Load Current (A)",
            y="Efficiency (%)",
            color="Voltage (V)",
            markers=True,
            title="Efficiency vs. Input Current for Each Voltage",
            labels={"Current (A)": "Input Current (A)", "Efficiency (%)": "Efficiency (%)"},
        )

        fig.update_yaxes(range=[0, 100])

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
def generate_dash_layout(test_setup_name, notes, data_by_voltage, oscilloscope1_screenshots, oscilloscope2_screenshots, oscilloscope3_screenshots, setup_pictures, osc1_notes, osc2_notes, osc3_notes):
    title_section = html.Div([
        html.H1(test_setup_name, className="text-center my-4"),
        html.H4("Notes:", className="text-center my-2"),
        html.P(notes, className="text-center my-2 text-muted")
    ])

        # Data table sections (excluding the last 4 columns)
    table_sections = []


    for voltage, data in data_by_voltage.items():
        filtered_data = data.loc[:, : "Efficiency (%)"]
        num_columns = len(filtered_data.columns)

        # Determine header groups based on the number of columns
        input_headers = set()
        efficiency_headers = set()
        remaining_headers = set()

        if num_columns == 11:
            input_headers.update(range(6))  # First 6 columns
            efficiency_headers.add(num_columns - 1)  # Last column
            remaining_headers.update(range(6, num_columns - 1))  # Middle columns (pink)
        elif num_columns == 7:
            input_headers.update(range(3))  # First 3 columns
            efficiency_headers.add(num_columns - 1)  # Last column
            remaining_headers.update(range(3, num_columns - 1))  # Middle columns (pink)

        # Initialize the style_header_conditional list
        style_header_conditional = []

        # Add styles for input headers (blue)
        style_header_conditional.extend([
            {
                "if": {"column_id": filtered_data.columns[idx]},
                "backgroundColor": "#b0bfc2",  # Light blue
                "color": "black",
                "fontWeight": "bold",
            }
            for idx in input_headers
        ])

        # Add styles for efficiency headers (green)
        style_header_conditional.extend([
            {
                "if": {"column_id": filtered_data.columns[idx]},
                "backgroundColor": "#b0c2b2",  # Light green
                "color": "black",
                "fontWeight": "bold",
            }
            for idx in efficiency_headers
        ])

        # Add styles for remaining headers (pink)
        style_header_conditional.extend([
            {
                "if": {"column_id": filtered_data.columns[idx]},
                "backgroundColor": "#dbbfc9",  # Light pink
                "color": "black",
                "fontWeight": "bold",
            }
            for idx in remaining_headers
        ])

        # Create the table section
        table_sections.append(html.Div([
            html.H3(f"Test Data for {voltage} V", className="text-center my-4"),
            html.Div(
                dash_table.DataTable(
                    id=f"data-table-{voltage}",
                    columns=[
                        {"name": col, "id": col, "type": "text"}
                        for col in filtered_data.columns
                    ],
                    data=filtered_data.to_dict("records"),
                    style_table={"width": "560px", "margin": "auto", "border": "1px solid lightgray", "overflowX": "hidden"},
                    style_header={  # Default header style
                        "backgroundColor": "#eaeaea",
                        "fontWeight": "bold",
                        "fontSize": "9px",
                        "whiteSpace": "normal",
                        "padding": "2px",
                    },
                    style_header_conditional=style_header_conditional,
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

    def format_notes_with_linebreaks(notes):
        # Add a newline before numbers followed by a parenthesis
        formatted_notes = re.sub(r"(\d\))", r"\n\1", notes)
        return formatted_notes

    def create_image_tile_with_notes_and_caption(img_path, notes):
        # Format notes with line breaks
        formatted_notes = format_notes_with_linebreaks(notes)
        file_name = os.path.basename(img_path).split(".png")[0]  # Extract file name without extension

        return html.Div([
            # Notes section on the left
            html.Div([
                html.Pre(f"Notes: {formatted_notes}", className="text-left text-muted", style={
                    "margin": "5px",
                    "fontSize": "10px",
                    "whiteSpace": "pre-wrap"  # Ensure line breaks are preserved
                })
            ], style={"flex": "1", "padding": "5px"}),  # Flex for notes

            # Image and caption section on the right
            html.Div([
                html.Img(src=f"/assets/{img_path}", style={
                    "width": "100%",
                    "height": "150px",
                    "borderRadius": "5px",
                    "objectFit": "contain",  # Prevent cropping
                    "backgroundColor": "#f8f8f8"  # Add a background to enhance visibility
                }),
                html.P(file_name, className="text-center text-muted", style={"fontSize": "10px", "marginTop": "5px"})  # Caption below the image
            ], style={"flex": "2", "textAlign": "center"}),  # Flex for image and caption

        ], style={
            "display": "flex",
            "flexDirection": "row",
            "width": "400px",
            "height": "200px",
            "border": "1px solid lightgray",
            "borderRadius": "5px",
            "padding": "5px",
            "margin": "5px",
            "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
        })



    def group_screenshots_by_voltage_and_current(screenshots):
        grouped = {}
        for img_path in screenshots:
            parts = os.path.basename(img_path).split("_")
            if len(parts) >= 3 and "V" in parts[1] and "A" in parts[2]:
                voltage = parts[1].replace("V", "")
                current = parts[2].replace("A", "").replace(".png", "").replace(".jpg", "")
                try:
                    # Convert to float for proper numeric sorting
                    voltage = float(voltage)
                    current = float(current)
                except ValueError:
                    continue  # Skip files with invalid formatting

                if voltage not in grouped:
                    grouped[voltage] = {}
                if current not in grouped[voltage]:
                    grouped[voltage][current] = []
                grouped[voltage][current].append(img_path)
        return grouped


    def generate_combined_oscilloscope_section(grouped_screenshots, osc_1, osc_2, osc_3):
        sections = []
        for voltage, currents in sorted(grouped_screenshots.items()):  # Voltage is a float
            voltage_section = [html.H4(f"Oscilloscope Screenshots for {voltage} V", className="text-center my-3")]
            for current, images in sorted(currents.items()):  # Current is a float
                current_section = [html.H5(f"At Current {current} A", className="text-center my-3")]
                current_section.append(html.Div([
                    # Create a row of tiles for each current
                    create_image_tile_with_notes_and_caption(img, 
                        osc_1 if "oscilloscope1" in img else osc_2 if "oscilloscope2" in img else osc_3)
                    for img in images
                ], style={
                    "display": "flex",
                    "flexWrap": "wrap",
                    "justifyContent": "center",  # Center tiles horizontally
                    "alignItems": "center",  # Center tiles vertically
                    "gap": "10px"
                }))
                voltage_section.append(html.Div(current_section, style={"textAlign": "center", "marginBottom": "20px"}))
            sections.append(html.Div(voltage_section, style={"border": "1px solid lightgray", "padding": "10px", "margin": "10px"}))
        return html.Div(sections)



    # Combine all oscilloscope screenshots into one list
    all_screenshots = oscilloscope1_screenshots + oscilloscope2_screenshots + oscilloscope3_screenshots

    # Group by voltage and current
    grouped_screenshots = group_screenshots_by_voltage_and_current(all_screenshots)

    # Generate a single section for all screenshots with tiles and specific notes
# Generate a single section for all screenshots with compact, centered tiles and specific notes
    oscilloscope_section = html.Div([
        html.H3("Combined Oscilloscope Screenshots", className="text-center my-4"),
        generate_combined_oscilloscope_section(grouped_screenshots, osc1_notes, osc2_notes, osc3_notes)
    ], style={"textAlign": "center"})

    

    setup_section = html.Div([
        html.H3("Setup Pictures", className="text-center my-4"),
        html.Div([
            create_image_with_caption(img)
            for img in setup_pictures
        ], style={"textAlign": "center"})
    ])

    oscilloscope_graphs = generate_oscilloscope_graphs(data_by_voltage, "assets/")

    return dbc.Container([
        title_section,
        *table_sections,
        efficiency_graph_section,
        html.Hr(),
        *oscilloscope_graphs,  # Include VMax graphs
        html.Hr(),
        oscilloscope_section,
        html.Hr(),
        setup_section,
    ], fluid=True)

def start_dash_server(app):
    # Start the Dash server
    app.run_server(debug=False, host="127.0.0.1", port=8050)


def main(test_folder, test_setup_name, notes, osc1_notes, osc2_notes, osc3_notes, save_folder):
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
    oscilloscope1_screenshots, oscilloscope2_screenshots, oscilloscope3_screenshots = load_oscilloscope_screenshots(assets_folder)
    setup_pictures = load_setup_pictures(assets_folder)

    generate_pdf(test_folder, test_setup_name, notes, data_by_voltage, oscilloscope1_screenshots, oscilloscope2_screenshots, oscilloscope3_screenshots, assets_folder, setup_pictures, osc1_notes, osc2_notes, osc3_notes)

    shared_drive_folder = save_folder
    copy_test_folder_to_shared_drive(test_folder, shared_drive_folder)
    # Create the Dash app
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.title = test_setup_name

    app.layout = generate_dash_layout(
        test_setup_name,
        notes,
        data_by_voltage,
        oscilloscope1_screenshots,
        oscilloscope2_screenshots,
        oscilloscope3_screenshots,
        setup_pictures,
        osc1_notes,
        osc2_notes,
        osc3_notes
    )

    # Start the Dash server
    host = "127.0.0.1"
    port = 8050
    print(f"\nDashboard is running! Open your browser and go to: https://{host}:{port}\n")
    app.run_server(debug=True, host=host, port=port)
  
    




if __name__ == "__main__":
    if len(sys.argv) < 13:
        print("Usage: python dashboard.py <test_folder> <test_setup_name> <notes> <osc1_ch1> <osc1_ch2> <osc1_ch3> <osc1_ch4> <osc2_ch1> <osc2_ch2> <osc2_ch3> <osc2_ch4>")
        sys.exit(1)

    test_folder = sys.argv[1]
    test_setup_name = sys.argv[2]
    notes = sys.argv[3].replace("_", " ")
    osc1_notes = f"Oscilloscope 1 Channels: 1) {sys.argv[4].replace('_', ' ')} 2) {sys.argv[5].replace('_', ' ')} 3) {sys.argv[6].replace('_', ' ')} 4) {sys.argv[7].replace('_', ' ')}"
    osc2_notes = f"Oscilloscope 2 Channels: 1) {sys.argv[8].replace('_', ' ')} 2) {sys.argv[9].replace('_', ' ')} 3) {sys.argv[10].replace('_', ' ')} 4) {sys.argv[11].replace('_', ' ')}"
    osc3_notes = f"Oscilloscope 3 Channels: 1) {sys.argv[12].replace('_', ' ')} 2) {sys.argv[13].replace('_', ' ')} 3) {sys.argv[14].replace('_', ' ')} 4) {sys.argv[15].replace('_', ' ')}"
    save_folder = sys.argv[16]
    main(test_folder, test_setup_name, notes, osc1_notes, osc2_notes, osc3_notes, save_folder)


