import json
import os.path
from hashlib import sha256

NOT_SIGNED = None
GENESIS_BLOCK = sha256(bytes(json.dumps({'header': {'version': '0.01a',
                                                    'timestamp': 0,
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

    def __str__(self):
        return f"[TX: {self.dumps()}]"

    @staticmethod
    def loads(data):
        """
        Чтение транзакции из JSON в формате строки и создание объекта
        :param data: JSON в формате строки
        :return: Transaction
        """
        js = json.loads(data)
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
        if addr not in self.participants:
            raise RuntimeError(f"'{addr}' could not sign {str(self)}")
        if self.participants[addr] != NOT_SIGNED:
            raise RuntimeError(f"'{addr}' already signed -> {addr}: {self.participants[addr]}")
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
        return tuple(self.participants.keys())

    def dumps(self):
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

    def __init__(self, transaction: Transaction, timestamp: int = None, parents: dict = None):
        """
        :param transaction: готовая транзакция
        :param parents: хеши родительских блоков
        :param timestamp: временная метка - количество нс с начала Эпохи
        """
        if not transaction.is_ready():
            raise RuntimeError(f"Could not create block for unsigned transaction: {transaction}; "
                               f"parents: {parents}, time: {timestamp}")
        self.tx = transaction
        self.parents = parents if parents else {}
        self.timestamp = timestamp
        self.approved = None
        self.on_iter = 1

    def __hash__(self):
        return int(self.hashs(), 16)

    def hashs(self):
        return sha256(bytes(json.dumps({'header': {'version': self.version,
                                                   'timestamp': self.timestamp,
                                                   'parents': self.parents}}), 'utf-8')).hexdigest()

    def __eq__(self, other):
        return self.version == other.version and \
               self.timestamp == other.timestamp and \
               self.tx == other.tx

    def copy(self):
        b = Block(self.tx, self.timestamp, self.parents.copy())
        b.approved = self.approved
        b.on_iter = self.on_iter
        return b

    def set_parents(self, parents: dict):
        """
        :param parents: dict адрес - хэш
        :return:
        """
        participants = self.participants()
        for parent, hsh in parents.items():
            if parent not in participants:
                raise RuntimeError(f"Parent {parent} not in {participants}")
            self.parents[parent] = hsh

    def participants(self):
        return tuple(self.tx.participants.keys())

    def sender(self):
        return self.tx.sender

    def dumps(self):
        """
        :return: json объект блока транзакции
        """
        return json.dumps({'header': {'version': self.version,
                                      'timestamp': self.timestamp,
                                      'parents': self.parents},
                           'transaction': self.tx.dumps(),
                           'iter': self.on_iter})

    @staticmethod
    def loads(data):
        """
        Чтение блока транзакции из строки
        :param data: строка содержащая дамп Block
        :return: Block
        """
        data = json.loads(data)
        return Block.l(data)

    def save(self, path_to_dir):
        """
        Запись блока транзакции в файл
        :param path_to_dir: путь до файла
        """
        if not self.tx.is_ready():
            raise RuntimeError(f"WTF - block is not ready")
        if not self.approved or self.approved is False:
            raise RuntimeError(f"Block {self} is not approved and can't be saved")
        if not os.path.abspath(path_to_dir):
            os.makedirs(path_to_dir)
        fname = self.hashs()
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
            return Block.l(data)

    @staticmethod
    def l(data):
        block = Block(Transaction.loads(data['transaction']), data['header']['timestamp'], data['header']['parents'])
        block.version = data['header']['version']
        block.approved = True
        block.on_iter = data['iter']
        return block
