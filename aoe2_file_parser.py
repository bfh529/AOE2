# read in a datafile
# parse each row and summarize it according to the following example:
# Begin example data row:
# Boh-Gur-Chi (me-Andy-Tom) v Azt-Hin-Per-Burg (Spencer-Ethan-Jared-Ryan) - arabia, got our trash kicked in, loss.aoe2record
# End example data row
# Begin interpretation:
# What this means is that I played a game of Age of Empires 2 ("AOE2"), with Andy and Tom as my teammates, 
# against a team consisting of Spencer, Ethan, Jared, and Ryan, that I played as the Bohemians ("Boh"), 
# Andy as the Gurjaras ("Gur"), Tom as the Chinese ("Chi"), Spencer as the Aztecs ("Azt"), Ethan as the 
# Hindustanis ("Hin"), Jared as the Persians ("Per"), and Ryan as the Burgundians ("Burg"), where the map 
# played upon was Arabia; the summary of the game is the text between the map specification and the result 
# ("loss").  "Loss" means that my team lost the game and the other team won the game.
# End interpretation
# Please give a summary of the won-loss records of each player resulting from that game.
# Also, list all the players in one list with their record in W-L format and winning percentage, ordered by winning percentage.
# Some further things to note about the data:
# - Civilization abbreviations will be 2-5 letters long
# - "me" always means myself, but list me as "Brian"
# - some games will have a tag called "epic" listed with them; please keep track of these
# - the map will be listed after a hyphen and before a comma
# - the "epic" tag may be in various places in the string, but usually immediately before or after the map name
# - the summary will follow after a comma or hyphen and will go up to the comma preceding the result
# - the result will be "win" or "loss"

# TODO:
# Questions:
# what about different game modes, such as "koth" or "dtw" or "500 pop" or "co-op"?
# what about handicaps?
# incorporate map type
# save to a Neo4j database
# can't have two players with the same name or it fouls up the dictionary keys

import numpy as np
import pandas as pd


CIV_DICT = {
    'Arm': 'Armenians', 'Azt': 'Aztecs', 'Ben': 'Bengalis', 'Ber': 'Berbers',
    'Boh': 'Bohemians', 'Brit': 'Britons', 'Bul': 'Bulgarians', 'Burg': 'Burgundians',
    'Burm': 'Burmese', 'Byz': 'Byzantines', 'Cel': 'Celts', 'Chi': 'Chinese',
    'Cum': 'Cumans', 'Drav': 'Dravidians', 'Eth': 'Ethiopians', 'Fra': 'Franks',
    'Geo': 'Georgians', 'Got': 'Goths', 'Gur': 'Gurjaras', 'Hin': 'Hindustanis',
    'Hun': 'Huns', 'Inc': 'Incas', 'Ital': 'Italians', 'Jap': 'Japanese',
    'Khm': 'Khmer', 'Kor': 'Koreans', 'Lit': 'Lithuanians', 'Mag': 'Magyars',
    'Malay': 'Malay', 'Mali': 'Malians', 'May': 'Mayans', 'Mon': 'Mongols',
    'Per': 'Persians', 'Pol': 'Poles', 'Port': 'Portuguese', 'Rom': 'Romans',
    'Sar': 'Saracens', 'Sic': 'Sicilians', 'Slob': 'Slobs', 'Spa': 'Spanish',
    'Tat': 'Tatars', 'Teut': 'Teutons', 'Tur': 'Turks', 'Viet': 'Vietnamese',
    'Vik': 'Vikings'
}

GAME_NIGHT_PLAYERS = [
    'Ammon', 'Andy', 'Bill', 'Brian', 'Chris', 'Connor', 'Ethan', 
    'Hayden', 'Jared', 'Jimmy', 'Joel', 'Jordan', 'Juan', 'Lana', 'Laremy',
    'McKay', 'MikeM', 'MikeS', 'Nita', 'Phelecia', 'Ryan', 'Smoom', 'Spencer',
    'Tom', 'Travis'
]

DEFAULT_FILE = '../AOE2/all_saved_games.xlsx'


def populate_game_nights():
    now = np.datetime64('now').astype('datetime64[D]')
    date = np.datetime64('2022-11-10').astype('datetime64[D]')

    game_nights, other_thursdays = [], []

    while date < now:
        game_nights.append(date)
        date += np.timedelta64(7, 'D')
        other_thursdays.append(date)
        date += np.timedelta64(7, 'D')

    # exceptions
    game_nights.append(np.datetime64('2022-11-26').astype('datetime64[D]'))
    game_nights.append(np.datetime64('2024-07-03').astype('datetime64[D]'))

    return game_nights, other_thursdays


def read_records_from_file(filename):
    with open(filename, 'r') as f:
        if filename.endswith('.xlsx'):
            records = pd.read_excel(filename)
            if hasattr(records, 'to_records'):
                records = records.to_records(index=False)
        else:
            records = [line.strip() for line in f.readlines()]
            if records and records[0].startswith('Name,CreationTime'):
                records = records[1:]
    return records


def parse_game_record(record):
    # determine if it was an epic game
    epic = '- epic -' in record[0]
    if epic:
        record[0] = record[0].replace('epic - ', '')

    # determine whether it was on a game night or other Thursday
    game_nights, other_thursdays = populate_game_nights()
    date = record[1].astype('datetime64[D]')
    game_night, other_thursday = False, False
    if date in game_nights:
        game_night = True
    elif date in other_thursdays:
        other_thursday = True

    # section off teams, map, and result
    if len(record[0].split(' - ', 1)) == 2:
        teams_raw, map_and_result = record[0].split(' - ', 1)
        map_name = map_and_result.split(',')[0].strip()
        result = map_and_result.split(',')[-1].strip().replace('.aoe2record', '')
    else: # no game summary provided (e.g., for a "1st-half" game)
        result = 'no decision'
        map_name = ''
        teams_raw = record[0].split(',')[0].strip().replace('.aoe2record', '')
    if 'win' not in result and 'loss' not in result:
        if result == 'smurf':
            result = 'loss'
        else:
            result = 'no decision'

    # parse teams_raw
    player_teams = teams_raw.split(' v ')
    if len(player_teams) < 2: # e.g., mirror game w/ Andy
        player_teams.append(player_teams[0])

    teams = []
    for i, pt in enumerate(player_teams):
        if ', win' in pt:
            pt = pt.replace(', win', '')
            teams.append(parse_team(pt, i + 1))
            if isinstance(result, list):
                for key in teams[-1].keys():
                    result.append(key)
            else:
                result = [key for key in teams[-1].keys()]
        else:
            teams.append(parse_team(pt, i + 1))

    # determine if it was a ranked game
    ranked = True
    if all(k in GAME_NIGHT_PLAYERS or k == 'AI' for k in teams[1].keys()):
        ranked = False

    # determine if it was a team game
    team_game = True
    if len(teams) == 2:
        if len(teams[0]) == 1 and len(teams[1]) == 1:
            team_game = False
    else:
        for team in teams:
            if len(team) == 1:
                team_game = False

    return {
        'epic': epic,
        'game_night': game_night,
        'other_thursday': other_thursday,
        'ranked': ranked,
        'team_game': team_game,
        'map': map_name,
        'result': result,
        'teams': {f'team_{i + 1}': teams[i] for i in range(len(teams))}
    }


def parse_team(team_str, number):
    if '(' in team_str and ':' in team_str: # for handicaps
        while ':' in team_str:
            # handicap = int(team_str[team_str.index(':')+1:team_str.index(':') + 4])
            team_str = team_str.replace(':', '')
            # TODO: handle handicaps
        team_str = team_str[:team_str.index(' (')] + team_str[team_str.index(')') + 1:]
    if '(' in team_str:
        civs, players = team_str.split(' (')
        if '-' in team_str and team_str[team_str.index('-') - 1] != ' ' and team_str[team_str.index('-') + 1] != ' ':
            players = players.replace(')', '').split('-')
        elif '-' not in team_str:
            players = [players.replace(')', '')]
    else:
        if number == 1:
            players = ['me']
        else:
            players = ['Andy']
        civs = team_str
    civs = civs.split('-')
    if players[0].startswith('me') and number == 1:
        players[0] = 'Brian'
    if players[0] == 'mirror':
        if number == 1:
            players = ['Brian']
        if number == 2:
            players = ['Andy']
        civs = [civs[0]]
    return dict(zip(players, civs))


def summarize_records(records, contest_type='', min_games_played=0, players_excluded=[]):
    player_records = {}
    for record in records:
        # parsed = parse_game_record(record) # TODO: won't work for non-Excel files
        result = record['result']
        teams = []
        for i in record['teams'].keys():
            teams.append(record['teams'][i])
        if result == 'no decision':
            for team in teams:
                for player in team.keys():
                    player_records.setdefault(player, {'wins': 0, 'losses': 0, 'no decisions': 0})
                    player_records[player]['no decisions'] += 1
            continue

        if len(teams) == 2:
            for player in teams[0].keys():
                player_records.setdefault(player, {'wins': 0, 'losses': 0, 'no decisions': 0})
                if result == 'win':
                    player_records[player]['wins'] += 1
                else:
                    player_records[player]['losses'] += 1

            for player in teams[1].keys():
                player_records.setdefault(player, {'wins': 0, 'losses': 0, 'no decisions': 0})
                if result == 'loss':
                    player_records[player]['wins'] += 1
                else:
                    player_records[player]['losses'] += 1
        else:
            for team in teams:
                for player in team.keys():
                    player_records.setdefault(player, {'wins': 0, 'losses': 0, 'no decisions': 0})
                    if player in result:
                        player_records[player]['wins'] += 1
                    else:
                        player_records[player]['losses'] += 1

    summary = []
    for player, record in player_records.items():
        wins = record['wins']
        losses = record['losses']
        no_decisions = record['no decisions']
        decisions = wins + losses
        total_games = decisions + no_decisions
        win_percentage = (wins / decisions) * 100 if decisions > 0 else 0
        if total_games >= min_games_played and player not in players_excluded:
            summary.append({'Player': player, f'{contest_type} Record': f"{wins}-{losses}", f'{contest_type} Win %': f"{win_percentage:.2f}"})

    summary.sort(key=lambda x: float(x[f'{contest_type} Win %']), reverse=True)
    return summary


def filter_player_games(player, civ=None, result=None, records=[]):
    """
    Filter games a certain player played in.

    Parameters
    ----------
    player : str
        The player to filter by.
    civ : str or None, default None
        The civilization to filter by. If None, don't filter.
    result : str or None, default None
        The result to filter by. If None, don't filter.
    records : list of dicts or None, default None
        The records to filter. If None, use all records.

    Returns
    -------
    list of dicts
        The filtered records.
    """
    if len(records) == 0:
        for record in read_records_from_file(DEFAULT_FILE):
            records.append(parse_game_record(record))

    filtered_records = []
    for record in records:
        teams = record['teams']
        # change for more than 2 teams
        if any(player in teams[f'team_{i + 1}'] for i in range(len(teams))):
            if civ is not None:
                for i in range(len(teams)):
                    if player in teams[f'team_{i + 1}']:
                        player_civ = teams[f'team_{i + 1}'][player]
                        break
                if player_civ not in [civ, CIV_DICT[civ]]:
                    continue
            if result is not None:
                if result not in [record['result']] * 2:
                    continue
            filtered_records.append(record)

    return filtered_records

if __name__ == '__main__':
    print(summarize_records('../AOE2/all_saved_games.xlsx'))
