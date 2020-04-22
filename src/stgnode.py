from src.block import *
from src.usrnode import *


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
        self.stg_map = []     # list of StgNodes
        self.user_map = {}    # addr and its UsrNode
        self.block_mesh = {}  # addr and its head
        self.queue = []

    def __del__(self):
        with open(os.path.join(self.path_to_dir, HEAD_FILE), "w") as f:
            json.dump({'heads': self.block_mesh, 'queue': self.queue}, f)

    @staticmethod
    def load(path, stg_map, usr_map=None):
        pass

    def add_new_block(self, block: Block):
        self.queue.append(block)

    def add_new_user(self, user: UsrNode):
        if user.addr not in self.user_map:
            self.user_map[user.addr] = user
        assert self.user_map[user.addr].head == user.head
        if user.addr not in self.block_mesh:
            self.block_mesh[user.addr] = user.head = GENESIS_BLOCK
            # сообщить остальным о новом пользователе
            for stg in self.stg_map:
                stg.block_mesh[user.addr] = GENESIS_BLOCK
        else:
            user.head = self.block_mesh[user.addr]
        user.inited = True

    def check_chain(self, block: Block):
        assert not block.approved
        pass

    def perform(self):
        if not self.queue:
            return
        block = self.queue.pop(0)
        # обмен с другими stg c целью поиска конфликтов - надо подумать
        # todo: continue

    def request_user(self, user):
        if user in self.user_map:
            return self.user_map[user]
        for stg in self.stg_map:
            if user in stg.user_map:
                return stg.user_map[user]
        raise RuntimeError(f"There is no such user: {user}")

    def get_users(self, users):
        assert users
        return [self.request_user(user) for user in users]
