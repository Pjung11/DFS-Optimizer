def fix_name_mismatches(rankings):
    # fix any name mismatches - change fp/ffa version to match DK
    rankings.loc[rankings['Id'] == 'Patrick Mahomes II', 'Id'] = 'Patrick Mahomes'
    rankings.loc[rankings['Id'] == 'Gabriel Davis', 'Id'] = 'Gabe Davis'
    return rankings

def set_position_constraints(game_mode):
    # Set position constraints
    if game_mode == 'showdown':
        pos_num_available = {
            'CPT': 1,
            'FLEX': 5
        }
    else:
        pos_num_available = {
            'QB': 1,
            'RB': 2,
            'WR': 3,
            'TE': 1,
            'FLEX': 1,
            'DST': 1
        }
    return pos_num_available