import blockmesh.node as node
from progress.bar import IncrementalBar
import json
import csv
import os

STG_DIR = r'Storages'
USR_DIR = r'Users'
MODEL_F = r'MODEL'
RESULT_F = r'RESULT.csv'
USR_NODE = r'usr_'
STG_NODE = r'stg_'


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
        if mul < 1:
            raise ValueError("Multiplier must be > 0")
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
    def load_simple(path_to_dir):
        path_to_dir = os.path.abspath(path_to_dir)
        if path_to_dir is None:
            raise NotADirectoryError(f"Could not load Model: {path_to_dir} does not exist")
        with open(os.path.join(path_to_dir, MODEL_F), "r") as file:
            data = json.load(file)
            model = Model(node.Mod[data["mod"]], path_to_dir, data['num'][0], data['num'][1],
                          data['dur'][0], data['dur'][1])
            model.model_time = ModelTime.loads(data['ts'])
            model.performed = data['perf']
            return model

    @staticmethod
    def load(path_to_dir):
        model = Model.load_simple(path_to_dir)
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
        bar_u = IncrementalBar('Load users', max=model.usr_num)
        for i in range(model.usr_num):
            model.usrs.append(node.User.load(os.path.join(path_to_dir, USR_DIR, f"{USR_NODE}{i}"),
                                             model.stgs[i % model.stg_num]))
            bar_u.next()
        bar_u.finish()
        return model

    def perform(self, rounds: int, failures: dict = None):
        failures = {} if not failures else failures
        for k in failures:
            if k >= self.stg_num or k < 0:
                raise ValueError(f"Bad failures: {failures}. Stgs: {self.stg_num}. Usrs: {self.usr_num}")
            for v in failures[k]:
                if v >= self.usr_num or v < 0:
                    raise ValueError(f"Bad failures: {failures}. Stgs: {self.stg_num}. Usrs: {self.usr_num}")
        disabled = {}
        header = list(self.get_stat().keys())
        bar = IncrementalBar('Rounds', max=rounds)
        with open(os.path.join(self.path, RESULT_F), 'a', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, header)
            if self.performed == 0:
                writer.writeheader()
            for i in range(rounds):
                self.disable(disabled, failures, i + 1)
                self.usr_step(i)
                self.stg_step()
                self.performed += 1
                stat = self.get_stat()
                writer.writerow(stat)
                bar.next()
        bar.finish()

    def get_stat(self):
        queues = []
        queue_len = 0
        stg_usrs = []
        stg_usrs_count = 0
        stg_active = 0
        bc = {}
        for i, stg in enumerate(self.stgs):
            queues.append(stg.queue_len())
            queue_len += stg.queue_len()
            stg_usrs.append(stg.local_bm_participants())
            stg_usrs_count += stg.local_bm_participants()
            lbc = stg.block_count
            if lbc in bc:
                bc[lbc].append(i)
            else:
                bc[lbc] = [i]
            if stg.available:
                stg_active += 1
        return {"Performed": self.performed,
                "Timestamp": self.model_time.time,
                "StgTotal": self.stg_num,
                "UsrTotal": self.usr_num,
                "GlobalBM": bc,
                "LocalBM": [u.block_count for u in self.usrs],
                "StgActive": stg_active,
                "QueueLen": queues,
                "AvgQueue": queue_len / self.stg_num,
                "StgUsrs": stg_usrs,
                "AvgStgUsrs": stg_usrs_count / self.stg_num}

    def disable(self, disabled, failures, i):
        if i in failures:
            for k in failures[i]:
                if k in disabled:
                    disabled[k] += 1
                else:
                    self.stgs[k].disable()
                    disabled[k] = 1
        for k in disabled.copy():
            disabled[k] -= 1
            if disabled[k] < 0:
                self.stgs[k].enable()
                disabled.pop(k)

    def usr_step(self, offset):
        for i in range(self.usr_num):
            if (i + 1) % self.duration[0] == 0:
                self.model_time.tick()
            self.usr_perform(i, [(i + 1 + offset) % self.usr_num])

    def usr_perform(self, sender: int, receivers: list):
        if sender >= len(self.usrs) or sender < 0:
            raise ValueError()
        for recv in receivers:
            if recv == sender or recv >= len(self.usrs) or recv < 0:
                raise ValueError()
        self.usrs[sender].perform([self.usrs[i].addr for i in receivers], {"info": f"{sender} -> {receivers}"})

    def stg_step(self):
        self.model_time.tick()
        v_3_4 = 3 * (self.duration[1] - 1) // 4
        for s in self.stgs:
            s.perform_step_1()
        self.model_time.tick(v_3_4)
        for s in self.stgs:
            s.perform_step_2()
        self.model_time.tick(self.duration[1] - v_3_4)
