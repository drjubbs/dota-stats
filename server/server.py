# -*- coding: utf-8 -*-
"""Flask server to display analytics results, uses a common instance of 
SQLAlchemy to deal with concurrency.
"""
import json
import os
import datetime as dt
import pandas as pd
import pytz
import plotly
import plotly.graph_objs as go
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
DB_URI="mysql://{0}:{1}@{2}/{3}".format(
            os.environ['DOTA_USERNAME'],
            os.environ['DOTA_PASSWORD'],
            os.environ["DOTA_HOSTNAME"],
            os.environ['DOTA_DATABASE'],
            )
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


def get_health_metrics(days, timezone):
    """Returns a Pandas dataframe summarizing number of matches processed
    over an interval of days."""

    # Start with empty dataframe, by hour
    local_tz=pytz.timezone(timezone)

    utc_offset=local_tz.utcoffset(dt.datetime.now())
    utc_hour=int(utc_offset.total_seconds()/3600)

    now=dt.datetime.utcnow()
    now=now+utc_offset
    now_hour=dt.datetime(now.year, now.month, now.day, now.hour, 0, 0)

    times=[(now_hour-dt.timedelta(hours=i)).strftime("%Y-%m-%dT%H:00:00")\
                for i in range(24*days)]
    times=["{0}{1:+03d}00".format(t,utc_hour) for t in times]

    df_summary1=pd.DataFrame(index=times, data={
                                            1 : [0]*len(times),
                                            2 : [0]*len(times),
                                            3 : [0]*len(times),
                                          })

    # Fetch from database
    begin=int((dt.datetime.utcnow()-dt.timedelta(days=days)).timestamp())
    begin=str(begin)+"_0"
    stmt="select date_hour_skill, rec_count from fetch_summary "
    stmt+="where date_hour_skill>='{}'"
    rows=pd.read_sql_query(stmt.format(begin), Base.engine)

    date_hour_skill = rows['date_hour_skill'].tolist()
    rec_count = rows['rec_count'].tolist()

    # Split out times and localize to current timezone (East Coast US)
    # Note that using pytz causes the timestamps to localize relative
    # to the stated time and not current time. To avoid discontinuities
    # we'll localize to current time.
    times=[dt.datetime.utcfromtimestamp(int(t.split("_")[0]))\
            for t in date_hour_skill]
    times=[t+utc_offset for t in times]
    times=[t.strftime("%Y-%m-%dT%H:00:00") for t in times]
    times=["{0}{1:+03d}00".format(t,utc_hour) for t in times]

    # Get remaining fields
    skills=[int(t.split("_")[1]) for t in date_hour_skill]

    # Pivot for tablular view
    df_summary2=pd.DataFrame({
        'date_hour' : times,
        'skill' : skills,
        'count' : rec_count
        })
    df_summary2=df_summary2.pivot(index='date_hour',
                                  columns='skill', values='count').\
                                          fillna(0).\
                                          astype('int32').\
                                          sort_index(ascending=False)
    df_summary=df_summary1.add(df_summary2, fill_value=0)

    # Rename columns
    df_summary=df_summary[[1,2,3]]
    df_summary.columns=['normal', 'high', 'very_high']
    df_summary=df_summary.sort_index(ascending=False)

    # For summary table
    rows=zip(df_summary.index.values,
             df_summary['normal'].values,
             df_summary['high'].values,
             df_summary['very_high'].values)

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
    record_count_plot=json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return record_count_plot, rows

@app.route('/')
def status():
    """Index page for server, currently contains everything on the site"""

    #---------------------------------------------------------------
    # Win rate by skill level
    #---------------------------------------------------------------

    df_sql=pd.read_sql_table("fetch_win_rate",Base.engine)
    df_sql['skill']=[int(t.split("_")[-1]) for t in df_sql['hero_skill']]

    radiant_vs_dire=[]
    pick_vs_win={}

    for skill in list(set(df_sql['skill'])):
        df_sub=df_sql[df_sql['skill']==skill]
        radiant_vs_dire.append(
                100*(df_sub.sum()['radiant_win']/\
                    (df_sub.sum()['radiant_total'])))

        pick_vs_win[skill] = go.Figure(
            go.Scatter(
                x=df_sub['total'].values,
                y=df_sub['win_pct'].values,
                text=df_sub['hero'].values,
                mode='markers+text',
                textposition='top center'))

        pick_vs_win[skill].update_layout(title="Skill {0}".format(skill),
                     height=700,
                     width=700)
        pick_vs_win[skill].update_xaxes({'title' : 'Number of Games'})
        pick_vs_win[skill].update_yaxes({'title' : 'Win %'})

    win_rate_1 = json.dumps(pick_vs_win[1], cls=plotly.utils.PlotlyJSONEncoder)
    win_rate_2 = json.dumps(pick_vs_win[2], cls=plotly.utils.PlotlyJSONEncoder)
    win_rate_3 = json.dumps(pick_vs_win[3], cls=plotly.utils.PlotlyJSONEncoder)

    #---------------------------------------------------------------
    # Health metrics
    #---------------------------------------------------------------
    rec_plot14, _ = get_health_metrics(14, 'US/Eastern')
    rec_plot3, rec_count_table = get_health_metrics(3, 'US/Eastern')
    return render_template("index.html",
                            radiant_vs_dire=radiant_vs_dire,
                            win_rate_1=win_rate_1,
                            win_rate_2=win_rate_2,
                            win_rate_3=win_rate_3,
                            rec_count_table=rec_count_table,
                            rec_plot3=rec_plot3,
                            rec_plot14=rec_plot14,)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
