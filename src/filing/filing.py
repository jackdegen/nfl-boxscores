import os
import glob

import pandas as pd

class Filing:
    # Class to take care of filing each dataframe + additional functionality later on
    def __init__(self, season: str):

        self.season = season
        self.data_dir = os.getcwd().replace('src', 'data')
        self.season_dir = os.path.join(self.data_dir, season)
        self.boxscores_dir = os.path.join(self.season_dir, 'boxscores')

        # Check to make sure if directories exist, if not create them
        for directory in (self.data_dir, self.season_dir, self.boxscores_dir):
            if not os.path.exists(directory):
                os.mkdir(directory)

    def clean_name(self, name: str) -> str:
        """
        Standardizes name across PFR, FD, DK
        """
        return ' '.join(name.split(' ')[:2]).replace('.', '')


    def save_boxscore(self, df: pd.DataFrame, away: str, home: str) -> None:
        """
        Saves boxscore as csv (later on can configure different formats)
        Saves in form of away-home-week#.csv
        Want to instead save as away-home.csv
        """
        filename = f'{away}-{home}.csv'
        
        fpath = os.path.join(self.boxscores_dir, filename)
        df.to_csv(fpath, index=False)

        return

    
    def combined(self, **kwargs) -> pd.DataFrame:
        """
        Will create massive dataset if not created yet and save it
        If master dataset already created, will return csv on file
        This will not be cleaned by default
        """

        self.combined_fpath: str = os.path.join(self.season_dir, f'{self.season}-raw.csv')

        # If exists return and exit
        if os.path.exists(self.combined_fpath):
            return pd.read_csv(self.combined_fpath)

        combined =  (pd
                     .concat([ pd.read_csv(file) for file in glob.glob(self.boxscores_dir + '/*.csv') ])
                     .reset_index(drop=True)
                    )

        combined.to_csv(self.combined_fpath, index=False)

        return combined

    def positions(self, **kwargs) -> pd.DataFrame:
        """
        Returns a Series indexed by player containing positions for every player
        Uses same logic as self.combined() to initially create
        Saved as a DataFrame (csv) so need to do quick conversion
        TODO: write dir2csv function
        """

        # Where file is saved/accessed from --> DNE at first because needs to be created
        self.positions_fpath: str = os.path.join(self.season_dir, f'{self.season}-positions.csv')

        if os.path.exists(self.positions_fpath):
            return (pd
                    .read_csv(self.positions_fpath)
                    .assign(name=lambda df_: df_['name'].map(lambda name_: self.clean_name(name_)))
                    .set_index('name')
                   )


            
        # Source of positions will come from contest-files
        # Going to use FanDuel because little cleaner in general (no '/FLEX' & more standard column names/organization)
        # Need to figure out how to deal with fact that source is not public outside local machine
        # Also issues with the fact only have stuff for last two seasons
        self.positions_source: str = os.path.join(self.season_dir, 'contest-files', 'fanduel', 'main-slate')

        # Reduce overhead by reading only standard slates, not late or thanksgiving 
        #      --> have to do multiple weeks so get all teams that played in primetime games as well
        is_standard = lambda file_: 'a.csv' not in file_ and 'thanksgiving' not in file_

        # Target columns with preferred names, can add $ later
        columns_ = {
            'Nickname': 'name',
            'Position': 'pos',
        }
        
        combined_contest_files = (pd
                                  .concat([ 
                                      pd.read_csv(file, usecols=columns_.keys()) 
                                      for file in glob.glob(self.positions_source + '/*.csv') 
                                      if is_standard(file) 
                                  ])
                                  .reset_index(drop=True)
                                  .rename(columns_, axis=1)
                                  .drop_duplicates('name')
                                  # .set_index('name')
                                 )

        # Extra conditional to account for primetime games team since not in main-slate data yet
        # Can probably remove in a few weeks once every team has played main slate
        if self.season == '2023-2024':
            combined_primetime_files = (pd
                                        .concat([
                                            pd.read_csv(file, usecols=columns_.keys())
                                            for file in glob.glob(self.positions_source.replace('main-slate', 'single-game') + '/*.csv')
                                        ])
                                        .reset_index(drop=True)
                                        .rename(columns_, axis=1)
                                        .drop_duplicates('name')
                                       )

            combined_contest_files = (pd
                                      .concat([
                                          combined_contest_files,
                                          combined_primetime_files
                                      ])
                                      .drop_duplicates('name')
                                     )
        
        # Issues with saving file with index currently
        combined_contest_files.to_csv(self.positions_fpath, index=False)

        return (combined_contest_files
                .assign(name=lambda df_: df_['name'].map(lambda name_: self.clean_name(name_)))
                .set_index('name')
               )

        
        











