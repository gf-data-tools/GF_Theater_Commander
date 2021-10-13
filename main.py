# %%
import ujson
import csv
from utils import *
import itertools
import math
import pulp as lp

# %% 战区关卡参数
theater_id = '738'  # 关卡id,如736代表第7期第3区域第6关
fairy_ratio = 1.25  # 妖精加成：5星1.25
max_dolls = 20  # 上场人数

# %%
theater_config = get_theater_config(theater_id)
class_weight = theater_config['class_weight']
advantage = theater_config['advantage']
fight_mode = theater_config['fightmode']
# %%
name_table = get_name_table()
# %%
with open(r'resource/doll.json') as f:
    doll_info = ujson.load(f)
with open(r'resource/equip.json',encoding='utf-8') as f:
    equip_info = ujson.load(f)
with open(r'info/user_info.json') as f:
    user_info = ujson.load(f)
# %% 统计持有人形信息
my_dolls = {}
for doll in doll_info:
    id = doll['id']
    if 1200 < id < 20000 or id > 30000:
        continue
    my_dolls[doll['id']] = {
        'id':doll['id'],
        'name':name_table[doll['name']],
        'gun_level': 0,
        'skill1': 1,
        'skill2': 0,
        'number': 1,
        'favor': 0,
    }
for doll in user_info['gun_with_user_info']:
    for k in ['gun_level','skill1','skill2','number']:
        my_dolls[int(doll['gun_id'])][k] = max(int(doll[k]), my_dolls[int(doll['gun_id'])][k])
    my_dolls[int(doll['gun_id'])]['favor'] = max(int(doll['favor'])//10000, my_dolls[int(doll['gun_id'])]['favor'])

with open(r'info/my_dolls.json','w',encoding='utf-8') as f:
    ujson.dump(my_dolls, f, ensure_ascii=False, indent=2)
# %% 统计持有装备信息
my_equips = {}
for equip in equip_info:
    if equip['rank'] < 5:
        continue
    id = equip['id']
    my_equips[equip['id']] = {
        'id':equip['id'],
        'name':name_table[equip['name']],
        'code':equip['code'],
        'fit_guns': equip['fit_guns'],
        'level_00': 0,
        'level_10': 0,
    }
for _, equip in user_info['equip_with_user_info'].items():
    id = int(equip['equip_id'])
    if id not in my_equips.keys():
        continue
    level = int(equip['equip_level'])
    if level == 10:
        my_equips[id]['level_10'] += 1
    else:
        my_equips[id]['level_00'] += 1
        
with open(r'info/my_equips.json','w',encoding='utf-8') as f:
    ujson.dump(my_equips, f, ensure_ascii=False, indent=2)

# %% 计算各人形不同配装的效能
choices = {}
for doll in doll_info:
    id = doll['id']
    if 1200 < id < 20000 or id > 30000:
        continue
    if my_dolls[id]['gun_level'] == 0:
        continue
    equip_group_all = []
    for category, type_str in enumerate(doll['type_equip'].split('|')):
        equip_group_category = []
        types = [int(i) for i in type_str.split(',')]
        # print(category, types)
        for equip in equip_info:
            if equip['rank'] <5 or equip['type'] not in types:
                continue
            if equip['fit_guns'] and id not in equip['fit_guns']:
                continue
            eid = equip['id']
            if my_equips[eid]['level_10'] > 0:
                equip_group_category.append((equip, 10))
            if my_equips[eid]['level_00'] > 0 and my_equips[eid]['level_10'] < max_dolls:
                equip_group_category.append((equip, 0))
        # print([name_table[equip[0]['name']] for equip in equip_group_category])
        equip_group_all.append(equip_group_category)
    # print(my_dolls[id])
    # print(doll)
    for i,j,k in itertools.product(*equip_group_all):
        strength = doll_attr_calculate(doll,my_dolls[id],[i,j,k])
        # print(strength)
        sp_ratio = 1.2 if id % 20000 in advantage else 1
        score = math.floor(class_weight[doll['type']]*sp_ratio*fairy_ratio*strength[fight_mode]/100)
        # print(name_table[i[0]['name']],i[1],name_table[j[0]['name']],j[1],name_table[k[0]['name']],k[1],score)
        recipe_name = f"{my_dolls[id]['name']}_{name_table[i[0]['name']]}_{i[1]}_{name_table[j[0]['name']]}_{j[1]}_{name_table[k[0]['name']]}_{k[1]}"
        recipe_content = {
            my_dolls[id]['name']:-1,
            f"{name_table[i[0]['name']]}_{i[1]}":0,
            f"{name_table[j[0]['name']]}_{j[1]}":0,
            f"{name_table[k[0]['name']]}_{k[1]}":0,
            'score': score
        }
        recipe_content[f"{name_table[i[0]['name']]}_{i[1]}"]-=1
        recipe_content[f"{name_table[j[0]['name']]}_{j[1]}"]-=1
        recipe_content[f"{name_table[k[0]['name']]}_{k[1]}"]-=1
        choices[recipe_name] = recipe_content
print(len(choices.items()))
# %%
resource = {}
for id, doll in my_dolls.items():
    if doll['gun_level'] > 0:
        resource[doll['name']]=1
for id, equip in my_equips.items():
    if equip['level_10'] > 0:
        resource[f"{equip['name']}_10"]=equip['level_10']
    if equip['level_00'] > 0:
        resource[f"{equip['name']}_0"]=equip['level_00']
resource['count'] = max_dolls
resource['score'] = 0
lp_vars = {}
problem = lp.LpProblem('battlefield', lp.LpMaximize)
for k, recipe in choices.items():
    lp_vars[k] = lp.LpVariable(k, cat=lp.LpBinary)
    for r, c in recipe.items():
        resource[r] += c*lp_vars[k]
    resource['count'] -= lp_vars[k]
for k, v in resource.items():
    problem += v >= 0, k
problem += resource['score']
print(problem.solve())
print(resource['score'].value())
res = []
for k, v in lp_vars.items():
    if v.value()>0:
        res.append((k, choices[k]['score'], v.value()))
res.sort(key=lambda x: x[1], reverse=True)
for r in res:
    print(r[0], r[1], r[2])
# %%
