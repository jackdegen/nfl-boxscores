import os
import glob

import pandas as pd

class Filing:
    # Class to take care of filing each dataframe + additional functionality later on
    # Site agnostic
    def __init__(self, season: str):

        self.season = season
        self.data_dir = os.getcwd().replace('src', 'data')
        self.season_dir = os.path.join(self.data_dir, season)
        self.boxscores_dir = os.path.join(self.season_dir, 'boxscores')
        self.snap_counts_dir = os.path.join(self.season_dir, 'snap-counts')

        self.advanced_stats_dir = os.path.join(self.season_dir, 'advanced-stats')
        self.advanced_passing_dir = os.path.join(self.advanced_stats_dir, 'passing')
        self.advanced_rushing_dir = os.path.join(self.advanced_stats_dir, 'rushing')
        self.advanced_receiving_dir = os.path.join(self.advanced_stats_dir, 'receiving')
        
        # Check to make sure if directories exist, if not create them
        # Can optimize a little bit by working backwards 
        #      --> if advanced_passing_dir exists, then advanced_stats_dir exists, which means that season_dir exists etc.
        for directory in (self.data_dir, self.season_dir, self.boxscores_dir, self.snap_counts_dir, self.advanced_stats_dir, self.advanced_passing_dir, self.advanced_rushing_dir, self.advanced_receiving_dir):
            if not os.path.exists(directory):
                os.mkdir(directory)

        # Initialize and fill when called
        self.boxscores = dict()
        self.snapcounts = dict()
        self.adv_stats = dict()

    def clean_name(self, name: str) -> str:
        """
        Standardizes name across PFR, FD, DK
        """
        return ' '.join(name.split(' ')[:2]).replace('.', '')

    # Returns the last week of data saved
    def get_last_week_saved(self):
        # Only to be used with current year
        # File format: path/{team}-week#.csv --> #.csv --> #
        extract_week = lambda fname: int(fname.split('week')[-1].split('.')[0])
        return max(set([extract_week(file) for file in glob.glob(self.snap_counts_dir + '/*.csv')]))
        


    def save_boxscore(self, df: pd.DataFrame, away: str, home: str) -> None:
        """
        Saves boxscore as csv (later on can configure different formats)
        Saves in form of away-home.csv --> Will never have duplication issues
        """
        filename = f'{away}-{home}.csv'
        
        fpath = os.path.join(self.boxscores_dir, filename)
        df.to_csv(fpath, index=False)

        return

    def load_boxscores(self):
        if len(self.boxscores):
            return self.boxscores

        combined =( pd.concat(
                    [pd.read_csv(file) for file in glob.glob(self.boxscores_dir + '/*.csv')])
                  )
        self.boxscores = {team_: combined.loc[combined['team']==team_] for team_ in combined['team'].drop_duplicates()}
        
        return self.boxscores

    def save_snapcounts(self, df: pd.DataFrame, team: str, week: int) -> None:
        """
        Saves snapcounts for fantasy position players
        Saves in form of team-week#.csv
        """
        filename = f'{team}-week{week}.csv'
        fpath = os.path.join(self.snap_counts_dir, filename)
        df.to_csv(fpath, index=False)

        return

    def load_snapcounts(self):
        if len(self.snapcounts):
            return self.snapcounts

        combined =( pd.concat(
                    [pd.read_csv(file) for file in glob.glob(self.snap_counts_dir + '/*.csv')])
                  )
        self.snapcounts = {team_: combined.loc[combined['team']==team_] for team_ in combined['team'].drop_duplicates()}
        
        return self.snapcounts


    def save_advanced_stats(self, df: pd.DataFrame, stat_category: str, team: str, week: str) -> None:
        """
        Save advanced stats for team from specific weak, where stat_category is one of (passing, rushing, receiving)
        Saves in stat_category directory in form of team-week#.csv
        Example: Advanced passing from Bills weak one: data_dir/season_dir/advanced-stats/passing/buf-week1.csv
        """
        filename = f'{team}-week{week}.csv'
        fpath = os.path.join(self.advanced_stats_dir, stat_category, filename)
        df.to_csv(fpath, index=False)

        return


    def load_advanced_stats(self):
        if len(self.adv_stats):
            return self.adv_stats

        for category in ('passing', 'rushing', 'receiving'):

            cat_df = pd.concat([
                pd.read_csv(file) for file in glob.glob(self.advanced_stats_dir + f'/{category}/*.csv')
            ])

            self.adv_stats[category] = {
                team_: cat_df.loc[cat_df['team']==team_] for team_ in cat_df['team'].drop_duplicates()
            }
        
        return self.adv_stats

    
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


    def combined_boxscores(self):

        return (pd
                .concat([ pd.read_csv(file) for file in glob.glob(self.boxscores_dir + '/*.csv') ])
                .reset_index(drop=True)
               )

    def combined_snapcounts(self):

        return (pd
                .concat([ pd.read_csv(file) for file in glob.glob(self.snap_counts_dir + '/*.csv') ])
                .reset_index(drop=True)
               )


        
        











