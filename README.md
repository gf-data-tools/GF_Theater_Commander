# GF_Theater_Commander
## Requirements
- ujson
- pulp
- prettytable
  
Install dependencies by running `pip install -r requirements.txt`

## Data Preparation
Get `user_info.json` using [GFAlarm](
https://gall.dcinside.com/mgallery/board/view?id=micateam&no=1439586) or other tools and put it under `./info`

## Usage
```
usage: main.py [-h] [-m MAX_DOLLS] [-f FAIRY_RATIO] [-u UPGRADE_RESOURCE] [-r REGION] [-p] theater_id

positional arguments:
  theater_id            theater id, e.g. 736 indicates 7th event, difficulty 3, stage 6

options:
  -h, --help            show this help message and exit
  -m MAX_DOLLS, --max_dolls MAX_DOLLS
                        the maxium T-dolls you can send
  -f FAIRY_RATIO, --fairy_ratio FAIRY_RATIO
                        the fairy ratio, default to 2 (4 5-star fairies)
  -u UPGRADE_RESOURCE, --upgrade_resource UPGRADE_RESOURCE
                        amount of equipments you can upgrade, notice that
                        exclusive equipments usually consume 3
  -r REGION, --region REGION
                        ch/tw/kr/jp/us
  -p, --perfect
                        use perfect team instead of your own team
```
Run `python main.py -h` to see details.