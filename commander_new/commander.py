import itertools
import math
from dataclasses import dataclass
from pathlib import Path
from typing import *

import pulp as lp
from gf_utils2.gamedata import GameData
from gf_utils2.userinfo.base import BaseGameObject
from gf_utils2.userinfo.gun import Equip, Gun
from gf_utils2.userinfo.user_info import UserInfo


@dataclass
class EquipUserRecord:
    lv00_obj: Equip
    lv00_cnt: int
    lv10_obj: Equip
    lv10_cnt: int
    upgrade: int
    fit_guns: list[int]


@dataclass
class GunChoiceInfo:
    gun: Gun
    equips: Tuple[Equip, Equip, Equip]
    effect: int
    score: int


@dataclass
class RecipeRecord:
    content: dict[str, int | float]
    info: Equip | GunChoiceInfo


class Commander:
    def __init__(
        self, game_data: GameData, solver: lp.LpSolver, user_data: dict
    ) -> None:
        self.game_data = game_data
        self.solver = solver
        self.user_data = user_data
        BaseGameObject.set_gamedata(game_data)

    def load_user_info(self) -> Tuple[dict[int, Gun], dict[int, EquipUserRecord]]:
        def gun_priority(gun: Gun):
            return (
                gun.number,
                gun.gun_level,
                gun.if_modification,
                gun.skill1,
                gun.skill2,
                gun.soul_bond,
            )

        gun_user_record: DefaultDict[int, Gun] = DefaultDict(Gun)
        for record in self.user_data["gun_with_user_info"]:
            gun = Gun(record)
            gid = gun.gun_id % 20000
            gun_user_record[gid] = max(gun, gun_user_record[gid], key=gun_priority)

        equip_user_record: dict[int, EquipUserRecord] = {}
        for record in self.user_data["equip_with_user_info"].values():
            equip_obj = Equip(record)

            idx = equip_obj.equip_id
            equip = equip_obj.equip_info

            upgrade = -1 if not equip["bonus_type"] else equip["exclusive_rate"]
            equip_user_record.setdefault(
                idx,
                EquipUserRecord(
                    lv00_obj=Equip(equip_id=idx, equip_level=0),
                    lv00_cnt=0,
                    lv10_obj=Equip(equip_id=idx, equip_level=10),
                    lv10_cnt=0,
                    upgrade=upgrade,
                    fit_guns=[int(i) for i in equip["fit_guns"].split(",")]
                    if equip["fit_guns"]
                    else [],
                ),
            )
            if equip_obj.equip_level == 10:
                equip_user_record[idx].lv10_cnt += 1
            else:
                equip_user_record[idx].lv00_cnt += 1

        return gun_user_record, equip_user_record

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
                    soul_bond=1,
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
                    soul_bond=1,
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
            upgrade = -1 if not equip["bonus_type"] else equip["exclusive_rate"]
            equip_user_record[idx] = EquipUserRecord(
                lv00_obj=Equip(equip_id=idx, equip_level=0),
                lv00_cnt=999 if upgrade < 0 else 0,
                lv10_obj=Equip(equip_id=idx, equip_level=10),
                lv10_cnt=0 if upgrade < 0 else 999,
                upgrade=upgrade,
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
    ) -> dict[str, RecipeRecord]:
        theater_config = self.get_theater_config(theater_id, game_data["theater_area"])
        choices: dict[str, RecipeRecord] = {}

        equip_type_groups: DefaultDict[int, list[EquipUserRecord]] = DefaultDict(list)
        for eid, equip in user_equip.items():
            equip_info = equip.lv00_obj.equip_info
            equip_type_groups[equip_info["type"]].append(equip)
            if equip.upgrade < 0:
                continue
            if equip.lv00_cnt > 0 and equip.lv10_cnt < max_dolls:
                choices[f"u_e{eid}"] = RecipeRecord(
                    content={
                        f"e{eid}_0": -1,
                        f"e{eid}_10": 1,
                        "upgrade": -equip.upgrade,
                    },
                    info=equip.lv00_obj,
                )

        for gid, gun in user_gun.items():
            gun_info = gun.gun_info
            equip_choices: list[list[Equip]] = []
            for i in range(1, 4):
                equippable_types = [
                    int(e) for e in gun_info[f"type_equip{i}"].split(";")[-1].split(",")
                ]
                equippable_equips: list[Equip] = []
                for erec in itertools.chain(
                    *[equip_type_groups[t] for t in equippable_types]
                ):
                    if not erec.fit_guns or gid in erec.fit_guns:
                        if erec.lv00_cnt > 0 and erec.lv10_cnt < max_dolls:
                            equippable_equips.append(erec.lv00_obj)
                        if erec.upgrade > 0:
                            equippable_equips.append(erec.lv10_obj)
                equip_choices.append(equippable_equips)

            for equips in itertools.product(*equip_choices):
                if len({e.equip_info["type"] for e in equips}) < 3:
                    continue
                gun.equips = equips
                effect = gun.battle_efficiency(
                    night=theater_config["fight_mode"] == "night",
                    max_eat=True,
                    max_adjust=True,
                    max_favor=True,
                )
                sp_ratio = 1.2 if gid in theater_config["advantage"] else 1
                score = math.floor(
                    theater_config["class_weight"][gun_info["type"] - 1]
                    * (sp_ratio * fairy_ratio * effect / 100)
                )

                e1, e2, e3 = equips
                recipe_name = (
                    f"r_g{gid}"
                    f"_e{e1.equip_id}_{e1.equip_level}"
                    f"_e{e2.equip_id}_{e2.equip_level}"
                    f"_e{e3.equip_id}_{e3.equip_level}"
                )
                choices[recipe_name] = RecipeRecord(
                    content={
                        f"g_{gid}": -1,
                        "count": -1,
                        "score": score,
                        f"e{e1.equip_id}_{e1.equip_level}": -1,
                        f"e{e2.equip_id}_{e2.equip_level}": -1,
                        f"e{e3.equip_id}_{e3.equip_level}": -1,
                    },
                    info=GunChoiceInfo(gun, equips, effect, score),
                )
        return choices

    def problem_solve(
        self,
        choices: dict[str, RecipeRecord],
        user_gun: dict[int, Gun],
        user_equip: dict[int, EquipUserRecord],
        max_dolls: int,
        upgrade_resource: int,
    ) -> tuple[list[Tuple[Equip, int]], list[GunChoiceInfo]]:
        resource: dict[str, lp.LpAffineExpression] = {}
        for id in user_gun.keys():
            resource[f"g_{id}"] = 1
        for eid, equip in user_equip.items():
            resource[f"e{eid}_10"] = equip.lv10_cnt
            resource[f"e{eid}_0"] = equip.lv00_cnt
        resource["count"] = max_dolls
        resource["score"] = 0
        resource["upgrade"] = upgrade_resource

        lp_vars: dict[str, lp.LpVariable] = {}
        coeff_lp_var_dict = DefaultDict(list)
        problem = lp.LpProblem("battlefield", lp.LpMaximize)
        for k, recipe in choices.items():
            lp_vars[k] = lp.LpVariable(k, cat=lp.LpInteger, lowBound=0)
            for r, c in recipe.content.items():
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
                    u_info.append((choices[k].info, v))
                else:
                    g_info.append(choices[k].info)
        return u_info, g_info

    def analyze(
        self,
        u_info: list[Tuple[Equip, int]],
        g_info: list[GunChoiceInfo],
        use_perfect=False,
    ) -> tuple[list, list]:
        # analyze result
        equip_counter = DefaultDict(int)
        g_records: list[dict[str, int | str]] = []

        for gun_choice in g_info:
            gun = gun_choice.gun
            e1, e2, e3 = gun_choice.equips
            g_records.append(
                {
                    "type_id": gun.gun_info["type"],
                    "type": ["HG", "SMG", "RF", "AR", "MG", "SG"][
                        gun.gun_info["type"] - 1
                    ],
                    "idx": gun.gun_id,
                    "name": gun.gun_info["name"],
                    "effect": gun_choice.effect,
                    "score": gun_choice.score,
                    "level": gun.gun_level,
                    "rank": gun.gun_info["rank_display"],
                    "soul_bond": gun.soul_bond,
                    "skill1": gun.skill1,
                    "skill2": gun.skill2,
                    "equip1": e1.equip_info["name"],
                    "erank1": e1.equip_info["rank"]
                    if e1.equip_info["type"] not in [18, 19, 20]
                    else 6,
                    "elv1": e1.equip_level,
                    "equip2": e2.equip_info["name"],
                    "erank2": e2.equip_info["rank"]
                    if e2.equip_info["type"] not in [18, 19, 20]
                    else 6,
                    "elv2": e2.equip_level,
                    "equip3": e3.equip_info["name"],
                    "erank3": e3.equip_info["rank"]
                    if e3.equip_info["type"] not in [18, 19, 20]
                    else 6,
                    "elv3": e3.equip_level,
                }
            )
            for e in gun_choice.equips:
                equip_counter[e.equip_id] += 1

        u_records: list[dict[str, int | str]] = []
        if not use_perfect:
            equip_counter = {info.equip_id: v.value() for info, v in u_info}

        equip_info = self.game_data["equip"]
        for eid, count in equip_counter.items():
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

    def solve(
        self,
        theater_id: int,
        fairy_ratio: float,
        max_dolls: int,
        upgrade_resource: int,
        use_perfect: bool,
    ) -> tuple[list, list]:
        if use_perfect:
            gun_record, equip_record = self.load_perfect_info()
        else:
            gun_record, equip_record = self.load_user_info()
        choices = self.prepare_choices(
            gun_record, equip_record, theater_id, max_dolls, fairy_ratio
        )
        u_info, g_info = self.problem_solve(
            choices, gun_record, equip_record, max_dolls, upgrade_resource
        )
        g_records, u_records = self.analyze(u_info, g_info, use_perfect)
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
    g_records, u_records = commander.solve(1048, 2, 30, 999, False)
    for gr in g_records:
        print(gr)
    for ur in u_records:
        print(ur)
