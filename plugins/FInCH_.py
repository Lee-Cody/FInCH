#Copyright 2024 Cody Lee, All Rights Reserved#
from ij import IJ
from FInCH.GridGen import *
from FInCH.Utils import *
from FInCH.Interface import *
from FInCH.DataManager import *
from FInCH.FInCHPlugins import *

######################
version = "1.0.0"
ini_name = 'FInCH.ini'
defaults = {
	'transcriptionFactors': {
		"bcat":"DAB with blue",
		"cam":"DAB with blue",
		"tgfb":"DAB with blue",
		"fgf":"DAB with blue",
		"bmp4":"VectorRed with Blue",
		"dkk":"VectorRed with Blue",
		"ihh":"VectorRed with Blue",
		"wnt4":"VectorRed with Blue"
	},
	'useUpperAndLowerFiles':False,
	'thresholdCutoffValue':207,
	'defaultSpectra': ["DAB with blue","VectorRed with Blue"]
}
######################
	
def mainFInCH():
	IJ.log("Started FInCH v{}".format(version))
	errorbool = False
	#get settings and directories:
	dm = dataManager(version,ini_name,defaults)
	fm = fMenu(dm)
	errorbool = dm.checkINI()
	if errorbool is False:
		errorbool = fm.displayMenu()
	if errorbool is False:
		while fm.redo_setup:
			errorbool = dm.checkINI(force_new_ini = True)
			fm.redo_setup = False
			if errorbool is False:
				errorbool = fm.displayMenu()
	if errorbool is False:
		errorbool = dm.getDirectories()
	if errorbool is False:
		errorbool = dm.gatherImages()
	if errorbool is False:
		errorbool = dm.loadData()
	if errorbool is False:
		try:
			errorbool = dm.processImages()
		except Exception as e:
			print"error in processImages"
			cleanExit()
			print"Error FInCH.mainFInCH() calling fm.processImages(dm): ",repr(e)
			return		
	######## - Example of FInCHPlugins.py testFunction() - ########
	#if errorbool is False:
#		1) testFunction(dm.fimplist[0].grid)
#		OR:
#		2) for fimp in dm.fimplist:
#				testFunction(fimp.grid)	
	########
	if errorbool is False:
		try:
			errorbool = dm.openImages()
		except Exception as e:
			print"error in openImages"
			cleanExit()
			print"Error FInCH.mainFInCH() calling fm.openImages(): ",repr(e)
			return	
	if errorbool is False:
		fm.showNavMenu()
	return
	
mainFInCH()
IJ.log("Done!")
print"DONE"
