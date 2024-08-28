import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import warnings

warnings.filterwarnings("ignore")


def gen(df, color_palette, layout_palette, color_trans):
    if len(df.index) == 0:
        p_fig = go.Figure(data=[go.Pie(values=[0], hole=.5, marker=dict(colors=[color_trans['blue']]), direction='clockwise', sort=False)])
        
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

    p_spent = 0
    p_remaining = 0
    p_overdraft = 0

    percent_spent = int(df['transaction_amount'].sum() / df['goal_target_amount'].sum() * 100)

    colors = [color_palette['red'],color_palette['blue'],color_trans['blue']]

    if df['transaction_amount'].sum() > df['goal_target_amount'].sum():
        p_spent = df['goal_target_amount'].sum()
        p_remaining = 0
        p_overdraft = df['transaction_amount'].sum() - df['goal_target_amount'].sum()
    else:
        p_spent = df['transaction_amount'].sum()
        p_remaining = df['goal_target_amount'].sum() - df['transaction_amount'].sum()
        p_overdraft = 0

    values = [p_overdraft, p_spent, p_remaining]

    p_fig = go.Figure(data=[go.Pie(values=values, hole=.7, marker=dict(colors=colors), direction='clockwise', sort=False, labels=['Overspent','Spent','Remaining'])])

    status = ''
    if percent_spent < 70: status = 'Great'
    elif percent_spent < 80: status = 'Good'
    elif percent_spent < 90: status = 'Warning'
    elif percent_spent < 100: status = 'Close'
    else: status = 'Bad'

    def bgstatus_color():
        if status == 'Great':
            return color_palette['green']
        elif status == 'Good':
            return '#d1e231'
        elif status == 'Warning':
            return color_palette['yellow']
        elif status == 'Close':
            return color_palette['orange']
        else: return color_palette['red']

    p_fig.update_layout(dict(
        title = dict(text=''),
        font = dict(family="Poppins"),
        paper_bgcolor=layout_palette['black'],
        plot_bgcolor=layout_palette['black'],
        font_family="Poppins",
        font_color=layout_palette['white'],
        showlegend=False,
        annotations=[dict(text='<b> '+str(percent_spent) + '% </b>', x=0.5, y=0.55, font_size=20, showarrow=False, bordercolor=(bgstatus_color()), borderwidth = 5),
                                dict(text='$' + str('{:,}'.format(int(p_spent + p_overdraft))) + " spent", x=0.5, y=0.35, font_size=12, showarrow=False)],
        hoverlabel=dict(bgcolor=layout_palette['darkgray'],font_family="Poppins",font_size=14,font_color=layout_palette['white']),
        margin=dict(t=40,b=40,l=40,r=40)
    ))

    p_fig.update_traces(hoverinfo='value+label',hovertemplate='$%{value}<extra></extra>',textinfo = 'none')

    return p_fig  