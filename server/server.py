import json
import os
import pandas as pd
import datetime as dt
import pytz
from dateutil.tz import tzlocal
import plotly.express as px
import pandas as pd
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from flask import Flask, render_template
import mariadb

app = Flask(__name__)

@app.route('/')
def status():

    # Setup connection
    conn = mariadb.connect(
    user=os.environ['DOTA_USERNAME'],
    password=os.environ['DOTA_PASSWORD'],
    host=os.environ["DOTA_HOSTNAME"],
    database=os.environ['DOTA_DATABASE'])
    c=conn.cursor()

    skill_dict = {
        1: 'Normal Skill',
        2: 'High Skill',
        3: 'Very High Skill',        
    }

    #---------------------------------------------------------------
    # Win rate by skill level
    #---------------------------------------------------------------
    df_sql=pd.read_sql("select * from fetch_win_rate",conn)
    df_sql['skill']=[int(t.split("_")[-1]) for t in df_sql['hero_skill']]
   
    radiant_vs_dire=[]
    fig=make_subplots(
            rows=1,
            cols=3,
            subplot_titles=("Normal","High","Very High"))

    counter=1
    for skill in list(set(df_sql['skill'])):
        df_sub=df_sql[df_sql['skill']==skill]
        radiant_vs_dire.append( 
                100*(df_sub.sum()['radiant_win']/\
                    (df_sub.sum()['radiant_total'])))
    
        time_range=set(df_sub['time_range']).pop()
        title="{1} UTC".format(skill_dict[skill], time_range)
        
        fig.add_trace(go.Scatter(
                            x=df_sub['total'].values, 
                            y=df_sub['win_pct'].values, 
                            text=df_sub['hero'].values,
                            mode='markers+text',
                            textposition='top center'),
                          row=1,
                          col=counter)
        counter=counter+1

    fig.update_layout(title=title,
                     height=600,
                     width=1600,
                     showlegend=False)
    fig.update_xaxes({'title' : 'Number of Games'})
    fig.update_yaxes({'title' : 'Win %'})
    win_rate_figs=json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    #-----------------------------------------------------------------
    # Record count health metrics
    #-----------------------------------------------------------------

    # Start with empty dataframe, by hour
    DAYS=7
    TIMEZONE=pytz.timezone("US/Eastern")
    UTC=pytz.timezone("UTC")

    utc_offset=TIMEZONE.utcoffset(dt.datetime.now())
    utc_hour=int(utc_offset.total_seconds()/3600)
 
    now=dt.datetime.utcnow().astimezone(TIMEZONE) 
    now_hour=dt.datetime(now.year, now.month, now.day, now.hour, 0, 0)

    times=[(now_hour-dt.timedelta(hours=i)).strftime("%Y-%m-%dT%H:00:00%z") for i in range(24*DAYS)]
    times=["{0}{1:+03d}00".format(t,utc_hour) for t in times]

    df_summary1=pd.DataFrame(index=times, data={
                                            1 : [0]*len(times), 
                                            2 : [0]*len(times), 
                                            3 : [0]*len(times), 
                                          })

    # Fetch from database
    begin=int((dt.datetime.utcnow()-dt.timedelta(days=DAYS)).timestamp())
    begin=str(begin)+"_0"
    c.execute("select date_hour_skill, rec_count from fetch_summary where date_hour_skill>='{}'".format(begin))
    rows=c.fetchall()

    # Split out times and localize to current timezone (East Coast US)
    # Note that using pytz causes the timestamps to localize relative
    # to the stated time and not current time. To avoid discontinuities
    # we'll localize to current time.
    times=[dt.datetime.utcfromtimestamp(int(t[0].split("_")[0])) for t in rows]
    times=[t-utc_offset for t in times]
    times=[t.strftime("%Y-%m-%dT%H:00:00") for t in times]
    times=["{0}{1:+03d}00".format(t,utc_hour) for t in times]

    # Get remaining fields
    skills=[int(t[0].split("_")[1]) for t in rows]
    rec_count=[t[1] for t in rows]

    # Pivot for tablular view
    df_summary2=pd.DataFrame({
        'date_hour' : times,
        'skill' : skills,
        'count' : rec_count
        })
    df_summary2=df_summary2.pivot(index='date_hour', columns='skill', values='count').fillna(0).astype('int32').sort_index(ascending=False)
    df_summary=df_summary1.add(df_summary2, fill_value=0)

    # Rename columns
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
                            radiant_vs_dire=radiant_vs_dire,
                            win_rate_figs=win_rate_figs,
                            rows=rows, 
                            record_count_plot=record_count_plot)
