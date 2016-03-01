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

# Using a Monte Carlo Tree Search Framework create an AI agent to play a very simple version
# of Blizzard's CCG HearthStone

import sys
from math import *
import random
import copy

STARTING_HLTH = 30
HAND_CARD_LIMIT = 10
DECK_SIZE = 30
STARTING_HAND_SIZE = 3
MAX_MANA = 10

class Movetype:
    EndTurn = 1
    PlayCard = 2
    Attack = 3

def pp(self):
    if self is 1:
        return "END TURN"
    elif self is 2:
        return "PLAY"
    else:
        return "ATTACK"

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
        s = str(self.name) + " " + str(self.hp)
        return s

class Game:

    def __init__(self):
        self.player = [Player("Player1",idf=0),Player("Player2",idf=1)]
        for i in range(2*DECK_SIZE):
            a = random.randint(1,MAX_MANA)
            b = random.randint(1,MAX_MANA)
            c = (a + b) // 2
            self.player[i % 2].deck.append(Card(atk = a, hth = b, cost = c))
        self.mana = 1
        self.tempmana = 1
        self.current_player = self.player[0]
        self.opp_player = self.player[1]
        self.turn = 1
        # NB we do the initial draw for player 1 here.
        for i in range(0,(2*STARTING_HAND_SIZE)+1):
            self.player[i % 2].DrawCard()
        # TODO Add coin

    def IncreaseMana(self):
        self.mana = min(MAX_MANA, self.mana + 1)

    def Clone(self):
        st = Game()
        st = copy.deepcopy(self)
        return st

    def SwitchActivePlayer(self):
        self.current_player, self.opp_player = self.opp_player,self.current_player

    def DoMove(self, move):

        if move[0] is Movetype.EndTurn:
            if self.current_player == self.player[1]:
                self.IncreaseMana()
            for i in self.current_player.board:
                i.sick = False
            self.SwitchActivePlayer()
            self.tempmana = self.mana
            self.current_player.DrawCard()

        elif move[0] is Movetype.PlayCard:
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

        if self.player[0].hp <= 0 or self.player[1].hp <= 0:
            return []

        valid_moves = [[Movetype.EndTurn]]

        for idx,i in enumerate(self.current_player.hand):
            if i.cost <= self.tempmana:
                valid_moves.append([Movetype.PlayCard,i,idx])

        for idx,i in enumerate(self.current_player.board):
            if i.sick:
                continue
            for jdx,j in enumerate(self.opp_player.board):
                valid_moves.append([Movetype.Attack,idx,jdx])
            valid_moves.append([Movetype.Attack,idx,-1])

        return valid_moves

    def GetResult(self, player_v):
        
        if self.player[player_v].hp <= 0:
            if self.player[1 - player_v].hp <= 0:
                # Draw
                return 0.1
            else:
                return 0.0
        elif self.player[1 - player_v].hp <= 0:
            return 1.0
        else:
            print("Error!!!")
            return 0.5

    def __repr__(self):

        s = "* " +  str(self.current_player.name) + " turn - " + str(self.tempmana) + "/" + str(self.mana) + " mana \n"
        s += "| " + str(self.player[0]) + "\n> "
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
        s += "\n| " + str(self.player[1]) + "\n"
        return s

class Node:

    def __init__(self, move = None, parent = None, state = None):
        self.move = move 
        self.parentNode = parent # "None" for the root node
        self.childNodes = []
        self.wins = 0
        self.visits = 0
		# The player that 'finished' the game is related to the End Turn 
        if move and (move[0] == Movetype.EndTurn):
            self.untriedMoves = []
            self.playerJustMoved = 1-state.current_player.idf
        else:
            self.untriedMoves = state.GetMoves()
            self.playerJustMoved = state.current_player.idf

    def UCTSelectChild(self):
        s = max(self.childNodes, key = lambda c: c.wins/c.visits +
sqrt(2*log(self.visits)/c.visits))
        return s

    def AddChild(self, m, s):
        n = Node(move = m, parent = self, state = s)
        self.untriedMoves.remove(m)
        self.childNodes.append(n)
        return n

    def Update(self, result):
        self.visits += 1
        self.wins += result

    def __repr__(self):
        return "[M:" + str(self.move) + " W/V:" + str(self.wins) + "/" + str(self.visits) + " U:" + str(self.untriedMoves) + "]"

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
        for c in self.childNodes:
             s += str(c) + "\n"
        return s


def UCT(rootstate, itermax, verbose = False):
    rootnode = Node(state = rootstate)

    for i in range(itermax):
        node = rootnode
        state = rootstate.Clone()

        # Select
        while node.untriedMoves == [] and node.childNodes != []: 
            node = node.UCTSelectChild()
            state.DoMove(node.move)

        # Expand
        if node.untriedMoves != []: 
            m = random.choice(node.untriedMoves)
            state.DoMove(m)
            node = node.AddChild(m,state) # add child and descend tree

        # Rollout
        while state.GetMoves() != []: # while state is non-terminal
            state.DoMove(random.choice(state.GetMoves()))

        # Backpropagate
        while node != None: 
            node.Update(state.GetResult(node.playerJustMoved)) 
            node = node.parentNode

    if (verbose): print(rootnode.TreeToString(0))
    else: print(rootnode.ChildrenToString())

    return max(rootnode.childNodes, key = lambda c: c.visits).move

def UCTPlayGame():

	# Seed with an int so games can be reproduced
    random.seed(1)
    state = Game()

    while (state.player[0].hp > 0 and state.player[1].hp > 0):
        print(str(state))
        m = UCT(rootstate = state, itermax = 1000, verbose = False)
        print("Best Move: " + pp(m[0]) + ": " + str(m[1:])+ "\n")
        state.DoMove(m)
    if state.GetResult(state.current_player.idf) == 1.0:
        print(str(state.current_player) + " wins!")
    elif state.GetResult(state.current_player.idf) == 0.0:
        print(str(state.opp_player) + " wins!")
    else:
        print ("Nobody wins!")
    print(str(state))

if __name__ == "__main__":
    UCTPlayGame()
