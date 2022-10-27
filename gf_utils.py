import os
from typing import Iterable
from urllib import request
from urllib.error import URLError
from socket import timeout
import socket
from tqdm.auto import tqdm
from multiprocessing import Pool
from logger_tt import logger

class MultiProcessDownloader:
    def __init__(self,n_jobs:int=16,timeout:float=30,retry:int=10):
        self.n_jobs = n_jobs
        self.timeout = timeout
        self.retry = retry 
        self.pool = Pool(n_jobs)

    def download(self, tasks:Iterable[Iterable]):
        for task in tasks:
            task.append(self.retry)
            task.append(self.timeout)
        try:
            for _ in tqdm(self.pool.imap_unordered(download_multitask, tasks),total=len(tasks),ascii=True): 
                pass
        except KeyboardInterrupt as e:
            self.pool.terminate()
            self.pool.join()
            raise e

def download(url, path, max_retry=10,timeout_sec=30):
    socket.setdefaulttimeout(timeout_sec)
    fname = os.path.split(path)[-1]
    logger.info(f'Start downloading {fname}')
    for i in range(max_retry):
        try:
            if not os.path.exists(path):
                request.urlretrieve(url,path+'.tmp')
                os.rename(path+'.tmp',path)
        except (URLError, timeout, ConnectionResetError):
            logger.warning(f'Failed to download {fname} for {i+1}/10 tries')
            continue
        else:
            logger.info(f'Successfully downloaded {fname}')
            break
    else:
        logger.error(f'Exceeded max retry times, failed to download {fname} from {url}')
    return path

def download_multitask(x):
    return download(*x)

# %%
import os
import json
import logging
# %%
special_keys = {
    "achievement": "identity",
    "attendance_info": None,
    "auto_mission": "mission_id",
    "bingo_task_info": "task_id",
    "chess_creation_logic": None,
    "daily_info": "identity",
    "daily": "identity",
    "enemy_standard_attribute": "level",
    "equip_category": "category",
    "equip_exp_info": "level",
    "equip_type": "type",
    "furniture_establish_info": "establish_id",
    "game_config_info": "parameter_name",
    "guild_level": "lv",
    "gun_exp_info": "lv",
    "gun_obtain_info": "obtain_id",
    "kalina_favor_info": "level",
    "main_quest_info": "identity",
    "mission_draw_bonus": None,
    "mission_event_prize_info": "mission_id",
    "mission_targettrain_battlesetting": "difficult_level",
    "sangvis_advance": "lv",
    "sangvis_exp": "lv",
    "seven_attendance_info": None,
    "seven_spendpoint_info": None,
    "squad_chip_exp": "lv",
    "squad_exp": "lv",
    "squad_rank": "star_id",
    "squad_type": "type_id",
    "weekly_info": "identity",
    "weekly": "identity",
}

def get_stc_data(stc_dir, table_dir=None,subset=None,to_dict=True):
    stc_data = dict()
    for fname in os.listdir(stc_dir):
        name = os.path.splitext(fname)[0]
        if subset is not None and name not in subset:
            continue
        if fname=='catchdata':
            continue
        logging.debug(f'Reading {fname}')
        with open(os.path.join(stc_dir,fname),encoding='utf-8') as f:
            data = json.load(f)
            if to_dict and len(data)>0:
                k = 'id' if 'id' in data[0].keys() else (special_keys[name] if name in special_keys.keys() else None)
                if k is not None:
                    data = {d[k]: d for d in data}
            stc_data[name] = data
    return stc_data
    

def convert_text(data, text_table):
    if type(data)==list:
        return [convert_text(i,text_table) for i in data]
    elif type(data)==dict:
        return {k: convert_text(v,text_table) for k,v in data.items()}
    else:
        text = text_table(data)
        if text != '':
            return text
        else:
            return data

# %%
if __name__=='__main__':
    logging.basicConfig(level='DEBUG',force=True)
    table_dir = r'.\data-miner\data\ch\asset\table'
    stc_dir = r'.\data-miner\data\ch\stc'
    stc = get_stc_data(stc_dir,table_dir)
# %%
