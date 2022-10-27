from functools import reduce
import itertools
from attr_calc import doll_attr_calculate
import math
from pprint import pprint
from tqdm import tqdm

def get_theater_config(theater_id, theater_area):
    area_cfg = theater_area[theater_id]
    if area_cfg['boss'] == '':
        raise AttributeError(f'{theater_id}不是要塞关卡')
    
    class_weight = [int(i) for i in area_cfg['boss_score_coef'].split(';')]
    advantage = [int(i) for i in area_cfg['advantage_gun'].split(',')]
    fight_mode = 'day' if area_cfg['boss'][-1]=='0' else 'night'
    return dict(
        class_weight=class_weight,
        advantage=advantage,
        fight_mode=fight_mode
    )

def prepare_choices(user_gun, user_equip, theater_id, max_dolls, fairy_ratio, game_data):
    gun_info, equip_info = game_data['gun'], game_data['equip']
    theater_config = get_theater_config(theater_id, game_data['theater_area'])
    choices = {}
    
    for eid, equip in equip_info.items():
        stat = {}
        bonus = {s.split(':')[0]:int(s.split(':')[1]) for s in equip['bonus_type'].split(',') if equip['bonus_type']}
        for k in ["pow", "hit", "dodge", "speed", "rate", "critical_harm_rate", "critical_percent", "armor_piercing", "armor", "shield", "damage_amplify", "damage_reduction", "night_view_percent", "bullet_number_up"]:
            if equip[k] != '':
                smin, smax = [int(i) for i in equip[k].split(',')]
                stat[k] = dict(min=smin,max=smax)
                if k in bonus:
                    stat[k]['upgrade']=bonus[k]
        equip['stat'] = stat

    equip_type_groups = {}
    for eid, my_equip in user_equip.items():
        equip = equip_info[eid]
        equip_type_groups.setdefault(equip['type'],{})
        equip_type_groups[equip['type']][eid] = my_equip
        if not equip['bonus_type']:
            continue
        if my_equip['level_00'] > 0 and my_equip['level_10'] < max_dolls:
            recipe_name = f"u_e{eid}"
            recipe_content = {
                f"e{eid}_0":-1,
                f"e{eid}_10":1,
                "upgrade":-equip['exclusive_rate'],
            }
            recipe_info = {'eid':eid}
            choices[recipe_name] = {'content': recipe_content, 'info': recipe_info}
    # pprint(equip_type_groups)
    for id, my_gun in user_gun.items():
        gun = gun_info[my_gun['gun_id']]
        tmp = list(map(lambda x: [equip_type_groups.get(int(i),{}) for i in x.split(';')[-1].split(',')], [gun[f'type_equip{i}'] for i in range(1,4)]))
        equip_types = [{k:v for k,v in reduce(lambda a,b:a|b, eq, {}).items() if id in v['fit_guns'] or (not v['fit_guns'])} for eq in tmp]
        equip_choices = [
            [(k,10) for k,v in t.items() if v['level_00']+v['level_10']>0 and v['upgrade']>0] + 
            [(k,0) for k,v in t.items() if v['level_00']>0] for t in equip_types
        ]
        for equips in itertools.product(*equip_choices):
            if len({equip_info[eid]['type'] for eid,elv in equips})<3:
                continue
            effect = doll_attr_calculate(gun, my_gun, [(equip_info[eid],elv) for eid,elv in equips])
            sp_ratio = 1.2 if id in theater_config['advantage'] else 1
            score = math.floor(theater_config['class_weight'][gun['type']-1]*sp_ratio*fairy_ratio*effect[theater_config['fight_mode']]/100)
            e1,e2,e3 = equips
            recipe_name = f"r_g{id}_e{e1[0]}lv{e1[1]}_e{e2[0]}lv{e2[1]}_e{e3[0]}lv{e3[1]}"
            recipe_content = {
                f"g_{id}":-1, 'count':-1, 'score': score,
                f'e{e1[0]}_{e1[1]}':-1, f'e{e2[0]}_{e2[1]}':-1, f'e{e3[0]}_{e3[1]}':-1,
            }
            recipe_info = {
                'gid': my_gun['gun_id'],
                'eid_1': e1[0], 'elv_1': e1[1],
                'eid_2': e2[0], 'elv_2': e2[1],
                'eid_3': e3[0], 'elv_3': e3[1],
                'score': score
            }
            choices[recipe_name] = {'content': recipe_content, 'info': recipe_info}
    return choices

if __name__=='__main__':
    from gf_utils.stc_data import get_stc_data
    from load_user_info import load_user_info
    import re
    import json
    game_data = get_stc_data('data/ch')
    
    with open(r'info/user_info.json','rb') as f:
        data = f.read().decode('ascii','ignore')
        data = re.sub(r'"name":".*?"',r'"name":""',data)
        user_info = json.loads(data)

    user_gun, user_equip = load_user_info(user_info,game_data)
    prepare_choices(user_gun,user_equip,848,30,2,game_data)