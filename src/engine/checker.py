import numpy as np
import pandas as pd
import matplotlib as mpl

import itertools
from itertools import combinations
from functools import cache
from tqdm.notebook import tqdm


class Checker:
    def __init__(self, data: dict[[str], dict[[str], str|float|int]], **kwargs):

        self.data = data

        self.TEAMS = tuple(set([self.data[name]['team'] for name in self.data]))

        # Defaults to optimizing past lineups --> No checks beyond rules for competition
        self.PAST = kwargs.get('past', True)

        # print(f'Past Flag = {self.PAST}')

        # Position limits for a single team in lineup
        self.position_limits = {
            'RB': 1, # Want max 1 RB from a team
            'WR': 2, # Want max 2 WR from a team
            'TE': 1, # Want max 1 TE from a team
        }
        
        self.mincost = 35_000
        self.maxcost = 50_000
        self.size = 6

        if len(kwargs.get('lineup_filters', dict())):
            filters = kwargs['lineup_filters']
            self.maxcost = filters.get('maxcost', self.maxcost)
            filter_output = sum([
                ['Adding the following filters:\n'],
                [f'{filter_}: {filter_value}' for filter_, filter_value in filters.items()],
            ], [])

            print(*filter_output, sep='\n')

    @cache
    def pvalue(self, name: str, value: str) -> float|int:
        return self.data[name][value]

    @cache
    def order(self, names: tuple[str,...], **kwargs) -> tuple[str,...]:
        value: int|float|str = kwargs.get('by', 'salary')
        return tuple(sorted(names, key=lambda p: self.pvalue(p, value), reverse=True))
    
    @cache
    def pvalues(self, lineup: tuple[str,...], value: str):
        return tuple([self.pvalue(name,value) for name in lineup])

    @cache
    def positions(self, lineup):
        return self.pvalues(lineup,'pos')
    
    @cache
    def fpts(self, lineup):
        return self.pvalues(lineup,'fpts')
    
    @cache
    def salaries(self, lineup):
        return self.pvalues(lineup,'salary')
    
    @cache
    def teams(self, lineup):
        return self.pvalues(lineup,'team')


    # Recursive
    @cache
    def cost(self, lineup: tuple[str,...], *args) -> int:
        if len(lineup) == 1:
            return self.pvalue(lineup[0], 'salary')
        
        if 'no-bonus' in args:
            head,*tail = lineup
            tail = tuple(tail)
            return self.pvalue(head,'salary') + self.cost(lineup[1:], 'no-bonus')
        
        if len(lineup) == self.size:
            multi: float = 1.0 if 'no-bonus' in args else 1.5
            return multi*self.pvalue(lineup[0],'salary') + self.cost(lineup[1:], 'no-bonus')
        
        return sum(self.salaries(lineup))
    
    @cache
    def points(self, lineup: tuple[str,...], *args) -> float:
        fpts_ = self.fpts(lineup) # tuple of fpts
        bonus: bool = 'no-bonus' not in args
        return 1.5*fpts_[0] + sum(fpts_[1:]) if bonus else sum(fpts_)

    @cache
    def teamcheck(self, lineup: tuple[str,...]) -> bool:
        return len(set(self.teams(lineup))) > 1

    @cache
    def salarycheck(self, lineup: tuple[str,...]) -> bool:
        cost_: int = self.cost(lineup)
        if cost_ <= self.maxcost:
            return cost_ >= self.mincost

        return False

    @cache
    def pointscheck(self, lineup: tuple[str,...]) -> bool:
        return 0.0 not in self.fpts(lineup)

    @cache
    def positioncheck(self, lineup: tuple[str,...]) -> bool:

        lineup_positions = self.positions(lineup)
        # lineup_fpts = self.fpts(lineup)
        
        # Punt check
        # if len([pts for pts in lineup_fpts if pts <= 6.0]) > 1:
        #     return False

        # No 2K, 2DST or 0QB lineups
        if lineup_positions.count('K') == 2 or lineup_positions.count('DST') == 2 or lineup_positions.count('QB') == 0:
            return False
        
        team_positions = {team_: [self.pvalue(name_, 'pos') for name_ in lineup if self.pvalue(name_, 'team') == team_] for team_ in self.TEAMS}

        # Example: {'ATL': {'QB':1, 'WR': 2}, 'JAX': {'QB': 1, 'RB': 1, 'WR': 1}}
        position_counts = {
            team_: {
                pos_: positions_.count(pos_) for pos_ in set(positions_)
            }
            for team_, positions_ in team_positions.items()
        }

        
        for pos_, limit_ in self.position_limits.items():
            if any([position_counts[team_].get(pos_, 0) > limit_ for team_ in self.TEAMS]):
                return False

        for pos_counts in position_counts.values():
            # If 5, 1 distribution, have either DST or K or both
            if sum(pos_counts.values()) == 5:
                return bool(sum([pos_counts.get(pos_, 0) for pos_ in ('K', 'DST')]))

            # If 5,1 distribution, have only WR as 1
            if sum(pos_counts.values()) == 1:
                return bool(pos_counts.get('WR', 0))

            # 75% of all TE lineups are stacked with QB
            if 'TE' in pos_counts and 'QB' not in pos_counts:
                return False
        
        return True

    def teammatecheck(self, lineup: tuple[str,...]) -> bool:
        return True

    def check(self, lineup: tuple[str,...]) -> bool:
        # Has to be true of all lineups, regardless of past or present
        follows_rules = all([
            self.teamcheck(lineup),
            self.salarycheck(lineup)
        ])

        if self.PAST:
            return follows_rules

        return all([
            follows_rules,
            self.positioncheck(lineup),
            # self.teammatecheck(lineup)
        ])