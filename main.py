# %%
import ujson
import csv
from utils import *
import itertools
import math
import pulp as lp

# %% 战区关卡参数
theater_id = '743'  # 关卡id,如736代表第7期第3区域第6关
fairy_ratio = 1.25  # 妖精加成：5星1.25
max_dolls = 20  # 上场人数
upgrade_resource = 30 # 可以用于强化的资源量（普通装备消耗1份，专属消耗3份）

# %%
theater_config = get_theater_config(theater_id)
theater_config['max_dolls'] = max_dolls
theater_config['fairy_ratio'] = fairy_ratio
# %%
name_table = get_name_table()
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
problem = lp.LpProblem('battlefield', lp.LpMaximize)
for k, recipe in choices.items():
    lp_vars[k] = lp.LpVariable(k, cat=lp.LpInteger, lowBound=0)
    for r, c in recipe.items():
        resource[r] += c*lp_vars[k]
    if k[:2] != '强化':
        resource['count'] -= lp_vars[k]
for k, v in resource.items():
    problem += v >= 0, k
problem += resource['score']
problem.solve()
print(resource['score'].value())
strn = []
res = []
for k, v in lp_vars.items():
    if v.value()>0:
        if k[:2] == '强化':
            strn.append((k, v.value()))
        else:
            res.append((k, choices[k]['score']))
res.sort(key=lambda x: x[1], reverse=True)
for r in strn:
    print(r[0], r[1],sep='\t')
for r in res:
    print(r[0], r[1],sep='\t')
# %%
