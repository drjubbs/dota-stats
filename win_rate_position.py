# -*- coding: utf-8 -*-
"""Algorthm for win probability by farm position. See README.md, contains
code to estimate role based on `prior` probability models.
"""

import os
import sys
import json
from itertools import permutations
import mariadb
import pandas as pd
import numpy as np
sys.path.append("..")
import meta             # pylint: disable=import-error, wrong-import-position

MATCH_CUTOFF = 30       # Number of matches needed to calculate winrate

class HeroMaxLikelihood:
    """Use maximum likelihood methods to assign heroes to positions
    and calculate winrates.
    """
    def __init__(self, prior_filename):
        """Initialize class using `prior_filename` for prior data.
        """

        # Red and change underscores to dashes...
        with open(prior_filename) as json_file:
            table = json.loads(json_file.read())

        self._prior_table = pd.DataFrame(table['prior'])
        self._prior_table_fast = self._prior_table.values
        self.prior_version = table['version']

        # Check
        if not np.all(self._prior_table.values>=1.0e-3):
            raise ValueError("Some prior entries less than eps 1.0e-3")

        # Convert to dictionary for speed
        self._prior_dict=self._prior_table.transpose().to_dict()

    def likelihood(self, heroes_idx, max_log_like):
        """Log likehood of heros base on prior distribution. Note this function
        works off hero index (not hero number!) to speed up calculation.

        Since the heroes_are given in the correct position, we simply need the
        log sum diagonal of the matrix defined by heroes_idx.
        """

        # Original
        log_like = 0
        for hero, position in zip(heroes_idx, ["P{}".format(t+1) for t in range(5)]):
            log_like += np.log(self._prior_dict[meta.HERO_DICT[hero]][position])

            # Terminate early if we're already below a better match
            if log_like<max_log_like:
                break

        return log_like

    def find_max_likelihood(self, heroes, verbose=False):
        """Cycle thru all permutations and assign farm positions."""

        max_perm = [0, 1, 2, 3, 4]
        max_like = self.likelihood(heroes, -1000)

        for this_perm in permutations(range(5)):
            test_heroes = [heroes[t] for t in this_perm]
            this_like = self.likelihood(test_heroes, max_like)

            if verbose:
                raise NotImplementedError("This function works off the hero "\
                                        "index which is not human readable")
                ##print(this_like, test_heroes)

            if this_like > max_like:
                max_like = this_like
                max_perm = this_perm

        return ([heroes[t] for t in max_perm], max_like)

    def row_to_matrix(self, heroes, win_mat, count_mat, win):
        """Given list of heroes, count matrices and binary flag win, return a
        matrix of wins and totals for a single row.
        """
        heroes_max_l, _ = self.find_max_likelihood(heroes)
        jdx = 0
        for hero in heroes_max_l:
            idx = meta.HEROES.index(hero)
            count_mat[idx][jdx] += 1
            if win==1:
                win_mat[idx][jdx] += 1
            jdx += 1
        return win_mat, count_mat

    def matches_to_summary(self, rows):
        """Given database rows, return two matrices, one for hero count
        by position, one for hero win by position.

            row[1] - radiant heroes
            row[2] - dire heroes
            row[3] - radiant win

        """

        total_count_mat = np.zeros((meta.NUM_HEROES, 5))
        total_win_mat = np.zeros((meta.NUM_HEROES, 5))

        for row in rows:

            radiant_heroes=json.loads(row[1])
            dire_heroes=json.loads(row[2])

            total_win_mat, total_count_mat = \
                self.row_to_matrix(radiant_heroes,
                                           total_win_mat,
                                           total_count_mat,
                                           bool(row[3]))

            total_win_mat, total_count_mat = \
                self.row_to_matrix(dire_heroes,
                                           total_win_mat,
                                           total_count_mat,
                                           not bool(row[3]))

        return total_win_mat, total_count_mat


def main():
    """Main entry point"""
    # Database fetch
    conn = mariadb.connect(
        user=os.environ['DOTA_USERNAME'],
        password=os.environ['DOTA_PASSWORD'],
        host=os.environ['DOTA_HOSTNAME'],
        database=os.environ['DOTA_DATABASE'])
    cursor=conn.cursor()

    stmt="SELECT match_id, radiant_heroes, dire_heroes, radiant_win FROM dota_matches LIMIT 5000"
    cursor.execute(stmt)

    rows=cursor.fetchall()
    print("{0} matches found in database".format(len(rows)))

    hml = HeroMaxLikelihood(os.path.join("analytics", "prior_final.json"))
    total_win_mat, total_count_mat = hml.matches_to_summary(rows)

    total_count_mat[total_count_mat<MATCH_CUTOFF]=np.nan
    win_rate_position = pd.DataFrame(np.divide(total_win_mat, total_count_mat))
    win_rate_position.index = meta.HERO_DICT.values()
    win_rate_position.columns = ["P1", "P2", "P3", "P4", "P5"]

if __name__ == "__main__":
    main()
