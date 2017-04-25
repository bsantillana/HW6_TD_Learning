# -*- coding: latin-1 -*-
import random
import sys
import os
import pickle

sys.path.append("..")  # so other modules can be found in parent dir
from Player import *
from Constants import *
from Construction import CONSTR_STATS
from Ant import UNIT_STATS
from Move import Move
from math import sqrt
from GameState import addCoords
from AIPlayerUtils import *
from pprint import pprint


##
# AIPlayer
# Description: The responsbility of this class is to interact with the game by
# deciding a valid move based on a given game state. This class has methods that
# will be implemented by students in Dr. Nuxoll's AI course.
#
# Variables:
#   playerId - The id of the player.
##
class AIPlayer(Player):
    # __init__
    # Description: Creates a new Player
    #
    # Parameters:
    #   inputPlayerId - The id to give the new player (int)
    ##
    def __init__(self, inputPlayerId):
        super(AIPlayer, self).__init__(inputPlayerId, "HW 6 Agent")

        # Tweaking these should definitely alter the success of the AI
        self.NUM_DESIRED_DRONES = 1
        self.NUM_DESIRED_WORKERS = 2
        self.MIN_DESIRED_FOOD = 2

        # We would like to know where our tunnel is
        self.myTunnel = None

        # Keep track of which player we are
        self.ID = inputPlayerId
        if inputPlayerId == PLAYER_ONE:
            self.enemyID = PLAYER_TWO
        else:
            self.enemyID = PLAYER_ONE

        # Our list of consolidated state objects
        self.consolidatedState = []

        ##
        # File I/O code. This searches the parent directory to find a pickle file which we will use to
        # import the states and their utilities
        #   NOTE: You may have to change the chdir call to a more specific file path if it doesn't work
        ##
        os.chdir('..')
        path = os.getcwd()
        for file in os.listdir(path):
            if file.endswith(".p"):
                self.readFile()
        # Setting the discount factor variable
        self.discountFact = 0.99
        # Setting the learning rate variable
        self.learningRate = 0.1
        # Creating the list of utilities to use when picking an action
        self.Utilities = []

    ##
    # getPlacement
    #
    # Description: The getPlacement method corresponds to the
    # action taken on setup phase 1 and setup phase 2 of the game.
    # In setup phase 1, the AI player will be passed a copy of the
    # state as currentState which contains the board, accessed via
    # currentState.board. The player will then return a list of 11 tuple
    # coordinates (from their side of the board) that represent Locations
    # to place the anthill and 9 grass pieces. In setup phase 2, the player
    # will again be passed the state and needs to return a list of 2 tuple
    # coordinates (on their opponent's side of the board) which represent
    # Locations to place the food sources. This is all that is necessary to
    # complete the setup phases.
    #
    # Parameters:
    #   currentState - The current state of the game at the time the Game is
    #       requesting a placement from the player.(GameState)
    #
    # Return: If setup phase 1: list of eleven 2-tuples of ints -> [(x1,y1), (x2,y2),?,(x10,y10)]
    #       If setup phase 2: list of two 2-tuples of ints -> [(x1,y1), (x2,y2)]
    ##
    def getPlacement(self, currentState):
        if currentState.phase == SETUP_PHASE_1:

            # We will setup our base to give food gatherers max freedom
            return [(0, 0), (5, 2),
                    (0, 3), (1, 3), (2, 3), (3, 3),
                    (4, 3), (5, 3), (6, 3),
                    (7, 3), (8, 3)]

        ##
        # Phase Two of setup... we will try to place the food as far away
        # from the enemy anthill/tunnel as possible
        elif currentState.phase == SETUP_PHASE_2:

            enemyConsts = getConstrList(currentState, self.enemyID, (ANTHILL, TUNNEL))
            enemyConstCords = [enemyConsts[0].coords, enemyConsts[1].coords]
            foodCoords = [enemyConsts[0].coords, enemyConsts[1].coords]
            dists = [0, 0]

            for x in range(0, 10):
                for y in range(6, 10):
                    if getConstrAt(currentState, (x, y)) == None:
                        # find the distance from this cell to the enemy tunnel
                        newDists = (stepsToReach(currentState, enemyConstCords[0], (x, y)),
                                    stepsToReach(currentState, enemyConstCords[1], (x, y)))

                        # If this is farther away, save it
                        if newDists[0] > dists[0]:
                            foodCoords[0] = (x, y)
                            dists[0] = newDists[0]
                            continue
                        if newDists[1] > dists[1]:
                            foodCoords[1] = (x, y)
                            dists[1] = newDists[1]

            return foodCoords

        # This should never happen
        return None

    ##
    # getMove
    # Description: The getMove method corresponds to the play phase of the game
    # and requests from the player a Move object. All types are symbolic
    # constants which can be referred to in Constants.py. The move object has a
    # field for type (moveType) as well as field for relevant coordinate
    # information (coordList). If for instance the player wishes to move an ant,
    # they simply return a Move object where the type field is the MOVE_ANT constant
    # and the coordList contains a listing of valid locations starting with an Ant
    # and containing only unoccupied spaces thereafter. A build is similar to a move
    # except the type is set as BUILD, a buildType is given, and a single coordinate
    # is in the list representing the build location. For an end turn, no coordinates
    # are necessary, just set the type as END and return.
    #
    # Parameters:
    #   currentState - The current state of the game at the time the Game is
    #       requesting a move from the player.(GameState)
    #
    # Return: Move(moveType [int], coordList [list of 2-tuples of ints], buildType [int]
    ##
    def getMove(self, currentState):
        # Creating a list of actions
        actions = []
        # Adding all of the possible moves to the actions list
        actions = listAllLegalMoves(currentState)
        # Creating a list of the next states we can be in
        nextStates = []
        # Removing the build moves from the actions list as we don't want to build any anys
        for i in actions:
            if type(i) == BUILD:
                actions.remove(i)
        # Getting the next states based on the actions we can take
        for i in actions:
            nextStates.append(getNextState(currentState, i))
        # Creating a list to put the consolidated states in
        nextConsolidatedStates = []
        # Adding the consolidated states to the list
        for i in nextStates:
            nextConsolidatedStates.append(self.consolidatState(i))
        # Creating a list of utilities
        utilityList = []
        # Getting the utilities of the states we can enter based on the utilities we have learned
        for i in range(0, len(nextConsolidatedStates)):
            for j in self.consolidatedState:
                if dir(j) == dir(nextConsolidatedStates[i]):
                    utilityList.append(j.Utility)
                else:
                    utilityList.append(-10)
        # Setting the max utility we've seen already to a very low number
        maxUtil = -100000
        maxIndex = 0
        # Search through the possible states and pick the one that has the highest utility and get its index in the list
        for i in range(0, len(utilityList)):
            if utilityList[i] > maxUtil:
                maxUtil = utilityList[i]
                maxIndex = i
        # Choose the action that will lead us to the state with the highest utility
        return actions[maxIndex]



    ##
    # getAttack
    # Description: The getAttack method is called on the player whenever an ant completes
    # a move and has a valid attack. It is assumed that an attack will always be made
    # because there is no strategic advantage from withholding an attack. The AIPlayer
    # is passed a copy of the state which again contains the board and also a clone of
    # the attacking ant. The player is also passed a list of coordinate tuples which
    # represent valid locations for attack. Hint: a random AI can simply return one of
    # these coordinates for a valid attack.
    #
    # Parameters:
    #   currentState - The current state of the game at the time the Game is requesting
    #       a move from the player. (GameState)
    #   attackingAnt - A clone of the ant currently making the attack. (Ant)
    #   enemyLocation - A list of coordinate locations for valid attacks (i.e.
    #       enemies within range) ([list of 2-tuples of ints])
    #
    # Return: A coordinate that matches one of the entries of enemyLocations. ((int,int))
    ##
    def getAttack(self, currentState, attackingAnt, enemyLocations):
        # Employ ancient roman battle techniques to defeat the enemy
        return enemyLocations[0]

    ##
    # registerWin
    # Description: The last method, registerWin, is called when the game ends and simply
    # indicates to the AI whether it has won or lost the game. This is to help with
    # learning algorithms to develop more successful strategies.
    #
    # Parameters:
    #   hasWon - True if the player has won the game, False if the player lost. (Boolean)
    #
    def registerWin(self, hasWon):
        # method templaste, not implemented
        # Each time your agent completes a game, save your current state utilities to a file.

        # This was used to write to the pickle file after every game
        #self.writeFile()
        pass

    ##
    # makePath
    #
    # Description: makePath is a modified version of createPathTowards in the AIPlayerUtils file. it will
    #              create a path towards whatever your destination is, while also returning any ants that
    #              are owned by the AI and are in the path. This is useful for moving ants out of the way
    #              of other ants.
    # Parameters:
    #   currentState - The current state object for the game
    #   sourceCoords - The coordinates to start the path at
    #   targetCoords - The coordinates we are trying to get to
    #   movement - The movement value for that particular ant
    #
    def makePath(self, currentState, sourceCoords, targetCoords, movement):
        distToTarget = approxDist(sourceCoords, targetCoords)
        path = [sourceCoords]
        curr = sourceCoords
        antsInPath = []

        # keep adding steps to the path until movement runs out
        while (movement > 0):

            found = False  # was a new step found to add to the path
            for coord in listAdjacent(sourceCoords):
                # is this a step headed in the right direction?
                if (approxDist(coord, targetCoords) < distToTarget):

                    # how much movement does it cost to get there?
                    constr = getConstrAt(currentState, coord)
                    moveCost = 1  # default cost
                    if (constr != None):
                        moveCost = CONSTR_STATS[constr.type][MOVE_COST]

                    # if I have enough movement left then add it to the path
                    if (moveCost <= movement):
                        # add the step to the path
                        found = True
                        path.append(coord)

                        # See if there's an ant there, if so, add it to our ant in path list
                        ant = getAntAt(currentState, coord)
                        if ant != None:
                            if ant.player == PLAYER_TWO:
                                antsInPath.append(ant)
                            else:
                                # If it is not our ant, then this is as far as we can go
                                return [path, antsInPath]

                        # restart the search from the new coordinate
                        movement = movement - moveCost
                        sourceCoords = coord
                        break
            if (not found):
                break  # no usable steps found

        return [path, antsInPath]

    ##
    # moveAntInPath
    #
    # Description: Generates a move object for any ant that is in the path of the given ant. The direction
    #              the ant moves is rather arbitrary, it's only goal is to move out of the path, whatever
    #              that means.
    # Parameters:
    #   currentState - The current state of the game
    #   ant - The ant object we want to move
    #   antDest - Where the ant is trying to go
    #   antType - The type of the ant, used to find out movement
    ##
    def moveAntInPath(self, currentState, ant, antDest, antType):
        pathWithAnts = self.makePath(currentState, ant.coords, antDest, UNIT_STATS[antType][MOVEMENT])
        path = pathWithAnts[0]
        antsInPath = pathWithAnts[1]

        # If there are ants in the way and they haven't been moved, try to move them
        for antInPath in antsInPath:
            if not antInPath.hasMoved:
                for cell in listReachableAdjacent(currentState, antInPath.coords,
                                                  UNIT_STATS[antInPath.type][MOVEMENT]):
                    if cell not in path and getConstrAt(currentState, cell) is None:
                        path = createPathToward(currentState, antInPath.coords, cell,
                                                UNIT_STATS[antInPath.type][MOVEMENT])
                        return Move(MOVE_ANT, path, None)

        # No ant can be moved
        return None

    ##
    #   findPathCost
    #
    #   Description: Calculates how many steps it would take to complete a path
    #
    #   Parameters:
    #       path - The path in question, follows the format [(srcX, srcY), ..., (dstX, dstY)]
    ##
    def findPathCost(self, currentState, path):
        # If our path isn't long enough or it is a cycle then cost is 0
        if len(path) < 3 or path[0] == path[len(path) - 1]:
            return 0

        # Path starts at 0 cost
        pathCost = 0
        for cell in path:

            # Get the cell cost, add it to our running total
            cellCost = 1  # default
            constAtCell = getConstrAt(currentState, cell)
            if constAtCell is not None:
                cellCost = CONSTR_STATS[constAtCell.type][MOVE_COST]

            pathCost += cellCost

        return pathCost

    ###
    # writeFile
    #
    # Description: Takes the objects from our consolidated states and writes them to a pickle file
    #
    # Parameters:
    #   self - the object that has called this function
    ###
    def writeFile(self):
        # Opening the file
        f = open('santilla18_kister19.p', 'wb')
        # Writing the list of objects to the output file
        pickle.dump(self.consolidatedState,f)
        # Closing the file
        f.close()

    ###
    # readFile
    #
    # Description: Takes the objects from a pickle file and stores them into our consolidated states list
    #
    # Parameters:
    #   self - the object that has called this function
    #
    ###
    def readFile(self):
        # Opening the file
        f = open('santilla18_kister19.p', 'rb')
        # Retrieving the data from the file and putting it into our consolidated states list
        self.consolidatedState = pickle.load(f)
        # Printing the states to the terminal for the user to see them
        print self.consolidatedState
        # Closing the file
        f.close()
    ##
    # hasWon(int)
    # Description: Determines whether the game has ended in victory for the given player.
    #
    # Parameters:
    #   playerId - The ID of the player being checked for winning (int)
    #   currentState - The current state of the game
    #
    # Returns: True if the player with playerId has won the game.
    ##
    def hasWon(self, currentState, playerId):
        opponentId = (playerId + 1) % 2

        if ((currentState.phase == PLAY_PHASE) and
            ((currentState.inventories[opponentId].getQueen() == None) or
                    (currentState.inventories[opponentId].getAnthill().captureHealth <= 0) or
                    (currentState.inventories[playerId].foodCount >= FOOD_GOAL) or
                    (currentState.inventories[opponentId].foodCount == 0 and
                    len(currentState.inventories[opponentId].ants) == 1))):
            return True

        else:
            return False

    ##
    # reward(float)
    # Description: Takes in a state and generates the reward for that given state.
    #
    # Parameters:
    #   currentState - The current state of the game
    #
    # Returns: The reward for the given state
    ##
    def reward(self, currentState):
        # If we have won, return a 1
        if self.hasWon(currentState, self.playerId):
            return 1
        # If we have lost, return a 0
        elif self.hasWon(currentState, (self.playerId+1)%2):
            return 0
        # If we haven't won or lost, return -0.01
        else:
            return -0.01

    ##
    # consolidatState
    # Description: Takes a game state and returns a consolidated version of it.
    #
    # Parameters:
    #   currentState - The current state of the game
    ##
    def consolidatState(self, currentState):
        # Getting if we have won/lost
        aiWon = self.hasWon(currentState,self.playerId)
        enemyWon = self.hasWon(currentState, (self.playerId+1)%2)
        # Creating a consolidated version of the current state
        newState = Consolidation(currentState, aiWon, enemyWon)
        # Appending this state to our list of consolidated states
        self.consolidatedState.append(newState)

    ##
    # tdLearning
    # Description: Performs the TD Learning algorithm on the set of consolidated states we have
    #
    # Parameters:
    #   cs - The current state of the game
    #   nextState - The next state of the game we are going to be in
    ##
    def tdLearning(self,cs,nextState):
        # Creating a consolidated object out of the next state
        obj = Consolidation(nextState,self.hasWon(cs,self.playerId),self.hasWon(cs, (self.playerId+1)%2))
        # Getting the utility
        utility = obj.Utility
        # Searching through the list of states to see if we already have a utility for this state. If so use that utility
        for i in self.consolidatedState:
            if dir(obj) == dir(i):
                utility = i.Utility
        # Updating all of the previous states based on the TD Learning algorithm
        for i in self.consolidatedState:
            i.Utility = i.Utility + self.learningRate*(self.reward(cs)+self.discountFact*((utility)-i.Utility))


##
# Consolidation
# Description: This class contains some elements of an Antics state. It contains what we have
# deemed the most important parts of the state to use to generate an utility
#
#
# Variables:
#   currentState - The current state to be consolidated
#   iWon - A boolean variable telling us if we have won
#   iLost - A boolean variable telling us if we have lost
##
class Consolidation(Player):
    # __init__
    # Description: Creates a new Player
    #
    # Parameters:
    #   inputPlayerId - The id to give the new player (int)
    ##
    def __init__(self, currentState, iWon, iLost):
        # If I have won this is a good utility, so set it to be a large number
        if iWon:
            self.Utility = 1000
        # If I have lost this is a bad utility, so set it to be a large negative number
        elif iLost:
            self.Utility = -1000
        # Otherwise set my utility to a random number
        else:
            self.Utility = random.randint(0,100)

        ##
        # The following code gathers information about the state to use to create the variables for the class
        ##
        self.myTunnel = None

        if (self.myTunnel == None):
            self.myTunnel = getConstrList(currentState, currentState.whoseTurn, (TUNNEL,))[0]

        for inv in currentState.inventories:
            if inv.player == currentState.whoseTurn:
                inventory = inv
            else:
                enemyInv = inv

        antHill = inventory.getAnthill()

        # Distinguish our ants
        workers = []
        drones = []
        soldiers = []
        rangers = []
        queen = []
        for ant in inventory.ants:
            antType = ant.type
            workers.append(ant) if antType == WORKER else 0
            drones.append(ant) if antType == DRONE else 0
            soldiers.append(ant) if antType == SOLDIER else 0
            rangers.append(ant) if antType == R_SOLDIER else 0
            queen.append(ant) if antType == QUEEN else 0

        # Distinguish enemy ants
        enemyworkers = []
        enemydrones = []
        enemysoldiers = []
        enemyrangers = []
        enemyqueen = []
        for ant in enemyInv.ants:
            antType = ant.type
            enemyworkers.append(ant) if antType == WORKER else 0
            enemydrones.append(ant) if antType == DRONE else 0
            enemysoldiers.append(ant) if antType == SOLDIER else 0
            enemyrangers.append(ant) if antType == R_SOLDIER else 0
            enemyqueen.append(ant) if antType == QUEEN else 0

        # Obtain our food list and prune the food list
        # to only contain our food
        foodList = getConstrList(currentState, None, (FOOD,))
        enemyFood = []
        for food in foodList:
            if food.coords[1] > 3:
                enemyFood.append(food)

        for food in enemyFood:
            foodList.remove(food)

        # Prune ant list to contain only our ants
        antsToRemove = []
        for ant in workers:
            if ant.player != currentState.whoseTurn:
                antsToRemove.append(ant)

        for ant in antsToRemove:
            workers.remove(ant)


        ##
        # Setting the class variables using the information from the state gathered above
        #
        self.myNumFood = inventory.foodCount
        self.enemyNumFood = enemyInv.foodCount
        self.myNonWorkers = len(workers)
        self.enemyNonWorkers = len(enemyworkers)
        self.distToTunnel = []
        self.enemyDistToQueen = []

        ##
        # Getting the information to add to the distance to tunnel and distance to queen lists
        ##
        tunnelCoords = self.myTunnel.coords
        for ant in inventory.ants:
            antCoords = ant.coords
            valuex = abs(tunnelCoords[0] - antCoords[0])
            valuey = abs(tunnelCoords[1] - antCoords[1])
            value = sqrt(abs(valuex - valuey))
            self.distToTunnel.append(value)

        queenCoords = inventory.getQueen().coords
        for ant in enemysoldiers:
            enemyCoords = ant.coords
            valuex = abs(enemyCoords[0] - antCoords[0])
            valuey = abs(enemyCoords[1] - antCoords[1])
            value = sqrt(abs(valuex - valuey))
            self.enemyDistToQueen.append(value)
