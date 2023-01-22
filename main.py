import json
import locale
import os
import shutil
import tkinter as tk
import tkinter.ttk as ttk
from functools import partial, wraps
from gettext import install
from pathlib import Path
from threading import RLock, Thread
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showerror, showinfo
from tkinter.simpledialog import Dialog
from typing import *

import pulp as lp

from gf_utils import GameData, download
from load_user_info import load_perfect_info, load_user_info
from prepare_choices import prepare_choices


def menu_from_dict(
    master: tk.Widget, options: dict, var_key: tk.Variable, var_value: tk.Variable
):
    menu = tk.Menu(master, tearoff=False)
    for k, v in options.items():
        if isinstance(v, dict):
            menu.add_cascade(label=k, menu=menu_from_dict(menu, v, var_key, var_value))
        else:
            menu.add_radiobutton(
                label=k,
                indicatoron=False,
                command=lambda k=k, v=v: (var_key.set(k), var_value.set(v)),
            )
    return menu


def var_min_max(var: tk.IntVar, min: int, max: int, *_):
    try:
        v = var.get()
    except:
        v = 0
    if v < min:
        var.set(min)
    if v > max:
        var.set(max)


def treeview_sort_column(tv: ttk.Treeview, col: str, reverse: bool):
    l = [(tv.set(k, col), k) for k in tv.get_children("")]
    try:
        l.sort(key=lambda t: int(t[0]), reverse=reverse)
    except ValueError:
        l.sort(reverse=reverse)
    # rearrange items in sorted positions
    for index, (val, k) in enumerate(l):
        tv.move(k, "", index)
        tv.item(k, tags=("oddrow" if index % 2 else "evenrow"))

    # reverse sort next time
    tv.heading(col, command=partial(treeview_sort_column, tv, col, not reverse))


def locked(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        with self.lock:
            func(self, *args, **kwargs)

    return wrapped


class TheaterCommander(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = RLock()
        self.setup()

    def setup(self, region="ch"):
        install(region)
        self.title(_("战区计算器"))
        for widget in self.winfo_children():
            widget.destroy()
        self.download_data(region)
        self.gamedata = GameData(f"data/{region}")

        self.var_stage = tk.IntVar(self, value=948)
        self.var_stage_d = tk.StringVar(self, _("第9期 核心8"))
        self.var_gun = tk.IntVar(self, value=30)
        self.var_gun.trace_add("write", partial(var_min_max, self.var_gun, 0, 999))
        self.var_fairy = tk.IntVar(self, value=4)
        self.var_fairy.trace_add("write", partial(var_min_max, self.var_fairy, 0, 4))
        self.var_upgrade = tk.IntVar(self, value=0)
        self.var_upgrade.trace_add(
            "write", partial(var_min_max, self.var_upgrade, 0, 100)
        )
        self.var_perfect = tk.BooleanVar(self, value=False)
        self.var_encoding = tk.StringVar(self, value=locale.getdefaultlocale()[-1])

        frm_control_panel = tk.Frame(self)
        frm_control_panel.grid_columnconfigure(0, weight=100, minsize=100)
        frm_control_panel.grid_columnconfigure(1, weight=160, minsize=160)
        tk.Label(frm_control_panel, text=_("服务器切换")).grid(row=0, column=0)
        frm_btns = tk.Frame(frm_control_panel)
        frm_btns.grid(row=0, column=1, sticky="we")
        frm_btns.grid_columnconfigure(0, weight=1)
        opt_region = tk.OptionMenu(
            frm_btns,
            tk.StringVar(self, value=region),
            *["ch", "tw", "kr", "us", "jp"],
            command=lambda r: self.setup(r),
        )
        opt_region.config(relief="groove", indicatoron=False)
        opt_region.grid(row=0, column=0, sticky="we")
        tk.Button(
            frm_btns,
            text=_("  更新数据  "),
            command=lambda region=region: Thread(
                target=self.download_data, args=(region, True)
            ).start(),
        ).grid(row=0, column=1, sticky="we")

        tk.Label(frm_control_panel, text=_("关卡选择")).grid(row=1, column=0)
        self.setup_stage_menu(frm_control_panel).grid(row=1, column=1, sticky="we")

        tk.Label(frm_control_panel, text=_("人形数量")).grid(row=2, column=0)
        tk.Entry(frm_control_panel, textvariable=self.var_gun).grid(
            row=2, column=1, sticky="we"
        )

        tk.Label(frm_control_panel, text=_("妖精数量")).grid(row=3, column=0)
        tk.Entry(frm_control_panel, textvariable=self.var_fairy).grid(
            row=3, column=1, sticky="we"
        )

        tk.Label(frm_control_panel, text=_("强化资源")).grid(row=4, column=0)
        self.ent_upgrade = tk.Entry(frm_control_panel, textvariable=self.var_upgrade)
        self.ent_upgrade.grid(row=4, column=1, sticky="we")

        frm_control_panel.grid_rowconfigure(5, weight=0, minsize=40)
        tk.Checkbutton(
            frm_control_panel, text=_("完美配置"), variable=self.var_perfect
        ).grid(row=5, column=0)

        self.frm_upload = tk.Frame(frm_control_panel)
        self.frm_upload.grid_columnconfigure(0, weight=1)
        self.frm_upload.grid(row=5, column=1, sticky="we")
        tk.Button(self.frm_upload, text=_("导入"), command=self.read_file).grid(
            row=0, column=0
        )
        tk.Label(self.frm_upload, text=_("编码")).grid(row=0, column=1)
        tk.Entry(self.frm_upload, textvariable=self.var_encoding, width=8).grid(
            row=0, column=2
        )
        self.lbl_upload_status = tk.Label(self.frm_upload, text="      ", width=4)
        self.lbl_upload_status.grid(row=0, column=3)

        self.btn_calculate = tk.Button(
            frm_control_panel,
            text=_("开始计算"),
            command=lambda: Thread(target=self.execute).start(),
            state="disabled",
        )
        self.btn_calculate.grid(row=7, column=0, columnspan=2, sticky="we")

        self.var_perfect.trace_add("write", lambda *_: self.switch_perfect())

        equip_table_bar = ttk.Scrollbar(self, orient="vertical")
        equip_table = ttk.Treeview(self, yscrollcommand=equip_table_bar.set)
        equip_table_bar.config(command=equip_table.yview)

        column_cfg = {
            "name": {"text": _("装备"), "width": 120},
            "rank": {"text": _("星级"), "width": 40},
            "count": {"text": _("数量"), "width": 40},
        }
        equip_table["columns"] = list(column_cfg.keys())
        equip_table.column("#0", width=0, stretch=tk.NO)
        equip_table.heading("#0", text="", anchor=tk.CENTER)
        for k, v in column_cfg.items():
            equip_table.column(k, anchor="e", width=v["width"])
            equip_table.heading(
                k,
                text=v["text"],
                anchor="e",
                command=partial(treeview_sort_column, equip_table, k, False),
            )
        equip_table.tag_configure("oddrow", background="#dddddd")

        gun_table_bar = ttk.Scrollbar(self, orient="vertical")
        gun_table = ttk.Treeview(self, yscrollcommand=gun_table_bar.set)
        gun_table_bar.config(command=gun_table.yview)

        column_cfg = {
            "type": {"text": _("枪种"), "width": 40},
            "idx": {"text": _("编号"), "width": 60},
            "name": {"text": _("人形"), "width": 120},
            "score": {"text": _("得分"), "width": 40},
            "level": {"text": _("等级"), "width": 40},
            "rank": {"text": _("星级"), "width": 40},
            "favor": {"text": _("好感"), "width": 40},
            "skill1": {"text": _("技能1"), "width": 40},
            "skill2": {"text": _("技能2"), "width": 40},
            "equip1": {"text": _("装备1"), "width": 120},
            "elv1": {"text": _("装等1"), "width": 40},
            "equip2": {"text": _("装备2"), "width": 120},
            "elv2": {"text": _("装等2"), "width": 40},
            "equip3": {"text": _("装备3"), "width": 120},
            "elv3": {"text": _("装等3"), "width": 40},
        }
        gun_table["columns"] = list(column_cfg.keys())
        gun_table.column("#0", width=0, stretch=tk.NO)
        gun_table.heading("#0", text="", anchor=tk.CENTER)
        for k, v in column_cfg.items():
            gun_table.column(k, anchor="e", width=v["width"])
            gun_table.heading(
                k,
                text=v["text"],
                anchor="e",
                command=partial(treeview_sort_column, gun_table, k, False),
            )
        gun_table.tag_configure("oddrow", background="#dddddd")

        gun_table_bar.pack(padx=5, pady=5, fill="y", side="right")
        gun_table.pack(padx=5, pady=5, fill="both", side="right", expand=True)
        frm_control_panel.pack(padx=5, pady=5, side="top", fill="x")
        equip_table_bar.pack(fill="y", side="right")
        equip_table.pack(padx=5, pady=5, fill="both", expand=True)

        self.gun_table = gun_table
        self.equip_table = equip_table

    @locked
    def download_data(self, region="ch", re_download=False):
        data_dir = Path(__file__).resolve().parent / f"data/{region}"
        tmp_dir = Path(__file__).resolve().parent / f"data/tmp"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(tmp_dir)
        try:
            for table in ["gun", "equip", "theater_area"]:
                self.title(_("战区计算器") + _(" - 正在下载") + f"{table}.json")
                url = f"https://github.com/gf-data-tools/gf-data-{region}/raw/main/formatted/json/{table}.json"
                if not (data_dir / f"{table}.json").exists() or re_download:
                    download(url, str(tmp_dir / f"{table}.json"))
                    os.rename(tmp_dir / f"{table}.json", data_dir / f"{table}.json")
        except Exception as e:
            showerror(
                title=_("下载数据失败"),
                message=_("下载 {} 失败").format(url) + f"\n{e.__class__.__name__}: {e}",
            )
        else:
            if re_download:
                showinfo(title=_("完成下载"), message="数据已更新")
            self.gamedata = GameData(data_dir)
        finally:
            self.title(_("战区计算器"))

    def setup_stage_menu(self, master=None) -> tk.Menubutton:
        stage_dict = DefaultDict(dict)
        difficulty = {"1": _("初级"), "2": _("中级"), "3": _("高级"), "4": _("核心")}
        for idx, area in self.gamedata["theater_area"].items():
            if area["boss"]:
                a, b, c = str(idx)
                d = difficulty[b]
                stage_dict[_("第{}期").format(a)][_("第{}期 {}{}").format(a, d, c)] = idx

        opt_stage = tk.Menubutton(
            master, textvariable=self.var_stage_d, relief="groove"
        )
        opt_stage.config(
            menu=menu_from_dict(opt_stage, stage_dict, self.var_stage_d, self.var_stage)
        )
        return opt_stage

    def read_file(self):
        try:
            fname = askopenfilename(filetypes=[("JSON", "*.json")])
            if fname:
                self.user_data = json.load(
                    Path(fname).open("r", encoding=self.var_encoding.get())
                )
                self.lbl_upload_status.config(text=_("完成"), fg="green")
                self.btn_calculate.config(state="normal")
        except Exception as e:
            self.lbl_upload_status.config(text=_("失败"), fg="red")
            self.btn_calculate.config(state="disabled")
            showerror(title=_("读取用户信息失败"), message=f"{e.__class__.__name__}: {e}")

    def switch_perfect(self):
        if self.var_perfect.get():
            self.frm_upload.grid_forget()
            self.btn_calculate.config(state="normal")
            self.ent_upgrade.config(state="disabled")
        else:
            self.frm_upload.grid(row=5, column=1, sticky="we")
            self.btn_calculate.config(state="disabled")
            self.ent_upgrade.config(state="normal")
            self.lbl_upload_status.config(text=_(""), fg="green")

    @locked
    def execute(self):
        self.title(_("战区计算器") + _(" - 计算中"))
        # prepare data
        game_data = self.gamedata
        for item in self.gun_table.get_children():
            self.gun_table.delete(item)
        for item in self.equip_table.get_children():
            self.equip_table.delete(item)

        theater_id = self.var_stage.get()
        fairy_ratio = 1 + self.var_fairy.get() / 4
        max_dolls = self.var_gun.get()
        upgrade_resource = self.var_upgrade.get()
        use_perfect = self.var_perfect.get()
        if use_perfect:
            upgrade_resource = 999

        gun_info, equip_info = game_data["gun"], game_data["equip"]
        if use_perfect:
            user_gun, user_equip = load_perfect_info(game_data)
        else:
            user_gun, user_equip = load_user_info(self.user_data, game_data)
        choices = prepare_choices(
            user_gun, user_equip, theater_id, max_dolls, fairy_ratio, game_data
        )

        # optimization
        resource = {}
        for id, item in user_gun.items():
            resource[f"g_{id}"] = 1
        for eid, equip in user_equip.items():
            resource[f"e{eid}_10"] = equip["level_10"]
            resource[f"e{eid}_0"] = equip["level_00"]
        resource["count"] = max_dolls
        resource["score"] = 0
        resource["upgrade"] = upgrade_resource
        lp_vars = {}
        coeff_lp_var_dict = DefaultDict(list)
        problem = lp.LpProblem("battlefield", lp.LpMaximize)
        for k, recipe in choices.items():
            lp_vars[k] = lp.LpVariable(k, cat=lp.LpInteger, lowBound=0)
            for r, c in recipe["content"].items():
                # build a dict with value as lists of (coefficient, LpVar) tuples before building LpAffineExpression in bulk
                # else doing += coefficient*LpVar would trigger significantly amount of costly LpAffineExpression.__init__ call
                coeff_lp_var_dict[r].append((lp_vars[k], c))
        for k, v in coeff_lp_var_dict.items():
            resource[k] += lp.LpAffineExpression(v)
        for k, v in resource.items():
            problem += v >= 0, k
        problem += resource["score"] + 0.001 * resource["upgrade"]

        lp_bin: Path = (
            Path(__file__).resolve().parent
            / "solverdir"
            / "cbc"
            / lp.operating_system
            / lp.arch
            / lp.LpSolver_CMD.executableExtension("cbc")
        )
        problem.solve(lp.COIN_CMD(msg=0, path=str(lp_bin)))

        u_info, g_info = [], []
        for k, v in lp_vars.items():
            if v.value() > 0:
                if k[0] == "u":
                    u_info.append([choices[k]["info"], v])
                else:
                    g_info.append([choices[k]["info"], v])

        # analyze result
        equip_counter = DefaultDict(int)
        for i, (info, v) in enumerate(g_info):
            record = {
                "type": ["HG", "SMG", "RF", "AR", "MG", "SG"][
                    gun_info[info["gid"]]["type"] - 1
                ],
                "idx": info["gid"],
                "name": gun_info[info["gid"]]["name"],
                "score": info["score"],
                "level": user_gun[info["gid"] % 20000]["gun_level"],
                "rank": gun_info[info["gid"]]["rank_display"],
                "favor": user_gun[info["gid"] % 20000]["favor"],
                "skill1": user_gun[info["gid"] % 20000]["skill1"],
                "skill2": user_gun[info["gid"] % 20000]["skill2"],
                "equip1": equip_info[info[f"eid_1"]]["name"],
                "elv1": info[f"elv_1"],
                "equip2": equip_info[info[f"eid_2"]]["name"],
                "elv2": info[f"elv_2"],
                "equip3": equip_info[info[f"eid_3"]]["name"],
                "elv3": info[f"elv_3"],
            }
            self.gun_table.insert(
                "",
                "end",
                values=[str(v) for v in record.values()],
                tags=("oddrow" if i % 2 else "evenrow"),
            )
            for i in range(1, 4):
                equip_counter[info[f"eid_{i}"]] += 1

        if not use_perfect:
            self.equip_table.heading("count", text="强化")
            for i, (info, v) in enumerate(u_info):
                record = {
                    "name": equip_info[info["eid"]]["name"],
                    "rank": 6
                    if equip_info[info[f"eid"]]["type"] in [18, 19, 20]
                    else equip_info[info["eid"]]["rank"],
                    "count": int(v.value()),
                }
                self.equip_table.insert(
                    "",
                    "end",
                    values=[str(v) for v in record.values()],
                    tags=("oddrow" if i % 2 else "evenrow"),
                )
        else:
            self.equip_table.heading("count", text="数量")
            for i, (eid, count) in enumerate(equip_counter.items()):
                record = {
                    "name": equip_info[eid]["name"],
                    "rank": 6
                    if equip_info[eid]["type"] in [18, 19, 20]
                    else equip_info[eid]["rank"],
                    "count": count,
                }
                self.equip_table.insert(
                    "",
                    "end",
                    values=[str(v) for v in record.values()],
                    tags=("oddrow" if i % 2 else "evenrow"),
                )


if __name__ == "__main__":
    window = TheaterCommander()
    window.mainloop()
