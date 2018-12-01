import panda as cf
import random
from threading import Thread
import sys
from math import sqrt

# Python 3 backwards compatibility
try:
    input = raw_input
except NameError:
    pass

class AgniKai():
	def __init__( self, name ):
		# Initialize the Panda Colorfight Client
		self.game = cf.Game()
		self.game.JoinGame( name )

		# Initialize the variables
		self.lastAttack = None
		self.threshold = 4.0
		self.mode = 0
		self.MODE_EXPAND = 0
		self.MODE_LOOT = 1
		self.MODE_RECHARGE = 2

		# Initialize the starting game state
		self.game.Refresh()
		self.FetchInfo()

		# Initialize the threads
		self.playing = True
		self.refreshThread = Thread( target = self.Refresh )
		self.refreshThread.start()
		self.playThread = Thread( target = self.Play )
		self.playThread.start()
		self.stopThread = Thread( target = self.Stop )
		self.stopThread.start()

	"""
		Define the Thread Functions
	"""

	# Refreshes the Game State
	def Refresh( self ):
		while self.playing:
			self.game.Refresh()
			self.FetchInfo()

	# Runs all the AI actions
	def Play( self ):
		while self.playing:
			self.GameLoop()

	# Allows for keyboard interrupt
	def Stop( self ):
		input()
		self.playing = False

	"""
		Convenience Functions
	"""

	# Checks if two cells are identical
	def SameCell( self, c1, c2 ):
		if c1 == None or c2 == None:
			return False
		return c1.x == c2.x and c1.y == c2.y

	# Returns the distance between two cells by perimeter
	def PerimeterDistance( self, c1, c2 ):
		return abs( c2.x - c1.x ) + abs( c2.y - c1.y )

	# Returns the distace between two cells by diagonal
	def DiagonalDistance( self, c1, c2 ):
		return sqrt( ( c2.x - c1.x ) ** 2 + ( c2.y - c1.y ) ** 2 )

	# Checks if the cell is one of the player's
	def OwnCell( self, cell ):
		return cell.owner == self.game.uid

	# Checks if the cell is one of an enemy
	def EnemyCell( self, cell ):
		return not self.OwnCell( cell ) and not cell.owner == 0

	# Checks if the cell is gold
	def GoldCell( self, cell ):
		return cell.cellType == "gold"

	# Checks if the cell is energy
	def EnergyCell( self, cell ):
		return cell.cellType == "energy"

	# Returns the cells adjacent to a specific cell
	def GetAdjacent( self, cell ):
		cellUp = self.game.GetCell( cell.x, cell.y - 1 )
		cellRight = self.game.GetCell( cell.x + 1, cell.y )
		cellDown = self.game.GetCell( cell.x, cell.y + 1 )
		cellLeft = self.game.GetCell( cell.x - 1, cell.y )
		return ( cellUp, cellRight, cellDown, cellLeft )

	# Checks the cell and updates the game state
	def CheckAdjacent( self, cell ):
		if not cell == None:
			if not self.OwnCell( cell ):
				self.adjacentCells.append( cell )
				if self.GoldCell( cell ):
					self.adjacentGoldNum += 1
					self.adjacentGoldCells.append( cell )
				elif self.EnergyCell( cell ):
					self.adjacentEnergyNum += 1
					self.adjacentEnergyCells.append( cell )
				elif self.EnemyCell( cell ):
					self.adjacentEnemyNum += 1
					self.adjacentEnemyCells.append( cell )
				else:
					self.adjacentNormalNum += 1
					self.adjacentNormalCells.append( cell )

	# A smarter implementation of the attack function
	def Attack( self, cell, boost = False ):
		if not self.SameCell( cell, self.lastAttack ):
			if cell.takeTime <= self.threshold and not cell.takeTime == -1:
				data = self.game.AttackCell( cell.x, cell.y, boost = boost )
				if data[ 0 ]:
					self.lastAttack = cell
					self.game.data[ "cells" ][ cell.x + cell.y * 30 ][ "t" ] = -1
					self.game.data[ "cells" ][ cell.x + cell.y * 30 ][ "o" ] = self.game.uid
				return data
			return ( False, None, "Too long to attack" )
		return ( False, None, "Same as the last cell" )

	# An implementation of attack that ensures the target is hit
	def EnsureAttack( self, cell, boost = False ):
		data = self.Attack( cell, boost = self.boost )
		while data[ 1 ] == 3:
			data = self.Attack( cell, boost = self.boost )
		return data

	# Get the game state
	def FetchInfo( self ):
		self.playerCells = []
		self.playerBases = []
		self.adjacentCells = []
		self.adjacentNormalCells = []
		self.adjacentGoldCells = []
		self.adjacentEnergyCells = []
		self.adjacentEnemyCells = []
		self.adjacentNormalNum = 0
		self.adjacentGoldNum = 0
		self.adjacentEnergyNum = 0
		self.adjacentEnemyNum = 0
		self.unclaimedGoldCells = []
		self.unclaimedEnergyCells = []
		self.unclaimedGoldNum = 0
		self.unclaimedEnergyNum = 0
		for x in range( self.game.width ):
			for y in range( self.game.height ):
				cell = self.game.GetCell( x, y )
				if self.OwnCell( cell ):
					if cell.isBase:
						self.playerBases.append( cell )
					else:
						self.playerCells.append( cell )
					cellUp, cellRight, cellDown, cellLeft = self.GetAdjacent( cell )
					self.CheckAdjacent( cellUp )
					self.CheckAdjacent( cellRight )
					self.CheckAdjacent( cellDown )
					self.CheckAdjacent( cellLeft )
				else:
					if self.GoldCell( cell ):
						self.unclaimedGoldNum += 1
						self.unclaimedGoldCells.append( cell )
					elif self.EnergyCell( cell ):
						self.unclaimedEnergyNum += 1
						self.unclaimedEnergyCells.append( cell )

	# Expansion mode
	def Expand( self ):
		if self.adjacentGoldNum > 0:
			for target in self.adjacentGoldCells:
				data = self.EnsureAttack( target, boost = self.boost )
				if data[ 0 ]:
					return
		if self.adjacentEnergyNum > 0:
			for target in self.adjacentEnergyCells:
				data = self.EnsureAttack( target, boost = self.boost )
				if data[ 0 ]:
					return
		if self.adjacentEnemyNum > 0 and ( self.adjacentNormalNum == 0 or random.randrange( 4 ) == 0 ):
			while self.adjacentEnemyNum > 0:
				target = self.adjacentEnemyCells.pop( random.randrange( self.adjacentEnemyNum ) )
				self.adjacentEnemyNum -= 1
				data = self.EnsureAttack( target, boost = self.boost )
				if data[ 0 ]:
					return
		elif self.adjacentNormalNum > 0:
			while self.adjacentNormalNum > 0:
				target = self.adjacentNormalCells.pop( random.randrange( self.adjacentNormalNum ) )
				self.adjacentNormalNum -= 1
				data = self.EnsureAttack( target, boost = self.boost )
				if data[ 0 ]:
					return

	# Recharge mode
	def Recharge( self ):
		targetCells = []
		for targetEnergy in self.unclaimedEnergyCells:
			for adjacent in self.adjacentCells:
				targetCells.append( ( adjacent, self.PerimeterDistance( targetEnergy, adjacent ), self.DiagonalDistance( targetEnergy, adjacent ) ) )
		targetCells.sort( key = lambda tup: ( tup[ 1 ], tup[ 2 ] ) )
		for target in targetCells:
			target = target[ 0 ]
			data = self.EnsureAttack( target, boost = self.boost )
			if data[ 0 ]:
				return

	# The intelligence to run at every tick
	def GameLoop( self ):
		self.boost = False
		if self.game.energy >= 95.0:
			self.boost = True
		if self.game.gold >= 60.0 and self.game.baseNum < 3:
			newBase = random.choice( self.playerCells )
			self.game.BuildBase( newBase.x, newBase.y )
		if self.mode == self.MODE_EXPAND:
			self.Expand()
			if self.unclaimedEnergyNum > 0:
				self.mode = self.MODE_RECHARGE
		elif self.mode == self.MODE_LOOT:
			pass
		elif self.mode == self.MODE_RECHARGE:
			self.Recharge()
			self.mode = self.MODE_EXPAND		

name = "Pandamonium"
if len( sys.argv ) == 2:
	name = sys.argv[ 1 ]
pandamonium = AgniKai( name )