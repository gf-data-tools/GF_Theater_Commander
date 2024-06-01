import json
import locale
import logging
import os
import shutil
import socket
import tkinter as tk
import tkinter.ttk as ttk
from base64 import standard_b64decode, standard_b64encode
from functools import partial, wraps
from gettext import install
from multiprocessing.pool import ThreadPool
from pathlib import Path
from threading import RLock, Thread
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showerror, showinfo
from tkinter.scrolledtext import ScrolledText
from tkinter.simpledialog import Dialog
from typing import *
from urllib import request
from urllib.error import HTTPError

import pulp as lp
from gf_utils2.gamedata import GameData

from commander_new.commander import Commander
from gunframe import GunFrame

logger = logging.getLogger(__name__)


def download(url, path, max_retry=3, timeout_sec=5):
    socket.setdefaulttimeout(timeout_sec)
    fname = os.path.split(path)[-1]
    logger.info(f"Start downloading {fname}")
    for i in range(max_retry):
        try:
            if not os.path.exists(path):
                request.urlretrieve(url, path + ".tmp")
                os.rename(path + ".tmp", path)
        except Exception as e:
            if i + 1 < max_retry:
                logger.warning(
                    f"Failed to download {fname} for {i+1}/{max_retry} tries"
                )
                continue
            else:
                logger.exception(repr(e))
                raise
        else:
            logger.info(f"Successfully downloaded {fname}")
            break
    return path


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
    def wrapped(self: "TheaterCommander", *args, **kwargs):
        if self.lock.acquire(timeout=0.01):
            self.lock.release()
            with self.lock:
                func(self, *args, **kwargs)
        else:
            print("action ignored")

    return wrapped


class TheaterCommander(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = RLock()
        self.setup()
        self.user_data = None
        self.g_records = None
        self.u_records = None

    def setup(self, region="ch"):
        install(region)
        self.title(_("战区计算器"))
        for widget in self.winfo_children():
            widget.destroy()
        self.download_data(region)

        self.var_stage = tk.IntVar(self, value=1048)
        self.var_stage_d = tk.StringVar(self, _("第10期 核心8"))
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
        self.equip_column = column_cfg
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

        gun_table = ttk.Frame(self)
        self.lbl_total_score = tk.Label(
            master=gun_table, text=_("总效能：") + f"{0:>6}", anchor="w", justify="left"
        )
        self.lbl_total_score.grid(row=0, column=0, sticky="w")

        self.lbl_assist = tk.Label(
            master=gun_table, text=_(""), anchor="w", justify="left"
        )
        self.lbl_assist.grid(row=0, column=1, columnspan=2, sticky="w")

        sort_box = tk.Frame(gun_table)
        sort_box.grid(row=0, column=4, sticky="e")
        tk.Label(sort_box, text=_("排序")).pack(side="left")
        opt_sort_by = tk.OptionMenu(
            sort_box,
            tk.StringVar(self, value="枪种"),
            *["枪种", "等级", "星级", "编号", "效能", "好感"],
            command=self.update_gun_frame,
        )
        opt_sort_by.config(relief="groove", indicatoron=False)
        opt_sort_by.pack(side="left")
        tk.Button(sort_box, text=_("配队码"), command=self.export).pack(side="left")

        self.gun_frame: list[GunFrame] = []

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
        os.makedirs(tmp_dir)
        (data_dir / "stc").mkdir(parents=True, exist_ok=True)
        (data_dir / "table").mkdir(parents=True, exist_ok=True)
        try:
            pool = ThreadPool(processes=24)
            stc_names = [
                'equip', 'game_config_info', 'gun', 'gun_type_info', 'sangvis', 
                'sangvis_advance', 'sangvis_character_type', 'sangvis_resolution', 
                'sangvis_type', 'squad', 'squad_advanced_bonus', 'squad_chip', 
                'squad_chip_exp', 'squad_color', 'squad_cpu', 'squad_cpu_completion', 
                'squad_data_daily', 'squad_exp', 'squad_grid', 'squad_in_ally', 
                'squad_rank', 'squad_standard_attribution', 'squad_type', 
                'theater_area'
            ]  # fmt: skip
            txt_names = [
                "equip",
                "gun",
                "sangvis",
                "sangvis_character_type",
                "squad",
                "squad_chip",
                "squad_color",
                "squad_data_daily",
                "squad_type",
                "theater_area",
            ]

            task_params = []
            base_url = f"https://github.com/gf-data-tools/gf-data-{region}/raw/main"

            for table in stc_names:
                if table.endswith("info"):
                    url = f"{base_url}/catchdata/{table}.json"
                else:
                    url = f"{base_url}/stc/{table}.json"
                tmp_path = tmp_dir / f"{table}.json"
                tgt_path = data_dir / f"stc/{table}.json"
                task_params.append((url, tmp_path, tgt_path))

            for table in txt_names:
                url = f"{base_url}/asset/table/{table}.txt"
                tmp_path = tmp_dir / f"{table}.txt"
                tgt_path = data_dir / f"table/{table}.txt"
                task_params.append((url, tmp_path, tgt_path))

            cnt = 0
            tot = len(stc_names) + len(txt_names)
            self.title(_("战区计算器") + _(" - 更新数据") + f"({cnt}/{tot})")

            def update(url, tmp_path, tgt_path):
                try:
                    if not tgt_path.exists() or re_download:
                        download(url, str(tmp_path))
                        if tgt_path.exists():
                            os.remove(tgt_path)
                        tmp_path.rename(tgt_path)
                    return url, None
                except Exception as e:
                    return url, e

            for url, ret in pool.imap_unordered(lambda p: update(*p), task_params):
                if isinstance(ret, Exception):
                    raise ret
                cnt += 1
                self.title(_("战区计算器") + _(" - 更新数据") + f"({cnt}/{tot})")

        except Exception as e:
            showerror(
                title=_("下载数据失败"),
                message=_("下载 {} 失败").format(url) + f"\n{repr(e)}",
            )
            raise
        else:
            if re_download:
                showinfo(title=_("完成下载"), message="数据已更新")
            self.gamedata = GameData(data_dir / "stc", data_dir / "table")
            print(list(self.gamedata.keys()))
        finally:
            self.title(_("战区计算器"))
            if re_download:
                self.setup()

    def setup_stage_menu(self, master=None) -> tk.Menubutton:
        stage_dict = DefaultDict(dict)
        difficulty = {"1": _("初级"), "2": _("中级"), "3": _("高级"), "4": _("核心")}
        for idx, area in self.gamedata["theater_area"].items():
            if area["boss"]:
                i = str(idx)
                a, b, c = i[:-2], i[-2], i[-1]
                d = difficulty[b]
                stage_dict[_("第{}期").format(a)][
                    _("第{}期 {}{}").format(a, d, c)
                ] = idx

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
            showerror(
                title=_("读取用户信息失败"), message=f"{e.__class__.__name__}: {e}"
            )

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

    def update_gun_frame(self, sort_by: str = "枪种"):
        sort_dict = {
            "枪种": "tyep_id",
            "编号": "idx",
            "效能": "score",
            "等级": "level",
            "星级": "rank",
            "好感": "favor",
        }
        match sort_dict[sort_by]:
            case "default" | "tyep_id":
                self.g_records.sort(
                    key=lambda r: (-r["type_id"], r["level"], r["rank"], r["idx"]),
                    reverse=True,
                )
            case _:
                self.g_records.sort(key=lambda r: (r[sort_dict[sort_by]]), reverse=True)

        for frame in self.gun_frame:
            frame.destroy()

        self.gun_frame = []
        for i, record in enumerate(self.g_records):
            frame = GunFrame(master=self.gun_table)
            frame.update(record)
            frame.grid(row=i // 5 + 1, column=i % 5)
            self.gun_frame.append(frame)

        for item in self.equip_table.get_children():
            self.equip_table.delete(item)
        self.u_records.sort(key=lambda r: (r["rank"], -r["count"]))
        for i, record in enumerate(self.u_records):
            self.equip_table.insert(
                "",
                "end",
                values=[str(record[k]) for k in self.equip_column],
                tags=("oddrow" if i % 2 else "evenrow"),
            )

    @locked
    def execute(self):
        self.title(_("战区计算器") + _(" - 计算中"))

        lp_bin: Path = (
            Path(__file__).resolve().parent
            / "solverdir"
            / "cbc"
            / lp.operating_system
            / lp.arch
            / lp.LpSolver_CMD.executableExtension("cbc")
        )
        solver = lp.COIN_CMD(msg=0, path=str(lp_bin))

        commander = Commander(self.gamedata, solver, self.user_data)

        self.assist_units = (
            []
            # if self.var_perfect.get()
            # else commander.get_assist_unit(self.var_stage.get())
        )
        self.g_records, self.u_records = commander.solve(
            theater_id=self.var_stage.get(),
            fairy_ratio=1 + self.var_fairy.get() / 4,
            max_dolls=self.var_gun.get(),
            upgrade_resource=self.var_upgrade.get(),
            use_perfect=self.var_perfect.get(),
        )

        # analyze result
        total_score = (
            0
            + sum([r["score"] for r in self.g_records])
            # + sum([i[1] for i in self.assist_units])
        )
        self.lbl_total_score.config(text=_("总效能：") + f"{total_score:>6}")
        self.lbl_assist.config(
            text=" ".join(f"{name}({score})" for name, score, _ in self.assist_units)
        )
        self.update_gun_frame()
        self.title(_("战区计算器"))
        print(list(commander.game_data._GameData__data.keys()))

    def export(self):
        top = tk.Toplevel(self)
        top.title("配队码")
        text = ScrolledText(top, width=150, height=8, font=("Consolas", 10))
        text.pack(expand=True, fill="both")
        print("export")
        pos = [7, 8, 9, 12, 13]

        for i in range(0, len(self.g_records), 5):
            gun_codes = ["0-0-0-0-0"] * 5
            for j, record in enumerate(self.g_records[i : i + 5]):
                gun_codes[j] = (
                    f"{record['idx']}-{pos[j%5]}-{record['eid1']}-{record['eid2']}-{record['eid3']}"
                )
            code = "1|" + ";".join(gun_codes) + "|0"
            code = standard_b64encode(code.encode()).decode()
            print(code)
            text.insert("end", code + "\n")
        text.configure(state="disabled")  # 设置为不可编辑状态


if __name__ == "__main__":
    window = TheaterCommander()
    window.mainloop()
