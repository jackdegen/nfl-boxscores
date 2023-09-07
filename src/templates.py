# File to store web address templates that will be used repeatedly with slightly different forms


# Returns directory page for all boxscores of certain year
# Links to every boxscore found on this page
# Defaults to most recent year
def directory_url(year='2022') -> str:
    return f'https://www.footballdb.com/games/index.html?lg=NFL&yr={year}'