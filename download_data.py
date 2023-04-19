from pathlib import Path

from gf_utils import download

REGIONS = ["ch", "kr", "tw", "jp", "us"]
TABLES = [
    'theater_area', 'squad', 'squad_chip', 'squad_standard_attribution', 'squad_type', 
    'squad_rank', 'squad_advanced_bonus', 'squad_chip_exp', 'squad_cpu', 
    'squad_cpu_completion', 'sangvis', 'sangvis_advance', 'sangvis_type', 
    'sangvis_resolution', 'gun', 'equip', 'game_config_info', 'gun_type_info'
]  # fmt:skip


def download_data(dir="./data", region="ch"):
    data_dir = Path(dir)
    data_dir.mkdir(exist_ok=True)
    (data_dir / region).mkdir(exist_ok=True)
    for table in TABLES:
        url = f"https://github.com/gf-data-tools/gf-data-{region}/raw/main/formatted/json/{table}.json"
        path = data_dir / region / f"{table}.json"
        if not path.exists():
            download(url, str(path))


if __name__ == "__main__":
    download_data()
