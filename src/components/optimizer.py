import pandas as pd
from pulp import *

from src.utils import set_position_constraints

class OptimizeLineup:
    def __init__(self, game_mode, availables, n_lineups, force_ins, add_results):
        self.game_mode = game_mode
        self.availables = availables
        self.n_lineups = n_lineups
        self.force_ins = force_ins
        self.add_results = add_results

    def run_optimizer(self): 
        salaries = {}
        points = {}
        actuals = {}

        # Create dictionaries of the form {Position: {id: salaries or points}}

        for pos in self.availables.Position.unique():
            available_pos = self.availables[self.availables.Position == pos]
            salary = list(available_pos[['Id', 'Salary']].set_index('Id').to_dict().values())[0]
            point = list(available_pos[['Id', 'FPPG']].set_index('Id').to_dict().values())[0]
            if self.add_results:
                actual = list(available_pos[['Id', 'ActualFP']].set_index('Id').to_dict().values())[0]
                actuals[pos] = actual
            salaries[pos] = salary
            points[pos] = point

        force_df = self.availables[self.availables['Id'].isin(self.force_ins)]
        force_list = [f"{p}_{i.replace(' ', '_')}" for p, i in zip(force_df['Position'], force_df['Id'])]

        pos_num_available = set_position_constraints(self.game_mode)

        salary_cap = 50000

        all_lineups = pd.DataFrame()

        # Loop over the desired number of lineups
        for lineup in range(1, self.n_lineups+1):
            # create binary pulp variable to track whether player is chosen or not
            # variables of the form <pos>_<id>
            _vars = {k: LpVariable.dict(k, v, cat='Binary') for k, v in points.items()}
            
            prob = LpProblem('Fantasy', LpMaximize)   
            rewards = []
            costs = []
            position_constraints = []
            results = []
            
            # iterate over players to populate tracking lists for solving
            for k, v in _vars.items():
                costs += lpSum([salaries[k][i] * _vars[k][i] for i in v])
                rewards += lpSum([points[k][i] * _vars[k][i] for i in v])
                prob += lpSum([_vars[k][i] for i in v]) == pos_num_available[k]
                if self.add_results:
                    results += lpSum([actuals[k][i] * _vars[k][i] for i in v])

                
            # set constraints so cant select same player for cpt and flex
            # TODO: this assumes cpt and flex lists are the same, may not be if we screen availables
            if self.game_mode == 'showdown':
                for i, v in enumerate(_vars['CPT'].values()):
                    prob += v + list(_vars['FLEX'].values())[i] <= 1
                    
             #   for p in self.force_ins:
             #       prob += _vars['CPT'][p] + _vars['FLEX'][p] == 1
            
            # set constraints so cant select same player for position slots and flex
            if self.game_mode == 'classic':
                # here flex has multiple positions
                # get all positions and sort to match flex order
                pos_dct = {}
                pos_dct.update(_vars['RB'])
                pos_dct.update(_vars['WR'])
                pos_dct.update(_vars['TE'])
                pos_dct = dict(sorted(pos_dct.items()))

                for i, v in enumerate(pos_dct.values()):
                    prob += v + list(_vars['FLEX'].values())[i] <= 1

            # set force ins
            for p in self.force_ins:
                forcein_pos = list(self.availables[self.availables['Id'] == p]['Position'])
                if len(forcein_pos) == 1:
                    prob += _vars[forcein_pos[0]][p] == 1
                if len(forcein_pos) == 2:
                    prob += _vars[forcein_pos[0]][p] + _vars[forcein_pos[1]][p] == 1
            
            # add points and salaries to the solver
            # rewards is our objective function (notice no constraint)
            prob += lpSum(rewards)
            prob += lpSum(costs) <= salary_cap
            # first lineup will have highest total score
            # for subsequent lineups lower the previous score to ensure varied lineups
            if not lineup == 1:
                prob += (lpSum(rewards) <= total_score-.01)
            prob.solve(PULP_CBC_CMD(msg=0))

            # score format here is FPPG1*player1 name + FFPG2* player2 name ...
            score = str(prob.objective)
            results = str(results)
            #constraints = [str(const) for const in prob.constraints.values()]
            
            colnum = 1

            # loop over player/binary list
            for v in prob.variables():
                # score here replaces player name with binary indicator of whether selected (varValue)
                score = score.replace(v.name, str(v.varValue))
                #if self.add_results:
                results = results.replace(v.name, str(v.varValue))

                # save players selected for lineup to dataframe
                if v.varValue !=0:
                    all_lineups.loc[lineup, colnum] = v.name
                    colnum += 1

            # save total_score to dataframe
            total_score = eval(score)
            all_lineups.loc[lineup, 'ProjFP'] = total_score

            if self.add_results:
                total_actual = eval(results)
                all_lineups.loc[lineup, 'ActualFP'] = total_actual

        return all_lineups