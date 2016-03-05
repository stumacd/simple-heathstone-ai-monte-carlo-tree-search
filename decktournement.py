# This is a very simple implementation of the UCT Monte Carlo Tree Search algorithm in Python 2.7.
# The function UCT(rootstate, itermax, verbose = False) is towards the bottom of the code.
# It aims to have the clearest and simplest possible code, and for the sake of clarity, the code
# is orders of magnitude less efficient than it could be made, particularly by using a 
# state.GetRandomMove() or state.DoRandomRollout() function.
# 
# Example GameState classes for Nim, OXO and Othello are included to give some idea of how you
# can write your own GameState use UCT in your 2-player game. Change the game to be played in 
# the UCTPlayGame() function at the bottom of the code.
# 
# Written by Peter Cowling, Ed Powley, Daniel Whitehouse (University of York, UK) September 2012.
# 
# Licence is granted to freely use and distribute for any sensible/legal purpose so long as this comment
# remains in any distributed code.
# 
# For more information about Monte Carlo Tree Search check out our web site at www.mcts.ai

from math import *
import random
import copy

STARTING_HLTH = 30
HAND_CARD_LIMIT = 10
DECK_SIZE = 30
STARTING_HAND_SIZE = 3
MAX_MANA = 10

tree = dict()

PRINTS = True

class Movetype:
    EndTurn = 1
    PlayCard = 2
    Attack = 3

def pp(self):
    if self[0] is 1:
        return "END TURN"
    elif self[0] is 2:
        s = "PLAY: "
        s += str(self[1])
        return s
    else:
        s = "ATTACK: "
        s += str(self[1]) + " -> "
        if self[2] == -1:
            s += "FACE"
        else:
            s += str(self[2])
        return s

class Card:
    def __init__(self,cost = 1, atk = 1, hth = 1):
        self.cost = cost
        self.atk = atk
        self.hth = hth
        self.sick = True

    def __repr__(self):
        s = str(self.atk) + "/" + str(self.hth) + "(" + str(self.cost) + ")"
        if self.sick:
            s += "S"
        return s

    def __lt__(self,other):
        return self.cost < other.cost

    def __hash__(self):
        return 1 * self.atk + 10 * self.cost + 100 * self.cost + self.sick * 10000

class Player:
    def __init__(self, name="Player",hp=STARTING_HLTH,idf = 1):
        self.name = name
        self.hp = hp
        self.deck = []
        self.hand = []
        self.board = []
        self.fatigue_ctr = 1
        self.idf = idf

    def DrawCard(self):
        if len(self.deck) > 0:
            if len(self.hand) > HAND_CARD_LIMIT:
                self.deck.pop
            else:
                self.hand.append(self.deck.pop())
        else:
            #print("Fatigue!")
            self.hp -= self.fatigue_ctr
            self.fatigue_ctr += 1

    def __repr__(self):
        return str(self.name)

class Game:

    def __init__(self,deck1,deck2):
        self.player = [Player("Player1",idf=0),Player("Player2",idf=1)]
        #for i in range(2*DECK_SIZE):
        #    a = random.randint(1,MAX_MANA)
        #    b = random.randint(1,MAX_MANA)
        #    c = (a + b) // 2
        #    self.player[i % 2].deck.append(Card(atk = a, hth = b, cost = c))
        random.shuffle(deck1)
        random.shuffle(deck2)
        self.player[0].deck = deck1 
        self.player[1].deck = deck2
        self.mana = 1
        self.tempmana = 1
        self.current_player = self.player[0]
        self.opp_player = self.player[1]
        self.turn = 1
        # NB we do the initial draw for player 1 here.
        for i in range(0,(2*(STARTING_HAND_SIZE+1))):
            self.player[i % 2].DrawCard()
        # Add coin
        coin = Card(cost=0,atk=0,hth=0)
        self.player[1].hand.append(coin)
        
    def __hash__(self):
        # useful elements
        s = 0
        for i in self.current_player.board:
            s ^= hash(i)
        for i in self.opp_player.board:
            s ^= hash(i)
        s ^= self.opp_player.hp*600
        s ^= self.tempmana * 7000
        return s

    def IncreaseMana(self):
        self.mana = min(MAX_MANA, self.mana + 1)

    def Clone(self):
        st = Game([],[])
        st = copy.deepcopy(self)
        return st

    def SwitchActivePlayer(self):
        self.current_player, self.opp_player = self.opp_player, self.current_player

    def DoMove(self, move):
        """ Update a state by carrying out the given move.
            Must update playerJustMoved.
        """

        if move[0] is Movetype.EndTurn:
            if self.current_player == self.player[1]:
                self.IncreaseMana()
            for i in self.current_player.board:
                i.sick = False
            self.SwitchActivePlayer()
            self.tempmana = self.mana
            self.current_player.DrawCard()

        elif move[0] is Movetype.PlayCard:
            # Test can be tightened later
            if move[1].cost is 0:
                # Coin
                self.tempmana += 1
                self.current_player.hand.pop(move[2])
                return

            self.tempmana -= move[1].cost
            self.current_player.board.append(self.current_player.hand.pop(move[2]))
            move[1].sick = True

        elif move[0] is Movetype.Attack:
            attacker = self.current_player.board[move[1]]
            attacker.sick = True
            if move[2] is not -1:
                defender = self.opp_player.board[move[2]]

                if attacker.hth - defender.atk <= 0:
                    self.current_player.board.remove(attacker)
                else:
                    attacker.hth -= defender.atk

                if defender.hth - attacker.atk <= 0:
                    self.opp_player.board.remove(defender)
                else:
                    defender.hth -= attacker.atk

            else:
                # Hero
                self.opp_player.hp -= attacker.atk
        
    def GetMoves(self):
        """ Get all possible moves from this state.
        """

        # Sometimes MCTS is a fickle mistress and the random playouts make
        # very poor decisions. Suchs as not attacking face and ending the turn
        # instead, or going face when the opponent has lethal on board.
        # I will code out these cases to avoid very poor decisions.
        # This should also make the random playouts a little more sensible 
        # allowing hopefully more insight.

        if self.player[0].hp <= 0 or self.player[1].hp <= 0:
            return []

        valid_moves = []

        for idx,i in enumerate(self.current_player.hand):
            if i.cost <= self.tempmana:
                valid_moves.append([Movetype.PlayCard,i,idx])
        # My lethal?
        my_atk_tot = 0
        for minion in self.current_player.board:
            if minion.sick:
                continue
            my_atk_tot += minion.atk
        if self.opp_player.hp < my_atk_tot:
            for idx,i in enumerate(self.current_player.board):
                if i.sick:
                    continue
                valid_moves.append([Movetype.Attack,idx,-1])
            return valid_moves
        
        # Does opp have lethal on board?
        opp_atk_tot = 0
        for minion in self.opp_player.board:
            opp_atk_tot += minion.atk
        lethal_on_board = False
        if self.current_player.hp < opp_atk_tot:
            lethal_on_board = True

        for idx,i in enumerate(self.current_player.board):
            if i.sick:
                continue
            for jdx,j in enumerate(self.opp_player.board):
                valid_moves.append([Movetype.Attack,idx,jdx])
            if not lethal_on_board:
                valid_moves.append([Movetype.Attack,idx,-1])

        free_face_hit = True

        for i in valid_moves:
            if i[2] != -1:
                free_face_hit = False

        if not free_face_hit or not valid_moves:
            valid_moves.append([Movetype.EndTurn])

        return valid_moves

    
    def GetResult(self, player_v):
        """ Get the game result from the viewpoint of playerjm. 
        """
        #print(player_v)
        if self.player[player_v].hp <= 0:
            if self.player[1 - player_v].hp <= 0:
                # Draw
                return 0.1
            else:
                return 0.0
        elif self.player[1 - player_v].hp <= 0:
            return 1.0
        else:
            # Shouldn't get here
            print("Error!!!")
            return 0.5

    def __repr__(self):
        """ Don't need this - but good style.
        """
        s = "* " +  str(self.current_player.name) 
        s += "'s turn - " + str(self.tempmana) + "/" + str(self.mana) + " mana \n"
        s += "| " + str(self.player[0]) + " " + str(self.player[0].hp) +"\n> "
        for i in self.player[0].hand:
            s += str(i) + " "
        s += "\n| "   
        for i in self.player[0].board:
            s += str(i) + " "
        s += "\n| "
        for i in self.player[1].board:
            s += str(i) + " "
        s += "\n> "
        for i in self.player[1].hand:
            s += str(i) + " "
        s += "\n| " + str(self.player[1].name) + " " + str(self.player[1].hp) + "\n"
        return s

class Node:
    """ A node in the game tree. Note wins is always from the viewpoint of playerJustMoved.
        Crashes if state not specified.
    """

    counter = 0

    def __init__(self, move = None, parent = None, state = None):
        Node.counter += 1
        self.move = move # the move that got us to this node - "None" for the root node
        self.parentNode = parent # "None" for the root node
        self.childNodes = []
        self.wins = 0
        self.visits = 0
        if move and (move[0] == Movetype.EndTurn):
            self.untriedMoves = []
            self.playerJustMoved = 1-state.current_player.idf
        else:
            self.untriedMoves = state.GetMoves()
            self.playerJustMoved = state.current_player.idf
        self.hash = hash(state)
        tree[self.hash] = self
        
    def UCTSelectChild(self):
        """ Use the UCB1 formula to select a child node. Often a constant UCTK is applied so we have
            lambda c: c.wins/c.visits + UCTK * sqrt(2*log(self.visits)/c.visits to vary the amount of
            exploration versus exploitation.
        """
        s = max(self.childNodes, key = lambda c: c.wins/c.visits + sqrt(2*log(self.visits)/c.visits))
        return s
    
    def AddChild(self, m, s):
        """ Remove m from untriedMoves and add a new child node for this move.
            Return the added child node
        """
        #h = hash(s)
        #print(h)
        # if h in tree:
        #     n = tree[h]
        # else:
        #     n = Node(move = m, parent = self, state = s)
        #     tree[h] = n

        if hash(s) in tree and m[0] is not Movetype.EndTurn:
            #State already made
            #print(hash(s))
            #print("State already made!")
            self.untriedMoves.remove(m)
            return #tree[hash(s)]
        else:
            n = Node(move = m, parent = self, state = s)    
            self.untriedMoves.remove(m)
            self.childNodes.append(n)
            return n
    
    def Update(self, result):
        """ Update this node - one additional visit and result additional wins. result must be from the viewpoint of playerJustmoved.
        """
        #print(result)
        self.visits += 1
        self.wins += result

    def __repr__(self):
        return "[M:" + str(self.move) + " W/V:" + str(self.wins) + "/" + str(self.visits) + " H:" + str(self.hash) + "]"

    def TreeToString(self, indent):
        s = self.IndentString(indent) + str(self)
        for c in self.childNodes:
             s += c.TreeToString(indent+1)
        return s

    def IndentString(self,indent):
        s = "\n"
        for i in range (1,indent+1):
            s += "| "
        return s

    def ChildrenToString(self):
        s = ""
        for c in sorted(self.childNodes,key =lambda c: c.move ):
             s += str(c) + "\n"
        return s


def UCT(rootstate, itermax, verbose = False):
    """ Conduct a UCT search for itermax iterations starting from rootstate.
        Return the best move from the rootstate.
        Assumes 2 alternating players (player 1 starts), with game results in the range [0.0, 1.0]."""

    tree.clear()
    # TODO slide to the next position keeping the using tree benefiting from the subtree playouts.
    rootnode = Node(state = rootstate)

    for i in range(itermax):
        #print(i)
        node = rootnode
        state = rootstate.Clone()

        # Select
        #print("Select")
        while node.untriedMoves == [] and node.childNodes != []: # node is fully expanded and non-terminal
            node = node.UCTSelectChild()
            state.DoMove(node.move)

        # Expand
        #print("Expand")
        if node.untriedMoves != [] and node is not None: # if we can expand (i.e. state/node is non-terminal)
            m = random.choice(node.untriedMoves) 
            state.DoMove(m)
            node = node.AddChild(m,state) # add child and descend tree

        #print("Rollout")
        # Rollout - this can often be made orders of magnitude quicker using a state.GetRandomMove() function
        # TODO make the opponent's hand unknown so that we can represent the imperfect information.
        while state.GetMoves() != []: # while state is non-terminal
            state.DoMove(random.choice(state.GetMoves()))

        #print(state)

        # Backpropagate
        #print("Backpropagate")
        while node != None: # backpropagate from the expanded node and work back to the root node
            #print (node.playerJustMoved)
            node.Update(state.GetResult(node.playerJustMoved)) # state is terminal. Update node with result from POV of node.playerJustMoved
            node = node.parentNode

    # Output some information about the tree - can be omitted
    if PRINTS:
        if (verbose): print (rootnode.TreeToString(0))
        else: print (rootnode.ChildrenToString())

    return max(rootnode.childNodes, key = lambda c: c.visits).move # return the move that was most visited
                
def UCTPlayGame(d1,d2):
    """ Play a sample game between two UCT players where each player gets a different number 
        of UCT iterations (= simulations = tree nodes).
    """
    state = Game(d1,d2)

    while (state.player[0].hp > 0 and state.player[1].hp > 0):
        if PRINTS:
            print (str(state))
        m = UCT(rootstate = state, itermax = 1000, verbose = True) # play with values for itermax and verbose = True
        if PRINTS:
            print ("Best Move: " + pp(m) + "\n")
        state.DoMove(m)
        # Attempt to hold tree from node that we moved to.

    if state.GetResult(state.current_player.idf) == 1.0:
        if PRINTS:
            print (str(state.current_player) + " wins!")
        return state.current_player.idf
    elif state.GetResult(state.current_player.idf) == 0.0:
        if PRINTS:
            print (str(state.opp_player) + " wins!")
        return state.opp_player.idf
    #else: 
        #print "Nobody wins!"
    if PRINTS:
        print (str(state))

if __name__ == "__main__":
    """ Play a single game to the end using UCT for both players. 
    """
    random.seed(2)
    # make 10 decks

    decks = []
    for i in range(0,10):
        d = []
        for j in range(0,30):
            a = random.randint(1,MAX_MANA)
            b = random.randint(1,MAX_MANA)
            c = (a + b) // 2
            d.append(Card(atk = a, hth = b, cost = c))
        decks.append(d)

    winner = [0] * 10

    for idx,d in enumerate(decks):
        print(sorted(d))
        print(winner[idx])

    for j in range(1,100):
        i = int(j % 100)
        print(j)
        if (i/10) is (i%10):
            continue
        w = UCTPlayGame(copy.deepcopy(decks[i // 10]), copy.deepcopy(decks[i % 10]))
        #print(Node.counter)
        if w == 0:
            winner[i//10] += 1
        else:
            winner[i%10] += 1

    for idx,d in enumerate(decks):
        print(sorted(d))
        print(winner[idx])
