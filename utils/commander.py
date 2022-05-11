# %%
from collections import defaultdict
import pyjson5
import re
import os
import itertools
import math
from .text_table import TextTable
import pulp as lp
from rich import box
from rich.table import Table, Column
from rich.console import Console, CONSOLE_HTML_FORMAT
from rich.markdown import Markdown
from rich.terminal_theme import MONOKAI
# %%
class Commander():
    def __init__(
        self, 
        table_tsv = r'resource/table.tsv',
        doll_json=r'resource/doll.json',
        equip_json=r'resource/equip.json',
        theater_info_json=r'resource/theater_info.json',
        user_info_json=r'info/user_info.json',
        solver=r'solverdir/cbc/win/64/cbc.exe',
        lang = 'zh-CN',
        box_per_row = None
    ) -> None:

        self.my_dolls, self.my_equips = self.get_user_info(doll_json, equip_json, user_info_json)
        self.text = TextTable(table_tsv,lang)
        with open(theater_info_json,'r',encoding='utf-8') as f:
            self.theater_info = pyjson5.load(f)
        self.solver = solver

        self.console = Console(record=True)
        if not box_per_row:
            self.box_per_row = (self.console.width)//24
        else:
            self.box_per_row = box_per_row
        self.console.width = self.box_per_row * 24 + 3

    @staticmethod
    def get_user_info(doll_json, equip_json, user_info_json):
        with open(doll_json,'r',encoding='utf-8') as f:
            doll_info = pyjson5.load(f)
        with open(equip_json,'r',encoding='utf-8') as f:
            equip_info = pyjson5.load(f)
        with open(user_info_json,'rb') as f:
            data = f.read().decode('ascii','ignore')
            data = re.sub(r'"name":".*?"',r'"name":""',data)
            user_info = pyjson5.decode(data)
        # 统计持有人形信息
        my_dolls = {}
        for doll in user_info['gun_with_user_info']:
            id = doll['gun_id']
            my_dolls.setdefault(
                id,
                {
                    'gun_level': 0,
                    'skill1': 1,
                    'skill2': 0,
                    'number': 1,
                    'favor': 0,
                    **doll_info[id]
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
                    'level_00': 0,
                    'level_10': 0,
                    **equip_info[id]
                }
            )
            level = int(equip['equip_level'])
            if level == 10:
                my_equips[id]['level_10'] += 1
            else:
                my_equips[id]['level_00'] += 1

        return my_dolls, my_equips

    def configure_theater(self,theater_id='848', max_dolls=30, fairy_ratio=2):
        theater = self.theater_info[theater_id]
        types = ['HG','SMG','RF','AR','MG','SG']
        assert theater['boss'], f'no boss fight in stage {theater_id}'
        self.theater_config = {
            'theater_id': theater_id,
            'class_weight': {types[i]: theater['class_weight'][i] for i in range(6)}, 
            'advantage': theater['advantage_gun'], 
            'max_dolls': max_dolls,
            'fairy_ratio': fairy_ratio,
            'fightmode': 'night' if theater['boss']['is_night'] else 'day'
        }

    def prepare_choices(self):
        upgrade_choices = {}
        for eid, equip in self.my_equips.items():
            if equip['level_00'] > 0 and equip['category'] != 'nightequip':
                recipe_name = f"u_e_{eid}"
                recipe_info = {'eid':eid, 'cost':equip['exclusive_rate']}
                upgrade_choices[recipe_name] = recipe_info

        doll_choices = {}
        for id, doll in self.my_dolls.items():
            equip_group_all = []
            for type_str in doll['type_equip'].split('|'):
                equip_group_category = []
                types = [int(i) for i in type_str.split(',')]
                
                for eid, equip in self.my_equips.items():
                    if equip['rank'] < 5 or equip['type'] not in types:
                        continue
                    if equip['fit_guns'] and doll['id'] not in equip['fit_guns']:
                        continue
                    if  equip['category'] != 'nightequip' and (equip['level_10'] > 0 or equip['level_00'] > 0):
                        equip_group_category.append((equip, 10))
                    if equip['level_00'] > 0:
                        equip_group_category.append((equip, 0))
                equip_group_all.append(equip_group_category)

            for equip_group in itertools.product(*equip_group_all):
                if len({a[0]['type'] for a in equip_group}) < 3:
                    continue
                strength = doll_attr_calculate(doll, equip_group)
                # print(strength)
                i,j,k = equip_group
                recipe_name = f"r_g_{id}_e_{i[0]['id']}_{i[1]}_{j[0]['id']}_{j[1]}_{k[0]['id']}_{k[1]}"
                recipe_info = {
                    'gid': id,
                    'equip': [dict(id=str(e[0]['id']),lv=e[1]) for e in equip_group],
                    'strength': strength
                }
                doll_choices[recipe_name] = recipe_info
                
        self.upgrade_choices, self.doll_choices = upgrade_choices, doll_choices

    def compute_score(self,choice_info):
        gid, strength = choice_info['gid'], choice_info['strength']
        class_weight = self.theater_config['class_weight'][self.my_dolls[gid]['type']]
        sp_ratio = 1.2 if gid in self.theater_config['advantage'] else 1
        fairy_ratio = self.theater_config['fairy_ratio']
        fight_mode = self.theater_config['fightmode']
        return math.floor(class_weight*sp_ratio*fairy_ratio*strength[fight_mode]/100)
            
    
    def problem_solving(self, upgrade_resource=0):
        resource = {}
        for id in self.my_dolls.keys():
            resource[f'g_{id}']=1
        for id, equip in self.my_equips.items():
            resource[f"e_{id}_10"]=equip['level_10']
            if equip['level_00'] > 0:
                resource[f"e_{id}_0"]=equip['level_00']
        resource['count'] = self.theater_config['max_dolls']
        resource['score'] = 0
        resource['upgrade'] = min(upgrade_resource,300)
        lp_vars = {}
        coeff_lp_var_dict = defaultdict(list)
        problem = lp.LpProblem('battlefield', lp.LpMaximize)
        for k, info in self.upgrade_choices.items():
            lp_vars[k] = lp.LpVariable(k, cat=lp.LpInteger, lowBound=0)
            coeff_lp_var_dict[f'e_{info["eid"]}_0'].append((lp_vars[k], -1))
            coeff_lp_var_dict[f'e_{info["eid"]}_10'].append((lp_vars[k], 1))
            coeff_lp_var_dict[f'upgrade'].append((lp_vars[k], -info['cost']))

        for k, info in self.doll_choices.items():
            lp_vars[k] = lp.LpVariable(k, cat=lp.LpInteger, lowBound=0)
            score = self.compute_score(info)
            coeff_lp_var_dict[f'g_{info["gid"]}'].append((lp_vars[k], -1))
            coeff_lp_var_dict['count'].append((lp_vars[k], -1))
            coeff_lp_var_dict['score'].append((lp_vars[k], score))
            for e in info['equip']:
                coeff_lp_var_dict[f'e_{e["id"]}_{e["lv"]}'].append((lp_vars[k], -1))
            
        for k,v in coeff_lp_var_dict.items():
            resource[k] += lp.LpAffineExpression(v)
        for k, v in resource.items():
            problem += v >= 0, k
        problem += resource['score'] + 0.001*resource['upgrade']
        problem.solve(lp.COIN_CMD(msg=0,path=self.solver))
        self.total_score, self.lp_vars = resource['score'].value(), lp_vars
        return resource['score'].value(), lp_vars

    def show_result(self):
        u_info, g_info = [], []
        for k, v in self.lp_vars.items():
            if v.value()>0:
                if k[0] == 'u':
                    u_info.append([self.upgrade_choices[k],int(v.value())])
                else:
                    g_info.append([self.doll_choices[k],self.compute_score(self.doll_choices[k])])
        u_info.sort(key=lambda x:0.001*v.value()-self.my_equips[x[0]['eid']]['exclusive_rate'],reverse=True)
        g_info.sort(key=lambda x:x[1],reverse=True)

        rank_color = {1:'magenta', 2:'white', 3:'cyan', 4:'green', 5:'yellow', 6:'red'}
        lv_color = {
            0:'grey', 1:'white', 2:'white', 3:'cyan',
            4:'cyan', 5:'cyan', 6:'green', 7:'green', 
            8:'green',9:'yellow',10:'yellow',
        }
        text = self.text
        my_dolls = self.my_dolls
        my_equips = self.my_equips

        equip_list = []
        for i, (info, v) in enumerate(u_info):
            if i%5 == 0:
                equip_table = Table.grid(
                    Column('name',width=16,justify='right'),
                    Column('value',width=5,justify='left'),
                    padding=(0,1,0,0)
                )
            ename, erank = (
                text(my_equips[info['eid']]['name']),
                6 if my_equips[info['eid']]['category']=='exclusive' else my_equips[info['eid']]['rank']
            )
            equip_table.add_row(f'[{rank_color[erank]}]{ename}', f'{v:2.0f}')
            if (i+1)%5 == 0 or i+1==len(u_info):
                equip_list.append(equip_table)

        strn_table = Table(show_header=False,show_lines=True,box=box.SQUARE,padding=(0,0,0,0),title='强化装备',title_justify='left')
        for i in range(0,len(equip_list),self.box_per_row):
            strn_table.add_row(*equip_list[i:min(i+self.box_per_row,len(equip_list))])
        
        gun_list = []
        for info, score in g_info:
            gun_table = Table.grid(
                Column('name',width=16,justify='right'),
                Column('value',width=5,justify='left'),
                padding=(0,1,0,0)
            )

            gun_name, gun_type, gun_rank, gun_favor = (
                text(my_dolls[info['gid']]['name']),
                text(my_dolls[info['gid']]['type']),
                my_dolls[info['gid']]['rank'] if not my_dolls[info['gid']]['collabo'] else 1,
                my_dolls[info['gid']]['favor']
            )
            gun_table.add_row(f'[{rank_color[gun_rank]} bold]{gun_name} [/{rank_color[gun_rank]} bold]{gun_type:<3}',f'{"[red]o" if gun_favor>100 else "[magenta] "} {gun_favor:3d}')
            # res_table.add_row((f'{gun_name}',gun_type))
            slv1, slv2 = (
                my_dolls[info['gid']]['skill1'], 
                my_dolls[info['gid']]['skill2'],
            )
            gun_table.add_row(f'效能：{score}', f'[{lv_color[slv1]}]{slv1:2d}'+'[white]/'+f'[{lv_color[slv2]}]{slv2:2d}')
            for e in info['equip']:
                ename, elv, erank = (
                    text(my_equips[e['id']]['name']),
                    e['lv'],
                    6 if my_equips[e['id']]['category']=='exclusive' else my_equips[e['id']]['rank']
                )
                gun_table.add_row(f'[{rank_color[erank]}]{ename}',f'[{lv_color[elv]}]{elv:2d}')
            gun_list.append(gun_table)
            
        res_table = Table(show_header=False,show_lines=True,box=box.SQUARE,padding=(0,0,0,0),title='出战配置',title_justify='left')

        for i in range(0,self.theater_config['max_dolls'],self.box_per_row):
            res_table.add_row(*gun_list[i:min(i+self.box_per_row,self.theater_config['max_dolls'])])
            
        full_table = Table(show_header=False,box=None,caption=f"总效能: {self.total_score:.0f}",caption_justify='left')
        full_table.add_row(strn_table)
        full_table.add_row(res_table)
        
        self.console.print(Markdown('# '+self.theater_config['theater_id']))
        self.console.print(full_table)

    def save_result(self, output_dir='info', font_family="'Sarasa Term SC'"):
        self.console.save_text(os.path.join(output_dir,'result.txt'),clear=False)
        code_format = re.sub("font-family:", f"font-family:{font_family},",CONSOLE_HTML_FORMAT)
        self.console.save_html(os.path.join(output_dir,'result.html'),code_format=code_format,clear=False,theme=MONOKAI)


# %%
def doll_attr_calculate(doll, equip_group):
    lv = doll['gun_level']
    favor_factor = 0.95 + (doll['favor']+10)//50*0.05

    attr_change = {"hp": 0, "pow": 0, "rate": 0, "hit": 0, "dodge": 0, "armor": 0}
    attr_fixed = {"critical_harm_rate": 150, "critical_percent": doll['crit'],
                  "armor_piercing": doll['armor_piercing'], "night_view_percent": 0, "bullet_number_up": doll['bullet']}
    attr_other = {
        "id": doll["id"], "star": doll["rank"], "upgrade": lv, "type": doll["type"], 
        "skill_effect_per": 0, "skill_effect": 0, 
        'number': doll['number'], 'skill1':doll['skill1'], 'skill2':doll['skill2']}

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
