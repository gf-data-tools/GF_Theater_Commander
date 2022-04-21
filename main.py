# %%
from collections import defaultdict
from utils import *
import pulp as lp
import argparse
from prettytable import PrettyTable
import os

# %% argparse
parser = argparse.ArgumentParser()
parser.add_argument('theater_id',default='748',type=str,help='关卡id,如736代表第7期高级区第6关')
parser.add_argument('-m','--max_dolls',type=int,default=30,help='上场人数')
parser.add_argument('-f','--fairy_ratio',type=float,default=1.25,help='妖精加成,默认5星1.25')
parser.add_argument('-u','--upgrade_resource',type=int,default=0,help='可以用于强化的资源量（普通装备消耗1份，专属消耗3份）')
parser.add_argument('-l', '--language', type=str, default='zh-CN', help='pick a column from resource/table.csv')
args = parser.parse_args()
# %% 战区关卡参数
theater_id = args.theater_id  # 关卡id,如736代表第7期第3区域第6关
fairy_ratio = args.fairy_ratio  # 妖精加成：5星1.25
max_dolls = args.max_dolls  # 上场人数
upgrade_resource = args.upgrade_resource # 可以用于强化的资源量（普通装备消耗1份，专属消耗3份）
language = args.language  # language code to be used to pick a column from resource/table.tsv

# %%
theater_config = get_theater_config(theater_id)
theater_config['max_dolls'] = max_dolls
theater_config['fairy_ratio'] = fairy_ratio
# %%
name_table = get_name_table(language)
doll_info, equip_info, my_dolls, my_equips = load_info()
# %% 计算各人形不同配装的效能
choices = prepare_choices(doll_info, equip_info, my_dolls, my_equips, theater_config)
# %%
resource = {}
for id, doll in my_dolls.items():
    if doll['gun_level'] > 0:
        resource[doll['name']]=1
for id, equip in my_equips.items():
    # if equip['level_10'] > 0:
    resource[f"{equip['name']}_10"]=equip['level_10']
    if equip['level_00'] > 0:
        resource[f"{equip['name']}_0"]=equip['level_00']
resource['count'] = max_dolls
resource['score'] = 0
resource['强化资源'] = upgrade_resource
lp_vars = {}
coeff_lp_var_dict = defaultdict(list)
problem = lp.LpProblem('battlefield', lp.LpMaximize)
for k, recipe in choices.items():
    lp_vars[k] = lp.LpVariable(k, cat=lp.LpInteger, lowBound=0)
    for r, c in recipe.items():
        # build a dict with value as lists of (coefficient, LpVar) tuples before building LpAffineExpression in bulk
        # else doing += coefficient*LpVar would trigger significantly amount of costly LpAffineExpression.__init__ call
        coeff_lp_var_dict[r].append((lp_vars[k], c))
    if k[:2] != '强化':
        resource['count'] -= lp_vars[k]
for k,v in coeff_lp_var_dict.items():
    resource[k] += lp.LpAffineExpression(v)
for k, v in resource.items():
    problem += v >= 0, k
problem += resource['score']

lp_bin_rel = lp.core.pulp_cbc_path.split('solverdir\\')[-1]
lp_bin_abs = os.path.join(os.getcwd(), 'solverdir', lp_bin_rel)
problem.solve(lp.COIN_CMD(msg=0,path=lp_bin_abs))

print(f"总效能: {resource['score'].value()}")
strn_table = PrettyTable(['强化装备','数量'])
res_table = PrettyTable(['人形','装备1','强化1','装备2','强化2','装备3','强化3','效能'])
for i in range(1,4):
    res_table.align[f'强化{i}'] = 'r'
res_table.sortby = '效能'
res_table.reversesort = True
for k, v in lp_vars.items():
    if v.value()>0:
        if k[:2] == '强化':
            strn_table.add_row(((get_translation(k[3:], name_table)), v.value()))
        else:
            new_row = k.split('\t')
            new_row = [get_translation(e, name_table) for e in new_row]
            new_row.append(choices[k]['score'])
            res_table.add_row(new_row)
print(strn_table)
print(res_table)

# %%
