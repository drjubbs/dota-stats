"""
## Encoding for Classification

## First order effects

Encode match data for classifiers to determine probability of a radiant win. It's tempting to write a linear logistic regression model 
like this:

`log(p/(1-p)) = c0 + x1*c1 + x2*c2 + x3*c3 + ... `

where `c0` is the intercept and represents the contribution from being on radiant, `x1` .. `xn` are indicator variables, 
where `1` indicates the hero was selected on radiant, and `-1` indicates the hero was selected on dire. The issue here 
is that the interpretation of the coefficients becomes difficult. If `c1` is high, does that mean a high win rate for 
radiant or a high loss rate for dire? This assumes that each hero has symmetric effects, radiant vs. dire, which is
not in general true.

Instead we will break each match into two vectors `x` and `y` (radiant and dire) and use only `{0,1}` indicator variables. 
For logistic classificaiton:

`log(p/(1-p)) = a0 + x1*b1 + x2*b2 + x3*b3 + ... + y1*c1 + y2*c2 + y3*c3 + ...`

where `x_n=1` denotes hero was present on radiant, and `y_n=-1` denotes the hero was present on dire. The negation
is used so that a positive coefficient on a dire term means the hero was more likely a win for dire.

Without the intercept, we will call this matrix `X1` which has shape `(num_matches, 2*num_heroes).

## Second order effects

Here we expand the descriptor to include hero/enemy interactions ("2nd order"). The benefit of doing this is the results 
of hero pairings will be interpretable using simple logistic regression. For each match, we define an interaction matrix `A_ij`, 
where `i` and `j` indicate which hero. Additionally, we flip parings to ensure j>i to keep the matrix upper triangular. 
If `A_ij` = 1, it indicates that hero `i` was on radiant, if `A_ij` = -1 hero `i` was on dire. For regression we'll 
unravel this matrix into a vector.

After regression we mirror about the diagonal and flip signs, so that the "row" of the matrix (e.g. the "Broodmother") row shows 
the correct direction of win/loss for radiant.

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


# +
def main():
    # Data selection
    BEGIN=dt.datetime(2020,9,3)
    END=dt.datetime(2020,9,8)
    SKILL=3

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
        int(BEGIN.timestamp()),
        int(END.timestamp()),
        SKILL)

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

        if counter % 100 == 0:
            print("{} of {}".format(counter,len(rows)))
        counter=counter+1

    sparse.save_npz("y.npz",sparse.csc_matrix(y))
    sparse.save_npz("X1.npz",sparse.csc_matrix(X1))
    sparse.save_npz("X2.npz",sparse.csc_matrix(X2))
    sparse.save_npz("X3.npz",sparse.csc_matrix(X3))
    
if __name__ == "__main__":
    main()
