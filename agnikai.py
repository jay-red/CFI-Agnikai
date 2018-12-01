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
		self.mode = 4
		self.sparkMode = 0
		self.MODE_EXPAND = 0
		self.MODE_LOOT = 1
		self.MODE_RECHARGE = 2
		self.MODE_ATTACK = 3
		self.MODE_ALL = 4

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

	# Checks if the cell is claimed
	def Claimed( self, cell ):
		return not cell.owner == 0

	# Checks if a cell's attack time is within the threshold
	def FastCell( self, cell, boost = False ):
		return ( cell.takeTime <= self.threshold or ( boost and cell.takeTime <= self.threshold * 4 ) ) and not cell.takeTime == -1

	# Checks if a boost should be done
	def CheckBoost( self, cell ):
		if self.game.energy >= 45.0 and ( self.EnergyCell( cell ) or self.GoldCell( cell ) ):
			return True
		elif self.game.energy >= 95.0:
			return True
		else:
			return False

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
					if self.FastCell( cell, boost = self.CheckBoost( cell ) ):
						self.fastAdjacentGoldCells.append( cell )
						self.fastAdjacentGoldNum += 1
				elif self.EnergyCell( cell ):
					self.adjacentEnergyNum += 1
					self.adjacentEnergyCells.append( cell )
					if self.FastCell( cell, boost = self.CheckBoost( cell ) ):
						self.fastAdjacentEnergyCells.append( cell )
						self.fastAdjacentEnergyNum += 1
				elif self.EnemyCell( cell ):
					self.adjacentEnemyNum += 1
					self.adjacentEnemyCells.append( cell )
				else:
					self.adjacentNormalNum += 1
					self.adjacentNormalCells.append( cell )

	# A smarter implementation of the attack function
	def Attack( self, cell, boost = False ):
		if not self.SameCell( cell, self.lastAttack ):
			if self.FastCell( cell, boost = boost ):
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

		# Adjacent cell information
		self.adjacentCells = []
		self.adjacentNormalCells = []
		self.adjacentGoldCells = []
		self.adjacentEnergyCells = []
		self.adjacentEnemyCells = []
		self.adjacentNormalNum = 0
		self.adjacentGoldNum = 0
		self.adjacentEnergyNum = 0
		self.adjacentEnemyNum = 0

		# Fast adjacent cell information
		self.fastAdjacentGoldCells = []
		self.fastAdjacentEnergyCells = []
		self.fastAdjacentGoldNum = 0
		self.fastAdjacentEnergyNum = 0

		# Overall unclaimed cell information
		self.unclaimedGoldCells = []
		self.unclaimedEnergyCells = []
		self.unclaimedGoldNum = 0
		self.unclaimedEnergyNum = 0

		# Claimed enemy cell information
		self.enemyGoldCells = []
		self.enemyEnergyCells = []
		self.enemyGoldNum = 0
		self.enemyEnergyNum = 0
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
						if self.Claimed( cell ):
							self.enemyGoldCells.append( cell )
							self.enemyGoldNum += 1
						else:
							self.unclaimedGoldNum += 1
							self.unclaimedGoldCells.append( cell )
					elif self.EnergyCell( cell ):
						if self.Claimed( cell ):
							self.enemyEnergyCells.append( cell )
							self.enemyEnergyNum += 1
						else:
							self.unclaimedEnergyNum += 1
							self.unclaimedEnergyCells.append( cell )

	# Expansion mode
	def Expand( self ):
		if self.adjacentGoldNum > 0:
			for target in self.adjacentGoldCells:
				data = self.EnsureAttack( target, boost = self.CheckBoost( target ) )
				if data[ 0 ]:
					return
		if self.adjacentEnergyNum > 0:
			for target in self.adjacentEnergyCells:
				data = self.EnsureAttack( target, boost = self.CheckBoost( target ) )
				if data[ 0 ]:
					return
		if self.adjacentEnemyNum > 0 and ( self.adjacentNormalNum == 0 or random.randrange( 4 ) == 0 ):
			while self.adjacentEnemyNum > 0:
				target = self.adjacentEnemyCells.pop( random.randrange( self.adjacentEnemyNum ) )
				self.adjacentEnemyNum -= 1
				data = self.EnsureAttack( target, boost = self.CheckBoost( target ) )
				if data[ 0 ]:
					return
		elif self.adjacentNormalNum > 0:
			while self.adjacentNormalNum > 0:
				target = self.adjacentNormalCells.pop( random.randrange( self.adjacentNormalNum ) )
				self.adjacentNormalNum -= 1
				data = self.EnsureAttack( target, boost = self.CheckBoost( target ) )
				if data[ 0 ]:
					return

	# Attacks the cell closest to any cell in a list of targets
	def Pursue( self, targets ):
		targetCells = []
		for target in targets:
			for adjacent in self.adjacentCells:
				targetCells.append( ( adjacent, self.PerimeterDistance( target, adjacent ), self.DiagonalDistance( target, adjacent ) ) )
		targetCells.sort( key = lambda tup: ( tup[ 1 ], tup[ 2 ] ) )
		for target in targetCells:
			target = target[ 0 ]
			data = self.EnsureAttack( target, boost = self.CheckBoost( target ) )
			if data[ 0 ]:
				return

	# Attacks the cell closest to an energy cell
	def Recharge( self ):
		if self.unclaimedEnergyNum > 0:
			self.Pursue( self.unclaimedEnergyCells )
		else:
			self.Pursue( self.enemyEnergyCells )

	# Attacks the cell closest to a gold cell
	def Loot( self ):
		if self.unclaimedGoldNum > 0:
			self.Pursue( self.unclaimedGoldCells )
		else:
			self.Pursue( self.enemyGoldCells )

	# Expands, Loots, and Recharges all in one
	def AllSpark( self ):
		if self.fastAdjacentEnergyNum > 0 or self.fastAdjacentGoldNum > 0 or self.sparkMode == self.MODE_EXPAND:
			self.Expand()
			if self.unclaimedGoldNum > 0 or self.enemyGoldNum > 0:
				self.sparkMode = self.MODE_LOOT
			elif self.unclaimedEnergyNum > 0 or self.enemyEnergyNum > 0:
				self.sparkMode = self.MODE_RECHARGE
		elif self.sparkMode == self.MODE_LOOT:
			self.Loot()
			if self.unclaimedEnergyNum > 0 or self.enemyEnergyNum > 0:
				self.sparkMode = self.MODE_RECHARGE
			else:
				self.sparkMode = self.MODE_EXPAND
		elif self.sparkMode == self.MODE_RECHARGE:
			self.Recharge()
			self.sparkMode = self.MODE_EXPAND

	# The intelligence to run at every tick
	def GameLoop( self ):
		self.boost = False
		if self.game.energy >= 95.0:
			self.boost = True
		if self.game.gold >= 60.0 and self.game.baseNum < 3:
			newBase = random.choice( self.playerCells )
			self.game.BuildBase( newBase.x, newBase.y )
		if self.mode == self.MODE_ALL:
			self.AllSpark()
		

name = "Pandamonium"
if len( sys.argv ) == 2:
	name = sys.argv[ 1 ]
pandamonium = AgniKai( name )