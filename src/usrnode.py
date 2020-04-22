from src.block import *
from src.stgnode import *

HEAD_FILE = "HEAD"


class UsrNode:
    """
    Класс реализующий функционал узлов-участников blockmesh сети
    """

    def __init__(self, path_to_dir: str, addr: str, sign: str, stg: StgNode = None, head: str = None):
        """
        :param path_to_dir: путь к дирректории в которой будут храниться блоки этого узла
        :param addr: идентификатор узла
        :param sign: подпись узла
        :param stg: узел-хранилище через который будет обеспечиваться взаимодействие с другими участниками
        """
        if not os.path.abspath(path_to_dir):
            os.makedirs(path_to_dir)
        self.path_to_dir = os.path.abspath(path_to_dir)
        self.addr = addr
        self.sign = sign
        self.stg = stg
        self.inited = False
        self.head = head

    def __del__(self):
        if self.inited and self.head:
            with open(os.path.join(self.path_to_dir, HEAD_FILE), "w") as f:
                json.dump({"head": self.head, "addr": self.addr, "sign": self.sign}, f)

    @staticmethod
    def load(path_to_dir, stg: StgNode):
        """
        Восстановление состояния узла-участника из файла
        :param path_to_dir: путь к дирректории
        :param stg:
        :return:
        """
        path_to_dir = os.path.abspath(path_to_dir)
        if path_to_dir is None:
            raise RuntimeError(f"Could not load UsrNode: {path_to_dir} does not exist")
        with open(os.path.join(path_to_dir, HEAD_FILE), "r") as f:
            data = json.load(f)
            node = UsrNode(path_to_dir, data['addr'], data['sign'], stg, data['head'])

            return node

    def change_stg(self, new_stg):
        pass

    def sign_tx(self, tx: Transaction):
        """
        Подписание транзакции
        :param tx: Транзакция
        :return: хэш родительского блока
        """
        assert self.inited
        tx.sign(self.addr, self.sign)
        return self.head

    def perform(self, recv_addr: list, data: dict = None):
        """
        Первый этап работы blockmesh - взаимодействие
        :param recv_addr: список получателей транзакции
        :param data: данные
        """
        assert self.inited
        tx = self._create_tx(recv_addr, data)
        parents = [receiver.sign_tx(tx) for receiver in self.stg.get_users(recv_addr)]
        block = self._create_block(tx, parents)
        self.stg.add_new_block(block)

    def receive_from_stg(self, block: Block):
        """
        Продолжение второго этапа работы blockmesh - внедрение блока
        :param block: блок для внедрения в локальную цепочку
        """
        pass

    def _create_tx(self, receivers: list, data: dict = None):
        """
        Создание транзакции
        :param receivers: список получателей транзакции
        :param data: данные
        :return: Транзакция - Transaction
        """
        return Transaction(sender_addr=self.addr, sender_sign=self.sign,
                           receivers=receivers, data=data if data else {})

    def _create_block(self, tx: Transaction, parents: list):
        """
        Создание блока транзакции
        :param tx: транзакция
        :param parents: cписок хэшей блоков родителей
        :return: Блок транзакции - Block
        """
        assert tx.sender == self.addr
        return Block(tx, parents, time.time_ns())
