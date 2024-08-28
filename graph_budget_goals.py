import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import warnings

warnings.filterwarnings("ignore")

def gen(df, color_palette, layout_palette):
    if len(df.index) == 0:
        p_fig = go.Figure(data=[go.Pie(values=[0], hole=.5, direction='clockwise', sort=False)])
        
        p_fig.update_layout(dict(
        title=dict(text='<b>No Transaction Data</b>',font=dict(size=14),x=0.5,y=0.5),
        font = dict(family="Poppins"),
        paper_bgcolor=layout_palette['black'],
        plot_bgcolor=layout_palette['black'],
        font_family="Poppins",
        font_color=layout_palette['white'],
        showlegend=False,
        margin=dict(t=40,b=40,l=40,r=40)
        ))
        #p_fig.update_traces(hoverinfo='value+label',hovertemplate='$%{value}<extra></extra>',textinfo = 'none')
        return p_fig


    fig = go.Figure(data=[
        go.Bar(name='Spent',x=df['goal_name'], y=df['plot_amount_spent'], marker={'color':color_palette['blue'],},hovertemplate='$%{y}<extra></extra>'),
        go.Bar(name='Remaining',x=df['goal_name'], y=df['plot_budget_remaining'], marker={'color':color_palette['blue'],'opacity':0.4},hovertemplate='$%{y}<extra></extra>'),
        go.Bar(name='Overspent',x=df['goal_name'], y=df['plot_overdraft'], marker={'color':color_palette['red']},hovertemplate='$%{y}<extra></extra>')
        ]
    )

    fig.update_layout(dict(
        barmode='stack',
        title=dict(text='<b>Budget Performance by Bucket</b>',font=dict(size=14),x=0.5,y=0.90),
        font_family="Poppins",
        font_color=layout_palette['white'],
        yaxis=dict(title='$ USD'),
        paper_bgcolor=layout_palette['black'],
        plot_bgcolor=layout_palette['black'],
        bargap=0.6,
        showlegend=False,
        font=dict(color=layout_palette['white']),
        yaxis_gridcolor=layout_palette['lightgray'],
        yaxis_griddash='dot',
        hoverlabel=dict(bgcolor=layout_palette['darkgray'],font_family="Poppins",font_size=14,font_color=layout_palette['white']),
        margin=dict(t=60,b=40,l=40,r=40)
    ))

    fig.update_traces(marker_line_width = 0,selector=dict(type="bar"))

    fig.update_xaxes(tickfont=dict(size = 14))

    df = df.round({'transaction_amount':2})

    fig.add_trace(go.Scatter(
    x=df['goal_name'], 
    y=df['transaction_amount'],
    text=df['transaction_amount'],
    mode='text',
    textposition='top center',
    textfont=dict(
        size=12,
    ),
    showlegend=False,
    hoverinfo='none'
    ))

    return fig

