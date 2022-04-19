
# %%
import csv
import math
import ujson
import itertools
# %%
def get_name_table():
    with open(r'resource/table.tsv','r',encoding='utf-8') as f:
        name_table = {}
        for row in csv.DictReader(f, delimiter='\t'):
            name_table[row['key']] = row['zh-CN']
    return name_table

# %%
def get_theater_config(theater_id='724'):
    with open(r'resource/theater_info.json','r',encoding='utf-8') as f:
        theater_info = ujson.load(f)
        theater = theater_info[theater_id]
    types = ['HG','SMG','RF','AR','MG','SG']
    assert theater['boss'], f'no boss fight in stage {theater_id}'
    return {
        'class_weight': {types[i]: theater['class_weight'][i] for i in range(6)}, 
        'advantage': theater['advantage_gun'], 
        'fightmode': 'night' if theater['boss']['is_night'] else 'day'
    }

# %%
def load_info():
    name_table = get_name_table()
    with open(r'resource/doll.json','r',encoding='utf-8') as f:
        doll_info = ujson.load(f)
    with open(r'resource/equip.json','r',encoding='utf-8') as f:
        equip_info = ujson.load(f)
    with open(r'info/user_info.json','r',encoding='utf-8',errors='ignore') as f:
        user_info = ujson.load(f)
    # %% 统计持有人形信息
    my_dolls = {}
    for doll in doll_info.values():
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

    # with open(r'info/my_dolls.json','w',encoding='utf-8') as f:
    #     ujson.dump(my_dolls, f, ensure_ascii=False, indent=2)
    # %% 统计持有装备信息
    my_equips = {}
    for equip in equip_info.values():
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
            
    # with open(r'info/my_equips.json','w',encoding='utf-8') as f:
    #     ujson.dump(my_equips, f, ensure_ascii=False, indent=2)
    return doll_info, equip_info, my_dolls, my_equips
# %%
def prepare_choices(doll_info, equip_info, my_dolls, my_equips, theater_config):
    name_table = get_name_table()
    class_weight = theater_config['class_weight']
    advantage = theater_config['advantage']
    fight_mode = theater_config['fightmode']
    max_dolls = theater_config['max_dolls']
    fairy_ratio = theater_config['fairy_ratio']
    choices = {}
    for equip in equip_info.values():
        eid = equip['id']
        if eid not in my_equips.keys() or eid in [16,49]:
            continue
        ename = my_equips[eid]['name']
        if my_equips[eid]['level_00'] > 0 and my_equips[eid]['level_10'] < max_dolls:
            choices[f"强化_{ename}"] = {
                f"{ename}_0":-1,
                f"{ename}_10":1,
                "强化资源":-equip['exclusive_rate'],
            }
    for doll in doll_info.values():
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
            for equip in equip_info.values():
                if equip['rank'] <5 or equip['type'] not in types:
                    continue
                if equip['fit_guns'] and id not in equip['fit_guns']:
                    continue
                eid = equip['id']
                if my_equips[eid]['level_10'] > 0 or my_equips[eid]['level_00'] > 0:
                    equip_group_category.append((equip, 10))
                if my_equips[eid]['level_00'] > 0 and my_equips[eid]['level_10'] < max_dolls:
                    equip_group_category.append((equip, 0))
            # print([name_table[equip[0]['name']] for equip in equip_group_category])
            equip_group_all.append(equip_group_category)
        # print(my_dolls[id])
        # print(doll)
        for i,j,k in itertools.product(*equip_group_all):
            if i[0]['type']==j[0]['type'] or i[0]['type']==k[0]['type'] or j[0]['type']==k[0]['type']:
                continue
            strength = doll_attr_calculate(doll,my_dolls[id],[i,j,k])
            # print(strength)
            sp_ratio = 1.2 if id % 20000 in advantage else 1
            score = math.floor(class_weight[doll['type']]*sp_ratio*fairy_ratio*strength[fight_mode]/100)
            # print(name_table[i[0]['name']],i[1],name_table[j[0]['name']],j[1],name_table[k[0]['name']],k[1],score)
            recipe_name = f"{my_dolls[id]['name']}\t{name_table[i[0]['name']]}\t{i[1]}\t{name_table[j[0]['name']]}\t{j[1]}\t{name_table[k[0]['name']]}\t{k[1]}"
            recipe_content = {
                my_dolls[id]['name']:-1,
                f"{name_table[i[0]['name']]}_{i[1]}":-1,
                f"{name_table[j[0]['name']]}_{j[1]}":-1,
                f"{name_table[k[0]['name']]}_{k[1]}":-1,
                'score': score
            }
            choices[recipe_name] = recipe_content
    return choices

# %%
def doll_attr_calculate(doll, my_doll, equip_group):
    lv = my_doll['gun_level']
    favor_factor = 0.95 + (my_doll['favor']+10)//50*0.05

    attr_change = {"hp": 0, "pow": 0, "rate": 0, "hit": 0, "dodge": 0, "armor": 0}
    attr_fixed = {"critical_harm_rate": 150, "critical_percent": doll['crit'],
                  "armor_piercing": doll['armor_piercing'], "night_view_percent": 0, "bullet_number_up": doll['bullet']}
    attr_other = {
        "id": doll["id"], "star": doll["rank"], "upgrade": lv, "type": doll["type"], 
        "skill_effect_per": 0, "skill_effect": 0, 
        'number': my_doll['number'], 'skill1':my_doll['skill1'], 'skill2':my_doll['skill2']}

    for key in ["pow", "hit", "dodge"]:
        attr_change[key] = gf_ceil(calculate(lv, key, doll) * favor_factor)
    for key in ["hp", "rate", "armor"]:
        attr_change[key] = gf_ceil(calculate(lv, key, doll))

    for equip, elv in equip_group:
        if not equip:
            continue
        attr_other["skill_effect_per"] = 30 if equip['id']==117 or equip['id']==118 else 0
        attr_other["skill_effect"] += int(equip["skill_effect"])

        for attr in attr_change.keys():
            if attr in equip['stat'].keys():
                stat = equip['stat'][attr]
                modif = 1
                if 'upgrade' in stat.keys() and elv == 10:
                    modif += stat['upgrade']/1000
                value = math.floor(stat['max'] * modif)
                attr_change[attr] += value

        for attr in attr_fixed.keys():
            if attr in equip['stat'].keys():
                stat = equip['stat'][attr]
                modif = 1
                if 'upgrade' in stat.keys() and elv == 10:
                    modif += stat['upgrade']/1000
                value = math.floor(stat['max'] * modif)
                attr_fixed[attr] += value
    day = doll_effect_calculate({"attr_change": attr_change, "attr_fixed": attr_fixed, "attr_other": attr_other}, "day")
    night = doll_effect_calculate({"attr_change": attr_change, "attr_fixed": attr_fixed, "attr_other": attr_other}, "night")

    return {"day": day, "night": night}


def doll_effect_calculate(gun_attr, fight_type):

    skill1 = gun_attr["attr_other"]['skill1']
    skill2 = gun_attr["attr_other"]['skill2']
    star = int(gun_attr["attr_other"]["star"])
    number = gun_attr["attr_other"]["number"]
    skill_effect = int(gun_attr["attr_other"]["skill_effect"])
    skill_effect_per = int(gun_attr["attr_other"]["skill_effect_per"])

    # 1技能效能 = ceiling（5*(0.8+星级/10)*[35+5*(技能等级-1)]*(100+skill_effect_per)/100,1) + skill_effect
    # 2技能效能 = ceiling（5*(0.8+星级/10)*[15+2*(技能等级-1)]*(100+skill_effect_per)/100,1) + skill_effect
    doll_skill_effect = gf_ceil(number*(0.8+star/10)*(35+5*(skill1-1))*(100+skill_effect_per)/100) + skill_effect
    if gun_attr["attr_other"]["upgrade"] >= 110:
        doll_skill_effect += gf_ceil(number*(0.8+star/10)*(15+2*(skill2-1))*(100+skill_effect_per)/100)

    life = int(gun_attr["attr_change"]["hp"])
    dodge = int(gun_attr["attr_change"]["dodge"])
    armor = int(gun_attr["attr_change"]["armor"])
    # 防御效能 = CEILING(生命*(35+闪避)/35*(4.2*100/MAX(1,100-护甲)-3.2),1)
    defend_effect = gf_ceil(life*number*(35+dodge)/35*(4.2*100/max(1, 100-armor)-3.2))

    hit = int(gun_attr["attr_change"]["hit"])
    night_view_percent = int(gun_attr["attr_fixed"]["night_view_percent"])
    if fight_type == "night":
        # 夜战命中 = CEILING(命中*(1+(-0.9*(1-夜视仪数值/100))),1)
        hit = gf_ceil(hit*(1+(-0.9*(1-night_view_percent/100))))

    attack = int(gun_attr["attr_change"]["pow"])
    rate = int(gun_attr["attr_change"]["rate"])
    critical = int(gun_attr["attr_fixed"]["critical_percent"])
    critical_damage = int(gun_attr["attr_fixed"]["critical_harm_rate"])
    armor_piercing = int(gun_attr["attr_fixed"]["armor_piercing"])
    bullet = int(gun_attr["attr_fixed"]["bullet_number_up"])
    if gun_attr["attr_other"]["type"] == "SG":
        # SG攻击 = 6*5*(3*弹量*(伤害+穿甲/3)*(1+暴击率*(暴击伤害-100)/10000)/(1.5+弹量*50/射速+0.5*弹量)*命中/(命中+23)+8)
        attack_effect = gf_ceil(6*number*(3*bullet*(attack+armor_piercing/3)*(1+critical*(critical_damage-100)/10000)/(1.5+bullet*50/rate+0.5*bullet)*hit/(hit+23)+8))
    elif gun_attr["attr_other"]["type"] == "MG":
        # MG攻击 = 7*5*(弹量*(伤害+穿甲/3)*(1+暴击率*(暴击伤害-100)/10000)/(弹量/3+4+200/射速)*命中/(命中+23)+8)
        attack_effect = gf_ceil(7*number*(bullet*(attack+armor_piercing/3)*(1+critical*(critical_damage-100)/10000)/(bullet/3+4+200/rate)*hit/(hit+23)+8))
    elif gun_attr["attr_other"]["type"] in ['HG','SMG','RF','AR']:
        # 其他攻击 = 5*5*(伤害+穿甲/3)*(1+暴击率*(暴击伤害-100)/10000)*射速/50*命中/(命中+23)+8)
        attack_effect = gf_ceil(5*number*((attack+armor_piercing/3)*(1+critical*(critical_damage-100)/10000)*rate/50*hit/(hit+23)+8))
    else:
        exit('gun type error: '+gun_attr["attr_other"]["type"])
    effect_total = doll_skill_effect + defend_effect + attack_effect
    return effect_total


def stc_to_text(text, name):
    tem = text[text.find(name) + len(name) + 1:]
    out_text = tem[:tem.find("\n")]
    return out_text


def bonus_handle(string):
    dict1 = {}
    attr1 = string.split(',')
    for key in attr1:
        type1 = key.split(':')[0]
        numb1 = key.split(':')[1]
        dict1[type1] = str(1 + int(numb1) / 1000)
    return dict1


def gf_ceil(number):
    if number % 1 < 0.0001:
        number = number - (number % 1)
    else:
        number = number - (number % 1) + 1
    return int(number)

BASIC = [16, 45, 5, 5]
BASIC_LIFE_ARMOR = [
    [[55, 0.555], [2, 0.161]],
    [[96.283, 0.138], [13.979, 0.04]]
]
BASE_ATTR = [
    [0.60, 0.60, 0.80, 1.20, 1.80, 0.00],
    [1.60, 0.60, 1.20, 0.30, 1.60, 0.00],
    [0.80, 2.40, 0.50, 1.60, 0.80, 0.00],
    [1.00, 1.00, 1.00, 1.00, 1.00, 0.00],
    [1.50, 1.80, 1.60, 0.60, 0.60, 0.00],
    [2.00, 0.70, 0.40, 0.30, 0.30, 1.00]
]
GROW = [
    [[0.242, 0], [0.181, 0], [0.303, 0], [0.303, 0]],
    [[0.06, 18.018], [0.022, 15.741], [0.075, 22.572], [0.075, 22.572]]
]
TYPE_ENUM = {"HG": 0, "SMG": 1, "RF": 2, "AR": 3, "MG": 4, "SG": 5}
ATTR_ENUM = {"hp": 0, "pow": 1, "rate": 2, "hit": 3, "dodge": 4, "armor": 5}


def calculate(lv, attr_type, doll):
    mod = 1
    if lv <= 100:
        mod = 0
    guntype = TYPE_ENUM[doll['type']]
    attr = ATTR_ENUM[attr_type]
    ratio = doll['stat'][attr_type]
    growth = doll['grow']

    if attr == 0 or attr == 5:
        return math.ceil(
            (BASIC_LIFE_ARMOR[mod][attr & 1][0] + (lv-1)*BASIC_LIFE_ARMOR[mod][attr & 1][1]) * BASE_ATTR[guntype][attr] * ratio / 100
        )
    else:
        base = BASIC[attr-1] * BASE_ATTR[guntype][attr] * ratio / 100
        accretion = (GROW[mod][attr-1][1] + (lv-1)*GROW[mod][attr-1][0]) * BASE_ATTR[guntype][attr] * ratio * growth / 100 / 100
        return math.ceil(base) + math.ceil(accretion)
# %%
