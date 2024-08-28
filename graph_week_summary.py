import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import warnings

warnings.filterwarnings("ignore")

def gen(w_df, selected_month, color_palette, layout_palette, cat_colors, month_dict):
    if len(w_df.index) == 0:
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

    w_fig = px.bar(w_df, x='week', y='transaction_amount', color='goal_name', custom_data=['goal_name'], color_discrete_sequence=cat_colors,hover_data=['transaction_amount','goal_name'])

    w_fig.update_layout(dict(
        title=dict(text='<b>Spending Overview by Week</b>',font=dict(size=14),x=0.5,y=.95),
        font_family="Poppins",
        font_color=layout_palette['white'],
        yaxis=dict(title='$ USD'),
        xaxis=dict(title=dict(text='Weeks in '+ month_dict[selected_month])),
        paper_bgcolor=layout_palette['black'],
        plot_bgcolor=layout_palette['black'],
        bargap=0.5,
        showlegend=True,
        font=dict(color=layout_palette['white']),
        yaxis_gridcolor=layout_palette['lightgray'],
        yaxis_griddash='dot',
        legend=dict(title=dict(text='<b>Bucket</b>',font_size=14),font_size=12),
        hoverlabel=dict(bgcolor=layout_palette['darkgray'],font_family="Poppins",font_size=14,font_color=layout_palette['white']),
        margin=dict(t=40,b=40,l=40,r=40)

    ))

    w_fig.update_traces(marker_line_width = 0,selector=dict(type="bar"),hovertemplate='%{customdata[0]}: $%{y}<extra></extra>')

    w_fig.update_xaxes(ticklabelstep=2, tickfont=dict(color='rgba(0, 0, 0, 0)'))

    totals = w_df.drop(columns=['goal_name'])

    totals = totals.groupby(['week'], as_index=False)['transaction_amount'].sum()

    totals = totals.round({'transaction_amount':2})

    w_fig.add_trace(go.Scatter(
    x=totals['week'], 
    y=totals['transaction_amount'],
    text=totals['transaction_amount'],
    mode='text',
    textposition='top center',
    textfont=dict(
        size=12,
    ),
    showlegend=False,
    hoverinfo='none'
    ))

    return w_fig