from src.block import *
from src.stgnode import StgNode
from model.model import Mod

HEAD_FILE = "HEAD"


class UsrNode:
    """
    Класс реализующий функционал узлов-участников blockmesh сети
    """

    def __init__(self, mod: Mod, path_to_dir: str, addr: str, sign: str, stg: StgNode = None, head: str = None):
        """
        :param mod: режим работы
        :param path_to_dir: путь к дирректории в которой будут храниться блоки этого узла
        :param addr: идентификатор узла
        :param sign: подпись узла
        :param stg: узел-хранилище через который будет обеспечиваться взаимодействие с другими участниками
        """
        if mod == Mod.Classic:
            self.allowed = None
        elif mod == Mod.Modified:
            self.allowed = True
        else:
            raise RuntimeError(f"Unknown mod: {mod.name}")
        self.mod = mod
        if not os.path.abspath(path_to_dir):
            os.makedirs(path_to_dir)
        self.path_to_dir = os.path.abspath(path_to_dir)
        self.addr = addr
        self.sign = sign
        self.stg = stg
        self.inited = False
        self.head = head
        stg.add_new_user(self)

    def __del__(self):
        if self.inited and self.head:
            with open(os.path.join(self.path_to_dir, HEAD_FILE), "w") as f:
                json.dump({"head": self.head, "addr": self.addr, "sign": self.sign, "mod": self.mod.name}, f)

    @staticmethod
    def load(path_to_dir, stg: StgNode):
        """
        Восстановление состояния узла-участника из файла
        :param path_to_dir: путь к дирректории
        :param stg: Узел-хранилище
        :return: UsrNode
        """
        path_to_dir = os.path.abspath(path_to_dir)
        if path_to_dir is None:
            raise RuntimeError(f"Could not load UsrNode: {path_to_dir} does not exist")
        with open(os.path.join(path_to_dir, HEAD_FILE), "r") as f:
            data = json.load(f)
            node = UsrNode(Mod[data['mod']], path_to_dir, data['addr'], data['sign'], stg, data['head'])
            return node

    def change_stg(self, new_stg: StgNode):
        # todo: сделать позже
        pass

    def sign_tx(self, tx: Transaction):
        """
        Подписание транзакции
        :param tx: Транзакция
        :return: хэш родительского блока
        """
        if not self.inited:
            raise RuntimeError("UsrNode not inited in his StgNode")
        tx.sign(self.addr, self.sign)
        return self.head

    def perform(self, recv_addr: list, data: dict = None):
        """
        Первый этап работы blockmesh - взаимодействие
        :param recv_addr: список получателей транзакции
        :param data: данные
        """
        if not self.inited:
            raise RuntimeError("UsrNode not inited in his StgNode")
        if self.mod == Mod.Classic:
            self.__perform(recv_addr, data)
        elif self.mod == Mod.Modified:
            self.__perform_mod(recv_addr, data)

    def __perform(self, recv_addr: list, data: dict = None):
        tx = self.__create_tx(recv_addr, data)
        for receiver in self.stg.get_users(recv_addr):
            receiver.sign_tx(tx)
        block = self.__create_block(tx)
        self.stg.add_new_block(block)

    def __perform_mod(self, recv_addr: list, data: dict = None):
        if not self.allowed:
            print(f"Not allowed yet to gen new transaction: {self.addr}")
            return
        tx = self.__create_tx(recv_addr, data)
        receivers = self.stg.get_users(recv_addr)
        for receiver in receivers:
            receiver.sign_tx(tx)
        block = self.__create_block(tx)
        self.stg.add_new_block(block)
        for receiver in receivers:
            receiver.stg.add_new_block(block)
        self.allowed = False

    def receive_from_stg(self, block: Block):
        """
        Продолжение второго этапа работы blockmesh - внедрение блока
        :param block: блок для внедрения в локальную цепочку
        """
        if block.approved and self.check_chain(block):
            self.head = block.save(self.path_to_dir)
            if self.mod == Mod.Modified and self.addr == block.sender():
                self.allowed = True

    def check_chain(self, block: Block):
        """
        Проверка локальной цепочки блокмеш
        :param block: блок внедряемый в локальную цепочку
        :return: Bool
        """
        if block.parents[self.addr] != self.head:
            raise RuntimeError(f"Check chain error:[ Block parent hash: {block.parents[self.addr]} "
                               f"!= Usr parent hash: {self.head} ]")
        parent_hash = self.head
        while parent_hash != GENESIS_BLOCK:
            try:
                read_block = Block.load(os.path.join(self.path_to_dir, parent_hash))
            except Exception as e:
                print(e)
                return False
            parent_hash = read_block.parents[self.addr]
        return True

    def __create_tx(self, receivers: list, data: dict = None):
        """
        Создание транзакции
        :param receivers: список получателей транзакции
        :param data: данные
        :return: Транзакция - Transaction
        """
        return Transaction(sender_addr=self.addr, sender_sign=self.sign,
                           receivers=receivers, data=data if data else {})

    def __create_block(self, tx: Transaction):
        """
        Создание блока транзакции
        :param tx: транзакция
        :return: Блок транзакции - Block
        """
        if tx.sender != self.addr:
            raise RuntimeError(f"Tx sender {tx.sender} != self addr {self.addr}")
        return Block(tx, time.time_ns())
