# %%
from collections import defaultdict
from utils import *
import pulp as lp
import argparse
import os

# %% argparse
parser = argparse.ArgumentParser()
parser.add_argument('theater_id',default='748',type=str,help='关卡id,如736代表第7期高级区第6关')
parser.add_argument('-m','--max_dolls',type=int,default=30,help='上场人数')
parser.add_argument('-f','--fairy_ratio',type=float,default=2,help='妖精加成,默认4个5星1+0.25*4=2倍')
parser.add_argument('-u','--upgrade_resource',type=int,default=0,help='可以用于强化的资源量（普通装备消耗1份，专属消耗3份）')
parser.add_argument('-l', '--language', type=str, default='zh-CN', help='pick a column from resource/table.csv')
args = parser.parse_args()
# %% 战区关卡参数
theater_id = args.theater_id  # 关卡id,如736代表第7期第3区域第6关
fairy_ratio = args.fairy_ratio  # 妖精加成：5星1.25
max_dolls = args.max_dolls  # 上场人数
upgrade_resource = min(args.upgrade_resource, 30*9) # 可以用于强化的资源量（普通装备消耗1份，专属消耗3份）
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
    resource[f'g_{id}']=1
for eid, equip in my_equips.items():
    resource[f"e_{eid}_10"]=equip['level_10']
    if equip['level_00'] > 0:
        resource[f"e_{eid}_0"]=equip['level_00']
resource['count'] = max_dolls
resource['score'] = 0
resource['upgrade'] = upgrade_resource
lp_vars = {}
coeff_lp_var_dict = defaultdict(list)
problem = lp.LpProblem('battlefield', lp.LpMaximize)
for k, recipe in choices.items():
    lp_vars[k] = lp.LpVariable(k, cat=lp.LpInteger, lowBound=0)
    for r, c in recipe['content'].items():
        # build a dict with value as lists of (coefficient, LpVar) tuples before building LpAffineExpression in bulk
        # else doing += coefficient*LpVar would trigger significantly amount of costly LpAffineExpression.__init__ call
        coeff_lp_var_dict[r].append((lp_vars[k], c))
    if k[0] != 'u':
        resource['count'] -= lp_vars[k]
for k,v in coeff_lp_var_dict.items():
    resource[k] += lp.LpAffineExpression(v)
for k, v in resource.items():
    problem += v >= 0, k
problem += resource['score'] + 0.001*resource['upgrade']

lp_bin = os.path.join(
    os.getcwd(),'solverdir\\cbc',
    lp.core.operating_system,lp.core.arch,
    lp.core.LpSolver_CMD.executableExtension('cbc')
)
problem.solve(lp.COIN_CMD(msg=0,path=lp_bin))
# %%
from rich import box
from rich.table import Table, Column
from rich.console import Console

console=Console(record=True)
if console.width < 60:
    console.width = 1000
box_per_row = min(5,(console.width-5)//24)

u_info, g_info = [], []
for k, v in lp_vars.items():
    if v.value()>0:
        if k[0] == 'u':
            u_info.append([choices[k]['info'],v])
        else:
            g_info.append([choices[k]['info'],v])
u_info.sort(key=lambda x:0.001*v.value()-equip_info[x[0]['eid']]['exclusive_rate'],reverse=True)
g_info.sort(key=lambda x:x[0]['score'],reverse=True)

rank_color = {1:'magenta', 2:'white', 3:'cyan', 4:'green', 5:'yellow', 6:'red'}
lv_color = {
    0:'white', 1:'white', 2:'white', 3:'cyan',
    4:'cyan', 5:'cyan', 6:'green', 7:'green', 
    8:'green',9:'yellow',10:'yellow',
}

equip_list = []
for i, (info, v) in enumerate(u_info):
    if i%5 == 0:
        equip_table = Table.grid(
            Column('name',width=16,justify='right'),
            Column('value',width=5,justify='left'),
            padding=(0,1,0,0)
        )
    ename, erank = (
        get_translation(equip_info[info['eid']]['name'], name_table),
        6 if equip_info[info['eid']]['category']=='exclusive' else equip_info[info['eid']]['rank']
    )
    equip_table.add_row(f'[{rank_color[erank]}]{ename}', f'{v.value():2.0f}')
    if (i+1)%5 == 0 or i+1==len(u_info):
        equip_list.append(equip_table)

strn_table = Table(show_header=False,show_lines=True,box=box.SQUARE,padding=(0,0,0,0),title='强化装备',title_justify='left')
for i in range(0,len(equip_list),box_per_row):
    strn_table.add_row(*equip_list[i:min(i+box_per_row,len(equip_list))])

gun_list = []
for info, v in g_info:
    gun_table = Table.grid(
        Column('name',width=16,justify='right'),
        Column('value',width=5,justify='left'),
        padding=(0,1,0,0)
    )

    gun_name, gun_type, gun_rank, gun_favor = (
        get_translation(my_dolls[info['gid']]['name'], name_table),
        get_translation(doll_info[info['gid']]['type'], name_table),
        doll_info[info['gid']]['rank'] if not doll_info[info['gid']]['collabo'] else 1,
        my_dolls[info['gid']]['favor']
    )
    gun_table.add_row(f'[{rank_color[gun_rank]} bold]{gun_name} [white]{gun_type}',f'{"[red]⚬" if gun_favor>100 else "[magenta]♡"} {gun_favor:3d}')
    # res_table.add_row((f'{gun_name}',gun_type))
    score, slv1, slv2 = (
        info['score'],
        my_dolls[info['gid']]['skill1'], 
        my_dolls[info['gid']]['skill2'],
    )
    gun_table.add_row(f'效能：{score}', f'[{lv_color[slv1]}]{slv1:2d}'+'[white]/'+f'[{lv_color[slv2]}]{slv2:2d}')
    for e in range(3):
        ename, elv, erank = (
            get_translation(equip_info[info[f'eid_{e+1}']]['name'], name_table),
            info[f'elv_{e+1}'],
            6 if equip_info[info[f'eid_{e+1}']]['category']=='exclusive' else equip_info[info[f'eid_{e+1}']]['rank']
        )
        gun_table.add_row(f'[{rank_color[erank]}]{ename}',f'[{lv_color[elv]}]{elv}')
    gun_list.append(gun_table)
    
res_table = Table(show_header=False,show_lines=True,box=box.SQUARE,padding=(0,0,0,0),title='出战配置',title_justify='left')

for i in range(0,max_dolls,box_per_row):
    res_table.add_row(*gun_list[i:min(i+box_per_row,max_dolls)])
full_table = Table(show_header=False,box=None,caption=f"总效能: {resource['score'].value():.0f}",caption_justify='left')

full_table.add_row(strn_table)
full_table.add_row(res_table)

console.print(full_table)
console.save_text('info/result.txt')

# %%
