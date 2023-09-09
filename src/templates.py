import datetime
import pandas as pd

def season_date_list(season):
    """
    Returns list of dates in %Y%m%d format for all dates in regular season
    """
    
    # Just going to do regular season for now
    SEASON_DATES = {
        '2022-2023': ('20220908', '20230108')
    }

    # Can shorten to not include Tuesday, Wednesday, Friday, and most Saturdays
    return [date.strftime('%Y%m%d') for date in pd.date_range(*SEASON_DATES[season])]


def week_url(year, week) -> str:
    """
    Returns page with all boxscores of certain week
    Links to every boxscore for that week found on this page
    """
    # return f'https://www.footballdb.com/games/index.html?lg=NFL&yr={year}'
    return f'https://www.pro-football-reference.com/years/{year}/week_{week}.htm'


def boxscore_url(date, hometeam):
    """
    Parameters date string in %Y%m%d format and hometeam
    Returns webpage for given boxscore
    Takes form: {parent_url}/boxscores/{date}0{hometeam}.htm --> Not sure why extra 0 at end
    """
    return f'https://www.pro-football-reference.com/boxscores/{date}0{hometeam}.htm'
    