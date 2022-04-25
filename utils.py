
# %%
import csv
import math
import ujson
import itertools
import re
# %%
def get_name_table(language: str = "zh-CN"):
    """
    Return the name table of the specified language.

    :param language: IETF language tag defined in the header of that tsv
    :return: name_table or the corresponding language if found
    """
    with open(r'resource/table.tsv','r',encoding='utf-8') as f:
        name_table = {}
        try:
            for row in csv.DictReader(f, delimiter='\t'):
                name_table[row['key']] = row[language]
        except KeyError:
            print(f'{language} does not exist in resource/table.tsv')
    return name_table


def get_translation(entry: str, name_table: dict):
    """
    Attempt to find a translation for the given entry

    For example, given an input "gun-10020171" ("Ribeyrolles MOD") and zh-CN name_table, the output will be "利贝罗勒".

    If no translation is available the output will be the same as input. (e.g. as of 20220416 JP you get gun-10020171).
    If the input is score or skill level the same numerical will be returned because nothing could be found.

    :param entry: a string to be translated
    :param name_table: name_table obtained from get_name_table()
    :return: translated string if translation exist
    """
    result = name_table.get(entry, entry)
    return result if result != '' else entry


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
    with open(r'resource/doll.json','r',encoding='utf-8') as f:
        doll_info = ujson.load(f)
    with open(r'resource/equip.json','r',encoding='utf-8') as f:
        equip_info = ujson.load(f)
    with open(r'info/user_info.json','rb') as f:
        data = f.read().decode('ascii','ignore')
        data = re.sub(r'"name":".*?"',r'"name":""',data)
        user_info = ujson.decode(data)
    # 统计持有人形信息
    my_dolls = {}
    for doll in user_info['gun_with_user_info']:
        id = doll['gun_id']
        my_dolls.setdefault(
            id,
            {
                'id':id,
                'name':doll_info[id]['name'],
                'gun_level': 0,
                'skill1': 1,
                'skill2': 0,
                'number': 1,
                'favor': 0,
            }
        )
        for k in ['gun_level','skill1','skill2','number']:
            my_dolls[id][k] = \
                max(int(doll[k]), my_dolls[id][k])
        my_dolls[id]['favor'] = \
            max(int(doll['favor'])//10000, my_dolls[id]['favor'])

    # 统计持有装备信息
    my_equips = {}
    for equip in user_info['equip_with_user_info'].values():
        id = equip['equip_id']
        if equip_info[id]['rank'] < 5:
            continue
        my_equips.setdefault(
            id,
            {
                'id':id,
                'name':equip_info[id]['name'],
                'fit_guns': equip_info[id]['fit_guns'],
                'level_00': 0,
                'level_10': 0,
            }
        )
        level = int(equip['equip_level'])
        if level == 10:
            my_equips[id]['level_10'] += 1
        else:
            my_equips[id]['level_00'] += 1

    return doll_info, equip_info, my_dolls, my_equips
# %%
def prepare_choices(doll_info, equip_info, my_dolls, my_equips, theater_config):
    class_weight = theater_config['class_weight']
    advantage = theater_config['advantage']
    fight_mode = theater_config['fightmode']
    max_dolls = theater_config['max_dolls']
    fairy_ratio = theater_config['fairy_ratio']
    choices = {}
    for eid, my_equip in my_equips.items():
        equip = equip_info[eid]
        # if eid in ['16','49']:
        #     continue
        ename = my_equip['name']
        if my_equip['level_00'] > 0 and my_equip['level_10'] < max_dolls:
            recipe_name = f"u_e_{eid}"
            recipe_content = {
                f"e_{eid}_0":-1,
                f"e_{eid}_10":1,
                "upgrade":-equip['exclusive_rate'],
            }
            recipe_info = {'eid':eid}
            choices[recipe_name] = {'content': recipe_content, 'info': recipe_info}
            
    for id, my_doll in my_dolls.items():
        doll = doll_info[id]
        equip_group_all = []
        for category, type_str in enumerate(doll['type_equip'].split('|')):
            equip_group_category = []
            types = [int(i) for i in type_str.split(',')]
            
            for eid, my_equip in my_equips.items():
                equip = equip_info[eid]
                if equip['rank'] < 5 or equip['type'] not in types:
                    continue
                if equip['fit_guns'] and doll['id'] not in equip['fit_guns']:
                    continue
                if my_equip['level_10'] > 0 or my_equip['level_00'] > 0:
                    equip_group_category.append((equip, 10, eid))
                if my_equip['level_00'] > 0 and my_equip['level_10'] < max_dolls:
                    equip_group_category.append((equip, 0, eid))
            equip_group_all.append(equip_group_category)

        for equip_group in itertools.product(*equip_group_all):
            if len({a[0]['type'] for a in equip_group}) < 3:
                continue
            strength = doll_attr_calculate(doll,my_doll, equip_group)
            # print(strength)
            sp_ratio = 1.2 if int(id) % 20000 in advantage else 1
            score = math.floor(class_weight[doll['type']]*sp_ratio*fairy_ratio*strength[fight_mode]/100)
            i,j,k = equip_group
            recipe_name = f"{my_doll['name']}\t{i[0]['name']}\t{i[1]}\t{j[0]['name']}\t{j[1]}\t{k[0]['name']}\t{k[1]}"
            recipe_name = f"r_g_{id}_e_{i[2]}_{i[1]}_{j[2]}_{j[1]}_{k[2]}_{k[1]}"
            recipe_content = {
                f"g_{id}":-1,
                f"e_{i[2]}_{i[1]}":-1,
                f"e_{j[2]}_{j[1]}":-1,
                f"e_{k[2]}_{k[1]}":-1,
                'score': score
            }
            recipe_info = {
                'gid': id,
                'eid_1': i[2], 'elv_1': i[1],
                'eid_2': j[2], 'elv_2': j[1],
                'eid_3': k[2], 'elv_3': k[1],
                'score': score
            }
            choices[recipe_name] = {'content': recipe_content, 'info': recipe_info}
            
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

    for equip, elv, eid in equip_group:
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
