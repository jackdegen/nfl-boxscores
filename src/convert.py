# Convert Pro-Football-Reference abbreviations to preferred abbreviations

# Only contains those with weird abbreviations
pfr_standard: dict[[str], str] = {
    'ram': 'lar', # Rams
    'nor': 'no', # Saints
    'sfo': 'sf', # 49ers
    'clt': 'ind', # Colts
    'htx': 'hou', # Texans
    'nwe': 'ne',
    'rav': 'bal',
    'kan': 'kc',
    'gnb': 'gb',
    'crd': 'ari',
    'oti': 'ten',
    'rai': 'lv',
    'sdg': 'lac',
    'tam': 'tb',
}

def initials(team):
    return pfr_standard.get(team, team)