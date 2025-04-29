import csv
from choicedesign.design import EffDesign
from biogeme.expressions import Beta, Variable
import biogeme.database as db
import biogeme.models as models
import pandas as pd
from biogeme.expressions import Beta, Variable, bioDraws, MonteCarlo, exp

#in algorithmy.py change iterperf.copy()  to interperf , and similar 
#change in design.py the:  for k in range(len(self.fixed)):
 #           if self.fixed[k] is not None: 
  #              init_design[self.fixed[k],k] = 0

Alts = ['alt1','alt2']
NCS = 12

# C = {	'name':		'B', #dummy
#         'levels':	[1,2,3],
#         'avail':    ['alt1','alt2'],
#         'fixed': None}

D2D = {	'name':		'D2D', #continuous
        'levels':	[0,10,30,70],
        'avail':    ['alt1','alt2'],
        'fixed': None}

D = {	'name':		'D', #continuous
        'levels':	[0,10,25,50],
        'avail':    ['alt1','alt2'],
        'fixed': None}



TS = {	'name':	    'TS', #continuous
        'levels':	[0,1],
        'avail':    ['alt1','alt2'],
        'fixed': None}

T2DR = {	'name':		'T2DR', #continuous
        'levels':	[1,2,4],
        'avail':    ['alt1','alt2'],
        'fixed': None}

T2DS = {	'name':		'T2DS', #continuous
        'levels':	[0,5,10],
        'avail':    ['alt1','alt2'],
        'fixed': None}




design = EffDesign(
    alts=Alts,
    ncs=NCS,
    atts_list=[D2D, D, TS, T2DR, T2DS])


cond = [
    'if ~( (alt1_TS==1) | (alt2_TS==1) ) then (alt1_D2D != alt2_D2D)', 
    'if (alt1_D2D <= alt2_D2D)  & (alt1_D >= alt2_D) & (alt1_TS <= alt2_TS) then 0==1', # remove dominant combinations
    
   
    'if (alt2_D2D <= alt1_D2D)  & (alt2_D >= alt1_D) & (alt2_TS <= alt1_TS) then 0==1', 
    
    
    'alt1_D != alt2_D', #different discounts
    'if alt1_TS == 1 then alt1_T2DS > 0', #if trip shift then time to departure subsequent must be >0
    'if alt2_TS == 1 then alt2_T2DS > 0',
    
    'if alt1_TS == 0 then alt1_T2DS == 0', # if no trip shift, no time to departure subsequent
    'if alt2_TS == 0 then alt2_T2DS == 0',
   
    'alt1_T2DR == alt2_T2DR ' #all the same time to departure recent

]







init_design = design.gen_initdesign(cond=cond, seed=1278)

print(init_design)


alt1_D2D = Variable('alt1_D2D')
alt1_D = Variable('alt1_D')
alt1_TS = Variable('alt1_TS')
alt1_T2DR = Variable('alt1_T2DR')
alt1_T2DS = Variable('alt1_T2DS')




alt2_D2D = Variable('alt2_D2D')
alt2_D = Variable('alt2_D')
alt2_TS = Variable('alt2_TS')
alt2_T2DR = Variable('alt2_T2DR')
alt2_T2DS = Variable('alt2_T2DS')





beta_D2D = Beta('beta_D2D',-0.02,None,None,0)
beta_D = Beta('beta_D',0.02,None,None,0)
beta_TS = Beta('beta_TS',-0.02,None,None,0)
beta_T2DR = Beta('beta_T2DR',-0.02,None,None,0)
beta_T2DS = Beta('beta_T2DS',-0.02,None,None,0)


sd_D2D = Beta('sd_D2D',0.1,None,None,0)
sd_D = Beta('sd_D',0.1,None,None,0)
sd_TS = Beta('sd_TS',0.1,None,None,0)
sd_T2DR = Beta('sd_T2DR',0.1,None,None,0)
sd_T2DS = Beta('sd_T2DS',0.1,None,None,0)


# Random parameters
beta_D2D_rnd = beta_D2D + sd_D2D * bioDraws('beta_D2D_rnd', 'NORMAL_MLHS')
beta_D_rnd = beta_D + sd_D * bioDraws('beta_D_rnd', 'NORMAL_MLHS')
beta_TS_rnd = beta_TS + sd_TS * bioDraws('beta_TS_rnd', 'NORMAL_MLHS')
beta_T2DR_rnd = beta_T2DR + sd_T2DR * bioDraws('beta_T2DR_rnd', 'NORMAL_MLHS')
beta_T2DS_rnd = beta_T2DS + sd_T2DS * bioDraws('beta_T2DS_rnd', 'NORMAL_MLHS')



V1 = beta_D2D_rnd * alt1_D2D + beta_D_rnd * alt1_D  + beta_TS_rnd * alt1_TS + beta_T2DR_rnd * alt1_T2DR + beta_T2DS_rnd * alt1_T2DS
V2 = beta_D2D_rnd * alt2_D2D + beta_D_rnd * alt2_D  + beta_TS_rnd * alt2_TS + beta_T2DR_rnd * alt2_T2DR + beta_T2DS_rnd * alt2_T2DS


V = {1: V1, 2: V2}





optimal_design, init_perf, final_perf, final_iter, ubalance_ratio = design.optimise(init_design=init_design,V=V,model='mnl_bayesian',draws=1000,time_lim = 5, verbose = True, seed=1278)

print(optimal_design)

import_df = pd.DataFrame(optimal_design)

# Export to CSV (SoSciSurvey handles CSV directly)
csv_path = "/Users/lauraknappik/sciebo - Knappik, Laura (7ZX85D@rwth-aachen.de)@rwth-aachen.sciebo.de/Dokumente/Projekte/Optimal_board_and_alight/Choice_Experiment/DCE_Python/CSV/Boarding_import.csv"
import_df.to_csv(csv_path, index=False)
