#https://github.com/Lee-Cody/FInCH
#Copyright 2024 Cody Lee
#Licensed under GPL-3.0
#Colour Deconvolution- ImageJ plugin: Ruifrok, Arnout & Johnston, Dennis. (2001). Quantification of histochemical staining by color deconvolution. Anal Quant Cytol Histol. 23. 
#Cody Lee, Carmen Sánchez Moreno, Alexander V. Badyaev
from ij import IJ
from FInCH.GridGen import *
from FInCH.Utils import *
from FInCH.Interface import *
from FInCH.DataManager import *
from FInCH.FInCHPlugins import *
from java.awt import Window

######################
version = "1.0.1"
ini_name = 'FInCH.ini'
defaults = {
	#ini default settings:
	'fileIdentifiers': {
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
	#setup menu default cd spectra:
	'defaultSpectra': [
		"DAB with blue",
		"VectorRed with Blue"
	],
	#colourdeconvolution.txt default settings:
	'colourdeconvolutiontxt':[
		u'#Stain_Name,R0,G0,B0,R1,G1,B1,R2,G2,B2\n',
		u'DAB with blue,0.650000000,0.704000000,0.286000000,0.26800000,0.57000000,0.7760000,0.5770000,0.58610000,0.56920000\n',
		u'VectorRed with Blue,0.67528754,0.62184477,0.39660534,0.18489036,0.9295033,0.31912246,0.5765431,0.58613986,0.56924343\n',
		u'H&E,0.644211000,0.716556000,0.266844000,0.09278900,0.95411100,0.28311100,0.00000000,0.00000000,0.0000000\n',
		u'H&E 2,0.490157340,0.768970850,0.410401730,0.04615336,0.84206840,0.53739250,0.00000000,0.00000000,0.0000000\n',
		u'H DAB,0.650000000,0.704000000,0.286000000,0.26800000,0.57000000,0.77600000,0.00000000,0.00000000,0.0000000\n',
		u'Feulgen Light Green,0.464209200,0.830083350,0.308271870,0.94705542,0.25373821,0.19650764,0.00000000,0.00000000,0.0000000\n',
		u'Giemsa,0.834750233,0.513556283,0.196330403,0.09278900,0.95411100,0.28311100,0.00000000,0.00000000,0.0000000\n',
		u'FastRed FastBlue DAB,0.213939210,0.851126690,0.477940220,0.74890292,0.60624161,0.26731082,0.26800000,0.57000000,0.7760000\n',
		u'Methyl Green DAB,0.980000000,0.144316000,0.133146000,0.26800000,0.57000000,0.77600000,0.00000000,0.00000000,0.0000000\n',
		u'H&E DAB,0.650000000,0.704000000,0.286000000,0.07200000,0.99000000,0.10500000,0.26800000,0.57000000,0.7760000\n',
		u'H AEC,0.650000000,0.704000000,0.286000000,0.27430000,0.67960000,0.68030000,0.00000000,0.00000000,0.0000000\n',
		u'Azan-Mallory,0.853033000,0.508733000,0.112656000,0.09289875,0.86620080,0.49098468,0.10732849,0.36765403,0.9237484\n',
		u'Masson Trichrome,0.799510700,0.591352100,0.105286670,0.09997159,0.73738605,0.66803260,0.00000000,0.00000000,0.0000000\n',
		u'Alcian blue & H,0.874622000,0.457711000,0.158256000,0.55255600,0.75440000,0.35374400,0.00000000,0.00000000,0.0000000\n',
		u'H PAS,0.644211000,0.716556000,0.266844000,0.17541100,0.97217800,0.15458900,0.00000000,0.00000000,0.0000000\n',
		u'Brilliant_Blue,0.314655480,0.660239500,0.681964640,0.38357300,0.52711410,0.75830240,0.74335430,0.51731443,0.4240403\n',
		u'RGB,0.000000000,1.000000000,1.000000000,1.00000000,0.00000000,1.00000000,1.00000000,1.00000000,0.0000000\n',
		u'CMY,1.000000000,0.000000000,0.000000000,0.00000000,1.00000000,0.00000000,0.00000000,0.00000000,1.0000000\n'
	]
}
######################

def mainFInCH():
	IJ.log("Started FInCH v{}".format(version))
	errorbool = False
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
			print"Error FInCH.mainFInCH() calling dm.processImages(): ",repr(e)
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
	if errorbool is not False:
		cleanExit()
	else:
		for javawindow in Window.getWindows():
			try:
				if "Console" in javawindow.title:
					javawindow.dispose()
			except:
				continue
	return
	
mainFInCH()
IJ.log("Done!")
print"DONE"
