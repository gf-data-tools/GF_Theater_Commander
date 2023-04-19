from pathlib import Path
from typing import *

import pulp as lp
from gf_utils2.gamedata import GameData
from gf_utils2.userinfo.base import BaseGameObject
from gf_utils2.userinfo.gun import Equip, Gun
from gf_utils2.userinfo.user_info import UserInfo

from .load_user_info import load_perfect_info, load_user_info
from .prepare_choices import prepare_choices


class EquipUserRecord(NamedTuple):
    lv00_obj: Equip
    lv00_cnt: int
    lv10_obj: Equip
    lv10_cnt: int
    upgrade: int
    fit_guns: list[int]


class RecipeRecord(NamedTuple):
    content: dict[str, int | float]
    info: dict[str, Gun | Equip | int | float]


class Commander:
    def __init__(
        self, game_data: GameData, solver: lp.LpSolver, user_data: dict
    ) -> None:
        self.game_data = game_data
        self.solver = solver
        self.user_data = user_data
        BaseGameObject.set_gamedata(game_data)

    def load_perfect_info(self) -> Tuple[dict[int, Gun], dict[int, EquipUserRecord]]:
        gun_info, equip_info = self.game_data["gun"], self.game_data["equip"]
        gun_user_record: dict[int, Gun] = {}
        for idx in gun_info.keys():
            if 9000 < idx < 20000 or idx > 30000:
                continue
            if idx < 9000:
                gun_user_record[idx] = Gun(
                    gun_id=idx,
                    gun_level=100,
                    number=5,
                    if_modification=0,
                    skill1=10,
                    skill2=0,
                )
            elif idx < 20000:
                continue
            elif idx < 30000:
                gun_user_record[idx - 20000] = Gun(
                    gun_id=idx,
                    gun_level=120,
                    number=5,
                    if_modification=3,
                    skill1=10,
                    skill2=10,
                )
            else:
                continue

        equip_user_record: dict[int, EquipUserRecord] = {}
        for idx, equip in equip_info.items():
            if (
                equip["rank"] < 5
                or equip["is_show"] == 0
                or equip["code"].endswith("_S")
            ):
                continue
            equip_user_record[idx] = EquipUserRecord(
                lv00_obj=Equip(equip_id=idx, equip_level=0),
                lv00_cnt=999,
                lv10_obj=Equip(equip_id=idx, equip_level=10),
                lv10_cnt=0,
                upgrade=-1 if not equip["bonus_type"] else equip["exclusive_rate"],
                fit_guns=[int(i) for i in equip["fit_guns"].split(",")]
                if equip["fit_guns"]
                else [],
            )

        return gun_user_record, equip_user_record

    @staticmethod
    def get_theater_config(theater_id, theater_area):
        area_cfg = theater_area[theater_id]
        if area_cfg["boss"] == "":
            raise AttributeError(f"{theater_id}不是要塞关卡")

        class_weight = [int(i) for i in area_cfg["boss_score_coef"].split(";")]
        advantage = [int(i) for i in area_cfg["advantage_gun"].split(",")]
        fight_mode = "day" if area_cfg["boss"][-1] == "0" else "night"
        return dict(
            class_weight=class_weight, advantage=advantage, fight_mode=fight_mode
        )

    def prepare_choices(
        self,
        user_gun: dict[int, Gun],
        user_equip: dict[int, EquipUserRecord],
        theater_id: int,
        max_dolls: int,
        fairy_ratio: float,
    ) -> dict[str, dict[str, dict[str, int]]]:
        theater_config = self.get_theater_config(theater_id, game_data["theater_area"])
        choices: dict[str, RecipeRecord] = {}

        equip_type_groups = DefaultDict(dict)
        for eid, equip in user_equip.items():
            equip_info = equip.lv00_obj.equip_info
            equip_type_groups[equip_info["type"]][eid] = equip
            if not equip_info["bonus_type"]:
                continue
            if equip.lv00_cnt > 0 and equip.lv10_cnt < max_dolls:
                choices[f"u_e{eid}"] = RecipeRecord(
                    content={
                        f"e{eid}_0": -1,
                        f"e{eid}_10": 1,
                        "upgrade": -equip_info["exclusive_rate"],
                    },
                    info={"equip": equip.lv00_obj},
                )

        for gid, gun in user_gun.items():
            gun_info = gun.gun_info
            tmp = list(
                map(
                    lambda x: [
                        equip_type_groups.get(int(i), {})
                        for i in x.split(";")[-1].split(",")
                    ],
                    [gun_info[f"type_equip{i}"] for i in range(1, 4)],
                )
            )
        return choices

    def solve(
        self,
        theater_id: int,
        fairy_ratio: float,
        max_dolls: int,
        upgrade_resource: int,
        use_perfect: bool,
    ):
        if use_perfect:
            upgrade_resource = 999
        game_data = self.game_data
        gun_info, equip_info = game_data["gun"], game_data["equip"]

        if use_perfect:
            user_gun, user_equip = load_perfect_info(game_data)
        else:
            user_gun, user_equip = load_user_info(self.user_data, game_data)
        choices = prepare_choices(
            user_gun, user_equip, theater_id, max_dolls, fairy_ratio, game_data
        )

        resource = {}
        for id in user_gun.keys():
            resource[f"g_{id}"] = 1
        for eid, equip in user_equip.items():
            resource[f"e{eid}_10"] = equip["level_10"]
            resource[f"e{eid}_0"] = equip["level_00"]
        resource["count"] = max_dolls
        resource["score"] = 0
        resource["upgrade"] = upgrade_resource
        lp_vars: dict[str, lp.LpVariable] = {}
        coeff_lp_var_dict = DefaultDict(list)
        problem = lp.LpProblem("battlefield", lp.LpMaximize)
        for k, recipe in choices.items():
            lp_vars[k] = lp.LpVariable(k, cat=lp.LpInteger, lowBound=0)
            for r, c in recipe["content"].items():
                coeff_lp_var_dict[r].append((lp_vars[k], c))
        for k, v in coeff_lp_var_dict.items():
            resource[k] += lp.LpAffineExpression(v)
        for k, v in resource.items():
            problem += v >= 0, k
        problem += resource["score"] + 0.001 * resource["upgrade"]

        problem.solve(self.solver)

        u_info, g_info = [], []
        for k, v in lp_vars.items():
            if v.value() > 0:
                if k[0] == "u":
                    u_info.append([choices[k]["info"], v])
                else:
                    g_info.append([choices[k]["info"], v])

        # analyze result
        equip_counter = DefaultDict(int)
        g_records: list[dict[str, int | str]] = []

        for i, (info, v) in enumerate(g_info):
            g_records.append(
                {
                    "type_id": gun_info[info["gid"]]["type"],
                    "type": ["HG", "SMG", "RF", "AR", "MG", "SG"][
                        gun_info[info["gid"]]["type"] - 1
                    ],
                    "idx": info["gid"],
                    "name": gun_info[info["gid"]]["name"],
                    "effect": info["effect"],
                    "score": info["score"],
                    "level": user_gun[info["gid"] % 20000]["gun_level"],
                    "rank": gun_info[info["gid"]]["rank_display"],
                    "favor": user_gun[info["gid"] % 20000]["favor"],
                    "skill1": user_gun[info["gid"] % 20000]["skill1"],
                    "skill2": user_gun[info["gid"] % 20000]["skill2"],
                    "equip1": equip_info[info[f"eid_1"]]["name"],
                    "erank1": equip_info[info[f"eid_1"]]["rank"]
                    if equip_info[info[f"eid_1"]]["type"] not in [18, 19, 20]
                    else 6,
                    "elv1": info[f"elv_1"],
                    "equip2": equip_info[info[f"eid_2"]]["name"],
                    "erank2": 6
                    if equip_info[info[f"eid_2"]]["type"] in [18, 19, 20]
                    else equip_info[info[f"eid_2"]]["rank"],
                    "elv2": info[f"elv_2"],
                    "equip3": equip_info[info[f"eid_3"]]["name"],
                    "erank3": 6
                    if equip_info[info[f"eid_3"]]["type"] in [18, 19, 20]
                    else equip_info[info[f"eid_3"]]["rank"],
                    "elv3": info[f"elv_3"],
                }
            )
            for i in range(1, 4):
                equip_counter[info[f"eid_{i}"]] += 1

        u_records: list[dict[str, int | str]] = []
        if not use_perfect:
            equip_counter = {info["eid"]: v.value() for info, v in u_info}
        for i, (eid, count) in enumerate(equip_counter.items()):
            u_records.append(
                {
                    "name": equip_info[eid]["name"],
                    "rank": 6
                    if equip_info[eid]["type"] in [18, 19, 20]
                    else equip_info[eid]["rank"],
                    "count": count,
                }
            )
        return g_records, u_records


if __name__ == "__main__":
    import json

    game_data = GameData(R"D:\Workspace\gfline\GF_Data_Tools\data\ch\formatted\json")
    lp_bin: Path = (
        Path(__file__).resolve().parent.parent
        / "solverdir"
        / "cbc"
        / lp.operating_system
        / lp.arch
        / lp.LpSolver_CMD.executableExtension("cbc")
    )
    solver = lp.COIN_CMD(msg=0, path=str(lp_bin))
    user_data = json.load(Path("info/user_info.json").open("r"))

    commander = Commander(game_data, solver, user_data)
    # g_records, u_records = commander.solve(1048, 2, 30, 0, False)
    gun_record, equip_record = commander.load_perfect_info()
    choices = commander.prepare_choices(gun_record, equip_record, 1048, 30, 4)
    print(choices)
