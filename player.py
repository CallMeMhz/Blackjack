from deck import Hand

class Player(object):

    def __init__(self, sock):
        self.sock = sock
        self.peername = sock.getpeername()
        self.status = 'watching'
        self.chips = None
        self.insurance = None
        self.hand = Hand()

    def set_status(self, status):
        self.status = status

    def bet(self, stakes):
        if stakes <= 0:
            # raise Exception('Wrong bet value')
            return False
        self.chips = stakes
        return True

    def add_bet(self, stakes):
        if stakes <= 0:
            # raise Exception('Wrong bet value')
            return False
        self.chips += stakes
        return True

    def set_insurance(self, val):
        self.insurance = val
        self.add_bet(self.chips / 2)

class Dealer(object):
    def __init__(self):
        self.hand = Hand()

    def get_hand(self):
        return self.hand
