import pandas as pd
import numpy as np

from src.utils import fix_name_mismatches

class ImportData:
    def __init__(self, week, game_mode, rank_src, matchup, add_results):
        self.week = week
        self.game_mode = game_mode
        self.rank_src = rank_src
        self.matchup = matchup
        self.add_results = add_results

    def read_dk(self):
        players = pd.read_csv(f'./data/DKSalaries_{self.matchup}_week{self.week}.csv', usecols=['Name', 'Roster Position', 'Salary']) #ID, AvgPointsPerGame
        players = players.rename(columns={'Name':'Id', 'Roster Position':'Position'})

        # classic doesn't separate position and flex. separate here. works better for our constraint setup
        if self.game_mode == 'classic':
            mask = players['Position'].isin(['WR/FLEX', 'RB/FLEX', 'TE/FLEX'])
            pos_df = players[mask].copy()
            pos_df['Position'] = pos_df['Position'].apply(lambda x: x.split('/')[0])
            flex_df = players[mask].copy()
            flex_df['Position'] = flex_df['Position'].apply(lambda x: x.split('/')[1])

            players = pd.concat([players[~mask], pos_df, flex_df])

        return players
    
    def read_adhoc_rankings(self, pt_col):
        all_rankings = pd.read_csv(f'./data/Adhoc_Week_{self.week}_Rankings.csv', usecols=['Player', 'Position', pt_col])
        all_rankings = all_rankings.rename(columns={'Player':'Id', pt_col:'FPPG'})
        # DK convention is only team name. With a space at the end. Annoying. Add one here
        all_rankings.loc[all_rankings['Position'] == 'DST', 'Id'] = all_rankings['Id'].apply(lambda x: x.split(' ')[-1]) + (' ')
        all_rankings = all_rankings[['Id', 'FPPG']]
        return all_rankings
    
    def read_rankings(self, players, adhoc_pt_col='Ceiling'):
    
        if self.rank_src == 'adhoc':
            all_rankings = self.read_adhoc_rankings(adhoc_pt_col)
        else:
            position_list = ['QB', 'RB', 'WR', 'TE', 'DST', 'K']
            all_rankings = pd.DataFrame()
            for pos in position_list:
                rankings = pd.read_csv(f'./data/FantasyPros_2023_Week_{self.week}_{pos}_Rankings.csv', usecols=['PLAYER NAME', 'PROJ. FPTS'])
                rankings = rankings.rename(columns={'PLAYER NAME':'Id', 'PROJ. FPTS':'FPPG'})

                # DK convention is only team name. With a space at the end. Annoying. Add one here
                if pos == 'DST':
                    rankings['Id'] = rankings['Id'].apply(lambda x: x.split(' ')[-1]) + (' ')

                all_rankings = pd.concat([all_rankings, rankings])
        
        all_rankings = fix_name_mismatches(all_rankings)

        player_rankings = players.merge(all_rankings, how='left', on='Id')

        if self.add_results:
            actual_results = pd.read_csv(f'./data/DKResults_{self.matchup}_week{self.week}.csv', 
                                         usecols=['Player', 'FPTS', 'Roster Position'])
            # DK lists CPT or FLEX scores. If CPT scale down (will rescale up in next step)
            actual_results['FPTS'] = np.where(actual_results['Roster Position'] == 'CPT',
                                              actual_results['FPTS'] * .75,
                                              actual_results['FPTS'])
            actual_results = actual_results.rename(columns={'Player':'Id', 'FPTS':'ActualFP'})
            player_rankings = player_rankings.merge(actual_results, how='left', on='Id')
        else:
            player_rankings['ActualFP'] = np.nan

        # Add 1.5 mutiplier to CPTs in showdown mode
        if self.game_mode == 'showdown':
            #player_rankings.loc[player_rankings['Position']=='CPT', 'FPPG'] = player_rankings['FPPG'] * 1.5
            player_rankings['FPPG'] = np.where(player_rankings['Position'] == 'CPT',
                                            player_rankings['FPPG'] * 1.5,
                                            player_rankings['FPPG'])
            if self.add_results:
                player_rankings['ActualFP'] = np.where(player_rankings['Position'] == 'CPT',
                                    player_rankings['ActualFP'] * 1.5,
                                    player_rankings['ActualFP'])

        return player_rankings
