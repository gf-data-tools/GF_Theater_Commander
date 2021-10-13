# %%
import ujson
import csv
from utils import *

name_table = get_name_table()
# %%
with open(r'resource/doll.json') as f:
    doll_info = ujson.load(f)
with open(r'resource/equip.json',encoding='utf-8') as f:
    equip_info = ujson.load(f)
with open(r'info/user_info.json') as f:
    user_info = ujson.load(f)
# %%
my_dolls = {}
for doll in doll_info:
    id = doll['id']
    if 1200 < id < 20000 or id > 30000:
        continue
    my_dolls[doll['id']] = {
        'id':doll['id'],
        'name':name_table[doll['name']],
        'gun_level': 1,
        'skill1': 1,
        'skill2': 0,
        'number': 1,
        'favor': 0,
    }
for doll in user_info['gun_with_user_info']:
    for k in ['gun_level','skill1','skill2','number']:
        my_dolls[int(doll['gun_id'])][k] = max(int(doll[k]), my_dolls[int(doll['gun_id'])][k])
    my_dolls[int(doll['gun_id'])]['favor'] = max(int(doll['favor'])//10000, my_dolls[int(doll['gun_id'])]['favor'])

with open(r'info/doll_info.csv','w',encoding='utf-8') as f:
    writer = csv.DictWriter(f, ['id','name','gun_level','skill1','skill2','number','favor'],lineterminator='\n')
    writer.writeheader()
    writer.writerows(my_dolls.values())
# %%
my_equips = {}
for equip in equip_info:
    if equip['rank'] < 5:
        continue
    id = equip['id']
    my_equips[equip['id']] = {
        'id':equip['id'],
        'name':name_table[equip['name']],
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
        
with open(r'info/equip_info.csv','w',encoding='utf-8') as f:
    writer = csv.DictWriter(f, ['id','name','level_00','level_10'],lineterminator='\n')
    writer.writeheader()
    writer.writerows(my_equips.values())
# %%
