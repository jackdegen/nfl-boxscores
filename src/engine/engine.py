import numpy as np
import pandas as pd
import matplotlib as mpl

import itertools
from itertools import combinations
from functools import cache
from tqdm.notebook import tqdm

from collections.abc import Sequence
from typing import Type

# from .lineup import Lineup
from .checker import Checker

from pandarallel import pandarallel
pandarallel.initialize(progress_bar=False, use_memory_fs=True, verbose=1) # vs 24?


"""

SHOWDOWN OPTIMIZER ENGINE

"""

class Engine:
    def __init__(self, data: pd.DataFrame, **kwargs):

        data = data.loc[data['fpts'] > 2.0]
        
        self.data = {
            name: {
                column: data.loc[name, column]
                for column in data.columns
            }
            for name in data.index
        }


        self.names = tuple(self.data.keys())
        self.values = ('salary', 'fpts', 'team'),
        self.sumcols = ['salary', 'fpts'],
        self.bonuscols = ('salary', 'fpts'),

        self.labels = ['CPT'] + [f'FLEX{n}' for n in range(1,6)]
        self.size = len(self.labels)
        self.checker = Checker(self.data, **kwargs)

        # self.bad_cpts = sum([
        #     kwargs.get('bad_captains', tuple()),
        #     tuple(data.loc[data['pos'].isin(['K', 'DST'])].index)
        # ], tuple()) if kwargs.get('past', False) else tuple()

        self.bad_cpts = kwargs.get('bad_captains', tuple())

        if kwargs.get('past', True):
            self.bad_cpts = tuple()

        else:
            self.bad_cpts = sum([
                kwargs.get('bad_captains', tuple()),
                tuple(data.loc[data['pos'].isin(['K', 'DST'])].index)
            ], tuple())

        self.PROGRESS_BAR = kwargs.get('progress_bar', True)

    
    @cache
    def get_value(self, name: str, value: str) -> float|int:
        return self.checker.pvalue(name, value)
    
    @cache
    def order(self, names: tuple[str,...], **kwargs) -> tuple[str,...]:
        return self.checker.order(names)
    
    @cache
    def rc_summer(self, names: tuple[str,...], value: str) -> float|int:
        
        if len(names) == 1:
            return self.get_value(names[0], value)
        
        head,*tail = names
        tail: tuple[str,...] = tuple(tail)
        
        return sum([ self.get_value(head, value), self.rc_summer(tail, value) ])
    
    
    @cache
    def sum_values(self, names: tuple[str,...], value: str, *args) -> float|int:
    
        if value in self.bonuscols:
            return {'salary': self.checker.cost, 'fpts': self.checker.points}[value](names, *args)
            
        return self.rc_summer(names, value)

    # Done after checking
    def analyze_lineup(self, lineup: tuple[str,...]) -> tuple[int|float,...]:
        # assert(isinstance(lineup, tuple))
        return tuple([ self.sum_values(tuple(lineup), column) for column in self.sumcols ])

    @cache
    def check(self, lineup: tuple[str,...]) -> bool:
        return self.checker.check(lineup)

    def generate(self) -> tuple[tuple[str,...],...]:
        
        lineups = list()

        cpt_iter = [name_ for name_ in self.names if name_ not in self.bad_cpts]
        
        if self.PROGRESS_BAR: cpt_iter = tqdm(cpt_iter)

        for cpt in cpt_iter:

            rest: tuple[str,...] = tuple([ pname for pname in self.names if pname != cpt ])
            # combos: tuple[PartialStr,...] = tuple(map( tuple, itertools.combinations(rest, self.size-1)))
            
            for combo in itertools.combinations(rest, self.size-1):

                lineup: tuple[str,...] = (cpt,) + self.order(tuple(combo))


                if self.check(lineup):
                    lineups.append( lineup )

        df = pd.DataFrame(data=lineups, columns=self.labels)
        df['fpts'] = [self.checker.points(lineup) for lineup in lineups]
        df['salary'] = [self.checker.cost(lineup) for lineup in lineups]
        return df
        # return tuple(lineups)

    def Lineups(self, **kwargs) -> pd.DataFrame:

        # ret: pd.DataFrame = pd.DataFrame(data=self.generate(), columns=self.labels)
        ret = self.generate()

        # Issues with hashing and cacheing (~bars~)
        
        # ret['lineup'] = ret[self.labels].apply(tuple, axis=1)

        # for col in self.sumcols:
        #     ret[col] = ret['lineup'].map(lambda lu: self.sum_values(lu, col))
        
        # Parallel
        # ret[self.sumcols] = ret.parallel_apply( lambda x: self.analyze_lineup( tuple(x.to_numpy()) ), axis=1, result_type='expand' )
        top_n = kwargs.get('top_n', 10)
        return (ret
                .assign(salary=lambda df_: df_.salary.astype('int'))
                .sort_values('fpts', ascending=False)
                .reset_index(drop=True)
                .head(top_n)
               )