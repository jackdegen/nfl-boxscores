ADV_PASSING_COLUMNS = [
    'player', # changed to 'name'
    'team',
    'pass_cmp',
    'pass_att',
    'pass_yds',
    'pass_first_down',
    'pass_first_down_pct',
    'pass_target_yds',
    'pass_tgt_yds_per_att',
    'pass_air_yds',
    'pass_air_yds_per_cmp',
    'pass_air_yds_per_att',
    'pass_yac',
    'pass_yac_per_cmp',
    'pass_drops',
    'pass_drop_pct',
    'pass_poor_throws',
    'pass_poor_throw_pct',
    'pass_sacked',
    'pass_blitzed',
    'pass_hurried',
    'pass_hits',
    'pass_pressured',
    'pass_pressured_pct',
    'rush_scrambles',
    'rush_scrambles_yds_per_att'
]

#rushing_advanced
ADV_RUSHING_COLUMNS = [
    'player',
    'team',
    'rush_att',
    'rush_yds',
    'rush_td',
    'rush_first_down',
    'rush_yds_before_contact',
    'rush_yds_bc_per_rush',
    'rush_yac',
    'rush_yac_per_rush',
    'rush_broken_tackles',
    'rush_broken_tackles_per_rush' # Incorrectly named on website, cant do much about it // Weird stat, ignore??
]

#receiving_advanced
ADV_RECEIVING_COLUMNS = [
    'player',
    'team',
    'targets',
    'rec',
    'rec_yds',
    'rec_td',
    'rec_first_down',
    'rec_air_yds',
    'rec_air_yds_per_rec',
    'rec_yac',
    'rec_yac_per_rec',
    'rec_adot',
    'rec_broken_tackles',
    'rec_broken_tackles_per_rec',
    'rec_drops',
    'rec_drop_pct',
    'rec_target_int',
    'rec_pass_rating'
]


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