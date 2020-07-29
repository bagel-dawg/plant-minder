import plotly.graph_objects as go
from plotly import tools
from plotly.subplots import make_subplots
import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta
from itertools import product

def generate_graph(time_deltas, db_con):
    d = datetime.now()
    grid_num = int(len(time_deltas) / 2)
    fig = make_subplots(
        rows=grid_num,
        cols=grid_num,
        shared_xaxes=False,
        vertical_spacing=0.05,
        specs=[
            [{"type": "scatter"}, {"type": "scatter"}],
            [{"type": "scatter"}, {"type": "scatter"}]
        ]
    )

    grids = list(product(range(grid_num), range(grid_num)))
    for index, time_delta in enumerate(time_deltas):
        query = "SELECT * FROM environment WHERE env_timestamp BETWEEN '{d1}' AND '{d2}'".format(d1=time_delta, d2=d)
        df = pd.read_sql_query(query, db_con)
        fig.add_trace(
            go.Scatter(
                line_shape='spline',
                x=df['env_timestamp'],
                y=df['temperature'],
                mode="lines",
                name='Temperature',
                legendgroup="group",
                line=dict(color='blue')
            ),
            row=grids[index][0]+1, col=grids[index][1]+1
        )
        fig.add_trace(
            go.Scatter(
                line_shape='spline',
                x=df['env_timestamp'],
                y=df['humidity'],
                mode="lines",
                name='Humidity',
                legendgroup="group",
                line=dict(color='red')
            ),
            row=grids[index][0]+1, col=grids[index][1]+1
        )
    
    fig.update_yaxes(range=[30,100], showgrid=True, gridwidth=1)
    
    fig.write_html(file="templates/charts.html", include_plotlyjs=False, full_html=False)