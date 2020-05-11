from enum import Enum
from src.stgnode import *
from src.usrnode import *

STG_DIR = r'Storages'
USR_DIR = r'Users'


class Mod(Enum):
    Classic = 1
    Modified = 2


class Model:
    """
    Класс реализующий функионал модели протокола блокмеш
    """

    def __init__(self, path_to_dir: str, stg_num: int, usr_num: int, duration_1: int, duration_2: int, activity: float):
        """
        :param path_to_dir:
        :param stg_num:
        :param usr_num:
        :param duration_1:
        :param duration_2:
        :param activity:
        """
        assert activity > 0  # когда лень писать обработку ошибок)))
        assert activity <= 1
        assert usr_num >= stg_num
        assert duration_1 >= duration_2
        if not os.path.abspath(path_to_dir):
            os.makedirs(path_to_dir)
        self.path = os.path.abspath(path_to_dir)
        self.duration_1 = duration_1
        self.duration_2 = duration_2
        self.stg_num = stg_num
        self.usr_num = usr_num
        self.stgs = [StgNode(os.path.join(self.path, STG_DIR, f"stg_{i}")) for i in range(self.stg_num)]
        self.usrs = [UsrNode(os.path.join(self.path, USR_DIR, f"usr_{i}"),
                             f"user{i}", f"sign{i}", self.stgs[i % self.stg_num]) for i in range(self.usr_num)]
        self.usr_activity = activity
        self.model_time = 1

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
