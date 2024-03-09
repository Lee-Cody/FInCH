#Copyright 2024 Cody Lee, All Rights Reserved#
from ij import IJ
from FInCH.GridGen import *
from FInCH.Utils import *
from FInCH.Interface import *
from FInCH.DataManager import *
from FInCH.FInCHPlugins import *

######################
version = "1.0.0"
######################
	
def mainFInCH():
	IJ.log("Started FInCH v{}".format(version))
	
	#####################################
	#default settings:
	
	threshlevel = 207
	substr = "Colour_2"
	
	#Change the following "stains" dictionary to choose different spectra for the Colour Deconvolution 2 FIJI plugin (located in colourdeconvolution.txt in your Fiji.app/plugins folder)
	#and/or change which transcription factor strings to look for at the start of filenames
	#The "stains" key should have a value that is a list of all possible transcription factors used in filenames
	#The other two keys should be a string matching the desired colour deconvolution plugin entry in the colourdeconvolution.txt file with a value that is a list of all TF names to use those spectra for
	#The stains dictionary should be compatible with any number of entries
	stains = {
		"DAB with blue": ["bcat","cam","tgfb","fgf"],
		"VectorRed with Blue": ["bmp4","dkk","ihh","wnt4"],
		"stains": ["bcat","cam","tgfb","fgf","bmp4","dkk","ihh","wnt4"]
		}
	
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
