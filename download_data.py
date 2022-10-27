from gf_utils import download
from pathlib import Path

REGIONS = ['ch','kr','tw','jp','us']
TABLES = ['gun','equip','theater_area']

def download_data(dir='./data',region='ch'):
    data_dir = Path(dir)
    data_dir.mkdir(exist_ok=True)
    (data_dir/region).mkdir(exist_ok=True)
    for table in TABLES:
        url = f'https://github.com/gf-data-tools/gf-data-{region}/raw/main/formatted/json/{table}.json'
        path = data_dir/region/f'{table}.json'
        if not path.exists():
            download(url, str(path),timeout_sec=5)
                
if __name__=='__main__':
    download_data()
