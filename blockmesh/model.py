import blockmesh.node as node
import json
import os

STG_DIR = r'Storages'
USR_DIR = r'Users'
MOD_F = r'MODEL'


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
        data = json.loads(data)
        return ModelTime(data["time"], data["step"])

    def tick(self, mul: int = 1):
        """
        Увеличить время
        :type mul: мультипликор
        """
        if mul < 1:
            raise ValueError("Multiplier must be > 0")
        self.time += self.step * mul


class Model:
    """
    Класс реализующий функионал модели протокола блокмеш
    """

    def __init__(self, mod: node.Mod, path_to_dir: str, stg_num: int, usr_num: int,
                 duration_1: int, duration_2: int, activity: float):
        """
        :param path_to_dir:
        :param stg_num:
        :param usr_num:
        :param duration_1:
        :param duration_2:
        :param activity:
        """
        if activity > 1 or activity < 0:
            raise ValueError(f"Wrong activity param: {activity}. Should be in (0..1)")
        self.path = node.mkdir(path_to_dir)
        self.duration_1 = duration_1
        self.duration_2 = duration_2
        self.stg_num = stg_num
        self.usr_num = usr_num
        self.stgs = [node.Storage(mod, os.path.join(self.path, STG_DIR, f"stg_{i}")) for i in range(self.stg_num)]
        for i in range(len(self.stgs) - 1):
            self.stgs[i + 1].join_bm(self.stgs[i])
        self.usrs = [node.User(mod, os.path.join(self.path, USR_DIR, f"usr_{i}"),
                               f"user{i}", f"sign{i}", self.stgs[i % self.stg_num]) for i in range(self.usr_num)]
        self.usr_activity = activity
        self.model_time = ModelTime()

    def save(self):
        for s in self.stgs:
            s.save()
        for u in self.usrs:
            u.save()
        with open(os.path.join(self.path, MOD_F), 'w') as out:
            json.dump({"num": [self.stg_num, self.usr_num],
                       "dur": [self.duration_1, self.duration_2],
                       "activity:": self.usr_activity,
                       "time_s": self.model_time.dumps()}, out)

    @staticmethod
    def load(path_to_dir):
        # todo: today
        pass

    def perform(self, rounds: int, failures: dict = None):
        for round in range(rounds):
            # расчкт сколько пользователей отвзаимодействовало
            for current_time in range(self.duration_1):
                # 
                pass
            self.__stg_step()

    def __stg_step(self):
        for i in range(self.duration_2):
            self.model_time.tick()
            for s in self.stgs:
                s.perform_step_1()
            for s in self.stgs:
                s.perform_step_2()
