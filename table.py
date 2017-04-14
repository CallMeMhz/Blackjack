'''
    Game Table(Room)
'''
from concurrent.futures import ThreadPoolExecutor as Pool
from threading import Semaphore, Thread

from deck import Deck, Hand
from player import Dealer, Player
from utils import RECV_BUFFER, send_msg, unpack_msg


class Table(object):
    '''Game table(room), include it\'s own thread pool to handle client socket'''

    def __init__(self, seats=6):

        self.status = 'waiting'
        self.current_turn = None
        self.seats = {'dealer': Dealer(), 'players': []}
        self.deck = Deck(6)

        self._max_seats = seats
        for _ in range(seats):
            self.seats['players'].append(None)
        self.__game_thread = None
        self._threadpool = Pool(20)
        self.__lock = None
        self.__sig = None

    def set_status(self, status):
        self.status = status

    def get_info(self):
        table = {
            'status': self.status,
            'current_turn': self.current_turn,
            'seats': {
                'dealer': self.seats['dealer'],
                'players': []
            },
            'deck': self.deck,
            'max_seats': self._max_seats
        }
        for player in self.seats['players']:
            if player:
                table['seats']['players'].append({
                    'status': player.status,
                    'chips': player.chips,
                    'insurance': player.insurance,
                    'hand': player.hand
                })
            else:
                table['seats']['players'].append(None)
        return table

    def get_seat(self, sock):
        for i, player in enumerate(self.seats['players']):
            if player and player.sock is sock:
                return i
        return -1

    def get_socks(self):
        socks = list()
        for player in self.seats['players']:
            if player:
                socks.append(player.sock)
        return socks

    def sit_down(self, client_sock, seat):
        if not 0 <= seat < self._max_seats:
            # raise Exception('Wrong seat number.')
            return False

        # Player already present
        if client_sock in self.get_socks():
            return False

        # Seat is empty
        if self.seats['players'][seat] is None:
            self.seats['players'][seat] = Player(client_sock)

            if self.status == 'waiting':
                self.__game_thread = Thread(target=self.game_body)

            return True
        else:
            return False

    def stand_up(self, seat):
        if not 0 <= seat < len(self.seats['players']):
            # raise Exception('Wrong seat number.')
            return False

        self.broadcast('### {} stand up.'.format(self.seats['players'][seat].peername))
        self.seats['players'][seat] = None

        # Set table status to 'wait' when the last player stand up
        if not self.get_socks():
            self.status = 'waiting'
            self.current_turn = None

    def turn_players(self, status, all=False):
        if all:
            yield self.seats['dealer']
        for player in self.seats['players']:
            if player and player.status == status:
                self.current_turn = player
                yield player
        self.current_turn = None

    def get_turn(self):
        return self.current_turn

    def broadcast(self, msg):
        '''
            broadcast msg to all socks
        '''
        for sock in self.get_socks():
            if sock is not None:
                send_msg(sock, msg)

    def game_body(self):
        '''game body'''

        while self.get_socks():
            self.__lock = Semaphore(0)
            self.set_status('begining')
            self.broadcast('########## Game Start!!! ##########')
            if len(self.deck) < 58:
                self.deck = Deck(6)
            self.deck.shuffle(3)

            # Call every player to bet
            self.set_status('betting')
            self.broadcast('### Now every player bet')
            __atleast_one_bet = False
            for current_player in self.turn_players(status='watching'):
                self.broadcast('### Waiting {} bet...'.format(current_player.peername))
                self.__lock.acquire()
                if current_player.chips is not None:
                    __atleast_one_bet = True
                    current_player.status = 'gamming'
                    msg = '### {} bets {}$.'.format(
                        current_player.peername,
                        current_player.chips)
                else:
                    msg = '### {} skip this round.'.format(current_player.peername)
                self.broadcast(msg)

            if not __atleast_one_bet:
                self.set_status('waiting')
                return

            # Deal initial cards
            self.set_status('dealing')
            for current_player in self.turn_players(status='gamming', all=True):
                current_player.hand.clear()
                current_player.hand.hit(self.deck, 2)
                if current_player == self.seats['dealer']:
                    # !BUG wating for fix! If dealer's fisrt card is in TJQK
                    # server should broadcast value 10 rather than TJQK litter
                    self.broadcast('### Dealer\'s Hand: {}, {} points.'.format(
                        [current_player.hand[0], '?'], current_player.hand[0].value))
                else:
                    if current_player.hand.count_points() == 21:
                        self.broadcast('### {} BlackJack!!! Hand: {}.'.format(
                            current_player.peername,
                            current_player.hand))
                    else:
                        self.broadcast('### {} Hand: {}, {} points.'.format(
                            current_player.peername,
                            current_player.hand,
                            current_player.hand.count_points()))

            # If dealer's first card is Ace, then ask if insurance
            if self.seats['dealer'].hand[0].value == 'A':
                self.set_status('insurance')
                for current_player in self.turn_players(status='gamming'):
                    self.broadcast('### Waiting {} insurance...'.format(current_player.peername))
                    # Block until insurance
                    # while self.get_insurance(current_turn) is None: sleep(0.1)
                    self.__lock.acquire()
                    if current_player.insurance:
                        msg = '### {} insured, now his/her bet is {}'.format(
                            current_player.peername,
                            current_player.chips)
                    else:
                        msg = '### {} uninsured.'.format(current_player.peername)
                    self.broadcast(msg)
                if self.seats['dealer'].hand.count_points() == 21:
                    # !!!!!!!!!!!!!!!!!!!!!!!!
                    pass

            # Players drawing
            self.set_status('drawing')
            for current_player in self.turn_players(status='gamming'):
                self.broadcast('### Now is {} turn.'.format(current_player.peername))
                while current_player.hand.count_points() < 21:
                    self.__sig = None
                    self.__lock.acquire()
                    self.broadcast('### Now {} hand: {}, points: {}.'.format(
                        current_player.peername,
                        current_player.hand,
                        current_player.hand.count_points()))
                    if self.__sig == 'stand':
                        self.broadcast('### {} stand.'.format(current_player.peername))
                        break
                else:
                    if current_player.hand.count_points() > 21:
                        self.broadcast('### {} BUSTS'.format(current_player.peername))

            # Dealer drawing
            if self.seats['dealer'].hand[0].value != 'A'\
               and self.seats['dealer'].hand.count_points() != 21:
                while self.seats['dealer'].hand.count_points() <= 16:
                    self.seats['dealer'].hand.hit(self.deck)
            self.broadcast('### Dealer hand: {}, point: {}.'.format(
                self.seats['dealer'].hand,
                self.seats['dealer'].hand.count_points()))
            if self.seats['dealer'].hand.count_points() > 21:
                self.broadcast('### Dealer BUSTS.')

            # Show Game Result
            dealer_points = self.seats['dealer'].hand.count_points()
            msg = '#' * 20 + '\n'
            msg += 'Dealer\'s points: {}.\n'.format(dealer_points)
            for current_player in self.turn_players(status='gamming'):
                # Reset players' status to watching
                current_player.set_status('watching')
                points = current_player.hand.count_points()
                msg += '{} points: {}, '.format(
                    current_player.peername,
                    points)
                if dealer_points < points <= 21\
                   or (dealer_points > 21 and points <= 21):
                    msg += 'WIN!!!\n'
                elif points == dealer_points <= 21:
                    msg += 'PUSH.\n'
                else:
                    msg += 'Fail.\n'
            msg += '#' * 20

            self.broadcast(msg)

            self.broadcast('########## OVER ##########')

    def client_handler(self, client_sock):
        '''Client Socket Thread Handler'''

        print('Got connection from', client_sock.getpeername())

        while True:
            _msg = client_sock.recv(RECV_BUFFER)
            if not _msg:
                break

            head, data = unpack_msg(_msg)
            if head == 'table':
                send_msg(client_sock, ('table', self.get_info()))

            elif head == 'sitdown':
                seat = int(data)
                if self.sit_down(client_sock, seat):
                    self.broadcast('### {} seats down at {}'.format(
                        client_sock.getpeername(), seat))
                    msg = ('suc_sit', seat)
                else:
                    msg = 'err_sit'

                send_msg(client_sock, msg)

                # if game is waiting for some player sit down to start
                if self.status == 'waiting':
                    self.__game_thread = Thread(target=self.game_body)
                    self.__game_thread.start()

            elif head == 'standup':
                seat = self.get_seat(client_sock)
                if seat >= 0:
                    self.stand_up(seat)
                    msg = 'suc_standup'
                else:
                    msg = 'err_standup'

                send_msg(client_sock, msg)

            elif head == 'bet':
                stakes = int(data)
                if self.current_turn\
                    and self.current_turn.sock is client_sock\
                    and self.status == 'betting':
                    if self.current_turn.bet(stakes):
                        msg = ('suc_bet', stakes)
                        self.__lock.release()
                    else:
                        msg = 'err_bet'
                else:
                    msg = 'err_bet'

                send_msg(client_sock, msg)

            elif head in ['insured', 'uninsured']:
                if self.current_turn\
                   and self.current_turn.sock is client_sock\
                   and self.status == 'insurance':
                    if head == 'insured':
                        self.current_turn.set_insurance(True)
                        msg = 'suc_insured'
                    else:
                        self.current_turn.set_insurance(False)
                        msg = 'suc_uninsured'
                    self.__lock.release()
                else:
                    msg = 'err_insurance'

                send_msg(client_sock, msg)

            elif head == 'hit':
                if self.current_turn\
                   and self.current_turn.sock is client_sock\
                   and self.status == 'drawing':
                    self.current_turn.hand.hit(self.deck)
                    self.__lock.release()
                    msg = 'suc_hit'
                    self.broadcast('### {} hit.'.format(self.current_turn.peername))
                else:
                    msg = 'err_hit'

                send_msg(client_sock, msg)


            elif head == 'stand':
                if self.current_turn\
                   and self.current_turn.sock is client_sock\
                   and self.status == 'drawing':
                    self.__sig = 'stand'
                    self.__lock.release()
                    msg = 'suc_stand'
                else:
                    msg = 'err_stand'

                send_msg(client_sock, msg)

            else:
                msg = 'unknow_cmd'
                send_msg(client_sock, msg)

        print('Client closed connection')
        seat = self.get_seat(client_sock)
        if seat is not None:
            self.stand_up(seat)
        client_sock.close()
