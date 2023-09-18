import requests
import time
import glob

import pandas as pd
pd.set_option('display.max_columns', 100)

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from tqdm.notebook import tqdm

# Local code
from filing import Filing

from ._conversions import (
    convert_initials,
    convert_teamname,
    standardize_initials,
    standardize_name
)
from ._info import (
    DEFENSIVE_FPTS_RULES,
    DEFENSIVE_TD_COLUMNS,
    KICKING_FPTS_RULES,
    OFFENSIVE_COLUMNS,
    PTS_ALLOWED_SCORING
)
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
        } if self.year != 2023 else {week: week_url(self.year, week) for week in range(1,3)} # Manual for now -> Need function to determine what week it is


        ff_options = Options()
        ff_options.add_argument('--headless')

        self.driver = webdriver.Firefox(options=ff_options)

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
            
            # Need to render some of the tables, so selenium necessary to fully utilize BeautifulSoup
            # Maybe add this outside of main loop?
            # ff_options = Options()
            # ff_options.add_argument('--headless')
            
            # driver = webdriver.Firefox(options=ff_options)
            self.driver.get(game_url)
            
            game_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            
            # game_soup = BeautifulSoup(
            #     requests.get(game_url).text,
            #     'html.parser'
            # )

            stat_table = game_soup.find_all('table', id='player_offense')[0]

            scorebox = game_soup.find_all('div', class_='scorebox')[0]
            
            away_team, home_team = tuple([convert_teamname(scorebox.find_all('strong')[i].get_text().replace('\n', '')) for i in (0,2)])
            away_score, home_score =  tuple([int(score.get_text().replace('\n','')) for score in scorebox.find_all('div', class_='scores')])
    
            # Different for names because th not td
            names = [
                standardize_name(self.clean_name(tag.get_text())) for tag in stat_table.find_all('th', attrs={'data-stat': 'player'})
                if tag.get_text() != 'Player'
            ]

            n_players = len(names)

            convert_stat_str = lambda stat, stat_val: stat_val if stat in ['player', 'team', 'pass_rating'] else int(stat_val)
            
            table_data = {
                stat: [convert_stat_str(stat, td.get_text()) for td in stat_table.find_all('td', attrs={'data-stat': stat})]
                for stat in OFFENSIVE_COLUMNS[1:]
            }
            
            # One-liners to either clean or add more info when more annoying then doing on massive dataframes
            fix_rating = lambda rating_str: float(rating_str) if len(rating_str) else 0.0
            teams = [standardize_initials(team) for team in set(table_data['team'])] # Careful having both this and away_team, home_team
            
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
            table_data['home'] = [ int(is_home(team)) for team in table_data['team'] ]
            table_data['score'] = [ get_score(team) for team in table_data['team'] ]
            table_data['opp_score'] = [ get_opp_score(team) for team in table_data['team'] ]
            table_data['winner'] = [ is_winner(team) for team in table_data['team'] ]

            table_data['spread'] = [ get_spread(team) for team in table_data['team'] ]
            table_data['total'] = [total_score] * n_players
            table_data['week'] = [week] * n_players
            
            # Defaults to WR, name already standardized
            table_data['pos'] = [ self.lookup_position.get(name, 'WR') for name in names ]

            # Need to figure out defense
            # Just need to remember in PPR format
            offense_df = (pd
                  .DataFrame(data={**{'name': names}, **table_data})
                  .assign(fpts=lambda df: 0.04*df.pass_yds + 4.0*df.pass_td - 1.0*df.pass_int + 0.1*df.rush_yds + 6.0*df.rush_td + 1.0*df.rec + 0.1*df.rec_yds + 6.0*df.rec_td - 1.0*df.fumbles_lost)
                 )

            ########################################################################################################
            # Defensive handling
            ########################################################################################################

            # This info comes from the offensive table
            # Team: # of times they were sacked
            # Example: BUF: # times Josh Allen was sacked
            team_defense_stats = {
                team: {
                    stat: offense_df.loc[offense_df['team'] == team, stat].sum()
                    for stat in ('pass_sacked', 'pass_int', 'fumbles_lost')
                }
                for team in teams
            }
            
            for team, def_stats in team_defense_stats.items():
                def_stats['pts_allowed'] = get_opp_score(team)
            
            def_table = game_soup.find_all('table', id='player_defense')[0]
            parse_defensive_stat = lambda stat_, stat_val: int(stat_val) if stat_ in DEFENSIVE_TD_COLUMNS[1:] else standardize_initials(stat_val)
            
            # ('team', 'def_int_td', 'fumbles_rec_td')
            def_table_data = {
                stat: [parse_defensive_stat(stat, td.get_text()) for td in def_table.find_all('td', attrs={'data-stat': stat})]
                for stat in DEFENSIVE_TD_COLUMNS
            }
            
            # Need to count touchdowns for defense, most important after points allowed
            team_def_tds = {team: 0 for team in teams}
            for cat in DEFENSIVE_TD_COLUMNS[1:]:
                for i, td in enumerate(def_table_data[cat]):
                    team_def_tds[def_table_data['team'][i]] += td

            
            # Initialize dictionary for fpts for defenses
            defense_fpts = {team: 0 for team in teams}
            
            # Careful having all in one loop
            for team in teams:
                for cat, multi in DEFENSIVE_FPTS_RULES.items():
                    defense_fpts[team] += team_defense_stats[get_opp(team)][cat]*multi
                    
                defense_fpts[team] += 6.0*team_def_tds[team]
                # Defense not responsible for opposing defense getting TD
                team_defense_stats[team]['pts_allowed'] -= 6.0*team_def_tds[team]
                
                for pts_range, fpts_ in PTS_ALLOWED_SCORING.items():
                    if team_defense_stats[team]['pts_allowed'] in pts_range:
                        defense_fpts[team] += fpts_


            defense_data = {
                'name': [ convert_initials(team_) for team_ in teams ],
                'team': teams,
                'opp': [ get_opp(team_) for team_ in teams ],
                'home': [ int(is_home(team)) for team in teams ],
                'week': [week] * 2,
                'score': [ get_score(team) for team in teams ],
                'opp_score':[ get_opp_score(team) for team in teams ],
                'winner': [ is_winner(team) for team in teams ],
                'spread': [ get_spread(team) for team in teams ],
                'total': [total_score] * 2,
                'pos': ['DST'] * 2,
                'fpts': [defense_fpts[team] for team in teams]
            }

            ########################################################################################################
            # Kicking
            ########################################################################################################

            kicking_table = game_soup.find_all('table', id='kicking')[0]

            kickers = [
                self.clean_name(tag.get_text()) for tag in kicking_table.find_all('th', attrs={'data-stat': 'player'})
                if tag.get_text() != 'Player'
            ]

            n_kickers = len(kickers)
            
            convert_kicking_val = lambda kick_val: int(kick_val) if len(kick_val) else 0
            parse_kicking_stat = lambda kick_stat, kick_val: convert_kicking_val(kick_val) if kick_stat != 'team' else standardize_initials(kick_val)
            kicking_data = {
                stat: [parse_kicking_stat(stat, td.get_text()) for td in kicking_table.find_all('td', attrs={'data-stat': stat})]
                for stat in ['team', 'xpm', 'fgm']
            }
            
            kicking_fpts = {kicker: 0.0 for kicker in kickers}
            
            for stat, multi in KICKING_FPTS_RULES.items():
                for i, kicking_val in enumerate(kicking_data[stat]):
                    kicking_fpts[kickers[i]] += kicking_val*multi
                    
            kicking_data = {
                'name': kickers,
                'team': [ standardize_initials(team) for team in kicking_data['team'] ],
                'opp': [ get_opp(team) for team in kicking_data['team'] ],
                'home': [ int(is_home(team)) for team in kicking_data['team'] ],
                'week': [week] * n_kickers,
                'score': [ get_score(team) for team in kicking_data['team'] ],
                'opp_score':[ get_opp_score(team) for team in kicking_data['team'] ],
                'winner': [ is_winner(team) for team in kicking_data['team'] ],
                'spread': [ get_spread(team) for team in kicking_data['team'] ],
                'total': [total_score] * n_kickers,
                'pos': ['K'] * n_kickers,
                'fpts': [kicking_fpts[kicker] for kicker in kickers]
            }
            ########################################################################################################

            df = (pd
                  .concat([
                      offense_df,
                      pd.DataFrame(defense_data),
                      pd.DataFrame(kicking_data)
                  ])
                  .fillna(0.0) # Careful
                  .assign(name=lambda df_: df_.name.str.strip())
                 )
            
            self.filing.save_boxscore(df, away_team, home_team)
            time.sleep(5)
        

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
            # Selenium causes webscraper to be much slower --> might not need as much time
            # time.sleep(1)
            print(f'Succesfully scraped boxscores for Week {weeknum}\n')
        
        
        return