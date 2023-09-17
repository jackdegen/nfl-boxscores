import requests
import time
import glob

import pandas as pd
pd.set_option('display.max_columns', 100)

from bs4 import BeautifulSoup
from tqdm.notebook import tqdm

# Local code
from filing import Filing

from ._conversions import (
    convert_teamname,
    standardize_initials,
    standardize_name
)
from ._info import DATA_COLUMNS
from ._templates import week_url


class Scraper:

    def __init__(self, year=2023):
        """
        """
        self.year: int = int(year)
        self.season: str = f'{self.year}-{self.year+1}'

        # Initialize filing object
        self.filing = Filing(self.season)

        # Load positions to add to boxscores
        self.positions = self.filing.positions()

        # Convert to dictionary to speed up (FrozenDict??)
        self.lookup_position: dict[[str], str] = {
            name: self.positions.loc[name, 'pos'] for name in self.positions.index
        }

        # NFL changed number of weeks in 2022
        num_weeks = 18 if self.year >= 2022 else 17
        
        # Going to start with just regular season
        self.week_pages = {
            week: week_url(self.year, week)
            for week in range(1,num_weeks+1)
        } if self.year != 2023 else {1: week_url(self.year, 1)} # Manual for now

        self.data_columns = DATA_COLUMNS

    def clean_name(self, name: str) -> str:
        """
        Standardizes name across PFR, FD, DK
        """
        return ' '.join(name.split(' ')[:2]).replace('.', '')

    def get_week_boxscores(self, week: int, url: str):
        """
        Returns every boxscore for given week and saves it to directory
        """

        root_url: str = 'https://www.pro-football-reference.com/'
        
        week_games_soup = BeautifulSoup(
            requests.get(url).text,
            'html.parser'
        )


        for game in week_games_soup.find_all('div', class_='game_summary expanded nohover'):
            
            game_url: str = f"{root_url}{game.find_all('td', class_='right gamelink')[0].find('a')['href']}"
            game_soup = BeautifulSoup(
                requests.get(game_url).text,
                'html.parser'
            )

            stat_table = game_soup.find_all('table', id='player_offense')[0]

            scorebox = game_soup.find_all('div', class_='scorebox')[0]
            
            away_team, home_team = tuple([convert_teamname(scorebox.find_all('strong')[i].get_text().replace('\n', '')) for i in (0,2)])
            away_score, home_score =  tuple([int(score.get_text().replace('\n','')) for score in scorebox.find_all('div', class_='scores')])
    
            # Different for names because th not td
            names = [
                standardize_name(self.clean_name(tag.get_text())) for tag in stat_table.find_all('th', attrs={'data-stat': 'player'})
                if tag.get_text() != 'Player'
            ]

            convert_stat_str = lambda stat, stat_val: stat_val if stat in ['player', 'team', 'pass_rating'] else int(stat_val)
            
            table_data = {
                stat: [convert_stat_str(stat, td.get_text()) for td in stat_table.find_all('td', attrs={'data-stat': stat})]
                for stat in self.data_columns[1:]
            }
            
            # One-liners to either clean or add more info when more annoying then doing on massive dataframes
            fix_rating = lambda rating_str: float(rating_str) if len(rating_str) else 0.0
            is_home = lambda team_: team_ == home_team
            get_opp = lambda team_: away_team if is_home(team_) else home_team
            get_score = lambda team_: home_score if is_home(team_) else away_score
            get_opp_score = lambda team_: away_score if is_home(team_) else home_score

            winning_team = home_team if home_score > away_score else away_team
            is_winner = lambda team_: int(team_ == winning_team)
            get_spread = lambda team_: home_score - away_score if is_home(team_) else away_score - home_score
            total_score = away_score + home_score
            
            table_data['pass_rating'] = [ fix_rating(rating) for rating in table_data['pass_rating'] ]
            table_data['team'] = [ standardize_initials(team) for team in table_data['team'] ]
            table_data['opp'] = [ get_opp(team) for team in table_data['team'] ]
            table_data['home'] = [ int(team == home_team) for team in table_data['team'] ]
            table_data['score'] = [ get_score(team) for team in table_data['team'] ]
            table_data['opp_score'] = [ get_opp_score(team) for team in table_data['team'] ]
            table_data['winner'] = [ is_winner(team) for team in table_data['team'] ]

            table_data['spread'] = [ get_spread(team) for team in table_data['team'] ]
            table_data['total'] = [total_score] * len(names)
            table_data['week'] = [week] * len(names)
            
            # Defaults to WR, name already standardized
            table_data['pos'] = [ self.lookup_position.get(name, 'WR') for name in names ]

            # Need to figure out defense
            # Just need to remember in PPR format
            df = (pd
                  .DataFrame(data={**{'name': names}, **table_data})
                  .assign(fpts=lambda df: 0.04*df.pass_yds + 4.0*df.pass_td - 1.0*df.pass_int + 0.1*df.rush_yds + 6.0*df.rush_td + 1.0*df.rec + 0.1*df.rec_yds + 6.0*df.rec_td - 1.0*df.fumbles_lost)
                 )


            
            self.filing.save_boxscore(df, away_team, home_team)
        

        return

    def get_season_boxscores(self) -> None:
        """
        Iterates through every boxscore for every game of every week
        Saves to data directory
        """

        print(f'Beginning scraping for {self.season} season\n')

        # Dont want to scrape data already saved (assuming previous data formatted correctly)
        # This will not get games if whole week of games not complete (only do on tuesday-wednesday)
        # if self.year == 2023:
        #     # .../../team1-team2-week#.csv --> Want just #
        #     extract_week = lambda fname: int(fname.split('/')[-1].split('.')[0].split('-')[2].replace('week', ''))
        #     boxscore_weeks = set([ extract_week(file) for file in glob.glob(self.filing.boxscores_dir + '/*.csv') ])

        #     self.week_pages = { week: page for week, page in self.week_pages.items() if week not in boxscore_weeks }


        if not len(self.week_pages):
            print(f'Boxscores for season {self.season} already up to date\n')
            return
            
        for weeknum, url in tqdm(self.week_pages.items()):
            print(f'Scraping boxscores for Week {weeknum}')
            self.get_week_boxscores(weeknum, url)
            # Need to sleep for 60 seconds so requests do not get blocked
            time.sleep(60)
            print(f'Succesfully scraped boxscores for Week {weeknum}\n')
        
        
        return