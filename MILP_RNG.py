"""
Model for RNG/NG
"""

import pulp

# Time-series constants
SBG = list(input_df['SBG(kWh)'])
D = list(input_df['NG_demand(m^3)'])
HOEP = list(input_df['HOEP'])
EMF = list(input_df['EMF(tonne/kWh)'])

# Fixed constants
N_max = 30000
nu_electrolyzer = var['value']['electrolyzer_eff']
E_HHV_H2 = var['value']['E_hhv_h2']
nu_reactor = var['value']['meth_reactor_eff']
HHV_H2 = var['value']['HHV_H2']
HHV_NG = var['value']['HHV_NG']
CO2_available = var['value']['CO2_available']
E_electrolyzer_min = var['value']['min_E_cap']
E_electrolyzer_max = var['value']['max_E_cap']
tau = 0.50

EMF_NG = var['value']['EMF_NG']
EMF_comb = var['value']['EMF_combRNG']
EMF_nuc = var['value']['EMF_nuclear']
EMF_bio = var['value']['EMF_bioCO2']
EMF_electrolyzer = var['value']['EMF_electrolyzer']
EMF_reactor = var['value']['EMF_reactor']

beta = var['value']['beta']
C_0 = var['value']['C_0']
mu = var['value']['mu']
gamma = var['value']['gamma']
k = var['value']['k']
C_upgrading = var['value']['C_upgrading']
C_CO2 = var['value']['C_CO2']
TC = var['value']['TC']
C_H2O = var['value']['C_H2O']
WCR = var['value']['water_cons_rate']
OPEX_upgrading = var['value']['OPEX_upgrading']
TVM = var['value']['TVM']

# Tank and compressor constants
I_max = var['value']['Imax'] # kmol
I_min= var['value']['Imin'] # kmol
F_max_booster = var['value']['Fmax_booster'] # kmol
F_max_prestorage =var['value']['Fmax_prestorage'] # kmol

CAPEX_booster = var['value']['CAPEX_booster'] # $
CAPEX_prestorage = var['value']['CAPEX_prestorage'] # $
CAPEX_tank = var['value']['CAPEX_tank'] # $

ECF_prestorage = var['value']['ECF_prestorage'] # kWh/kmol H2

# RNG model
LP_eps = pulp.LpProblem('LP_eps', pulp.LpMaximize)
LP_cost = pulp.LpProblem('LP_cost', pulp.LpMinimize)

RNG_max = pulp.LpVariable('RNG_max',
                          lowBound=0,
                          cat='Continuous')
N_electrolyzer_1 = pulp.LpVariable('N_electrolyzer_1',
                          lowBound=0,
                          cat='Integer')
alpha_1 = pulp.LpVariable.dicts('alpha_1',
                          [str(i) for i in range(1, N_max)],
                          cat='Binary')

E_1 = pulp.LpVariable.dicts('E_1',
                          [str(i) for i in input_df.index],
                          lowBound=0,
                          cat='Continuous')
RNG = pulp.LpVariable.dicts('RNG',
                          [str(i) for i in input_df.index],
                          lowBound=0,
                          cat='Continuous')
CO2 = pulp.LpVariable.dicts('CO2_1',
                          [str(i) for i in input_df.index],
                          lowBound=0,
                          cat='Continuous')
NG_1 = pulp.LpVariable.dicts('NG_1',
                          [str(i) for i in input_df.index],
                          lowBound=0,
                          cat='Continuous')

em_offset_1 = pulp.LpVariable('em_offset_1',
                          lowBound=0,
                          cat='Continuous')
em_rng = pulp.LpVariable('em_rng',
                          lowBound=0,
                          cat='Continuous')
em_ng = pulp.LpVariable('em_ng',
                          lowBound=0,
                          cat='Continuous')
# Number of prestorage compressors
N_prestorage = pulp.LpVariable('N_prestorage',
                          lowBound=0,
                          cat='Integer')
# Number of tanks
N_tank = pulp.LpVariable('N_tank',
                          lowBound=0,
                          cat='Integer')
# H2 flow directly from electrolyzers (m^3/h)
H2_direct = pulp.LpVariable.dicts('H2_direct',
                          [str(i) for i in input_df.index],
                          lowBound=0,
                          cat='Continuous')
# H2 flow going into tanks from electrolyzers (m^3/h)
H2_tank_in = pulp.LpVariable.dicts('H2_tank_in',
                          [str(i) for i in input_df.index],
                          lowBound=0,
                          cat='Continuous')
# H2 flow coming out from tanks (m^3/h)
H2_tank_out = pulp.LpVariable.dicts('H2_tank_out',
                          [str(i) for i in input_df.index],
                          lowBound=0,
                          cat='Continuous')
# Inventory level of H2 (m^3)
I_H2 = pulp.LpVariable.dicts('I_H2',
                          [str(i) for i in input_df.index],
                          lowBound=0,
                          cat='Continuous')

CAPEX_1 = pulp.LpVariable('CAPEX_1', lowBound=0, cat='Continuous')
OPEX_1 = pulp.LpVariable('OPEX_1', lowBound=0, cat='Continuous')

for LP in [LP_eps, LP_cost]:
    for i, h in enumerate([str(i) for i in input_df.index]):
        # Energy and flow constraints
        if h == '0':
            LP += RNG_max <= CO2_available
        LP += H2_direct[h] + H2_tank_in[h] == nu_electrolyzer * E_1[h] * E_HHV_H2 ** -1
        LP += RNG[h] == nu_reactor * (H2_direct[h] + H2_tank_out[h]) * HHV_H2 / HHV_NG
        LP += CO2[h] == RNG[h]
        
        # Hydrogen storage tank constraint
        if h == '0':
            LP += I_H2[h] == I_min * N_tank + H2_tank_in[h] - H2_tank_out[h]
        else:
            LP += I_H2[h] == I_H2[str(i - 1)] + H2_tank_in[h] - H2_tank_out[h]
        LP += I_H2[h] <= I_max * N_tank
        LP += I_H2[h] >= I_min * N_tank        

        # Demand constraint
        LP += NG_1[h] == D[i] - RNG[h]

        # Electrolyzer and reactor constraints
        LP += N_electrolyzer_1 * E_electrolyzer_min <= E_1[h]
        LP += N_electrolyzer_1 * E_electrolyzer_max >= E_1[h]
        LP += E_1[h] <= SBG[i]
        LP += RNG[h] <= RNG_max
        if h != '0':
            LP += -RNG_max * tau <= RNG[h] - RNG[str(i - 1)]
            LP += RNG_max * tau >= RNG[h] - RNG[str(i - 1)]
        if h == '0':
            LP += pulp.lpSum(n * alpha_1[str(n)] for n in range(1, N_max)) == N_electrolyzer_1
            LP += pulp.lpSum(alpha_1) <= 1

    # Emission constraints
    LP += pulp.lpSum(EMF_NG * NG_1[h] + EMF_comb * RNG[h] + EMF[int(h)] * E_1[h] + \
                       EMF_bio * CO2[h] + EMF_electrolyzer * (H2_direct[h] + H2_tank_in[h]) + EMF_reactor * RNG[h] + \
                       EMF[int(h)] * ECF_prestorage * H2_tank_in[h] for h in [str(x) for x in input_df.index]) \
        == em_rng
    LP += pulp.lpSum(EMF_NG * D[h] for h in input_df.index) == em_ng

# Eps Objective
LP_eps += em_ng - em_rng, 'Offset_1'
LP_eps.solve()
offset_max_1 = LP_eps.objective.value()
print(LP_eps.status)

# CAPEX
C_electrolyzer = [beta * C_0 * i ** mu for i in range(1, N_max)]
LP_cost += pulp.lpSum(alpha_1[str(n)] * C_electrolyzer[n - 1] for n in range(1, N_max)) + \
           gamma * RNG_max + k + C_upgrading * RNG_max + (N_tank * CAPEX_tank + N_prestorage * CAPEX_prestorage) * 20 \
    == CAPEX_1

# OPEX
LP_cost += pulp.lpSum(CO2[str(n)] * C_CO2 for n in input_df.index) + \
           pulp.lpSum(E_1[str(n)] * (HOEP[n] + TC) for n in input_df.index) + \
           pulp.lpSum((H2_direct[str(n)] + H2_tank_in[str(n)]) * C_H2O * WCR for n in input_df.index) + \
           pulp.lpSum(ECF_prestorage * H2_tank_in[str(n)] for n in input_df.index) + \
           OPEX_upgrading * RNG_max == OPEX_1

# Objectives
phi = 0.80
LP_cost += em_ng - em_rng == em_offset_1
LP_cost += em_offset_1 >= phi * offset_max_1
LP_cost += CAPEX_1 + OPEX_1 * TVM, 'Cost_1'

LP_cost.solve()
print(LP_cost.status)
