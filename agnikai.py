import panda as cf
import random
from threading import Thread
import sys
from math import sqrt
from time import sleep

# Python 3 backwards compatibility
try:
    input = raw_input
except NameError:
    pass

class AgniKai():
	def __init__( self, name ):
		# Initialize the Panda Colorfight Client
		self.game = cf.Game()

		# Attempt to join the game
		if self.game.JoinGame( name ):
			# Initialize the variables
			self.lastAttack = None
			self.lastMulti = []
			self.threshold = 3.09
			self.mode = 0
			self.sparkMode = 0
			self.MODE_EXPAND = 0
			self.MODE_LOOT = 1
			self.MODE_RECHARGE = 2
			self.MODE_SPECIAL = 3
			self.MODE_ALL = 4
			self.special = False
			self.newBase = None
			self.danger = False
			self.lastTitle = ""

			# Initialize the starting game state
			self.game.Refresh()
			self.FetchBases()
			self.FetchInfo()

			# Initialize the threads
			self.playing = True
			self.refreshThread = Thread( target = self.Refresh )
			self.refreshThread.start()
			self.playThread = Thread( target = self.Play )
			self.playThread.start()
			self.baseThread = Thread( target = self.Base )
			self.baseThread.start()
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

	# Runs all base related functions
	def Base( self ):
		while self.playing:
			self.FetchBases()
			try:
				self.BuildLoop()
			except:
				pass

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

	def HorizontalDistance( self, c1, c2 ):
		return abs( c2.x - c1.x )

	def VerticalDistance( self, c1, c2 ):
		return abs( c2.y - c1.y )

	# Returns the distance between two cells by perimeter
	def PerimeterDistance( self, c1, c2 ):
		return self.HorizontalDistance( c1, c2 ) + self.VerticalDistance( c1, c2 )

	# Returns the distace between two cells by diagonal
	def DiagonalDistance( self, c1, c2 ):
		return sqrt( self.HorizontalDistance( c1, c2 ) ** 2 + self.VerticalDistance( c1, c2 ) ** 2 )

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
		for temp in self.lastMulti:
			if self.SameCell( cell, temp ):
				return False
		return ( cell.takeTime <= self.threshold or ( boost and cell.takeTime <= self.threshold * 5 ) ) and not cell.takeTime == -1

	# Checks if a cell has any adjacent enemy or unclaimed cells
	def EdgeCell( self, cell ):
		cellUp, cellRight, cellDown, cellLeft = self.GetAdjacent( cell )
		if not cellUp == None and not self.OwnCell( cellUp ):
			return True
		elif not cellRight == None and not self.OwnCell( cellRight ):
			return True
		elif not cellDown == None and not self.OwnCell( cellDown ):
			return True
		elif not cellLeft == None and not self.OwnCell( cellLeft ):
			return True
		return False

	# Checks if a boost should be done
	def CheckBoost( self, cell ):
		if self.game.energy >= 45.0 and ( self.EnergyCell( cell ) or self.GoldCell( cell ) ):
			return True
		elif self.game.energy >= 95.0:
			return True
		else:
			return False

	def CheckMulti( self ):
		#if self.danger:
		#	return False
		#if self.game.goldCellNum >= 3:
		#	if self.game.baseNum == 3 and self.game.gold >= 75:
		#		return True
		return False

	# Returns the cells adjacent to a specific cell
	def GetAdjacent( self, cell ):
		cellUp = self.game.GetCell( cell.x, cell.y - 1 )
		cellRight = self.game.GetCell( cell.x + 1, cell.y )
		cellDown = self.game.GetCell( cell.x, cell.y + 1 )
		cellLeft = self.game.GetCell( cell.x - 1, cell.y )
		return ( cellUp, cellRight, cellDown, cellLeft )

	# Checks the adjacent cell and updates the game state
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

	def CheckAttackable( self, cell ):
		cellUp, cellRight, cellDown, cellLeft = self.GetAdjacent( cell )
		if not cellUp == None and self.OwnCell( cellUp ):
			return True
		elif not cellRight == None and self.OwnCell( cellRight ):
			return True
		elif not cellDown == None and self.OwnCell( cellDown ):
			return True
		elif not cellLeft == None and self.OwnCell( cellLeft ):
			return True
		return False

	def GetMultiDmg( self, cell ):
		t = -1
		m = 0
		n = 0
		cellUp, cellRight, cellDown, cellLeft = self.GetAdjacent( cell )
		if not cellUp == None and self.CheckAttackable( cellUp ) and self.FastCell( cellUp ):
			if cellUp.takeTime > t:
				t = cellUp.takeTime
			if self.OwnCell( cellUp ):
				m += 1
			else:
				n += 1
		if not cellRight == None and self.CheckAttackable( cellRight ) and self.FastCell( cellRight ):
			if cellRight.takeTime > t:
				t = cellRight.takeTime
			if self.OwnCell( cellRight ):
				m += 1
			else:
				n += 1
		if not cellDown == None and self.CheckAttackable( cellDown ) and self.FastCell( cellDown ):
			if cellDown.takeTime > t:
				t = cellDown.takeTime
			if self.OwnCell( cellDown ):
				m += 1
			else:
				n += 1
		if not cellLeft == None and self.CheckAttackable( cellLeft ) and self.FastCell( cellLeft ):
			if cellLeft.takeTime > t:
				t = cellLeft.takeTime
			if self.OwnCell( cellLeft ):
				m += 1
			else:
				n += 1
		return ( cell, n, m, t )

	def GetMulti( self, cell ):
		multiTargets = []
		cellUp, cellRight, cellDown, cellLeft = self.GetAdjacent( cell )
		if not cellUp == None:
			multiTargets.append( self.GetMultiDmg( cellUp ) )
		if not cellRight == None:
			multiTargets.append( self.GetMultiDmg( cellRight ) )
		if not cellLeft == None:
			multiTargets.append( self.GetMultiDmg( cellLeft ) )
		if not cellDown == None:
			multiTargets.append( self.GetMultiDmg( cellDown ) )
		multiTargets.sort( key = lambda tup: ( tup[ 1 ], tup[ 2 ], tup[ 3 ] ), reverse = True )
		return multiTargets[ 0 ]

	def TempTake( self, cell ):
		self.game.data[ "cells" ][ cell.x + cell.y * 30 ][ "t" ] = -1
		self.game.data[ "cells" ][ cell.x + cell.y * 30 ][ "o" ] = self.game.uid

	# A smarter implementation of the attack function
	def Attack( self, cell, boost = False, multi = False ):
		if multi or ( not multi and not self.SameCell( cell, self.lastAttack ) ):
			if self.FastCell( cell, boost = boost ):
				if multi:
					data = self.game.MultiAttack( cell.x, cell.y )
				else:
					data = self.game.AttackCell( cell.x, cell.y, boost = boost )
				if data[ 0 ]:
					if multi:
						self.lastMulti = []
						cellUp, cellRight, cellDown, cellLeft = self.GetAdjacent( cell )
						if not cellUp == None:
							self.TempTake( cellUp )
							self.lastMulti.append( cellUp )
						if not cellRight == None:
							self.TempTake( cellRight )
							self.lastMulti.append( cellRight )
						if not cellDown == None:
							self.TempTake( cellDown )
							self.lastMulti.append( cellDown )
						if not cellLeft == None:
							self.TempTake( cellLeft )
							self.lastMulti.append( cellLeft )
					else:
						self.lastAttack = cell
						self.TempTake( cell )
				return data
			return ( False, 9, "Too long to attack" )
		return ( False, 10, "Same as the last cell" )

	# Clears a cell with blast
	def ClearCell( self, target ):
		directions = ( ( 0, -1 ), ( 1, 0 ), ( 0, 1 ), ( -1, 0 ) )
		for direction in directions:
			data = self.game.Blast( target.x + direction[ 0 ], target.y + direction[ 1 ], "square" )
			if data[ 0 ]:
				return data
		return data

	def DirectThreat( self, cell, target ):
		if self.DiagonalDistance( cell, target ) < 2:
			return True
		else:
			return False

	def DistantThreat( self, cell, target ):
		h = self.HorizontalDistance( cell, target )
		v = self.VerticalDistance( cell, target )
		return ( h == 0 and v <= 4 ) or ( v == 0 and h <= 4 ) 

	def ResetDamage( self ):
		self.baseThreat = 0
		self.directThreats = 0
		self.distantThreats = 0
		self.goldDmg = 0
		self.energyDmg = 0
		self.baseDmg = 0
		self.normalDmg = 0

	def UpdateDamage( self, target ):
		if not target == None:
			if self.EnemyCell( target ):
				for base in self.playerBases:
					if self.DirectThreat( base, target ):
						self.directThreats += 1
				if not self.newBase == None and self.DistantThreat( self.newBase, target ):
					self.distantThreats += 1
				if target.cellType == "gold":
					self.goldDmg += 1
				elif target.cellType == "energy":
					self.energyDmg += 1
				elif target.isBase:
					self.baseDmg += 1
				else:
					self.normalDmg += 1

	def CheckDamage( self, dmg ):
		damageCheck = False
		damageCheck = damageCheck or dmg[ 1 ] > 0
		self.danger = damageCheck and self.game.baseNum == 1
		damageCheck = damageCheck or dmg[ 2 ] > 0
		self.danger = damageCheck or self.danger
		damageCheck = damageCheck or dmg[ 3 ] > 0
		damageCheck = damageCheck or dmg[ 4 ] > 0
		damageCheck = damageCheck or dmg[ 5 ] > 0
		#damageCheck = damageCheck or dmg[ 6 ] > 0
		return damageCheck

	def GetDamage( self ):
		return ( self.blastCell, self.distantThreats, self.directThreats, self.goldDmg, self.energyDmg, self.baseDmg, self.normalDmg, self.blastType )

	# Gets the damage in a square
	def GetSDamage( self ):
		self.ResetDamage()
		self.blastType = 0
		for x in range( -1, 2 ):
			for y in range( -1, 2 ):
				target = self.game.GetCell( self.blastCell.x + x, self.blastCell.y + y )
				self.UpdateDamage( target )
		return self.GetDamage()

	# Gets the damage in a horizontal line
	def GetHDamage( self ):
		self.ResetDamage()
		self.blastType = 1
		for x in range( -4, 5 ):
			target = self.game.GetCell( self.blastCell.x + x, self.blastCell.y )
			self.UpdateDamage( target )
		return self.GetDamage()

	# Gets the damage in a vertical line
	def GetVDamage( self ):
		self.ResetDamage()
		self.blastType = 2
		for y in range( -4, 5 ):
			target = self.game.GetCell( self.blastCell.x, self.blastCell.y + y )
			self.UpdateDamage( target )
		return self.GetDamage()

	# An implementation of attack that ensures the target is hit
	def EnsureAttack( self, cell, boost = False ):
		multi = False
		target = cell
		if self.CheckMulti() and not boost:
			check = self.GetMulti( cell )
			if check[ 1 ] > 1:
				multi = True
				target = check[ 0 ]
		data = self.Attack( target, boost = boost, multi = multi )
		while data[ 1 ] == 3:
			data = self.Attack( target, boost = boost, multi = multi )
		return data

	# Get the game state
	def FetchInfo( self ):
		self.playerCells = []

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

		# Blast targets
		self.blastTargets = []

		if not self.newBase == None and not self.newBase.isBuilding:
			self.newBase = None

		# Iterate over the map
		for x in range( self.game.width ):
			for y in range( self.game.height ):
				cell = self.game.GetCell( x, y )
				if self.OwnCell( cell ):
					if self.EdgeCell( cell ):
						self.blastCell = cell
						self.blastTargets.append( self.GetSDamage() )
						self.blastTargets.append( self.GetHDamage() )
						self.blastTargets.append( self.GetVDamage() )
					if not cell.isBase:
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
		self.special = False
		self.blastTargets.sort( key = lambda tup: ( tup[ 1 ], tup[ 2 ], tup[ 3 ], tup[ 4 ], tup[ 5 ], tup[ 6 ] ), reverse = True )
		#print( self.blastTargets[ 0 ] )
		if self.CheckDamage( self.blastTargets[ 0 ] ):
			#self.special = self.special or self.game.energy >= 30 and self.game.energyCellNum >= 9
			self.special = self.special or self.game.energy >= 60 and self.game.energyCellNum >= 5
			self.special = self.special or self.game.energy >= 80 and self.game.energyCellNum >= 1

	def FetchBases( self ):
		self.playerBases = []
		for x in range( self.game.width ):
			for y in range( self.game.height ):
				cell = self.game.GetCell( x, y )
				if self.OwnCell( cell ):
					if cell.isBase or cell.isBuilding:
						self.playerBases.append( cell )

	# A smarter base building function to pick the safest location
	def BuildLoop( self ):
		if self.game.gold >= 60.0 and self.game.baseNum < 3:
			targetCells = []
			for playerCell in self.playerCells:
				if not self.EdgeCell( playerCell ):
					distances = []
					for base in self.playerBases:
						distances.append( self.PerimeterDistance( base, playerCell ) )
					targetCells.append( ( playerCell, min( distances ) ) )
			targetCells.sort( key = lambda tup: tup[ 1 ], reverse = True )
			for target in targetCells:
				target = target[ 0 ]
				data = self.game.BuildBase( target.x, target.y )
				if data[ 0 ]:
					self.newBase = target
					return

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
		if self.sparkMode == self.MODE_EXPAND:
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
			if self.special:
				self.sparkMode = self.MODE_SPECIAL
			else:
				self.sparkMode = self.MODE_EXPAND
		elif self.sparkMode == self.MODE_SPECIAL:
			self.Special()
			self.sparkMode = self.MODE_EXPAND

	# The blaster
	def Special( self ):
		print( "special" )
		try:
			optimal = self.blastTargets[ 0 ]
		except:
			optimal = None
		print( "Optimal: " )
		print( optimal )
		for target in self.blastTargets:
			if self.danger and not self.SameCell( optimal[ 0 ], target[ 0 ] ):
				return
			direction = "square"
			if target[ len( target ) - 1 ] == 1:
				direction = "horizontal"
			elif target[ len( target ) - 1 ] == 2:
				direction = "vertical"
			if not self.CheckDamage( target ):
				return
			data = self.game.Blast( target[ 0 ].x, target[ 0 ].y, direction )
			while data[ 1 ] == 3:
				data = self.game.Blast( target[ 0 ].x, target[ 0 ].y, direction )
			if data[ 0 ]:
				if self.SameCell( optimal[ 0 ], target[ 0 ] ):
					print( "Hit!" )
				else:
					print( "Selected: " )
					print( target )
				print( "" )
				sleep( 1 )
				self.special = False
				return


	# The fitness function to determine what mode to switch to
	def Fitness( self ):
		if self.danger:
			self.mode = self.MODE_SPECIAL
		elif self.fastAdjacentEnergyNum > 0 or self.fastAdjacentGoldNum > 0:
			self.mode = self.MODE_EXPAND
		elif self.game.energyCellNum == 0:
			self.mode = self.MODE_RECHARGE
		elif self.game.goldCellNum == 0:
			self.mode = self.MODE_LOOT
		else:
			self.mode = self.MODE_ALL

	def Header( self, title ):
		if not self.lastTitle == title:
			print( title )
			self.lastTitle = title
			print( "" )

	# The intelligence to run at every tick
	def GameLoop( self ):
		self.Fitness()
		if self.mode == self.MODE_ALL:
			self.Header( "All Spark" )
			self.AllSpark()
		if self.mode == self.MODE_EXPAND:
			self.Header( "Expand" )
			self.Expand()
		elif self.mode == self.MODE_RECHARGE:
			self.Header( "Recharge" )
			self.Recharge()
			self.Expand()
		elif self.mode == self.MODE_LOOT:
			self.Header( "Loot" )
			self.Loot()	
			self.Expand()
		elif self.mode == self.MODE_SPECIAL:
			self.Header( "Danger" )
			self.Special()
			self.AllSpark()

name = "Pandamonium"
if len( sys.argv ) == 2:
	name = sys.argv[ 1 ]
pandamonium = AgniKai( name )
