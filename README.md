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
python main.py [-m MAX_DOLLS] [-f FAIRY_RATIO] [-u UPGRADE_RESOURCE] theater_id
```
Run `python main.py -h` to see details.