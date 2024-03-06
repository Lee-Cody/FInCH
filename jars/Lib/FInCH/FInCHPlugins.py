#FInCH Plugins
from FInCH.Utils import *
from FInCH.GridGen import *
from FInCH.DataManager import *
from FInCH.Interface import *
########################################
#Write any plugin functions here.
#You can call these in the FInCH_.py file in the "plugins" folder inside your fiji app directory.
#so, using the following function as an example. 
#You can see an example of implementation within the FInCH_.py file described above.
#Just ctrl+F that file for "testFunction"
########################################

def testFunction(someFInCHParameterLike_grid):

	rm = add_RoiM()
	rm.reset()
	grid = someFInCHParameterLike_grid
	grid_rois = grid.cell_rois
	grid_cell_fPolys = grid.cell_list
	
	#add all grid roi's to the roi manager:
	for roi in grid_rois:
		rm.addRoi(roi)
	#get the points of each grid cell (see the fGrid and fPoly classes in GridGen.py)
	for cell_fPoly in grid_cell_fPolys:
		points_temp = cell_fPoly.points
	#get the first point from the G5 cell in the grid, if it exists:
	if grid.G5:
		G5_fPoly = grid.G5
		p1 = G5_fPoly.p1
		x = p1[0]
		y = p1[1]
	#print information about the fGrid instance to the console:
	print"Grid info: ",grid.__dict__

	return

