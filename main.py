# %%
from utils.commander import Commander
import argparse
import os
from pathlib import Path
import pulp as lp
import pyjson5

os.chdir(Path(__file__).resolve().parent)
# %%
table_tsv = r'resource/table.tsv'
doll_json=r'resource/doll.json'
equip_json=r'resource/equip.json'
theater_info_json=r'resource/theater_info.json'
with open('config.json5','r') as f:
    config = pyjson5.load(f)
user_info_json = config['user_info_json']
output_dir = config['output_dir']
language = config['language']
font_family = config['font_family']

# %% argparse
parser = argparse.ArgumentParser()
parser.add_argument('theater_conf',default='748',type=str,nargs='+',help='关卡设置,可传入多个关卡,可覆盖全局设置,格式为theater_id[:m[:f[:u]]],如736代表第7期高级6,833:15:1.75:100代表第8期高级3,携带15人形3妖精,可用100份强化资源')
parser.add_argument('-m','--max_dolls',type=int,default=30,help='上场人数')
parser.add_argument('-f','--fairy_ratio',type=float,default=2,help='妖精加成,默认4个5星1+0.25*4=2倍')
parser.add_argument('-u','--upgrade_resource',type=int,default=0,help='可以用于强化的资源量（普通装备消耗1份，专属消耗3份）')
parser.add_argument('-b','--box_per_row', type=int,default=None, help='输出结果的列数，默认根据控制台宽度适配')
args = parser.parse_args()
# %% main
if __name__=='__main__':
    solver_bin=os.path.join(
        os.getcwd(),'solverdir/cbc',
        lp.core.operating_system,lp.core.arch,
        lp.core.LpSolver_CMD.executableExtension('cbc')
    )
    commander = Commander(
        table_tsv=table_tsv,
        doll_json=doll_json,
        equip_json=equip_json,
        theater_info_json=theater_info_json,
        user_info_json=user_info_json,
        solver=solver_bin,
        lang=language,
        box_per_row=args.box_per_row,
    )
    commander.prepare_choices()
    for conf_str in args.theater_conf:
        conf = conf_str.split(':')
        conf += ['' for _ in range(4-len(conf))]
        theater_id = conf[0]
        max_dolls = int(conf[1]) if conf[1] else args.max_dolls
        fairy_ratio = float(conf[2]) if conf[2] else args.fairy_ratio
        upgrade_resource = int(conf[3]) if conf[3] else args.upgrade_resource
        commander.configure_theater(theater_id,max_dolls,fairy_ratio)
        commander.problem_solving(upgrade_resource)
        commander.show_result()
    commander.save_result(output_dir=output_dir,font_family=font_family)
# %%
