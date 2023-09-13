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

def convert_initials(team):
    return pfr_standard.get(team.lower(), team).upper()