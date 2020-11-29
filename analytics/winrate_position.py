# -*- coding: utf-8 -*-
"""Algorthm for win probability by farm position. See README.md, contains
code to estimate role based on `prior` probability models.
"""

import os
import sys
from itertools import permutations
import mariadb
import pandas as pd
import ujson as json
import numpy as np
sys.path.append("..")
import meta             # pylint: disable=import-error, wrong-import-position

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
        self.prior_version = table['version']

        # Check
        if not np.all(self._prior_table.values>=1.0e-3):
            raise ValueError("Some prior entries less than eps 1.0e-3")

        # Convert to dictionary for speed
        self._prior_dict=self._prior_table.transpose().to_dict()

    def likelihood(self, heroes):
        """Log likehood of heros base on prior distribution"""

        log_like = 0
        for hero, position in zip(heroes, ["P{}".format(t+1) for t in range(5)]):
            log_like += np.log(self._prior_dict[meta.HERO_DICT[hero]][position])

        return log_like

    def find_max_likelihood(self, heroes, verbose=False):
        """Cycle thru all permutations and assign farm positions."""

        max_perm = [0, 1, 2, 3, 4]
        max_like = self.likelihood(heroes)
        for this_perm in permutations(range(5)):
            test_heroes = [heroes[t] for t in this_perm]
            this_like = self.likelihood(test_heroes)

            if verbose:
                print(this_like, test_heroes)

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

    stmt="SELECT match_id, radiant_heroes, dire_heroes, radiant_win FROM dota_matches LIMIT 100"
    cursor.execute(stmt)

    rows=cursor.fetchall()
    print("{0} matches found in database".format(len(rows)))

    hml = HeroMaxLikelihood("prior_final.json")
    total_win_mat, total_count_mat = hml.matches_to_summary(rows)

    print(total_count_mat)
    print("..............")
    print(total_win_mat)

if __name__ == "__main__":
    main()
