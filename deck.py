'''Module about deck, card'''
import random

class Card(object):
    '''Card'''
    def __init__(self, suit, val):
        self.suit = suit
        self.value = val

    def __repr__(self):
        return "({}, {})".format(self.suit, self.value)


class Deck(list):
    '''deck'''
    def __init__(self, n=1):
        super().__init__()
        for _ in range(n):
            for suit in ['Spade', 'Club', 'Diamond', 'Heart']:
                for val in 'A23456789TJQK':
                    self.append(Card(suit, val))

    def shuffle(self, n=1):
        '''shuffle deck'''
        for _ in range(n):
            random.shuffle(self)

    def draw(self):
        '''draw a card from deck'''
        return self.pop()


class Hand(Deck):
    def __init__(self):
        super().__init__(0)

    def hit(self, deck, n=1):
        for _ in range(n):
            card = deck.draw()
            self.append(card)

    def clear(self):
        self.__init__()

    def count_points(self):
        count = 0
        ace_count = 0

        for i in self:
            if i.value in ['T', 'J', 'Q', 'K']:
                count += 10
            elif i.value != 'A':
                count += int(i.value)
            else:
                ace_count += 1

        for _ in range(ace_count):
            if count+11 > 21:
                count += 1
            elif ace_count == 1:
                count += 11
            else:
                count += 1

        return count
