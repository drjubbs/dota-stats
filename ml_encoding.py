"""Encoding for Classification

See `win_classification` notebook for full description.

"""
import logging
import datetime as dt
import sys
import meta
import numpy as np
import mariadb
import os
from scipy import sparse
import ujson as json
import pickle


def first_order_vector(rad_heroes, dire_heroes):
    """Generate vector encoding hero selections. Length
    of vector is 2N, where [0:N] are {0,1} indicating radiant
    selection, and [N:N2] are {0,1} indicating dire.

         1 = Radiant
        -1 = Dire

    """
    X1=np.zeros(len(meta.HEROES)*2, dtype='b')
    for rh in rad_heroes:
        X1[meta.HEROES.index(rh)]=1
    for dh in dire_heroes:
        X1[meta.NUM_HEROES+meta.HEROES.index(dh)]=-1
    return X1


def second_order_hmatrix(rad_heroes, dire_heroes):
    """For a list of radiant and dire heroes, create an upper triangular matrix
    indicating radiant/dire pairs. By convention, 1 indicates first hero in i,j
    is on dire, -1 indicates first hero was on dire.
    
    rad_heroes: radiant heroes, numerical by enum
    dire_heroes: radiant heroes, numerical by enum
    
    """    
    X2=np.zeros([meta.NUM_HEROES,meta.NUM_HEROES], dtype='b')
    for rh in rad_heroes:
        for dh in dire_heroes:
            irh=meta.HEROES.index(rh)
            idh=meta.HEROES.index(dh)            
            if idh>irh:
                X2[irh,idh]=1
            if idh<irh:                
                X2[idh,irh]=-1
            if idh==irh:
                raise ValueError("Duplicate heroes: {} {}".format(rad_heroes,dire_heroes))
    return X2


def flatten_second_order_upper(X_in):    
    """Unravel upper triangular matrix into flat vector, skipping
    diagonal"""
    size=X_in.shape[1]
    X_flat=np.zeros(int(size*(size-1)/2), dtype='b')
    counter=0
    for i in [t for t in range(size)]:
        for j in [t+i+1 for t in range(size-i-1)]:            
            X_flat[counter]=X_in[i,j]
            counter=counter+1
    return X_flat


def unflatten_second_order_upper(vec):
    """Create upper triangular matrix from flat vector, skipping
    diagonal"""
    m=int((1+(1+8*vec.shape[0])**(0.5))/2)
    X=np.zeros([m,m])
    counter=0
    for i in range(m):
        for j in [t+i+1 for t in range(m-i-1)]:
            X[i,j]=vec[counter]
            X[j,i]=-vec[counter]            
            counter=counter+1
    return X


def create_features(begin,end,skill):
    """Main entry point to create first and second order
    features for classification.
    
    Returns:
        y: Target, 1 = radiant win, 0 = dire win
        X1: 2*N, heroes, 0:N radiant, N:2N dire
        X2: flatten upper triangular hero - vs. other team interaction
        X3: X1 + X2
    """
    

    # Database fetch
    conn = mariadb.connect(
        user=os.environ['DOTA_USERNAME'],
        password=os.environ['DOTA_PASSWORD'],
        host='192.168.86.120',
        #os.environ['DOTA_HOSTNAME'],
        database=os.environ['DOTA_DATABASE'])
    c=conn.cursor()

    # Fetch all rows
    stmt="SELECT start_time, match_id, radiant_heroes, dire_heroes, radiant_win FROM dota_matches WHERE start_time>={0} and start_time<={1} and api_skill={2}".format(
        int(begin.timestamp()),
        int(end.timestamp()),
        skill)

    c.execute(stmt)
    rows=c.fetchall()
    print("Records: {}".format(len(rows)))

    # Setup the targets
    y=np.array([t[-1] for t in rows])

    X1=np.zeros([len(rows),2*meta.NUM_HEROES], dtype='b')
    X2=np.zeros([len(rows),int(meta.NUM_HEROES*(meta.NUM_HEROES-1)/2)], dtype='b')

    # X3 = X1 + X2 concatenated
    X3=np.zeros([len(rows), X1.shape[1]+X2.shape[1]], dtype='b')

    counter=0
    for row in rows:
        t1=first_order_vector(json.loads(row[2]),json.loads(row[3]))        
        t2=flatten_second_order_upper(
                second_order_hmatrix(json.loads(row[2]), json.loads(row[3])))

        X1[counter,:]=t1
        X2[counter,:]=t2    
        X3[counter,:]=np.concatenate([t1,t2])    

        if counter % 10000 == 0:
            print("{} of {}".format(counter,len(rows)))
        counter=counter+1

    return (y, X1, X2, X3)
