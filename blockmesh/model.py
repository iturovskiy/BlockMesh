from progress.bar import IncrementalBar
import blockmesh.node as node
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import networkx as nx
import numpy as np
import ast
import json
import csv
import os

STG_DIR = r'Storages'
USR_DIR = r'Users'
MODEL_F = r'MODEL'
RESULT_F = r'RESULT.csv'
USR_NODE = r'usr_'
STG_NODE = r'stg_'
GRAPH_PIC = r'graph_'
PLOT_PIC = r'plot_'


def div_up(a: int, b: int) -> int:
    return 1 + ((a - 1) // b)


def mod_up(a: int, b: int) -> int:
    return 1 + ((a - 1) % b)


class ModelTime:
    """
    Класс реализующий функционал модельного-времени и таймсервера
    """

    def __init__(self, start_time: int = 1, step: int = 1):
        """
        :param start_time: начальное время
        :param step: шаг времени
        """
        if start_time < 1:
            raise ValueError("Start time must be > 0")
        if step < 1:
            raise ValueError("Step must be > 0")
        self.time = start_time
        self.step = step

    def dumps(self):
        return json.dumps({"time": self.time, "step": self.step})

    @staticmethod
    def loads(data):
        if not data:
            return ModelTime()
        data = json.loads(data)
        return ModelTime(data["time"], data["step"])

    def tick(self, mul: int = 1):
        """
        Увеличить время
        :type mul: мультипликтор
        """
        if mul < 0:
            raise ValueError("Multiplier must be >= 0")
        self.time += self.step * mul


class Model:
    """
    Класс реализующий функионал модели протокола блокмеш
    """

    def __init__(self, mod: node.Mod, path_to_dir: str, stg_num: int, usr_num: int,
                 duration_1: int, duration_2: int):
        """
        :param path_to_dir:
        :param stg_num:
        :param usr_num:
        :param duration_1:
        :param duration_2:
        """
        if mod != node.Mod.Classic and mod != node.Mod.Modified:
            raise ValueError(f"Unknown mod: {mod.name}")
        if stg_num < 1 or usr_num < 1:
            raise ValueError(f"Wrong number: {stg_num} > 0. {usr_num} > 0")
        if duration_1 < 1 or duration_2 > duration_1:
            raise ValueError(f"Wrong durations: d1: {duration_1} > 0. d2: {duration_2} <= d1: {duration_1}")
        self.mod = mod
        self.path = node.mkdir(path_to_dir)
        self.duration = [duration_1, duration_2]
        self.stg_num = stg_num
        self.usr_num = usr_num
        self.stgs = []
        self.usrs = []
        self.model_time = None
        self.performed = 0

    def init(self, ts=None):
        self.model_time = ts if ts else ModelTime()
        self.stgs = [node.Storage(self.mod, os.path.join(self.path, STG_DIR, f"{STG_NODE}{i}"),
                                  self.model_time) for i in range(self.stg_num)]
        for i in range(len(self.stgs) - 1):
            self.stgs[i + 1].join_bm(self.stgs[i])
        self.usrs = [node.User(self.mod, os.path.join(self.path, USR_DIR, f"{USR_NODE}{i}"),
                               f"user{i}", f"sign{i}", self.stgs[i % self.stg_num]) for i in range(self.usr_num)]

    def save(self):
        for s in self.stgs:
            s.save()
        for u in self.usrs:
            u.save()
        with open(os.path.join(self.path, MODEL_F), 'w') as out:
            json.dump({"mod": self.mod.name,
                       "num": [self.stg_num, self.usr_num],
                       "dur": self.duration,
                       "ts": self.model_time.dumps() if self.model_time else None,
                       "perf": self.performed}, out)

    @staticmethod
    def load(path_to_dir):
        path_to_dir = os.path.abspath(path_to_dir)
        if path_to_dir is None:
            raise NotADirectoryError(f"Could not load Model: {path_to_dir} does not exist")
        model = None
        with open(os.path.join(path_to_dir, MODEL_F), "r") as file:
            data = json.load(file)
            model = Model(node.Mod[data["mod"]], path_to_dir, data['num'][0], data['num'][1],
                          data['dur'][0], data['dur'][1])
            model.model_time = ModelTime.loads(data['ts'])
            model.performed = data['perf']
        bar_s = IncrementalBar('Load storages', max=model.stg_num)
        stg = node.Storage.load(os.path.join(path_to_dir, STG_DIR, f"{STG_NODE}0"), model.model_time)
        model.stgs.append(stg)
        bar_s.next()
        for i in range(1, model.stg_num):
            stg = node.Storage.load(os.path.join(path_to_dir, STG_DIR, f"{STG_NODE}{i}"), model.model_time)
            model.stgs.append(stg)
            model.stgs[i].join_bm(model.stgs[i - 1])
            bar_s.next()
        bar_s.finish()
        bar_u = IncrementalBar('Load users\t', max=model.usr_num)
        for i in range(model.usr_num):
            model.usrs.append(node.User.load(os.path.join(path_to_dir, USR_DIR, f"{USR_NODE}{i}"),
                                             model.stgs[i % model.stg_num]))
            bar_u.next()
        bar_u.finish()
        return model

    def run(self):
        header = list(self.get_stat().keys())
        usrs = [u for u in range(self.usr_num)]
        scale = self.usr_num * (self.usr_num - 1)
        scenario = {u: [x for i, x in enumerate(usrs) if i != u] for u in usrs}
        cur = self.stgs[0].block_count
        bar = IncrementalBar('Blocks in blockmesh', max=scale+cur)
        bar.next(cur)
        with open(os.path.join(self.path, RESULT_F), 'a', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, header)
            if self.performed == 0:
                writer.writeheader()
                writer.writerow(self.get_stat())
            while scenario or sum([stg.queue_len() for stg in self.stgs]) > 0:
                self.__usr_step(scenario)
                self.__stg_step()
                self.performed += 1
                writer.writerow(self.get_stat())
                bar.next(self.stgs[0].block_count - cur)
                cur = self.stgs[0].block_count
        bar.finish()

    def draw_graph(self):
        edges, pos, q = self.__graph()
        fig, ax = plt.subplots(figsize=(16, 9))
        g = nx.DiGraph()
        g.add_edges_from(edges)
        node_list = list(pos.keys())
        pos.update({i: (i + 1, 0) for i in range(self.performed)})
        nx.draw(g, pos, ax=ax, with_labels=True)
        nx.draw_networkx_edges(g, ax=ax, pos=pos, edgelist=q, width=1.2, edge_color='r')
        nx.draw_networkx_nodes(g, ax=ax, pos=pos, nodelist=node_list)
        nx.draw_networkx_labels(g, pos, labels={k: k for k in node_list})
        fig.savefig(os.path.join(self.path, f"{GRAPH_PIC}{self.performed}.png"), dpi=300)

    def draw_plot(self):
        x_data = []
        y_data_total_bm = []
        y_data_queue = []
        y_data_added = []
        added = 0
        with open(os.path.join(self.path, RESULT_F), 'r', newline='') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                x_data.append(int(row["Performed"]))
                gbm = int(row["GlobalBM"])
                y_data_total_bm.append(gbm)
                y_data_added.append(gbm - added)
                y_data_queue.append(sum(ast.literal_eval(row["Queues"])))
                added = gbm
        if len(x_data) != self.performed + 1:
            raise RuntimeError(f"WTF: {len(x_data)} != {self.performed + 1}")
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(x_data, y_data_total_bm, '-', label="Блоков в блокмеше")
        ax.plot(x_data, y_data_queue, '-', label="Блоков отложено")
        ax.plot(x_data, y_data_added, '-', label="Блоков внедрено")
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax.set_xlim(left=0, right=(x_data[-1] if x_data else 0))
        ax.set_ylim(bottom=0, top=(y_data_total_bm[-1] if y_data_total_bm else 0))
        ax.set_xlabel("Итерация")
        ax.set_ylabel("Количество блоков")
        ax.legend(loc='upper left')
        ax.grid(which="major", linewidth=1.0)
        fig.savefig(os.path.join(self.path, f"{PLOT_PIC}{self.performed}.png"), dpi=300)

    def get_sync_count(self):
        return len(set(self.stgs[0].block_mesh.values())) if self.stg_num > 0 else 0

    def get_stat(self):
        queues = []
        queue_len = 0
        bc = {}
        for i, stg in enumerate(self.stgs):
            queues.append(stg.queue_len())
            queue_len += stg.queue_len()
            lbc = stg.block_count
            if lbc in bc:
                bc[lbc].append(i)
            else:
                bc[lbc] = [i]
        return {"Performed": self.performed,
                "Timestamp": self.model_time.time,
                "GlobalBM": max(bc),
                "LocalBM": [u.block_count for u in self.usrs],
                "Queues": queues,
                "AvgQueue": queue_len / self.stg_num}

    def __usr_step(self, scenario):
        dur = self.duration[0]
        shallow = scenario.copy()
        for sender in shallow:
            if not shallow[sender]:
                scenario.pop(sender)
            for receiver in shallow[sender]:
                if not self.__usr_perform(sender, [receiver]):
                    break
                scenario[sender].remove(receiver)
            dur -= 1
            self.model_time.tick()
        self.model_time.tick(dur)

    def __usr_perform(self, sender: int, receivers: list):
        allowed = self.usrs[sender].generation_allowed
        res = allowed is None or allowed is True
        if res:
            if sender >= len(self.usrs) or sender < 0:
                raise ValueError(f"Wrong sender {sender}")
            for recv in receivers:
                if recv == sender or recv >= len(self.usrs) or recv < 0:
                    raise ValueError(f"Wrong receiver {recv} in {receivers}")
            self.usrs[sender].perform([self.usrs[i].addr for i in receivers], {"ypos": sender,
                                                                               "info": f"{sender} -> {receivers}"})
        return res

    def __stg_step(self):
        if self.mod == node.Mod.Classic:
            for s in self.stgs:
                s.perform_step_1()
            for s in self.stgs:
                s.perform_step_2(self.performed + 1)
            self.model_time.tick(self.duration[1])
        elif self.mod == node.Mod.Modified:
            div = 3
            iterations = self.duration[1] // div
            last = self.duration[1] - (div * iterations)
            for _ in range(iterations):
                for s in self.stgs:
                    s.perform_step_1()
                for s in self.stgs:
                    s.perform_step_2(self.performed + 1)
                self.model_time.tick(div)
            self.model_time.tick(last)

    def __graph(self):
        bc = {}
        for i, stg in enumerate(self.stgs):
            lbc = stg.block_count
            if lbc in bc:
                bc[lbc].append(i)
            else:
                bc[lbc] = [i]
        i = bc[max(bc)][0]

        stg = self.stgs[i]
        edge = {}
        pos = {}
        queue = list(set(stg.block_mesh.values()))
        while queue:
            block_id = queue.pop(0)
            if block_id is None or block_id in edge or block_id == node.GENESIS_BLOCK:
                continue
            block = stg.load_block(block_id)
            queue.extend(list(set(block.parents.values())))
            edge[block_id] = list(block.parents.values())
            pos[block_id] = [block.on_iter, block.tx.data['ypos']]

        p = {hash_node[0:5]: pos[hash_node] for hash_node in pos}
        p.update({user: [self.performed + 1, idx] for idx, user in enumerate(list(self.stgs[i].block_mesh.keys()))})
        q = [(u, self.stgs[i].block_mesh[u][0:5]) for u in self.stgs[i].block_mesh]
        e = []
        for s_hash in edge:
            for r_hash in edge[s_hash]:
                if r_hash == node.GENESIS_BLOCK:
                    e.append((s_hash[0:5], "GEN"))
                    p["GEN"] = [0, len(self.usrs) // 2]
                else:
                    e.append((s_hash[0:5], r_hash[0:5]))
        return e, p, q
