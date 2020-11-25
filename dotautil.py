# -*- coding: utf-8 -*-
"""Utility functions used by multiple scripts in the project. Includes:

    - MatchSerialization
    - Bitmask
    - MLEncoding

See individual methods for more information.
"""
import os
import mariadb
import numpy as np
import ujson as json
from match import match_pb
import meta

class MatchSerialization:
    """Contains methods to serialize/deserialize using ProtoBuf"""

    @staticmethod
    def protobuf_match_details(rad_heroes, dire_heroes, items, gold):
        """Serialize some match info to protobuf"""

        rad_list=[]
        for rad_hero in rad_heroes:
            rad_list.append(match_pb.Hero(
                hero=rad_hero,
                items=items[str(rad_hero)],
                gold_spent=gold[str(rad_hero)]
            ))

        dire_list=[]
        for dire_hero in dire_heroes:
            dire_list.append(match_pb.Hero(
                hero=dire_hero,
                items=items[str(dire_hero)],
                gold_spent=gold[str(dire_hero)]
            ))

        match_info=match_pb.MatchInfo(
            radiant_heroes=rad_list,
            dire_heroes=dire_list,
        )
        return match_info


    @staticmethod
    def unprotobuf_match_details(match_proto):
        """Deserialize match information from protobuf"""

        radiant_heroes=[]
        dire_heroes=[]
        gold_spent={}
        items={}
        for rad_hero in match_proto.radiant_heroes:
            radiant_heroes.append(rad_hero.hero)
            gold_spent[str(rad_hero.hero)]=rad_hero.gold_spent
            items[str(rad_hero.hero)]=list(rad_hero.items)

        for dire_hero in match_proto.dire_heroes:
            dire_heroes.append(dire_hero.hero)
            gold_spent[str(dire_hero.hero)]=dire_hero.gold_spent
            items[str(dire_hero.hero)]=list(dire_hero.items)

        return (radiant_heroes,
                dire_heroes,
                items,
                gold_spent)


class Bitmask:
    """Contains methods to convert from hero list to bitmasks, used in the
    database for search."""

    @staticmethod
    def encode_heroes_bitmask(heroes):
        """Returns a 3 BIGINT bitmask which encodes the heroes"""
        low_mask = 0
        mid_mask = 0
        high_mask = 0

        for hero_num in heroes:
            if 0 < hero_num <= 63:
                low_mask=low_mask | 2**hero_num
            elif 63 < hero_num <= 127:
                mid_mask=mid_mask | 2**(hero_num-64)
            elif 127 < hero_num <= 191:
                high_mask=mid_mask | 2**(hero_num-128)
            else:
                raise ValueError("Hero out of range %d" % hero_num)

        return low_mask, mid_mask, high_mask


    @staticmethod
    def where_bitmask(hero_num):
        """Returns SQL WHERE clause for a given hero"""

        if 0 < hero_num <= 63:
            bitmask = 2**hero_num
            stmt = "WHERE hero_mask_low & {0} = {0}".format(bitmask)
        elif 63 < hero_num <= 127:
            bitmask = 2**(hero_num-64)
            stmt = "WHERE hero_mask_mid & {0} = {0}".format(bitmask)
        elif 126 < hero_num <= 191:
            bitmask = 2**(hero_num-128)
            stmt = "WHERE hero_mask_high & {0} = {0}".format(bitmask)
        else:
            raise ValueError("Hero out of range %d" % hero_num)

        return stmt


    @staticmethod
    def decode_heroes_bitmask(bit_masks):
        """Returns list of heroes in match given a bitmask tuple/list"""

        low_mask, mid_mask, high_mask = bit_masks
        heroes = []
        for ibit in list(range(64)):
            if 2**ibit & low_mask == 2**ibit:
                heroes.append(ibit)
            if 2**ibit & mid_mask == 2**ibit:
                heroes.append(ibit+64)
            if 2**ibit & high_mask == 2**ibit:
                heroes.append(ibit+128)

        return heroes

class MLEncoding:
    """Methods to one-hot encode and decode hero information for machine
    learning applications.
    """

    @staticmethod
    def first_order_vector(rad_heroes, dire_heroes):
        """Generate vector encoding hero selections. Length
        of vector is 2N, where [0:N] are {0,1} indicating radiant
        selection, and [N:N2] are {0,1} indicating dire.

            1 = Radiant
            -1 = Dire

        """

        # Placeholder for results
        x1_data = np.zeros([len(rad_heroes), meta.NUM_HEROES*2], dtype='b')

        # For each row, create five repeated indicies so we can unroll
        # the list of heroes
        idx_rows = []
        for counter in range(len(rad_heroes)):
            idx_rows.extend(5*[counter])
        idx_rows = np.array(idx_rows)

        # For radiant, just unroll and convert to hero index from
        # hero number.
        idx_rad = np.array(rad_heroes).reshape(-1)
        idx_rad = np.array([meta.HEROES.index(t) for t in idx_rad])
        x1_data[(idx_rows, idx_rad)] = 1

        # For dire, offset by number of heroes
        idx_dire = np.array(dire_heroes).reshape(-1)
        idx_dire = np.array([meta.HEROES.index(t)+meta.NUM_HEROES \
                                                    for t in idx_dire])
        x1_data[(idx_rows, idx_dire)] = -1

        return x1_data


    @staticmethod
    def second_order_hmatrix(rad_heroes, dire_heroes):
        """For a list of radiant and dire heroes, create an upper triangular matrix
        indicating radiant/dire pairs. By convention, 1 indicates first hero in i,j
        is on dire, -1 indicates first hero was on dire. See README.md for more
        information.

        rad_heroes: radiant heroes, numerical by enum
        dire_heroes: radiant heroes, numerical by enum

        """
        data_x2=np.zeros([meta.NUM_HEROES,meta.NUM_HEROES], dtype='b')
        for rad_hero in rad_heroes:
            for dire_hero in dire_heroes:
                irh=meta.HEROES.index(rad_hero)
                idh=meta.HEROES.index(dire_hero)
                if idh>irh:
                    data_x2[irh,idh]=1
                if idh<irh:
                    data_x2[idh,irh]=-1
                if idh==irh:
                    raise ValueError("Duplicate heroes: {} {}".format(\
                                                    rad_heroes,dire_heroes))
        return data_x2

    @staticmethod
    def flatten_second_order_upper(x2_matrix):
        """Unravel upper triangular matrix into flat vector, skipping
        diagonal. See README.md for more information."""
        size=x2_matrix.shape[1]
        x_flat=np.zeros(int(size*(size-1)/2), dtype='b')

        idx = np.triu_indices(n=size, k=1)
        x_flat = x2_matrix[idx]

        return x_flat

    @staticmethod
    def unflatten_second_order_upper(x_flat):
        """Create upper triangular matrix from flat vector, skipping
        diagonal. See README.md for more information."""
        matrix_size = int((1+(1+8*x_flat.shape[0])**(0.5))/2)
        x_matrix = np.zeros([matrix_size, matrix_size])
        counter = 0
        for i in range(matrix_size):
            for j in [t+i+1 for t in range(matrix_size-i-1)]:
                x_matrix[i,j]=x_flat[counter]
                x_matrix[j,i]=-x_flat[counter]
                counter=counter+1
        return x_matrix

    @classmethod
    def create_features(cls, begin, end, skill):
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
            host=os.environ['DOTA_HOSTNAME'],
            database=os.environ['DOTA_DATABASE'])
        cursor=conn.cursor()

        # Fetch all rows
        stmt="SELECT start_time, match_id, radiant_heroes, dire_heroes, "
        stmt+="radiant_win FROM dota_matches WHERE start_time>={0} and "
        stmt+="start_time<={1} and api_skill={2}"
        stmt=stmt.format(
            int(begin.timestamp()),
            int(end.timestamp()),
            skill)

        cursor.execute(stmt)
        rows=cursor.fetchall()
        print("Records: {}".format(len(rows)))

        # Setup the targets
        radiant_win=np.array([t[-1] for t in rows])

        # First order effects
        rad_heroes = [json.loads(t[2]) for t in rows]
        dire_heroes = [json.loads(t[3]) for t in rows]
        x1_hero = cls.first_order_vector(rad_heroes, dire_heroes)

        # Second order effects
        x2_against = np.zeros([len(rows),\
            int(meta.NUM_HEROES*(meta.NUM_HEROES-1)/2)], dtype='b')

        # x_all = first order effects + match-ups ally vs. enemy
        x_all = np.zeros([len(rows), x1_hero.shape[1]+x2_against.shape[1]], dtype='b')

        counter=0
        for row in rows:
            x2_against[counter,:] = cls.flatten_second_order_upper(
                                    cls.second_order_hmatrix(
                                            json.loads(row[2]),
                                            json.loads(row[3])))
            x_all[counter, :] = np.concatenate([
                                    x1_hero[counter,:],
                                    x2_against[counter,:]
                                    ])

            if counter % 10000 == 0:
                print("{} of {}".format(counter,len(rows)))

            counter=counter+1

        return radiant_win, x1_hero, x2_against, x_all
