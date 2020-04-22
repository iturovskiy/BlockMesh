import json
import os.path
import time
from hashlib import sha256

NOT_SIGNED = 'EMPTY'
GENESIS_BLOCK = sha256(bytes(json.dumps({'header': {'version': '0.01a',
                                                    'timestamp': 1587560218714243400,
                                                    'parents': 'GENESIS'}}), 'utf-8')).hexdigest()


class Transaction:
    """
    Транзакция
    """
    sender = None
    participants = None
    data = {}

    def __init__(self, **kwargs):
        """
        sender_addr: str, sender_sign: str, receivers: list

        :param sender_addr: адрес отправителя
            :param participants: словарь адрес: подпись
        ИЛИ
            :param sender_sign: подпись отправителя
            :param receivers: список адресов получателей
        :param data: данные
        """
        if any(kwargs) is False:
            return
        self.sender = kwargs['sender_addr']
        if 'participants' in kwargs:
            self.participants = kwargs['participants']
        else:
            self.participants = {kwargs['sender_addr']: kwargs['sender_sign']}
            if 'receivers' in kwargs:
                for recv in kwargs['receivers']:
                    self.participants[recv] = NOT_SIGNED
        self.data = kwargs['data'] if 'data' in kwargs else dict()

    def __eq__(self, other):
        return self.sender == other.sender and self.participants == other.participants and self.data == other.data

    @staticmethod
    def load(sdata):
        """
        Чтение транзакции из JSON в формате строки и создание объекта
        :param sdata: JSON в формате строки
        :return: Transaction
        """
        js = json.loads(sdata)
        send = js['send']
        participants = js['participants']
        data = js['data']
        return Transaction(sender_addr=send, participants=participants, data=data)

    def sign(self, addr: str, sign: str):
        """
        Подпись транзакции получателем
        :param addr: адрес получателя
        :param sign: подпись получателя
        """
        assert addr in self.participants
        assert self.participants[addr] == NOT_SIGNED
        self.participants[addr] = sign

    def is_ready(self):
        """
        Проверка готовности транзакции
        """
        if self.sender is None or self.participants is None:
            return False
        for i in self.participants.values():
            if i == NOT_SIGNED:
                return False
        return True

    def get_participants(self):
        """
        :return: Список участников транзакции
        """
        return self.participants.keys()

    def json(self):
        """
        :return: json объект класса
        """
        return json.dumps({'send': self.sender,
                           'participants': self.participants,
                           'data': self.data})


class Block:
    """
    Блок транзакции
    """
    version = '0.01'  # версия, пущай будет
    # todo: approve for block

    def __init__(self, transaction: Transaction, parents: list = None, timestamp: int = None):
        """
        :param transaction: готовая транзакция
        :param parents: хеши родительских блоков
        :param timestamp: временная метка - количество нс с начала Эпохи
        """
        if not transaction.is_ready():
            raise RuntimeError(f"Could not create block for unsigned transaction: {transaction}; "
                               f"parents: {parents}, time: {timestamp}")
        self.tx = transaction
        self.parents = parents if parents else []
        self.timestamp = timestamp if timestamp else time.time_ns()
        self.approved = None

    def __hash__(self):
        return sha256(bytes(json.dumps({'header': {'version': self.version,
                                                   'timestamp': self.timestamp,
                                                   'parents': self.parents}}), 'utf-8')).hexdigest()

    def __eq__(self, other):
        return self.version == other.verson and self.timestamp == other.timestamp and \
               tuple(self.parents) == tuple(other.parents) and self.tx == other.tx

    def dumps(self):
        """
        :return: json объект блока транзакции
        """
        return json.dumps({'header': {'version': self.version,
                                      'timestamp': self.timestamp,
                                      'parents': self.parents},
                           'transaction': self.tx.json()})

    def save(self, path_to_dir):
        """
        Запись блока транзакции в файл
        :param path_to_dir: путь до файла
        """
        assert self.tx.is_ready()
        if not self.approved or self.approved is False:
            raise RuntimeError(f"Block {self} is not approved and can't be saved")
        if not os.path.abspath(path_to_dir):
            os.makedirs(path_to_dir)
        fname = str(self.__hash__())
        with open(os.path.join(path_to_dir, fname), "w") as out:
            out.write(self.dumps())
        return fname

    @staticmethod
    def load(path_to_file):
        """
        Чтение блока транзакции из файла и создание объекта
        :param path_to_file: путь до файла
        :return: Block
        """
        path_to_file = os.path.abspath(path_to_file)
        if path_to_file is None:
            raise RuntimeError(f"Could not load Block: {path_to_file} does not exist")
        if not os.path.isfile(path_to_file):
            raise RuntimeError(f"Could not load Block: {path_to_file} not file")
        with open(path_to_file, "r") as json_file:
            data = json.load(json_file)
            block = Block(Transaction.load(data['transaction']),
                          data['header']['parents'],
                          data['header']['timestamp'])
            block.version = data['header']['version']
            block.approved = True
            return block
