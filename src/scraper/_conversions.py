# Convert Pro-Football-Reference abbreviations to preferred abbreviations

# Only contains those with weird abbreviations
pfr_standard: dict[[str], str] = {
    'ram': 'lar', # Rams
    'nor': 'no', # Saints
    'sfo': 'sf', # 49ers
    'clt': 'ind', # Colts
    'htx': 'hou', # Texans
    'nwe': 'ne', # Patriots
    'rav': 'bal', # Ravens
    'kan': 'kc', # Chiefs
    'gnb': 'gb', # Packers
    'crd': 'ari', # Cardinals
    'oti': 'ten', # Titans
    'rai': 'lv', # Raiders
    'lvr': 'lv', # Raiders 2
    'sdg': 'lac', # Chargers
    'tam': 'tb', # Buccaneers
}

def standardize_initials(team):
    return pfr_standard.get(team.lower(), team).upper()


teamname_initials: dict[[str], str] = {
    'Arizona Cardinals': 'ARI',
    'Atlanta Falcons': 'ATL',
    'Baltimore Ravens': 'BAL',
    'Buffalo Bills': 'BUF',
    
    'Carolina Panthers': 'CAR',
    'Chicago Bears': 'CHI',
    'Cincinnati Bengals': 'CIN',
    'Cleveland Browns': 'CLE',
    
    'Dallas Cowboys': 'DAL',
    'Denver Broncos': 'DEN',
    'Detroit Lions': 'DET',
    'Green Bay Packers': 'GB',
    
    'Houston Texans': 'HOU',
    'Indianapolis Colts': 'IND',
    'Jacksonville Jaguars': 'JAX', # **
    'Kansas City Chiefs': 'KC',
    
    'Los Angeles Chargers': 'LAC',
    'Los Angeles Rams': 'LAR',
    'Las Vegas Raiders': 'LV', # **
    'Miami Dolphins': 'MIA',
    
    'Minnesota Vikings': 'MIN',
    'New England Patriots': 'NE',
    'New Orleans Saints': 'NO',
    'New York Giants': 'NYG',
    
    'New York Jets': 'NYJ',
    'Philadelphia Eagles': 'PHI',
    'Pittsburgh Steelers': 'PIT',
    'San Francisco 49ers': 'SF',
    
    'Seattle Seahawks': 'SEA',
    'Tampa Bay Buccaneers': 'TB',
    'Tennessee Titans': 'TEN',
    'Washington Commanders': 'WAS' # **
    
}


def convert_teamname(team_str):
    return teamname_initials[team_str]

