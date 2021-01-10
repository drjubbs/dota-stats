# -*- coding: utf-8 -*-
"""Flask server to display analytics results, uses a common instance of
SQLAlchemy to deal with concurrency.
"""
import json
import os
import plotly
import plotly.graph_objs as go
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from dota_stats import win_rate_pick_rate, fetch_summary

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DOTA_DB_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


def get_health_chart(days, timezone, hour=True):
    """Fetches a statistics health summary table and formats into a plotly
    chart."""

    df_summary, rows = fetch_summary.get_health_summary(days, timezone, hour)

    # For plot
    fig = go.Figure(data=[
        go.Bar(name='Normal',
               x=df_summary.index.values,
               y=df_summary['normal']),
        go.Bar(name='High',
               x=df_summary.index.values,
               y=df_summary['high']),
        go.Bar(name='Very High',
               x=df_summary.index.values,
               y=df_summary['very_high']),
    ])
    fig.update_layout(barmode='stack')
    record_count_plot = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return record_count_plot, rows


@app.route('/')
def status():
    """Index page for server, currently contains everything on the site"""

    # Win rate / pick rate by skill level
    df_sql = win_rate_pick_rate.get_current_win_rate_table(3)

    radiant_vs_dire = []
    pick_vs_win = {}

    time_range = list(set(df_sql['time_range']))[0]

    for skill in list(set(df_sql['skill'])):
        df_sub = df_sql[df_sql['skill'] == skill]
        radiant_vs_dire.append(
            100 * (df_sub.sum()['radiant_win'] /
                   (df_sub.sum()['radiant_total'])))

        pick_vs_win[skill] = go.Figure(
            go.Scatter(
                x=df_sub['total'].values,
                y=df_sub['win_pct'].values,
                text=df_sub['hero'].values,
                mode='markers+text',
                textposition='top center'))

        pick_vs_win[skill].update_layout(
            title="Skill {0}: {1}".format(skill, time_range),
            margin=dict(l=20, r=0, t=50, b=20),
            height=550,
            width=550)
        pick_vs_win[skill].update_xaxes({'title': 'Number of Games'})
        pick_vs_win[skill].update_yaxes({'title': 'Win %'})

    win_rate_1 = json.dumps(pick_vs_win[1], cls=plotly.utils.PlotlyJSONEncoder)
    win_rate_2 = json.dumps(pick_vs_win[2], cls=plotly.utils.PlotlyJSONEncoder)
    win_rate_3 = json.dumps(pick_vs_win[3], cls=plotly.utils.PlotlyJSONEncoder)

    # ---------------------------------------------------------------
    # Health metrics
    # ---------------------------------------------------------------
    rec_plot30, _ = get_health_chart(30, 'US/Eastern', hour=False)
    rec_plot3, rec_count_table = get_health_chart(3, 'US/Eastern')

    return render_template("index.html",
                           radiant_vs_dire=radiant_vs_dire,
                           win_rate_1=win_rate_1,
                           win_rate_2=win_rate_2,
                           win_rate_3=win_rate_3,
                           rec_count_table=rec_count_table,
                           rec_plot3=rec_plot3,
                           rec_plot30=rec_plot30, )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
