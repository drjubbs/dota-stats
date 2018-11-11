from flask import Flask, render_template
app = Flask(__name__)
import datetime as dt
import json
import pytz
import pandas as pd
import mysql.connector as mariadb
import os

nytz=pytz.timezone("America/New_York")
utc=pytz.timezone("UTC")


def count_data():    
    conn = mariadb.connect(host=os.environ["DOTA_SQL_HOST"], 
                           user=os.environ["DOTA_SQL_USER"],
                           password=os.environ["DOTA_SQL_PASS"],
                           database=os.environ["DOTA_SQL_DB"])
    cur = conn.cursor()            

    
    t=[]
    my_dates=[]
    my_fetch=[]

    cur.execute("select * from stats order by batch_time DESC")
    
    for row in cur.fetchall():
        this_time=dt.datetime.strptime(str(row[0]),"%Y%m%d%H")
        my_dates.append(this_time.strftime("%Y-%m-%d %H:00"))
        my_fetch.append(row[2])
        t.append((row[0], 
                  utc.localize(this_time).astimezone(nytz).\
                    strftime("%Y-%m-%d %H:00:00"), 
                  row[2], 
                  row[3]))

    # Last 5 days
    df=pd.DataFrame(t)
    df.columns=["hour","time","raw","processed"]
    df[df['hour']>=(max(df['hour'])-5*100)]
    return(df)


@app.route('/')
def hello_world():

    df=count_data()

    plt_dict={
        'type' : 'bar',
        'x' : list(df['time'].tolist()),
        'y' : list(df['raw'].tolist())
    }
    
    t=zip(df['time'],df['raw'])
    return(render_template("index.html", rows=t, plt_dict=json.dumps(plt_dict)))
    
if __name__ == "__main__":
    app.run()
    
