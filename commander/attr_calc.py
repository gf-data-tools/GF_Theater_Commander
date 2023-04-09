import math


def doll_attr_calculate(doll, my_doll, equip_group):
    lv = my_doll["gun_level"]
    favor_factor = 0.95 + (my_doll["favor"] + 10) // 50 * 0.05

    attr_change = {"hp": 0, "pow": 0, "rate": 0, "hit": 0, "dodge": 0, "armor": 0}
    attr_fixed = {
        "critical_harm_rate": 150,
        "critical_percent": doll["crit"],
        "armor_piercing": doll["armor_piercing"],
        "night_view_percent": 0,
        "bullet_number_up": doll["special"],
    }
    attr_other = {
        "id": doll["id"],
        "star": doll["rank"],
        "upgrade": lv,
        "type": doll["type"],
        "skill_effect_per": 0,
        "skill_effect": 0,
        "number": my_doll["number"],
        "skill1": my_doll["skill1"],
        "skill2": my_doll["skill2"],
    }

    for key in ["pow", "hit", "dodge"]:
        attr_change[key] = gf_ceil(calculate(lv, key, doll) * favor_factor)
    for key in ["hp", "rate", "armor"]:
        attr_change[key] = gf_ceil(calculate(lv, key, doll))
    for equip, elv in equip_group:
        if not equip:
            continue
        attr_other["skill_effect_per"] += equip["skill_effect_per"]
        attr_other["skill_effect"] += equip["skill_effect"]

        for attr in attr_change.keys():
            if attr in equip["stat"].keys():
                stat = equip["stat"][attr]
                modif = 1
                if "upgrade" in stat.keys() and elv == 10:
                    modif += stat["upgrade"] / 1000
                value = math.floor(stat["max"] * modif)
                attr_change[attr] += value

        for attr in attr_fixed.keys():
            if attr in equip["stat"].keys():
                stat = equip["stat"][attr]
                modif = 1
                if "upgrade" in stat.keys() and elv == 10:
                    modif += stat["upgrade"] / 1000
                value = math.floor(stat["max"] * modif)
                attr_fixed[attr] += value
    day = doll_effect_calculate(
        {
            "attr_change": attr_change,
            "attr_fixed": attr_fixed,
            "attr_other": attr_other,
        },
        "day",
    )
    night = doll_effect_calculate(
        {
            "attr_change": attr_change,
            "attr_fixed": attr_fixed,
            "attr_other": attr_other,
        },
        "night",
    )
    return {"day": day, "night": night}


def doll_effect_calculate(gun_attr, fight_type):

    skill1 = gun_attr["attr_other"]["skill1"]
    skill2 = gun_attr["attr_other"]["skill2"]
    star = int(gun_attr["attr_other"]["star"])
    number = gun_attr["attr_other"]["number"]
    skill_effect = int(gun_attr["attr_other"]["skill_effect"])
    skill_effect_per = int(gun_attr["attr_other"]["skill_effect_per"])

    # 1技能效能 = ceiling（5*(0.8+星级/10)*[35+5*(技能等级-1)]*(100+skill_effect_per)/100,1) + skill_effect
    # 2技能效能 = ceiling（5*(0.8+星级/10)*[15+2*(技能等级-1)]*(100+skill_effect_per)/100,1) + skill_effect
    doll_skill_effect = (
        gf_ceil(
            number
            * (0.8 + star / 10)
            * (35 + 5 * (skill1 - 1))
            * (100 + skill_effect_per)
            / 100
        )
        + skill_effect
    )
    if skill2 > 0:
        doll_skill_effect += gf_ceil(
            number
            * (0.8 + star / 10)
            * (15 + 2 * (skill2 - 1))
            * (100 + skill_effect_per)
            / 100
        )

    life = int(gun_attr["attr_change"]["hp"])
    dodge = int(gun_attr["attr_change"]["dodge"])
    armor = int(gun_attr["attr_change"]["armor"])
    # 防御效能 = CEILING(生命*(35+闪避)/35*(4.2*100/MAX(1,100-护甲)-3.2),1)
    defend_effect = gf_ceil(
        life * number * (35 + dodge) / 35 * (4.2 * 100 / max(1, 100 - armor) - 3.2)
    )

    hit = int(gun_attr["attr_change"]["hit"])
    night_view_percent = int(gun_attr["attr_fixed"]["night_view_percent"])
    if fight_type == "night":
        # 夜战命中 = CEILING(命中*(1+(-0.9*(1-夜视仪数值/100))),1)
        hit = gf_ceil(hit * (1 + (-0.9 * (1 - night_view_percent / 100))))

    attack = int(gun_attr["attr_change"]["pow"])
    rate = int(gun_attr["attr_change"]["rate"])
    critical = int(gun_attr["attr_fixed"]["critical_percent"])
    critical_damage = int(gun_attr["attr_fixed"]["critical_harm_rate"])
    armor_piercing = int(gun_attr["attr_fixed"]["armor_piercing"])
    bullet = int(gun_attr["attr_fixed"]["bullet_number_up"])
    if gun_attr["attr_other"]["type"] == 6:
        # SG攻击 = 6*5*(3*弹量*(伤害+穿甲/3)*(1+暴击率*(暴击伤害-100)/10000)/(1.5+弹量*50/射速+0.5*弹量)*命中/(命中+23)+8)
        attack_effect = gf_ceil(
            6
            * number
            * (
                3
                * bullet
                * (attack + armor_piercing / 3)
                * (1 + critical * (critical_damage - 100) / 10000)
                / (1.5 + bullet * 50 / rate + 0.5 * bullet)
                * hit
                / (hit + 23)
                + 8
            )
        )
    elif gun_attr["attr_other"]["type"] == 5:
        # MG攻击 = 7*5*(弹量*(伤害+穿甲/3)*(1+暴击率*(暴击伤害-100)/10000)/(弹量/3+4+200/射速)*命中/(命中+23)+8)
        attack_effect = gf_ceil(
            7
            * number
            * (
                bullet
                * (attack + armor_piercing / 3)
                * (1 + critical * (critical_damage - 100) / 10000)
                / (bullet / 3 + 4 + 200 / rate)
                * hit
                / (hit + 23)
                + 8
            )
        )
    elif gun_attr["attr_other"]["type"] in [1, 2, 3, 4]:
        # 其他攻击 = 5*5*(伤害+穿甲/3)*(1+暴击率*(暴击伤害-100)/10000)*射速/50*命中/(命中+23)+8)
        attack_effect = gf_ceil(
            5
            * number
            * (
                (attack + armor_piercing / 3)
                * (1 + critical * (critical_damage - 100) / 10000)
                * rate
                / 50
                * hit
                / (hit + 23)
                + 8
            )
        )
    else:
        exit("gun type error: " + gun_attr["attr_other"]["type"])
    effect_total = doll_skill_effect + defend_effect + attack_effect
    return effect_total


def stc_to_text(text, name):
    tem = text[text.find(name) + len(name) + 1 :]
    out_text = tem[: tem.find("\n")]
    return out_text


def bonus_handle(string):
    dict1 = {}
    attr1 = string.split(",")
    for key in attr1:
        type1 = key.split(":")[0]
        numb1 = key.split(":")[1]
        dict1[type1] = str(1 + int(numb1) / 1000)
    return dict1


def gf_ceil(number):
    if number % 1 < 0.0001:
        number = number - (number % 1)
    else:
        number = number - (number % 1) + 1
    return int(number)


BASIC = [16, 45, 5, 5]
BASIC_LIFE_ARMOR = [[[55, 0.555], [2, 0.161]], [[96.283, 0.138], [13.979, 0.04]]]
BASE_ATTR = [
    [0.60, 0.60, 0.80, 1.20, 1.80, 0.00],
    [1.60, 0.60, 1.20, 0.30, 1.60, 0.00],
    [0.80, 2.40, 0.50, 1.60, 0.80, 0.00],
    [1.00, 1.00, 1.00, 1.00, 1.00, 0.00],
    [1.50, 1.80, 1.60, 0.60, 0.60, 0.00],
    [2.00, 0.70, 0.40, 0.30, 0.30, 1.00],
]
GROW = [
    [[0.242, 0], [0.181, 0], [0.303, 0], [0.303, 0]],
    [[0.06, 18.018], [0.022, 15.741], [0.075, 22.572], [0.075, 22.572]],
]
TYPE_ENUM = {"HG": 0, "SMG": 1, "RF": 2, "AR": 3, "MG": 4, "SG": 5}
ATTR_ENUM = {"hp": 0, "pow": 1, "rate": 2, "hit": 3, "dodge": 4, "armor": 5}


def calculate(lv, attr_type, doll):
    mod = 1
    if lv <= 100:
        mod = 0
    guntype = doll["type"] - 1
    attr = ATTR_ENUM[attr_type]
    ratio = doll[f"ratio_{attr_type}"] if attr_type != "hp" else doll[f"ratio_life"]
    growth = doll["eat_ratio"]

    if attr == 0 or attr == 5:
        return math.ceil(
            (
                BASIC_LIFE_ARMOR[mod][attr & 1][0]
                + (lv - 1) * BASIC_LIFE_ARMOR[mod][attr & 1][1]
            )
            * BASE_ATTR[guntype][attr]
            * ratio
            / 100
        )
    else:
        base = BASIC[attr - 1] * BASE_ATTR[guntype][attr] * ratio / 100
        accretion = (
            (GROW[mod][attr - 1][1] + (lv - 1) * GROW[mod][attr - 1][0])
            * BASE_ATTR[guntype][attr]
            * ratio
            * growth
            / 100
            / 100
        )
        return math.ceil(base) + math.ceil(accretion)


if __name__ == "__main__":
    gun = {
        "id": 20001,
        "type": 1,
        "rank": 5,
        "ratio_life": 122,
        "ratio_pow": 125,
        "ratio_rate": 89,
        "ratio_speed": 100,
        "ratio_hit": 90,
        "ratio_dodge": 95,
        "ratio_armor": 0,
        "armor_piercing": 15,
        "crit": 20,
        "special": 0,
        "eat_ratio": 130,
        "effect_grid_center": 13,
        "effect_guntype": "0",
        "effect_grid_pos": "8,12,14,18",
        "effect_grid_effect": "1,12;3,30",
        "type_equip1": "1;4,13,16,18",
        "type_equip2": "2;6",
        "type_equip3": "3;10",
        "type_equip4": "",
    }
    my_gun = {
        "favor": 100,
        "gun_id": 20001,
        "gun_level": 120,
        "name": "柯尔特左轮",
        "number": 5,
        "skill1": 10,
        "skill2": 10,
    }
    equips = [
        (
            {
                "id": 122,
                "skill_effect": 0,
                "skill_effect_per": 0,
                "stat": {
                    "critical_percent": {"max": 15, "min": 12, "upgrade": 350},
                    "dodge": {"max": 8, "min": 6, "upgrade": 300},
                    "pow": {"max": 2, "min": 1, "upgrade": 500},
                },
                "type": 18,
            },
            10,
        ),
        (
            {
                "id": 72,
                "skill_effect": 0,
                "skill_effect_per": 0,
                "stat": {
                    "armor_piercing": {"max": -7, "min": -10},
                    "pow": {"max": 10, "min": 7, "upgrade": 500},
                },
                "type": 6,
            },
            10,
        ),
        (
            {
                "id": 40,
                "skill_effect": 0,
                "skill_effect_per": 0,
                "stat": {
                    "dodge": {"max": 25, "min": 20, "upgrade": 400},
                    "pow": {"max": -6, "min": -8},
                },
                "type": 10,
            },
            10,
        ),
    ]
    eff = doll_attr_calculate(gun, my_gun, equips)
    print(eff)
