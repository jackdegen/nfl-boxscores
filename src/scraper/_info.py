


DEFENSIVE_TD_COLUMNS = [
    'team',
    'def_int_td',
    'fumbles_rec_td'
]

# int_cats = def_td_categories[1:]

DEFENSIVE_FPTS_RULES = {
    'pass_sacked': 1.0,
    'pass_int': 2.0,
    'fumbles_lost': 2.0,
}

KICKING_FPTS_RULES = {
    'xpm': 1.0,
    'fgm': 3.0
}

# Column labels on pro-football-reference
OFFENSIVE_COLUMNS = [
    'player', # within href
    'team',
    'pass_cmp',
    'pass_att',
    'pass_yds',
    'pass_td',
    'pass_int',
    'pass_sacked',
    'pass_sacked_yds',
    'pass_long',
    'pass_rating',
    'rush_att',
    'rush_yds',
    'rush_td',
    'rush_long',
    'targets',
    'rec',
    'rec_yds',
    'rec_td',
    'rec_long',
    'fumbles',
    'fumbles_lost'
]

PTS_ALLOWED_SCORING = {
    range(0,1): 10.0,
    range(1,7): 7.0,
    range(7,14): 4.0,
    range(14,21): 1.0,
    range(21, 28): 0.0,
    range(28, 35): -1.0,
    range(35, 100): -4.0
}