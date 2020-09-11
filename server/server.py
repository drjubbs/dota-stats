import json
import os
import pandas as pd
import datetime as dt
import pytz
import plotly.express as px
import pandas as pd
import plotly
import plotly.graph_objs as go
from flask import Flask, render_template
import mariadb

app = Flask(__name__)

@app.route('/')
def status():

    conn = mariadb.connect(
    user=os.environ['DOTA_USERNAME'],
    password=os.environ['DOTA_PASSWORD'],
    host=os.environ["DOTA_HOSTNAME"],
    database=os.environ['DOTA_DATABASE'])
    c=conn.cursor()

    # Limit window of record counts
    begin=int((dt.datetime.utcnow()-dt.timedelta(days=3)).timestamp())
    begin=str(begin)+"_0"
    c.execute("select date_hour_skill, rec_count from fetch_summary where date_hour_skill>='{}'".format(begin))
    rows=c.fetchall()

    # Split out times and localize to my server timezone (East Coast US)
    mytz=pytz.timezone("US/Eastern")
    times=[dt.datetime.fromtimestamp(int(t[0].split("_")[0])) for t in rows]
    times=[mytz.localize(t).strftime("%Y-%m-%dT%H:00:00") for t in times]
    # Get remaining fields
    skills=[int(t[0].split("_")[1]) for t in rows]
    rec_count=[t[1] for t in rows]

    # Pivot for tablular view
    df_summary=pd.DataFrame({
        'date_hour' : times,
        'skill' : skills,
        'count' : rec_count
        })
    df_summary=df_summary.pivot(index='date_hour', columns='skill', values='count').fillna(0).astype('int32').sort_index(ascending=False)
    df_summary=df_summary[[1,2,3]]
    df_summary.columns=['normal', 'high', 'very_high']

    # For summary table
    rows=zip(df_summary.index.values,
             df_summary['normal'].values, 
             df_summary['high'].values, 
             df_summary['very_high'].values)

    # For plot
    fig = go.Figure(data=[
            go.Bar(name='Normal', x=df_summary.index.values, y=df_summary['normal']),
            go.Bar(name='High', x=df_summary.index.values, y=df_summary['high']),
            go.Bar(name='Very High', x=df_summary.index.values, y=df_summary['very_high']),
        ])
    fig.update_layout(barmode='stack')
    record_count_plot=json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template("index.html", 
                            rows=rows, 
                            record_count_plot=record_count_plot)
