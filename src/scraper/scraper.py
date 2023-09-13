import requests
import time

import pandas as pd
pd.set_option('display.max_columns', 100)

from bs4 import BeautifulSoup
from tqdm.notebook import tqdm

# Local code
from filing import Filing

from ._conversions import convert_initials
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
    
            # Different for names because th not td
            names = [
                self.clean_name(tag.get_text()) for tag in stat_table.find_all('th', attrs={'data-stat': 'player'})
                if tag.get_text() != 'Player'
            ]
            
            table_data = {
                stat: [td.get_text() for td in stat_table.find_all('td', attrs={'data-stat': stat})]
                for stat in self.data_columns[1:]
            }
            
            
            # Will do rest of cleaning later on, just wanted to not have any NA values in saved files and have standardized names, teams, and positions
            fix_rating = lambda rating_str: float(rating_str) if len(rating_str) else 0.0
            teams = tuple([convert_initials(team) for team in set(table_data['team'])])
            get_opp = lambda team_: teams[1] if team_ == teams[0] else teams[0]

            
            
            
            table_data['pass_rating'] = [ fix_rating(rating) for rating in table_data['pass_rating'] ]
            table_data['team'] = [ convert_initials(team) for team in table_data['team'] ]
            table_data['opp'] = [ get_opp(team) for team in table_data['team'] ]
            table_data['week'] = [ week for name in names ]
            
            # Defaults to WR, name already standardized
            table_data['pos'] = [ self.lookup_position.get(name, 'WR') for name in names ]
            
            df = pd.DataFrame(data={**{'name': names}, **table_data})
            self.filing.save_boxscore(df, week)
        

        return

    def get_season_boxscores(self) -> None:
        """
        Iterates through every boxscore for every game of every week
        Saves to data directory
        """

        print(f'Beginning scraping for {self.season} season\n')
        
        # Add check for if already done
        for weeknum, url in tqdm(self.week_pages.items()):
            print(f'Scraping boxscores for Week {weeknum}')
            self.get_week_boxscores(weeknum, url)
            # Need to sleep for 60 seconds so requests do not get blocked
            time.sleep(60)
            print(f'Succesfully scraped boxscores for Week {weeknum}\n')
        
        
        return