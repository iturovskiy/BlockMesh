from enum import Enum
import blockmesh.node as node
import os

STG_DIR = r'Storages'
USR_DIR = r'Users'


class Mod(Enum):
    Classic = 1
    Modified = 2


class ModelTime:
    """
    Класс реализующий функционал модельного-времени и таймсервера
    """

    def __init__(self, start_time: int = 1, step: int = 1):
        """
        :param start_time:
        """
        if start_time < 1:
            raise ValueError("Start time must be > 0")
        if step < 1:
            raise ValueError("Step must be > 0")
        self.time = start_time
        self.step = step

    def tick(self, mul: int = 1):
        """
        Увеличить время
        """
        if mul < 1:
            raise ValueError("Multiplier must be > 0")
        self.time += self.step * mul


class Model:
    """
    Класс реализующий функионал модели протокола блокмеш
    """

    def __init__(self, mod: Mod, path_to_dir: str, stg_num: int, usr_num: int,
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
        pass

    @staticmethod
    def load(path_to_dir):
        pass

    def perform(self, rounds: int, mod: Mod, failures: dict = None):
        for round in range(rounds):
            # расчкт сколько пользователей отвзаимодействовало
            for current_time in range(self.duration_1):
                # 
                pass
