from src.block import *
from src.usrnode import *

SHARED = []


class StgNode:
    """
    Класс реализующий функционал узлов-хранилищ blockmesh сети
    """

    def __init__(self, path_to_dir):
        """
        :param path_to_dir: путь к дирректории в которой будут храниться блоки этого узла
        """
        if not os.path.abspath(path_to_dir):
            os.makedirs(path_to_dir)
        self.path_to_dir = os.path.abspath(path_to_dir)
        self.stg_list = []    # list of StgNodes
        self.user_map = {}    # addr and its UsrNode
        self.block_mesh = {}  # addr and its head
        self.queue = []
        self.block_count = 1

    def __del__(self):
        """
        Деструктор. Записывает состояние узла-хранилища в файл
        """
        with open(os.path.join(self.path_to_dir, HEAD_FILE), "w") as f:
            json.dump({'heads': self.block_mesh, 'queue': self.queue}, f)

    @staticmethod
    def load(path, stg_map, usr_map=None):
        # todo: load for stg
        pass

    def add_new_block(self, block: Block):
        """
        Принятие блока на обработку с целью добавить в блокмеш
        :param block:
        """
        self.queue.append(block)

    def queue_len(self):
        return len(self.queue)

    def add_new_user(self, user: UsrNode):
        """
        Добавить нового пользователя в блокмеш
        :param user: UsrNode
        """
        if user.addr not in self.user_map:
            self.user_map[user.addr] = user
        assert self.user_map[user.addr].head == user.head
        if user.addr not in self.block_mesh:
            self.block_mesh[user.addr] = user.head = GENESIS_BLOCK
            # сообщить остальным о новом пользователе
            for stg in self.stg_list:
                stg.block_mesh[user.addr] = GENESIS_BLOCK
        else:
            user.head = self.block_mesh[user.addr]
        user.inited = True

    @staticmethod
    def check_block(block: Block):
        """
        WTF должна быть проверка транзакции в блоке
        :param block:
        :return:
        """
        return True if block.approved is None else False

    def perform_step_1(self):
        """
        Шаг 1 - "рассылка" блока для консенсуса
        """
        global SHARED
        while self.queue:
            block = self.queue.pop(0)
            if self.check_block(block) is False:
                block.approved = False
                self.user_map[block.sender()].receive_from_stg(block)
                continue
            SHARED.append((block, self))
            return

    @staticmethod
    def perform_step_2():
        """
        Шаг 2 - конфликтующие транзакции откладываются на следующую итерацию
        """
        global SHARED
        if not SHARED:
            return
        SHARED.sort(key=lambda b: b[0].timestamp)
        participants = {}
        for index, block, stg in enumerate(SHARED):
            users = block.participans()
            for user in users:
                if user in participants:
                    # откладываем транзакцию
                    stg.queue.insert(0, block)
                    SHARED.pop(index)
                    break

    @staticmethod
    def perform_step_2_modified():
        """
        Шаг 2 модифицированный
        """
        global SHARED
        if not SHARED:
            return
        SHARED.sort(key=lambda b: b[0].timestamp)
        # todo: continue

    def perform_step_3(self):
        """
        Шаг 3 - внедрение в блокмеш
        """
        global SHARED
        for block, _ in SHARED:
            users = block.participants()
            block.set_parents({usr: self.block_mesh[usr] for usr in users})
            fname = block.save(self.path_to_dir)
            for user in users:
                self.block_mesh[user] = fname
                if user in self.user_map:
                    self.user_map[user].receive_from_stg(block)
            self.block_count += 1

    @staticmethod
    def perform_step_4():
        """
        Шаг 4
        """
        global SHARED
        SHARED.clear()

    def get_users(self, users):
        """
        Запрос на взаимодействие с другими узлами-участниками
        :param users: список адресов
        :return: список UsrNode
        """
        assert users
        return [self.__request_user(user) for user in users]

    def __request_user(self, user):
        if user in self.user_map:
            return self.user_map[user]
        for stg in self.stg_list:
            if user in stg.user_map:
                return stg.user_map[user]
        raise RuntimeError(f"There is no such user: {user}")
