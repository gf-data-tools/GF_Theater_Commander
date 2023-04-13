import pandas as pd


def load_user_info(user_info: dict, game_data: dict):
    gun_info, equip_info = game_data["gun"], game_data["equip"]
    gun_user, equip_user = (
        user_info["gun_with_user_info"],
        user_info["equip_with_user_info"],
    )

    gun_user_df = pd.DataFrame.from_records(gun_user).reindex(
        columns=["gun_id", "gun_level", "skill1", "skill2", "number", "favor"]
    )
    for c in gun_user_df.columns:
        gun_user_df[c] = pd.to_numeric(gun_user_df[c])
    gun_user_df["raw_gun_id"] = gun_user_df["gun_id"] % 20000
    gun_user_df["favor"] = gun_user_df["favor"] // 10000
    gun_user_df_agg = gun_user_df.groupby("raw_gun_id").agg(max)
    gun_user_df_agg["name"] = gun_user_df_agg["gun_id"].map(
        lambda idx: gun_info[idx]["name"]
    )
    gun_user_record = gun_user_df_agg.to_dict(orient="index")

    equip_user_df = pd.DataFrame.from_dict(equip_user, orient="index").reindex(
        columns=["equip_id", "equip_level"]
    )
    for c in equip_user_df.columns:
        equip_user_df[c] = pd.to_numeric(equip_user_df[c])
    equip_user_df["equip_level"] = equip_user_df["equip_level"].map(
        lambda x: 0 if x < 10 else 10
    )
    equip_user_df["level_10"] = equip_user_df["equip_level"].map(
        lambda x: 1 if x == 10 else 0
    )
    equip_user_df["level_00"] = equip_user_df["equip_level"].map(
        lambda x: 0 if x == 10 else 1
    )
    equip_user_df_agg = (
        equip_user_df.groupby(["equip_id"])
        .agg(sum)
        .reset_index()
        .drop(columns=["equip_level"])
    )
    equip_user_df_agg["name"] = equip_user_df_agg["equip_id"].map(
        lambda idx: equip_info[idx]["name"]
    )
    equip_user_df_agg["rank"] = equip_user_df_agg["equip_id"].map(
        lambda idx: equip_info[idx]["rank"]
    )
    equip_user_df_agg["upgrade"] = equip_user_df_agg["equip_id"].map(
        lambda idx: -1
        if not equip_info[idx]["bonus_type"]
        else int(equip_info[idx]["exclusive_rate"])
    )
    equip_user_df_agg["fit_guns"] = equip_user_df_agg["equip_id"].map(
        lambda idx: [int(i) for i in equip_info[idx]["fit_guns"].split(",")]
        if equip_info[idx]["fit_guns"]
        else []
    )
    equip_user_df_agg = equip_user_df_agg.query("rank==5").set_index(
        "equip_id", drop=False
    )
    equip_user_record = equip_user_df_agg.to_dict(orient="index")

    return gun_user_record, equip_user_record


def load_perfect_info(game_data: dict):
    gun_info, equip_info = game_data["gun"], game_data["equip"]
    gun_user_record = {}
    for idx, gun in gun_info.items():
        if 9000 < idx < 20000 or idx > 30000:
            continue
        gun_user_record[idx % 20000] = {
            "gun_id": idx,
            "gun_level": 120 if idx > 20000 else 100,
            "skill1": 10,
            "skill2": 10 if idx > 20000 else 0,
            "number": 5,
            "favor": 200 if idx > 20000 else 150,
            "name": gun["name"],
        }

    equip_user_record = {}
    for idx, equip in equip_info.items():
        if equip["rank"] < 5 or equip["is_show"] == 0 or equip["code"].endswith("_S"):
            continue
        equip_user_record[idx] = {
            "equip_id": idx,
            "level_10": 0,
            "level_00": 99,
            "name": equip["name"],
            "rank": 5,
            "upgrade": -1 if not equip["bonus_type"] else equip["exclusive_rate"],
            "fit_guns": [int(i) for i in equip["fit_guns"].split(",")]
            if equip["fit_guns"]
            else [],
        }

    return gun_user_record, equip_user_record


if __name__ == "__main__":
    import json
    import re

    from gf_utils.stc_data import get_stc_data

    game_data = get_stc_data("data/ch")

    with open(r"info/user_info.json", "rb") as f:
        data = f.read().decode("ascii", "ignore")
        data = re.sub(r'"name":".*?"', r'"name":""', data)
        user_info = json.loads(data)

    user, equip = load_user_info(user_info, game_data)
    user, equip = load_perfect_info(game_data)
    print(user, equip)
