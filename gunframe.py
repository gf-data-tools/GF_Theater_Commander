import tkinter as tk

rank_color = {
    1: "magenta",
    2: "black",
    3: "blue",
    4: "green",
    5: "#B8860B",
    6: "red",
    7: "magenta",
}


class GunFrame(tk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(relief="groove", borderwidth="1p", *args, **kwargs)

        self.row = {}

        # row 1
        self.row[1] = tk.Frame(self)
        self.row[1].pack(anchor="w")

        self.var_level = tk.StringVar()
        self.lbl_level = tk.Label(
            self.row[1], textvariable=self.var_level, width=5, anchor="e"
        )
        self.lbl_level.pack(side="left")

        self.var_type = tk.StringVar()
        self.lbl_type = tk.Label(
            self.row[1], textvariable=self.var_type, width=4, anchor="w"
        )
        self.lbl_type.pack(side="left")

        self.var_name = tk.StringVar()
        self.lbl_name = tk.Label(
            self.row[1], textvariable=self.var_name, width=15, anchor="c"
        )
        self.lbl_name.pack(side="left")

        # row 2
        self.row[2] = tk.Frame(self)
        self.row[2].pack(anchor="w")

        self.var_favor = tk.StringVar()
        self.lbl_favor = tk.Label(
            self.row[2], textvariable=self.var_favor, width=5, anchor="e"
        )
        self.lbl_favor.pack(side="left")

        self.lbl_slv = tk.Label(self.row[2], text="", width=5, anchor="e")
        self.lbl_slv.pack(side="left")

        self.var_slv1 = tk.StringVar()
        self.lbl_slv1 = tk.Label(
            self.row[2], textvariable=self.var_slv1, width=2, anchor="e"
        )
        self.lbl_slv1.pack(side="left")

        self.lbl_slvslash = tk.Label(self.row[2], text="", width=1)
        self.lbl_slvslash.pack(side="left")

        self.var_slv2 = tk.StringVar()
        self.lbl_slv2 = tk.Label(
            self.row[2], textvariable=self.var_slv2, width=3, anchor="w"
        )
        self.lbl_slv2.pack(side="left")

        self.var_score = tk.StringVar()
        self.lbl_score = tk.Label(
            self.row[2], textvariable=self.var_score, width=5, anchor="w"
        )
        self.lbl_score.pack(side="left")

        self.var_equip = {}
        self.var_elv = {}
        self.lbl_equip = {}
        self.lbl_elv = {}
        for i in range(1, 4):
            self.row[i + 2] = tk.Frame(self)
            self.row[i + 2].pack(anchor="w")
            self.var_equip[i] = tk.StringVar()
            self.lbl_equip[i] = tk.Label(
                self.row[i + 2], textvariable=self.var_equip[i], width=19, anchor="e"
            )
            self.lbl_equip[i].pack(side="left")

            self.var_elv[i] = tk.StringVar()
            self.lbl_elv[i] = tk.Label(
                self.row[i + 2], textvariable=self.var_elv[i], width=5, anchor="e"
            )
            self.lbl_elv[i].pack(side="left")

    def update(self, g_records) -> None:
        self.lbl_slv.config(text="SLv")
        self.lbl_slvslash.config(text="/")

        self.var_name.set(g_records["name"])
        self.lbl_name.config(foreground=rank_color[g_records["rank"]])
        self.var_type.set(g_records["type"])

        self.var_favor.set(f"\u2665 {g_records['favor']:>3}")
        self.lbl_favor.config(
            foreground="magenta" if g_records["favor"] <= 100 else "red"
        )

        self.var_level.set(f"Lv{g_records['level']:>3}")
        self.lbl_level.config(foreground=rank_color[(g_records["level"] + 19) // 20])

        self.var_slv1.set(f"{g_records['skill1']:>2}")
        self.lbl_slv1.config(foreground=rank_color[(g_records["skill1"] + 8) // 3])
        self.var_slv2.set(f"{g_records['skill2']:>2}")
        self.lbl_slv2.config(foreground=rank_color[(g_records["skill2"] + 8) // 3])

        self.var_score.set(f"{g_records['score']:>5}")

        for i in range(1, 4):
            self.var_equip[i].set(g_records[f"equip{i}"])
            self.lbl_equip[i].config(foreground=rank_color[g_records[f"erank{i}"]])
            self.var_elv[i].set(f'Lv{g_records[f"elv{i}"]:>2}')
            self.lbl_elv[i].config(
                foreground=rank_color[(g_records[f"elv{i}"] + 8) // 3]
            )

    def reset(self):
        for attr in self.__dict__:
            if attr.startswith("var_"):
                a = getattr(self, attr)
                if isinstance(a, dict):
                    for v in a.values():
                        v.set("")
                else:
                    a.set("")
        self.lbl_slv.config(text="")
        self.lbl_slvslash.config(text="")


if __name__ == "__main__":
    # fmt: off
    recs = [{'type_id': 1, 'type': 'SMG', 'idx': 4, 'name': '蟒蛇', 'effect': {'day': 3898, 'night': 2832}, 'score': 2900, 'level': 100, 'rank': 3, 'favor': 100, 'skill1': 10, 'skill2': 0, 'equip1': 'RMR T4红点', 'erank1': 5, 'elv1': 10, 'equip2': '.357平头铅弹', 'erank2': 5, 'elv2': 10, 'equip3': 'IOP X4外骨骼', 'erank3': 5, 'elv3': 10}, {'type_id': 1, 'type': 'HG', 'idx': 20007, 'name': '斯捷奇金', 'effect': {'day': 4246, 'night': 3084}, 'score': 2632, 'level': 120, 'rank': 5, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'RMR T4红点', 'erank1': 5, 'elv1': 10, 'equip2': '16Lab空尖弹', 'erank2': 5, 'elv2': 10, 'equip3': '战术闪电呆毛', 'erank3': 5, 'elv3': 10}, {'type_id': 1, 'type': 'HG', 'idx': 20008, 'name': '马卡洛夫', 'effect': {'day': 4329, 'night': 3316}, 'score': 2683, 'level': 120, 'rank': 4, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': '战术握把', 'erank1': 6, 'elv1': 10, 'equip2': '9x18mm FTX', 'erank2': 5, 'elv2': 10, 'equip3': 'IOP X4外骨骼', 'erank3': 5, 'elv3': 10}, {'type_id': 1, 'type': 'HG', 'idx': 20010, 'name': 'PPK', 'effect': {'day': 4080, 'night': 3111}, 'score': 2529, 'level': 120, 'rank': 4, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'PPK消音器', 'erank1': 6, 'elv1': 10, 'equip2': '16Lab空尖弹', 'erank2': 5, 'elv2': 10, 'equip3': 'IOP X4外骨骼', 'erank3': 5, 'elv3': 10}, {'type_id': 1, 'type': 'HG', 'idx': 20012, 'name': 'C96', 'effect': {'day': 4145, 'night': 3253}, 'score': 2569, 'level': 120, 'rank': 4, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'C96橡木枪托', 'erank1': 6, 'elv1': 10, 'equip2': 'ILM空尖弹', 'erank2': 5, 'elv2': 10, 'equip3': 'IOP T4外骨骼', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 36, 'name': '春田', 'effect': {'day': 7091, 'night': 3449}, 'score': 2552, 'level': 100, 'rank': 4, 'favor': 100, 'skill1': 10, 'skill2': 0, 'equip1': '国家竞赛穿甲弹', 'erank1': 6, 'elv1': 10, 'equip2': 'VFL 6-24X56', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 20037, 'name': 'M14', 'effect': {'day': 7401, 'night': 3850}, 'score': 2664, 'level': 120, 'rank': 4, 'favor': 200, 'skill1': 10, 'skill2': 10, 'equip1': 'Mk211高爆穿甲弹', 'erank1': 5, 'elv1': 10, 'equip2': 'M2两脚架', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 20039, 'name': '莫辛-纳甘', 'effect': {'day': 7160, 'night': 3924}, 'score': 2577, 'level': 120, 'rank': 5, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'Mk211高爆穿甲弹', 'erank1': 5, 'elv1': 10, 'equip2': 'K6-24X56', 'erank2': 5, 'elv2': 10, 'equip3': 'Hayha记忆芯片', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 20046, 'name': 'Kar98k', 'effect': {'day': 8495, 'night': 4456}, 'score': 3058, 'level': 120, 'rank': 6, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'Mk211高爆穿甲弹', 'erank1': 5, 'elv1': 10, 'equip2': 'PM 5-25X56', 'erank2': 5, 'elv2': 10, 'equip3': '皇家卫队制服', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 20050, 'name': '李-恩菲尔德', 'effect': {'day': 8946, 'night': 4631}, 'score': 3220, 'level': 120, 'rank': 6, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'L42试验穿甲弹', 'erank1': 6, 'elv1': 10, 'equip2': 'No32 MKI', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 20053, 'name': 'NTW-20', 'effect': {'day': 7750, 'night': 4137}, 'score': 2790, 'level': 120, 'rank': 6, 'favor': 200, 'skill1': 10, 'skill2': 10, 'equip1': '20mm HEI', 'erank1': 6, 'elv1': 10, 'equip2': 'VFL 6-24X56', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 20095, 'name': '汉阳造88式', 'effect': {'day': 7146, 'night': 3755}, 'score': 2572, 'level': 120, 'rank': 4, 'favor': 200, 'skill1': 10, 'skill2': 10, 'equip1': '磁轨加速弹', 'erank1': 6, 'elv1': 10, 'equip2': '加速线圈', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 1, 'type': 'HG', 'idx': 20097, 'name': 'M950A', 'effect': {'day': 4419, 'night': 3245}, 'score': 2739, 'level': 120, 'rank': 6, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'WML&战术护木', 'erank1': 6, 'elv1': 10, 'equip2': '16Lab空尖弹', 'erank2': 5, 'elv2': 10, 'equip3': 'IOP X4外骨骼', 'erank3': 5, 'elv3': 10}, {'type_id': 1, 'type': 'HG', 'idx': 20114, 'name': '维尔德MkⅡ', 'effect': {'day': 4812, 'night': 3995}, 'score': 2983, 'level': 120, 'rank': 6, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'SF武器灯改', 'erank1': 5, 'elv1': 10, 'equip2': 'ILM空尖弹', 'erank2': 5, 'elv2': 10, 'equip3': '特种行动包', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 20124, 'name': 'S-SASS', 'effect': {'day': 7054, 'night': 3536}, 'score': 2539, 'level': 120, 'rank': 4, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'Mk211高爆穿甲弹', 'erank1': 5, 'elv1': 10, 'equip2': 'ACS-L', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 128, 'name': 'M99', 'effect': {'day': 6408, 'night': 3307}, 'score': 2768, 'level': 100, 'rank': 5, 'favor': 100, 'skill1': 10, 'skill2': 0, 'equip1': 'Mk211高爆穿甲弹', 'erank1': 5, 'elv1': 10, 'equip2': 'VFL 6-24X56', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 1, 'type': 'HG', 'idx': 183, 'name': '竞争者', 'effect': {'day': 4860, 'night': 3155}, 'score': 3615, 'level': 100, 'rank': 5, 'favor': 100, 'skill1': 10, 'skill2': 0, 'equip1': 'RMR T4红点', 'erank1': 5, 'elv1': 10, 'equip2': 'Mk211高爆穿甲弹', 'erank2': 5, 'elv2': 10, 'equip3': 'IOP X4外骨骼', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 20200, 'name': 'XM3', 'effect': {'day': 7761, 'night': 4275}, 'score': 2793, 'level': 120, 'rank': 5, 'favor': 200, 'skill1': 10, 'skill2': 10, 'equip1': 'M118LR', 'erank1': 6, 'elv1': 10, 'equip2': 'VFL 6-24X56', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 20201, 'name': '猎豹M1', 'effect': {'day': 6992, 'night': 3735}, 'score': 2517, 'level': 120, 'rank': 4, 'favor': 200, 'skill1': 10, 'skill2': 10, 'equip1': 'B32穿甲弹', 'erank1': 6, 'elv1': 10, 'equip2': 'VFL 6-24X56', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 1, 'type': 'HG', 'idx': 20212, 'name': 'K5', 'effect': {'day': 4101, 'night': 3204}, 'score': 2542, 'level': 115, 'rank': 5, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'RMR T4红点', 'erank1': 5, 'elv1': 10, 'equip2': '16Lab空尖弹', 'erank2': 5, 'elv2': 10, 'equip3': '大宇运动骨骼mk5', 'erank3': 5, 'elv3': 10}, {'type_id': 1, 'type': 'HG', 'idx': 20220, 'name': 'MP-443', 'effect': {'day': 4060, 'night': 3002}, 'score': 2517, 'level': 120, 'rank': 4, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'RMR T4红点', 'erank1': 5, 'elv1': 10, 'equip2': 'ILM空尖弹', 'erank2': 5, 'elv2': 10, 'equip3': 'IOP X4外骨骼', 'erank3': 5, 'elv3': 10}, {'type_id': 1, 'type': 'HG', 'idx': 20221, 'name': 'GSh-18', 'effect': {'day': 4445, 'night': 3130}, 'score': 2755, 'level': 120, 'rank': 4, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'RMR T4红点', 'erank1': 5, 'elv1': 10, 'equip2': '7n31', 'erank2': 5, 'elv2': 10, 'equip3': 'IOP X4外骨骼', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 20230, 'name': 'OBR', 'effect': {'day': 6975, 'night': 3726}, 'score': 2511, 'level': 120, 'rank': 4, 'favor': 100, 'skill1': 10, 'skill2': 10, 'equip1': 'Mk211高爆穿甲弹', 'erank1': 5, 'elv1': 10, 'equip2': 'HARRIS脚架', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 20252, 'name': 'KSVK', 'effect': {'day': 7591, 'night': 4136}, 'score': 2732, 'level': 120, 'rank': 5, 'favor': 200, 'skill1': 10, 'skill2': 10, 'equip1': '12.7mm 1SL', 'erank1': 6, 'elv1': 10, 'equip2': '16Lab6-24X56', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 1, 'type': 'HG', 'idx': 260, 'name': 'PA-15', 'effect': {'day': 4167, 'night': 2942}, 'score': 2583, 'level': 100, 'rank': 5, 'favor': 100, 'skill1': 10, 'skill2': 0, 'equip1': 'RMR T4红点', 'erank1': 5, 'elv1': 10, 'equip2': 'ILM空尖弹', 'erank2': 5, 'elv2': 10, 'equip3': 'MAB高性能运动骨骼', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 261, 'name': 'QBU-88', 'effect': {'day': 7469, 'night': 3866}, 'score': 3226, 'level': 100, 'rank': 5, 'favor': 100, 'skill1': 10, 'skill2': 0, 'equip1': 'Mk211高爆穿甲弹', 'erank1': 5, 'elv1': 10, 'equip2': '12x56CBX倍镜', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 266, 'name': 'R93', 'effect': {'day': 6957, 'night': 3689}, 'score': 3005, 'level': 100, 'rank': 5, 'favor': 100, 'skill1': 10, 'skill2': 0, 'equip1': 'Mk211高爆穿甲弹', 'erank1': 5, 'elv1': 10, 'equip2': 'VFL 6-24X56', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 1, 'type': 'HG', 'idx': 272, 'name': '沙漠之鹰', 'effect': {'day': 3803, 'night': 2615}, 'score': 2829, 'level': 100, 'rank': 5, 'favor': 100, 'skill1': 10, 'skill2': 0, 'equip1': 'RMR T4红点', 'erank1': 5, 'elv1': 10, 'equip2': 'ILM空尖弹', 'erank2': 5, 'elv2': 10, 'equip3': 'IOP X4外骨骼', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 316, 'name': '刘氏步枪', 'effect': {'day': 7103, 'night': 3609}, 'score': 2557, 'level': 100, 'rank': 5, 'favor': 100, 'skill1': 10, 'skill2': 0, 'equip1': 'Mk211高爆穿甲弹', 'erank1': 5, 'elv1': 10, 'equip2': 'VFL 6-24X56', 'erank2': 5, 'elv2': 10, 'equip3': '热光学迷彩披风', 'erank3': 5, 'elv3': 10}, {'type_id': 3, 'type': 'RF', 'idx': 1031, 'name': '佩可拉', 'effect': {'day': 6968, 'night': 3580}, 'score': 2508, 'level': 100, 'rank': 7, 'favor': 100, 'skill1': 10, 'skill2': 0, 'equip1': 'Mk211高爆穿甲弹', 'erank1': 5, 'elv1': 10, 'equip2': '16Lab6-24X56', 'erank2': 5, 'elv2': 10, 'equip3': '美梦多纳滋', 'erank3': 5, 'elv3': 10}]
    # fmt: on
    win = tk.Tk()
    # win.option_add("*font", "simsun 0 bold")
    for i, rec in enumerate(recs):
        gf = GunFrame(master=win)
        gf.update(rec)
        gf.grid(row=i // 5, column=i % 5, sticky="wsne", padx="1p", pady="1p")
    win.mainloop()
