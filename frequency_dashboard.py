import os
import sys
import pandas as pd
from dash import Dash, html, dcc, dash_table
import plotly.express as px


def create_dashboard(test_name, test_folder, save_folder):
    """
    Create a frequency sweep dashboard using Dash and Plotly Express.
    """
    app = Dash(__name__)

    # Load test data
    all_test_data = {}
    for file in os.listdir(test_folder):
        if file.endswith(".csv"):
            voltage = file.split("_")[-1].replace("V.csv", "")  # Extract voltage from filename
            file_path = os.path.join(test_folder, file)
            all_test_data[voltage] = pd.read_csv(file_path)

    # Efficiency vs. Frequency Graph
    graph_data = pd.DataFrame()
    for voltage, data in all_test_data.items():
        temp_data = data.copy()
        temp_data["Voltage"] = voltage
        graph_data = pd.concat([graph_data, temp_data], ignore_index=True)

    efficiency_fig = px.line(
        graph_data,
        x="Frequency (kHz)",
        y="Efficiency (%)",
        color="Voltage",
        title=f"Efficiency vs. Frequency at {graph_data['Load Current (A)'].iloc[0]:.2f} A",
        labels={"Efficiency (%)": "Efficiency (%)", "Frequency (kHz)": "Frequency (kHz)", "Voltage": "Voltage (V)"},
        markers=True,
    )
    efficiency_fig.update_layout(
        margin={"l": 40, "r": 40, "t": 40, "b": 40},
        height=400,
        width=600,
        template="plotly_white",
        title={"x": 0.5, "xanchor": "center"},
        legend={"title": "Voltage (V)"},
        yaxis_range=[50, 100],  # Set y-axis range between 0.50 and 1
    )

    # Test Data Tables
    table_sections = []
    for voltage, table_data in all_test_data.items():
        table_sections.append(html.Div([
            html.H3(f"Test Data for {voltage} V", className="text-center my-4"),
            dash_table.DataTable(
                id=f"data-table-{voltage}",
                columns=[
                    {"name": col, "id": col, "type": "text"} for col in table_data.columns
                ],
                data=table_data.to_dict("records"),
                style_table={
                    "width": "600px", 
                    "margin": "auto", 
                    "border": "1px solid lightgray", 
                    "overflowX": "hidden"},
                style_header={
                    "backgroundColor": "#f4f4f4",
                    "fontWeight": "bold",
                    "fontSize": "10px",
                    "padding": "5px",
                },
                style_cell={
                    "textAlign": "center",
                    "padding": "5px",
                    "fontSize": "10px",
                    "whiteSpace": "normal",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
                # style_data_conditional=[
                #     {
                #         "if": {"filter_query": "{Efficiency (%)} > 80"},
                #         "backgroundColor": "#d4f8e8",
                #         "color": "black",
                #     }
                # ],
            )
        ], style={"textAlign": "center"}))


    # Setup Images
    image_files = [f for f in os.listdir("assets") if f.endswith(".png")]
    image_sections = html.Div([
        html.H2("Setup Images", className="text-center my-4", style={"textAlign": "center"}),
        html.Div([
            html.Img(src=f"/assets/{img}", style={"width": "45%", "margin": "10px"})
            for img in image_files
        ], style={"textAlign": "center"}),
    ])

    # Layout
    app.layout = html.Div([
        html.H1(
        f"{test_name.replace('_', ' ')} Dashboard", 
        style={"textAlign": "center", "marginTop": "20px", "marginBottom": "20px"}),

        *table_sections,  # Tables first
        html.Hr(),
        # html.H2("Efficiency vs Frequency Graph", className="text-center my-4", style = {"textAlign": "center"} ),
        html.Div([
        html.H2("Efficiency vs. Frequency Graph", className="text-center my-4"),
        dcc.Graph(figure=efficiency_fig),
    ],
    style={"display": "flex", "flexDirection": "column", "alignItems": "center", "justifyContent": "center"},),
        html.Hr(),
        image_sections  # Images at the bottom
    ], style={"fontFamily": "Arial, sans-serif", "lineHeight": "1.6"})

    return app





if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python frequency_dashboard.py <test_folder> <test_name> <save_folder>")
        sys.exit(1)

    test_folder = sys.argv[1]
    test_name = sys.argv[2]
    save_folder = sys.argv[3]

    app = create_dashboard(test_name, test_folder, save_folder)
    app.run_server(debug=True)