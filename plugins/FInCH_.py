#Copyright 2024 Cody Lee, All Rights Reserved#
from ij import IJ
from FInCH.GridGen import *
from FInCH.Utils import *
from FInCH.Interface import *
from FInCH.DataManager import *
from FInCH.FInCHPlugins import *

######################
version = 1.0
######################
	
def mainFInCH():
	IJ.log("Started FInCH v{}".format(version))
	#####################################
	#default settings:
	threshlevel = 207
	substr = "Colour_2"
	stains = ["bcat","cam","tgfb","fgf","bmp4","dkk","ihh","wnt4"]
	restore_from_CSV = True
	#####################################
	errorbool = False
	rm = add_RoiM()
	#get settings and directories:	
	fm = fMenu(version,threshlevel,substr,stains)
	errorbool = fm.displayMenu()
	if errorbool:
		print"error in fMenu.displayMenu or user canceled a dialog"
		fm.errorWindow(1)
		cleanExit()
		return
	dm = dataManager(fm)
	fm.dataManager = dm
	errorbool = dm.loadData()
	if errorbool:
		print"error in dataManager.getData or user canceled a dialog"
		fm.errorWindow(2)
		cleanExit()
		return
	try:
		errorbool = fm.processImages(dm)
	except Exception as e:
		print"error in processImages"
		cleanExit()
		print"Error FInCH.mainFInCH() calling fm.processImages(dm): ",repr(e)
		return
	if errorbool:
		cleanExit()
		print"error in processImages or user canceled a dialog"
		return
		
	##### - Example of FInCHPlugins.py testFunction() - #####
#		1) testFunction(fm.fimplist[0].grid)
#		OR:
#		2) for fimp in fm.fimplist:
#				testFunction(fimp.grid)	
		
	try:
		errorbool = fm.openImages()
	except Exception as e:
		print"error in openImages"
		cleanExit()
		print"Error FInCH.mainFInCH() calling fm.openImages(): ",repr(e)
		return
	if errorbool:
		cleanExit()
		print"error in fm.openImages()"
		return
	fm.showNavMenu()
	return
	
mainFInCH()
IJ.log("Done!")
print"DONE"
