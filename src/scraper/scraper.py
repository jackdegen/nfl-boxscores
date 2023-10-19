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
    ADV_PASSING_COLUMNS,
    ADV_RUSHING_COLUMNS,
    ADV_RECEIVING_COLUMNS,
    DEFENSIVE_FPTS_RULES,
    DEFENSIVE_TD_COLUMNS,
    KICKING_FPTS_RULES,
    OFFENSIVE_COLUMNS,
    PTS_ALLOWED_SCORING
)
from ._templates import week_url


class Scraper:

    def __init__(self, year=2023):

        self.year: int = int(year)
        self.season: str = f'{self.year}-{self.year+1}'

        # Initialize filing object
        self.filing = Filing(self.season)

        # NFL changed number of weeks in 2022
        num_weeks = 18 if self.year >= 2022 else 17

        # Only works correctly if updating every week, better if can figure out way to determine what week it is as second part of range
        last_week_saved = num_weeks if self.year != 2023 else self.filing.get_last_week_saved()
        
        # Going to start with just regular season
        # Needs at least a day for advanced stats to load after MNF otherwise scraper issues
        self.week_pages = {
            week: week_url(self.year, week)
            for week in range(1,num_weeks+1)
        } if self.year != 2023 else {week: week_url(self.year, week) for week in range(6,7)} # range(last_week_saved+1, last_week_saved+2)

        ff_options = Options()
        ff_options.add_argument('--headless')

        self.driver = webdriver.Firefox(options=ff_options)

    def clean_name(self, name: str) -> str:
        """
        Standardizes name across PFR, FD, DK
        """
        clean_ = ' '.join(name.split(' ')[:2]).replace('.', '')
        return standardize_name(clean_)

    # parse_defensive_stat = lambda stat_, stat_val: int(stat_val) if stat_ in DEFENSIVE_TD_COLUMNS[1:] else standardize_initials(stat_val)
    def parse_defensive_stat(self, stat: str, stat_val: str):
        if stat == 'team':
            return standardize_initials(stat_val)

        if not len(stat_val) or stat_val == ' ':
            return 0

        return int(stat_val)

    def parse_adv_stat(self, stat: str, stat_val: str):
        if stat == 'team':
            return standardize_initials(stat_val)
    
        if 'pct' in stat or '%' in stat_val: # Just in case
            no_pct_sign = stat_val[:-1]
            return round( float(no_pct_sign)/100, 3 ) if len(no_pct_sign) else 0.0
    
        if not len(stat_val) or stat_val == ' ':
            return 0.0
    
        return float(stat_val) if '.' in stat_val else int(stat_val)

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
            
            self.driver.get(game_url)
            game_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            stat_table = game_soup.find_all('table', id='player_offense')[0]

            scorebox = game_soup.find_all('div', class_='scorebox')[0]
            
            away_team, home_team = tuple([convert_teamname(scorebox.find_all('strong')[i].get_text().replace('\n', '')) for i in (0,2)])
            away_score, home_score =  tuple([int(score.get_text().replace('\n','')) for score in scorebox.find_all('div', class_='scores')])
    
            # Different for names because th not td
            names = [
                self.clean_name(tag.get_text()) for tag in stat_table.find_all('th', attrs={'data-stat': 'player'})
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
            # table_data['pos'] = [ self.lookup_position.get(name, 'WR') for name in names ]

            # Need to figure out defense
            # Just need to remember in PPR format
            # TODO: figure out cleaner way for assign and bonuses
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
            # parse_defensive_stat = lambda stat_, stat_val: int(stat_val) if stat_ in DEFENSIVE_TD_COLUMNS[1:] else standardize_initials(stat_val)
            
            # ('team', 'def_int_td', 'fumbles_rec_td')
            def_table_data = {
                stat: [self.parse_defensive_stat(stat, td.get_text()) for td in def_table.find_all('td', attrs={'data-stat': stat})]
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
                # Issues might be here
                team_defense_stats[team]['pts_allowed'] -= 6.0*team_def_tds[get_opp(team)]
                
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

            # fpts_df = (pd
            #            .concat([
            #                offense_df,
            #                pd.DataFrame(defense_data),
            #                pd.DataFrame(kicking_data)
            #            ])
            #            .fillna(0.0) #Careful
            #            .assign(name=lambda df_: df_.name.str.strip()) # Whitespace issues
            #           )

            # # File after getting position from Pro-Football-Reference
            # self.filing.save_boxscore(fpts_df, away_team, home_team)
            
            ########################################################################################################
            # Snap Counts
            ########################################################################################################
            snapcounts_tables = {
                away_team: game_soup.find_all('table', id='vis_snap_counts')[0], #vis not away 
                home_team: game_soup.find_all('table', id='home_snap_counts')[0]
            }
            
            # Two separate tables instead of one combined table --> 2d dict
            snapcounts_data = {
                away_team: dict(),
                home_team: dict()
            }
            
            # Dont want lineman info (for now)
            target_pos = ('QB', 'WR', 'RB', 'TE')
            # Only want offensive data (for now) --> data-stat values in HTML
            snapcount_data_stats = ('player', 'pos', 'offense', 'off_pct')
            
            # Going to get everyone at first (easier) --> then will filter dict based on position / index
            for team, snapcount_html_table in snapcounts_tables.items():
                snapcounts_data[team]['name'] = [
                    self.clean_name(tag.get_text()) for tag in snapcount_html_table.find_all('th', attrs={'data-stat': 'player'})
                    if tag.get_text() != 'Player'
                ]
            
                for stat in snapcount_data_stats[1:]:
                    snapcounts_data[team][stat] = [td.get_text() for td in snapcount_html_table.find_all('td', attrs={'data-stat': stat})]
            

            # Initialize as empty outside loop in order to be used elsewhere
            name_position = {team_: dict() for team_ in (away_team, home_team)}
            
            # Now cleaning
            
            for team, snap_info in snapcounts_data.items():
                # Indexes of positions in target_pos
                num_entries = len(snap_info['name'])
                # Can actually use this as positions source instead of relying on external
                pos_indexes = [i for i in range(num_entries) if snap_info['pos'][i] in target_pos]

                # REMEMBER: snap_info = snapcounts_data[team]
                name_position[team] = {snap_info['name'][i]: snap_info['pos'][i] for i in pos_indexes}
                
                for stat in snap_info:
                    target_pos_values = [snap_info[stat][i] for i in pos_indexes]
                    if stat == 'offense':
                        target_pos_values = [int(val) for val in target_pos_values]
                    elif stat == 'off_pct':
                        target_pos_values = [float(val[:-1]) / 100 for val in target_pos_values]
                    snap_info[stat] = target_pos_values

            # Flatten name_position into 1d dict
            name_position = {
                **{name_: pos_ for name_, pos_ in name_position[away_team].items()},
                **{name_: pos_ for name_, pos_ in name_position[home_team].items()}
            }
            
            # Flattening, adding game info for subsequent individual dataframes 
            awayteam_df_data = snapcounts_data[away_team]
            hometeam_df_data = snapcounts_data[home_team]
            
            awayteam_num_rows = len(awayteam_df_data['name'])
            hometeam_num_rows = len(hometeam_df_data['name'])
            
            awayteam_df_data['team'] = [away_team] * awayteam_num_rows
            awayteam_df_data['opp'] = [home_team] * awayteam_num_rows
            
            hometeam_df_data['team'] = [home_team] * hometeam_num_rows
            hometeam_df_data['opp'] = [away_team] * hometeam_num_rows

            awayteam_df_data['week'] = [week] * awayteam_num_rows
            hometeam_df_data['week'] = [week] * hometeam_num_rows
            
            rename_columns = {
                'offense': 'snap_total',
                'off_pct': 'snap_percent'
            }
            # Make DataFrames
            away_snapcounts_df, home_snapcounts_df = tuple([
                (pd
                 .DataFrame(data_)
                 .rename(rename_columns, axis=1)
                )
                for data_ in (awayteam_df_data, hometeam_df_data)
            ])

            snapcounts_dfs = {
                away_team: away_snapcounts_df,
                home_team: home_snapcounts_df
            }

            for team, df_ in snapcounts_dfs.items():
                self.filing.save_snapcounts(df_, team, week)

            ########################################################################################################
            # Filing fpts dataframe here after being able to get positions directly from Pro-Football-Reference
            ########################################################################################################

            offense_df['pos'] = offense_df['name'].map(lambda name_: name_position.get(name_,'RB')) # Default to RB since sometimes LB or FB or weird positions get rushing attempt
            
            fpts_df = (pd
                       .concat([
                           offense_df,
                           pd.DataFrame(defense_data),
                           pd.DataFrame(kicking_data)
                       ])
                       .fillna(0.0) #Careful
                       .assign(name=lambda df_: df_.name.str.strip()) # Whitespace issues
                      )

            # Issues with current setup --> No 2pt conversions available from boxscore data, so also not applied

            # All bonuses worth 3
            dk_bonuses = {
                'pass_yds': 300.0,
                'rush_yds': 100.0,
                'rec_yds': 100.0
            }

            fpts_df['bonus'] = 0.0
            for stat, thresh in dk_bonuses.items():
                fpts_df.loc[fpts_df[stat] >= thresh, 'bonus'] += 3.0

            fpts_df['fpts'] += fpts_df['bonus']

            # File after getting position from Pro-Football-Reference
            self.filing.save_boxscore(fpts_df, away_team, home_team)

            ########################################################################################################
            # Advanced Stats
            ########################################################################################################

            ADV_COLUMNS = {
                'passing': ADV_PASSING_COLUMNS[1:],
                'rushing': ADV_RUSHING_COLUMNS[1:],
                'receiving': ADV_RECEIVING_COLUMNS[1:]
            }

            for category in ('passing', 'rushing', 'receiving'):
                adv_table = game_soup.find_all('table', id=f'{category}_advanced')[0]

                adv_table_names = [self.clean_name(tag.get_text()) for tag in adv_table.find_all('th', attrs={'data-stat': 'player'}) if tag.get_text() != 'Player']

                adv_data = {
                    **{
                        'name': adv_table_names,
                        'pos': [name_position.get(name_, 'RB') for name_ in adv_table_names],
                    },
                    **{
                        stat: [self.parse_adv_stat(stat, td.get_text()) for td in adv_table.find_all('td', attrs={'data-stat': stat})]
                        for stat in ADV_COLUMNS[category]
                    }
                }

                adv_df = pd.DataFrame(adv_data)
                adv_df['week'] = week
                
                # Save as individual team dataframe
                for team_ in adv_df['team'].drop_duplicates():
                    team_adv_df = adv_df.loc[adv_df['team'] == team_]
                    # Parameters: df, stat_category, team, week
                    self.filing.save_advanced_stats(team_adv_df, category, team_, week)
            

            # At most 16 games in one week
            # Cant have more than 20 requests in 1 minute
            # time.sleep(n) --> n = 4, 5 to be safe
            time.sleep(5)
        

        return

    def get_season_boxscores(self) -> None:
        """
        Iterates through every boxscore for every game of every week
        Saves to data directory
        """

        print(f'Beginning scraping for {self.season} season\n')

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