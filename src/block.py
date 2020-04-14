import json
import os.path


NOT_SIGNED = 'EMPTY'


class Transaction:
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
            for recv in kwargs['receivers']:
                self.participants[recv] = NOT_SIGNED
        self.data = kwargs['data'] if 'data' in kwargs else dict()

    def __eq__(self, other):
        return self.sender == other.sender and self.participants == other.participants and self.data == other.data

    @staticmethod
    def load(data):
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
            raise
        if self.participants[addr] != NOT_SIGNED:
            raise
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
    version = 0.01  # версия, пущай будет

    def __init__(self, transaction: Transaction, parents: list = None):
        self.tx = transaction
        self.parents = parents if parents else []

    def __hash__(self):
        return hash((self.version, *self.parents))

    def __eq__(self, other):
        return self.version == other.verson and tuple(self.parents) == tuple(other.parents) and self.tx == other.tx

    def json(self):
        """
        :return: json объект блока транзакции
        """
        return json.dumps({'header': {'version': self.version,
                                      'parents': self.parents},
                           'transaction': self.tx.json()})

    def save(self, path):
        """
        Запись блока транзакции в файл
        :param path: путь до файла
        """
        path = os.path.abspath(path)
        folder = os.path.dirname(path)
        if not folder:
            os.makedirs(folder)
        with open(path, "w") as out:
            out.write(self.json())

    @staticmethod
    def load(path):
        """
        Чтение блока транзакции из файла и создание объекта
        :param path: путь до файла
        :return: Block
        """
        path = os.path.abspath(path)
        with open(path) as json_file:
            data = json.load(json_file)
            txs = data['transaction']
            ver = data['header']['version']
            par = data['header']['parents']
            block = Block(Transaction.load(txs), par)
            block.version = ver
            return block
