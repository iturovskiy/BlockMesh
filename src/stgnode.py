from src.block import *
from src.usrnode import UsrNode, HEAD_FILE
from model.model import Mod


class StgNode:
    """
    Класс реализующий функционал узлов-хранилищ blockmesh сети
    """

    def __init__(self, mod: Mod, path_to_dir: str):
        """
        :param mod: режим работы
        :param path_to_dir: путь к дирректории в которой будут храниться блоки этого узла
        """
        if mod == Mod.Classic:
            self.queue = []
            self.shared_blocks = []
        elif mod == Mod.Modified:
            self.queue = {}
            self.shared_blocks = {}
        else:
            raise RuntimeError(f"Unknown mod: {mod.name}")
        self.mod = mod
        if not os.path.abspath(path_to_dir):
            os.makedirs(path_to_dir)
        self.path_to_dir = os.path.abspath(path_to_dir)
        self.stg_list = []    # list of StgNodes
        self.user_map = {}    # addr and its UsrNode
        self.block_mesh = {}  # addr and its head
        self.block_count = 1  # genesis at least

    def __del__(self):
        """
        Деструктор. Записывает состояние узла-хранилища в файл
        """
        with open(os.path.join(self.path_to_dir, HEAD_FILE), "w") as f:
            json.dump({'Mod': self.mod.name, 'heads': self.block_mesh, 'queue': self.queue}, f)

    @staticmethod
    def load(path, stg_map, usr_map=None):
        # todo: load for stg
        pass

    # todo: посчитать узловые блоки!!!

    def participants_bm(self):
        return len(self.block_mesh)

    def queue_len(self):
        return len(self.queue) if self.mod == Mod.Classic else sum(self.queue.values())

    def add_new_block(self, block: Block):
        """
        Принятие блока на обработку с целью добавить в блокмеш
        :param block: блок блокмеша
        """
        if self.mod == Mod.Classic:
            self.queue.append(block)
        elif self.mod == Mod.Modified:
            if block in self.queue:
                self.queue[block] += 1
            else:
                self.queue[block] = 1
        else:
            raise RuntimeError("WTF - add new block")

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

    def send_block(self, block, count=None):
        if self.mod == Mod.Classic:
            self.shared_blocks.append(block)
            for stg in self.stg_list:
                stg.shared_blocks.append(block)
        elif self.mod == Mod.Modified:
            # возможны ошибки
            if block in self.shared_blocks:
                self.shared_blocks[block] += count
            else:
                self.shared_blocks[block] = count
            for stg in self.stg_list:
                if block in stg.shared_blocks:
                    stg.shared_blocks[block] += count
                else:
                    stg.shared_blocks[block] = count
        else:
            raise RuntimeError("WTF - send block")

    def perform_step_1(self):
        """
        Шаг 1 - "рассылка" блока для консенсуса
        """
        if self.mod == Mod.Classic:
            self.__perform_step_1()
        elif self.mod == Mod.Modified:
            self.__perform_step_1_mod()
        else:
            raise RuntimeError("WTF - perform step 1")

    def __perform_step_1(self):
        while self.queue:
            block = self.queue[0]
            if self.check_block(block) is False:
                block.approved = False
                self.user_map[block.sender()].receive_from_stg(block)
                self.queue.pop(0)
                continue
            self.send_block(block)
            return

    def __perform_step_1_mod(self):
        while self.queue:
            block, count = list(self.queue.items())[0]
            if self.check_block(block) is False:
                block.approved = False
                self.user_map[block.sender()].receive_from_stg(block)
                self.queue.pop(block)
                continue
            self.send_block(block, count)
            return

    def perform_step_2(self):
        """
        Шаг 2 - Конфликтующие транзакции откладываются, валидные внедряются в блокмеш
        """
        if self.mod == Mod.Classic:
            self.__perform_step_2()
        elif self.mod == Mod.Modified:
            self.__perform_step_2_mod()
        else:
            raise RuntimeError("WTF - perform step 1")

    def __perform_step_2(self):
        if not self.shared_blocks:
            return
        self.shared_blocks.sort(key=lambda b: b.timestamp)
        participants = {}
        while self.shared_blocks:
            block = self.shared_blocks.pop(0)
            if not self.__check_and_insert(block, participants):
                continue
            if self.queue and block == self.queue[0]:
                self.queue.pop(0)
            self.block_count += 1

    def __perform_step_2_mod(self):
        if not self.shared_blocks:
            return
        blocks = list(self.shared_blocks.keys())
        blocks.sort(key=lambda b: b.timestamp)
        participants = {}
        while blocks:
            block = blocks.pop(0)
            count = self.shared_blocks.pop(block)
            if len(block.participants()) != count:
                print(f"Got participants: {len(block.participants())}. Expected: {count}")
                continue
            if not self.__check_and_insert(block, participants):
                continue
            if self.queue and block == list(self.queue.keys())[0]:
                self.queue.pop(block)
            self.block_count += 1

    def __check_and_insert(self, block, participants):
        # проверка
        users = block.participants()
        for user in users:
            if user in participants:
                return False
        participants.update(users)
        # внедрение в блокмеш
        block.set_parents({usr: self.block_mesh[usr] for usr in users})
        fname = block.save(self.path_to_dir)
        for user in users:
            self.block_mesh[user] = fname
            if user in self.user_map:
                self.user_map[user].receive_from_stg(block)
        return True

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
