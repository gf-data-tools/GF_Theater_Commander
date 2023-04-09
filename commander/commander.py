from pathlib import Path
from typing import *

import pulp as lp

from .gf_utils import GameData
from .load_user_info import load_perfect_info, load_user_info
from .prepare_choices import prepare_choices


class Commander:
    def __init__(
        self, game_data: GameData, solver: lp.LpSolver, user_data: dict
    ) -> None:
        self.game_data = game_data
        self.solver = solver
        self.user_data = user_data

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

    game_data = GameData("data/ch")
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
    g_records, u_records = commander.solve(1048, 2, 30, 0, False)
    print(g_records)
