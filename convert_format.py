import json
from pathlib import Path

src_data = json.load(Path(r'raw/gun.json').open())
Path('converted/').mkdir(exist_ok=True)
dst_data = {}
for src in src_data:
    dst = {}
    dst['id'] =src['id']
    dst['type'] = ['HG','SMG','RF','AR','MG','SG'][src['type']-1]
    for key in ['name','code','rank']:
        dst[key] = src[key]
    dst['collabo'] = 1 if src['rank_display']==7 else 0
    dst['duration'] = src['develop_duration']
    dst['stat'] = dict(
        hp=src['ratio_life'],
        pow=src['ratio_pow'],
        hit=src['ratio_hit'],
        dodge=src['ratio_dodge'],
        speed=src['ratio_speed'],
        rate=src['ratio_rate'],
        armor=src['ratio_armor'],
    )
    dst['armor_piercing'] = src['armor_piercing']
    dst['crit'] = src['crit']
    dst['bullet'] = src['special']
    dst['grow'] = src['eat_ratio']
    dst['type_equip'] = '|'.join([src[f'type_equip{i}'].split(';')[-1] for i in [1,2,3]])
    dst_data[str(src['id'])]=dst
json.dump(dst_data,Path(r'converted/doll.json').open('w'),indent=2)

src_data = json.load(Path(r'raw/equip.json').open())
Path('converted/').mkdir(exist_ok=True)
dst_data = {}
for src in src_data:
    dst = {}
    for key in ['id','type','name','code','rank']:
        dst[key] = src[key]
    dst['duration'] = src['develop_duration']
    dst['stat'] = {}
    bonus = {s.split(':')[0]:int(s.split(':')[1]) for s in src['bonus_type'].split(',') if src['bonus_type']}
    for k in ["pow", "hit", "dodge", "speed", "rate", "critical_harm_rate", "critical_percent", "armor_piercing", "armor", "shield", "damage_amplify", "damage_reduction", "night_view_percent", "bullet_number_up"]:
        if src[k] != '':
            smin, smax = [int(i) for i in src[k].split(',')]
            dst['stat'][k] = dict(min=smin,max=smax)
            if k in bonus:
                dst['stat'][k]['upgrade']=bonus[k]
    dst['powerup'] = {k:src[f'powerup_{k}'] for k in ['mp','ammo','mre','part']}
    dst['retire'] = {k:float(src[f'retire_{k}']) for k in ['mp','ammo','mre','part']}
    dst['exclusive_rate'] = src['exclusive_rate']
    dst['skill_effect'] = float(src['skill_effect'])
    dst['fit_guns'] = [int(i) for i in src['fit_guns'].split(',')] if src['fit_guns']!='' else []
    dst_data[str(src['id'])]=dst

json.dump(dst_data,Path(r'converted/equip.json').open('w'),indent=2,ensure_ascii=False)

src_data = json.load(Path(r'raw/theater_area.json').open())
Path('converted/').mkdir(exist_ok=True)
dst_data = {}
for src in src_data:
    dst = {}
    for key in ['id','name']:
        dst[key] = src[key]
    dst['desc'] = src['description']
    dst['class_weight'] = [int(i) for i in src['boss_score_coef'].split(';')]
    dst['advantage_gun'] = [int(i) for i in src['advantage_gun'].split(',')]
    if src['boss']:
        idx, night = [int(i) for i in src['boss'].split('-')]
        dst['boss']=dict(enemy_team_id=idx,is_night=bool(night))
    else:
        dst['boss']=None
    dst_data[str(src['id'])]=dst

json.dump(dst_data,Path(r'converted/theater_info.json').open('w'),indent=2,ensure_ascii=False)