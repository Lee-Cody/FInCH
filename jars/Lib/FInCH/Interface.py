#https://github.com/Lee-Cody/FInCH
#Copyright 2024 Cody Lee
#Licensed under GPL-3.0
#See FInCH_.py for colour deconvolution attribution
from FInCH.GridGen import *
from FInCH.Utils import *
from FInCH.FInCHPlugins import *
from FInCH.DataManager import *
from ij import IJ, ImageListener, WindowManager, ImagePlus, ImageStack
import ij.util
from ij.io import DirectoryChooser, FileSaver, OpenDialog
from sc.fiji.colourDeconvolution import Colour_Deconvolution
from ij.plugin.frame import RoiManager
from ij.process import ImageProcessor
from ij.gui import GenericDialog,Overlay,Roi,WaitForUserDialog,Toolbar
from ij.gui.Line import PointIterator
from fiji.util.gui import GenericDialogPlus
import os, sys, math, csv, copy, json, time, re
from java import net
from java.awt import 	(Color, GridLayout, GridBagLayout, GridBagConstraints,
						Dimension, Font, Insets, BorderLayout, Panel, Button, Window) 
from java.awt.event import ActionListener, MouseAdapter, WindowAdapter
from javax.swing import JFrame,JDialog,JLabel,JButton,JList,JPanel,JScrollPane,JOptionPane
########################################

#####listener for main fMenu.displayMenu() redo setup button:
class redoSetupListener(ActionListener):
	def __init__(self,dm,fm,menu):
		self.data_manager = dm
		self.fm = fm
		self.menu = menu
		
	def actionPerformed(self, event):
		self.fm.redo_setup = True
		self.menu.dispose()

class fMenu:
	def __init__(self,data_manager):
		self.data_manager = data_manager
		self.VSFont = Font("Courier", Font.PLAIN, 9)
		self.SFont = Font("Courier", Font.PLAIN, 12)
		self.MFont = Font("Courier", Font.PLAIN, 30)
		self.LFont = Font("Courier", Font.PLAIN, 108)
		self.VSFont_b = Font("Courier", Font.BOLD, 9)
		self.SFont_b = Font("Courier", Font.BOLD, 12)
		self.MFont_b = Font("Courier", Font.BOLD, 30)
		self.LFont_b = Font("Courier", Font.BOLD, 108)
		self.redo_setup = False
		data_manager.menuObj = self
		#make sure there are no open images and clean up any windows from previous runs:
		frames = JFrame.getFrames()
		for frame in frames:
			if "Navigator" in frame.getTitle():
				frame.dispose()
			else:
				continue
		for javawindow in Window.getWindows():
			try:
				if "Console" in javawindow.title:
					javawindow.dispose()
			except:
				continue
		if (len(WindowManager.getImageTitles()) > 0):
			alertgd = self.createDialog('alert_closeImages')
			alertgd.showDialog()
			errorbool = True
			return errorbool
		
	def displayMenu(self):
	#substring is the end of the image title we want after colour deconvolution
		dm = self.data_manager
		threshlevel = dm.threshold_value
		substring = dm.cd_substring
		rm = dm.rm
		rm.reset()
		errorbool = False
		impicon = dm.impicon
		implogo = dm.implogo
		self.redo_setup = False
		gd = self.createDialog('mainMenu')
		gd.showDialog()
		if (gd.wasOKed()):
			#get prefs
			#cast to int; getNextNumber always returns a double
			dm.rows = int(gd.getNextNumber())
			dm.cols = int(gd.getNextNumber())
			#booleans from user options:
			#entire folder of images?
			dm.singlefile = gd.getNextBoolean()
			#grid data already exists?
			dm.gridExist = gd.getNextBoolean()
			#collect pixel data?
			if dm.data_enabled:
				dm.getDataBool = gd.getNextBoolean()
				dm.cell_analysis = gd.getNextBoolean()
			else:
				dm.getDataBool = False
				dm.cell_analysis = gd.getNextBoolean()
#			self.lower_override = filegd.getNextBoolean()
			if dm.getDataBool:
				dm.CDBool = True
			
			if (dm.ini_settings['thresholdCutoffValue'] > 255) or (dm.ini_settings['thresholdCutoffValue'] < 0):
				self.errorWindow(3)
				errorbool = True
				return errorbool
			if (dm.rows < 1) or (dm.cols < 1):
				self.errorWindow(4)
				errorbool = True
				return errorbool
		else:
			if self.redo_setup:
				return errorbool
			else:
				print "User canceled main menu"
				errorbool = "cancel"
				return errorbool
		#filename for singlefile, savefolderpath/processed_folder is saved folder for CD images, filepath is for singlefile it is path + filename, 
		#folderpath is folder w/AOI imgs, CDfolderpath is where previously processed CD images are located retrieved from dialog from user
		#generally, CDfolderpath should = savefolderpath
		return errorbool

	def userINISetupMenu(self,default_settings,cdtxt_spectra):
		errorbool = False
		dm = self.data_manager
		impicon = dm.impicon
		ini_settings = {}
		temp_settings = {
			'impicon':impicon,
			'def_threshvalue':default_settings['thresholdCutoffValue'],
			'cdtxt_spectra':cdtxt_spectra,
			'upperlower':False
		}
		if dm.data_enabled is False:
			temp_settings['cdtxt_spectra'] = default_settings['defaultSpectra']
		tfs = []
		tfs_matched = []
		user_tfs_matched = []
		edited_tfs = []
		for key, value in default_settings['fileIdentifiers'].items():
			tfs.append(key)
			match = [key,value]
			tfs_matched.append(match)
		tfs.sort()
		temp_settings['tfs'] = tfs
		temp_settings['tfs_matched'] = tfs_matched
		temp_settings, errorbool = self._iniDialogTF(temp_settings)
		while errorbool == "retry":
			temp_settings, errorbool = self._iniDialogTF(temp_settings)
		if (errorbool == "cancel") or (errorbool is True):
			return None, errorbool
		ini_settings['tfs'] = temp_settings['tfs']
		ini_settings['tfs_matched'] = temp_settings['tfs_matched']
		ini_settings['def_threshvalue'] = temp_settings['def_threshvalue']
		ini_settings['upperlower'] = temp_settings['upperlower']
		if errorbool:
			return None, errorbool
		return ini_settings, errorbool
	
	def _iniDialogTF(self,temp_settings):
		errorbool = False
		retry_TF = False
		confirm_TF = False
		retry_TF_messages = []
		invalid_tfs = []
		edited_tfs = []
		tfs = temp_settings['tfs']
		gd = self.createDialog('ini_FilenameIds',dialogvariables=[tfs])
		gd.showDialog()
		if gd.wasOKed():
			try:
				edited_tfs_temp = str(gd.getNextString()).split(",")
			except Exception as e:
				self.errorWindow(12,error=e)
				errorbool = True
				return temp_settings,errorbool
			if (len(edited_tfs_temp) == 0) or (edited_tfs_temp is None):
				errorbool = "retry"
				retry_TF_messages.append("No valid entries found! There must be at least one valid entry to continue. Please try again and make sure to follow the formatting rules!")
			else:
				for temptf in edited_tfs_temp:
					temptf_formatted = re.sub(r'\W+','',temptf)
					if temptf == '':
						invalid_tfs.append("blank entry (',,')")
						confirm_TF = True
						continue
					if (temptf_formatted is None) or (temptf_formatted == ''):
						invalid_tfs.append(temptf)
						confirm_TF = True
						continue
					if temptf_formatted not in edited_tfs:
						edited_tfs.append(temptf_formatted)
			if (len(edited_tfs) == 0) and (errorbool != "retry"):
				confirm_TF = False
				errorbool = "retry"
				retry_TF_messages.append("No valid entries found! There must be at least one valid entry to continue.")
				retry_TF_messages.append("Please try again and make sure to follow the formatting rules!")
			if confirm_TF:
				gd = self.createDialog('ini_FilenameIds_confirm',dialogvariables=[invalid_tfs,edited_tfs])
				gd.showDialog()
				if gd.wasOKed():
					confirm_TF = False
				elif gd.wasCanceled():
					errorbool = True
					print"User canceled initial setup when getting filename identifiers"
					return temp_settings, errorbool
				else:
					errorbool = "retry"
					return temp_settings,errorbool
			if errorbool == "retry":
				retrygd = self.createDialog('ini_retry',dialogvariables=["Invalid Filename Identifier Entries",retry_TF_messages])
				retrygd.showDialog()
				if retrygd.wasCanceled():
					errorbool = True
					print"User canceled initial setup when getting filename identifiers"
				return temp_settings,errorbool
			if edited_tfs is None:
				edited_tfs = tfs
			temp_settings['edited_tfs'] = edited_tfs
			temp_settings['tfs'] = {}
			temp_settings['tfs'] = edited_tfs
			temp_settings, errorbool = self._iniDialogCD(temp_settings)
		else:
			errorbool = "cancel"
			print"User canceled initial setup when getting transcription factors"
			return temp_settings, errorbool
		return temp_settings, errorbool
	
	def _iniDialogCD(self,temp_settings):
		errorbool = False
		edited_tfs = temp_settings['edited_tfs']
		tfs_matched = temp_settings['tfs_matched']
		cdtxt_spectra = temp_settings['cdtxt_spectra']
		user_tfs_matched = []
		gd = self.createDialog('ini_CDSpectra',dialogvariables=[edited_tfs,cdtxt_spectra,tfs_matched])
		gd.showDialog()
		if gd.wasOKed():
			for i in range(len(edited_tfs)):
				tf = edited_tfs[i]
				spectra_temp = gd.getNextChoice()
				match_temp = [tf,spectra_temp]
				user_tfs_matched.append(match_temp)
			if (user_tfs_matched is None) or (len(user_tfs_matched) == 0):
				user_tfs_matched = tfs_matched
			temp_settings['user_tfs_matched'] = user_tfs_matched
			temp_settings['tfs_matched'] = user_tfs_matched
			temp_settings,errorbool = self._iniDialogThreshold(temp_settings)
			while errorbool == "retry":
				temp_settings, errorbool = self._iniDialogThreshold(temp_settings)
			if errorbool is True:
				return None, errorbool				
		elif gd.wasCanceled():
			errorbool = "cancel"
			print"User canceled initial setup when getting color deconvolution spectra"
			return temp_settings, errorbool
		else:
			temp_settings = self._iniDialogTF(temp_settings)
		return temp_settings, errorbool
		
	def _iniDialogThreshold(self,temp_settings):
		errorbool = False
		retry_thresh = False
		def_treshvalue = temp_settings['def_threshvalue']
		gd = self.createDialog('ini_ThresholdCutoffValue',dialogvariables=[def_treshvalue])
		gd.showDialog()
		if gd.wasOKed():
			try:
				threshval = int(gd.getNextNumber())
			except:
				threshval = -1
			if (threshval > 255) or (threshval < 1):
				errorbool = "retry"
				retrygd = self.createDialog('ini_retry',dialogvariables=["Invalid Threshold Cutoff Value",["The Threshold Cutoff Value must be a number between 1 and 255."]])
				retrygd.showDialog()
				if retrygd.wasCanceled():
					errorbool = True
					print"User canceled initial setup when getting filename identifiers"
				return temp_settings,errorbool
			temp_settings['def_threshvalue'] = threshval
			temp_settings,errorbool = self._iniDialogUpLow(temp_settings)
		elif gd.wasCanceled():
			errorbool = "cancel"
			print"User canceled initial setup when getting color deconvolution spectra"
			return None, errorbool
		else:
			temp_settings, errorbool = self._iniDialogCD(temp_settings)
		return temp_settings, errorbool
		
	def _iniDialogUpLow(self,temp_settings):
		errorbool = False
		uplow = temp_settings['upperlower']
		gd = self.createDialog('ini_UpperLowerFunction',dialogvariables=[uplow])
		gd.showDialog()
		if gd.wasOKed():
			uplow = gd.getNextBoolean()
			temp_settings['upperlower'] = uplow
		elif gd.wasCanceled():
			errorbool = "cancel"
			print"User canceled initial setup when getting color deconvolution spectra"
			return temp_settings, errorbool
		else:
			temp_settings,errorbool = self._iniDialogThreshold(temp_settings)
		return temp_settings, errorbool
	
	def createDialog(self,dialogtype,dialogvariables=None):
		dm = self.data_manager
		impicon = dm.impicon
		implogo = dm.implogo
		if dialogtype == 'mainMenu':
			gd = GenericDialogPlus("FInCH  v{}".format(dm.version))		
			if implogo is not None:
#				filegd.setInsets (int top, int left, int bottom)
				gd.setInsets(5, 5, 5)
				gd.setIconImage(impicon)
				gd.addImage(implogo)
				gd.addToSameRow()
			gd.addMessage("FInCH", self.LFont_b)
			gd.setInsets(0, 5, 5)
			gd.addMessage("File Iterating & Color deconvoluting Histogram", self.MFont_b)
			gd.setInsets(0, 5, 5)
			gd.addMessage("What dimensions would you like for the image grids?\n(Rows and Columns must be at least 1)")
			gd.setInsets(0, 15, 5)
			gd.addNumericField("Rows:", 10, 0)
			gd.addToSameRow()
			gd.addNumericField("Columns:", 10, 0)
			gd.setInsets(0, 5, 5)
			gd.addMessage("Would you like to process a single image?\n(leave un-checked to process an entire folder)")
			gd.setInsets(0, 15, 5)
			gd.addCheckbox("Process a single image", False)
			gd.setInsets(0, 5, 5)
			gd.addMessage("Processing Options:\nNote: if you just want to apply a grid to an AOI image that has been processed\nand already has a grid text file saved, check option 1 and leave the rest unchecked")
			gd.setInsets(0, 15, 5)
			gd.addCheckbox("1. Grid data already exists for image(s)", False)		
			if dm.data_enabled:
				gd.addToSameRow()
				gd.addCheckbox("2. Collect Pixel Data", True)
				gd.setInsets(0, 15, 5)
				gd.addCheckbox("3. Cell analysis", False)	
			else:
				gd.addToSameRow()
				gd.addCheckbox("2. Cell analysis", False)
				gd.setInsets(5, 5, 0)
				gd.addMessage("Data collection is disabled due to a problem with reading or creating colourdeconvolution.txt.",self.SFont_b,Color.red)
				gd.setInsets(0, 5, 15)
				gd.addMessage("There may be a problem with your FIJI &/or FInCH files.\nYou may have to download BOTH FIJI and FInCH again to enable data collection.")
			redo_setup_listener = redoSetupListener(dm,self,gd)
			gd.setInsets(0, 15, 5)
			gd.addButton("Complete initial setup (change settings)", redo_setup_listener)
		elif dialogtype == 'alert_closeImages':
			gd =  GenericDialogPlus("Alert")
			if impicon is not None:
				gd.setIconImage(impicon)
			gd.addMessage("Please close any open images and restart FInCH")
		elif dialogtype == 'ini_setupMenu':
			gd = GenericDialogPlus("FInCH  v{}".format(dm.version))		
			if implogo is not None:
				gd.setInsets(5, 5, 5)
				gd.setIconImage(impicon)
				gd.addImage(implogo)
				gd.addToSameRow()
			gd.addMessage("FInCH", self.LFont_b)
			gd.setInsets(0, 5, 5)
			gd.addMessage("File Iterating & Color deconvoluting Histogram", self.MFont_b)
			gd.setInsets(0, 5, 5)
			gd.addMessage("FInCH didn't find previous user settings and would like to perform initial setup.")
			gd.setInsets(0, 5, 5)
			gd.addMessage("Initial setup will walk you through the basic settings of FInCH.")
			gd.setInsets(0, 5, 5)
			gd.addMessage("The setup dialogs will help explain a bit about how FInCH works, or you can choose to continue with default settings.")
			gd.setInsets(0, 5, 5)
			gd.addMessage("Would you like to perform initial setup?")
			gd.enableYesNoCancel("Setup FInCH","Use Default Settings")
		elif dialogtype == 'ini_FilenameIds':
			gd = GenericDialog("Filename Identifiers (setup 1 of 4)")
			if impicon is not None:
				gd.setIconImage(impicon)
			gd.setInsets(10,5,0)
			gd.addMessage("FInCH will look for each of these identifiers in filenames. It uses these to:")
			gd.setInsets(0,20,0)
			gd.addMessage("-verify it is processing the correct files")
			gd.setInsets(0,20,0)
			gd.addMessage("-match each to the correct spectra for color deconvolution in FIJI.app/plugins/colourdeconvolution.txt")
			gd.setInsets(10,5,0)
			gd.addMessage("Filenames MUST start with one of the following in order for FInCH to recognize them.")
			gd.setInsets(20,5,20)
			gd.addStringField("Filename Identifiers: ",",".join(dialogvariables[0]),40)
			gd.setInsets(0,5,0)
			gd.addMessage("Alphanumeric characters only (abc,ABC,123); Avoid spaces; Separate entries with a comma: ','",self.SFont_b,Color.red)
			gd.setOKLabel("Next")
		elif dialogtype == 'ini_FilenameIds_confirm':
			gd = GenericDialog("Invalid Filename Identifier Entries")
			if impicon is not None:
				gd.setIconImage(impicon)
			gd.setInsets(5,5,0)	
			gd.addMessage("Some filename identifiers contained invalid characters, or there were blank or duplicate entries.")
			gd.setInsets(20,5,0)	
			gd.addMessage("Invalid entries: {}".format(dialogvariables[0]))
			gd.setInsets(5,5,0)	
			gd.addMessage("Valid entries: {}".format(dialogvariables[1]))	
			gd.setInsets(5,5,0)		
			gd.addMessage("These entries will be excluded from the settings file (FInCH.ini).")
			gd.setInsets(20,5,20)
			gd.addMessage("Would you like to continue with only the valid entries or go back and change the invalid entries?")
			gd.enableYesNoCancel("Continue","Back")
		elif dialogtype == 'ini_CDSpectra':
			gd = GenericDialog("Color Deconvolution Spectra (setup 2 of 4)")
			if impicon is not None:
				gd.setIconImage(impicon)
			gd.addMessage("FInCH will perform color deconvolution on the images based on the filename.")
			gd.addMessage("The spectra to use are read from FIJI.app/plugins/colourdeconvolution.txt")
			gd.addMessage("You can add additional color spectra to the above file and they will appear here")
			gd.addMessage("(follow the format shown in colourdeconvolution.txt)")
			for i in range(len(dialogvariables[0])):
				tf = dialogvariables[0][i]
				def_spectra = dialogvariables[1][0]
				for tfmatch in dialogvariables[2]:
					if tfmatch[0] == tf:
						def_spectra = tfmatch[1]
				gd.addChoice(tf,dialogvariables[1],def_spectra)
			gd.enableYesNoCancel("Next","Back")
		elif dialogtype == 'ini_ThresholdCutoffValue':
			gd = GenericDialog("Threshold Cutoff Value (setup 3 of 4)")
			if impicon is not None:
				gd.setIconImage(impicon)
			gd.setInsets(20,5,0)	
			gd.addMessage("FInCH will threshold images before collecting data using the following cutoff value (must be a number between 1-255).")
			gd.setInsets(5,5,0)	
			gd.addMessage("Increasing this value will DECREASE the sensitivity of thresholding, potentially increasing false negative pixels.")
			gd.setInsets(5,5,0)	
			gd.addMessage("Decreasing this value will INCREASE the sensitivity of thresholding, potentially increasing false positive pixels.")
			gd.setInsets(5,5,0)	
			gd.addMessage("Generally, you should only change this value if you are experiencing problems with the default value.")
			gd.setInsets(20, 15, 20)
			gd.addNumericField("Thresholding Cutoff Value: ",dialogvariables[0])
			gd.enableYesNoCancel("Next","Back")
		elif dialogtype == 'ini_UpperLowerFunction':
			gd = GenericDialog("Upper/Lower Image Functionality (setup 4 of 4)")
			if impicon is not None:
				gd.setIconImage(impicon)
			gd.setInsets(10,5,0)			
			gd.addMessage("FInCH will distinguish between upper and lower beaks in order to\npreserve grid cell resolution between images for the same individual.")
			gd.setInsets(5,5,0)
			gd.addMessage("If this is turned on, FInCH will:")
			gd.setInsets(0,20,0)
			gd.addMessage("-look for the words 'upper' and 'lower' in filenames\n-process filenames with upper in the name first\n-temporarily 'save' grid cell width & height for that 'upper' image\n-apply those dimensions to images that have the same name (where the only difference in the filename is 'lower' instead of 'upper').")
			gd.setInsets(5,5,0)
			gd.addMessage("(This means 'lower' images may not have grids with the user-specified columns/rows\nin order to have grid cells of the same dimension as their associated 'upper' file.")
			gd.setInsets(0,5,0)
			gd.addMessage("However, the associated 'upper' image will have those user-specific column & row dimensions.)")
			gd.setInsets(5,5,0)
			gd.addMessage("So, for an image with the following filename: [Bmp4_individualxyz_upper_4x_AOI.tif],\nFInCH will look for an image with filename: [Bmp4_individualxyz_lower_4x_AOI.tif]")
			gd.setInsets(5,5,0)	
			gd.addMessage("Check this checkbox to turn this function ON (make sure you are correctly naming your files!)")
			gd.setInsets(20,15,20)	
			gd.addCheckbox("Upper/Lower Functionality", dialogvariables[0])
			gd.enableYesNoCancel("Finish Setup","Back")
		elif dialogtype == 'ini_retry':
			gd = GenericDialog(dialogvariables[0])
			if impicon is not None:
				gd.setIconImage(impicon)
			for message in dialogvariables[1]:
				gd.addMessage(message)
		return gd
	
	def errorWindow(self,errortype,exit=True,error=None):
		print"errortype: ",errortype
		dm = self.data_manager
		impicon = dm.impicon
		errorgd = GenericDialogPlus("Error")
		errorgd.setInsets(5,5,0)
		errorgd.addMessage("FInCH encountered a bug but isn't hungry.")
		if impicon is not None: errorgd.setIconImage(impicon)
		if errortype == 0:
			if error:
				print"Error: ",repr(error)
			errorgd.addMessage("Please restart FInCH and try again.")
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 1:
			if error:
				print"Error: ",repr(error)
			errorgd.addMessage("Error displaying Main Menu or user canceled a necessary dialog")
			errorgd.addMessage("Please restart FInCH and try again.")
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 2:
			if error:
				print"Error: ",repr(error)
			errorgd.addMessage("Error checking for previous grid data or user canceled a necessary dialog")
			errorgd.addMessage("Please restart FInCH and try again.")
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 3:
			if error:
				print"Error: ",repr(error)
			errorgd.addMessage("Threshold level must be a number between 1 and 255")
			errorgd.addMessage("Please restart FInCH and select the option to redo initial setup\nin order to change this value to a valid number.")
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 4:
			if error:
				print"Error: ",repr(error)
			errorgd.addMessage("rows and columns can't be less than 1.")
			errorgd.addMessage("Please try again and use a number >= 1 for each.")
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 5:
			if error:
				print"Error: ",repr(error)
			errorgd.addMessage("Previous grid data was loaded but at least one image didn't have associated grid data")
			errorgd.addMessage("Please delete the grid data file and restart the program,\nselecting the option for no previous grid data.")
			errorgd.addMessage("This error may be caused by corrupted grid data,\nincorrect file architecture (wrong grid data file in this run's folder),\nchanged image titles in the folder,\nor the addition of new images into the folder since the last data collection.")
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 6:
			if error:
				print"Error: ",repr(error)
			errorgd.addMessage("Couldn't open a file.")
			errorgd.addMessage("Please double check file directories and try again")
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 7:
			if error:
				print"Error: ",repr(error)	
			errorgd.addMessage("Previous grid data was loaded but at least one image didn't have associated grid data")
			errorgd.addMessage("Please delete the grid data file and restart the program,\nselecting the option for no previous grid data.")
			errorgd.addMessage("All data for this run may need to be recollected\nsince new grid creation will lead to changing data values")
			errorgd.addMessage("This error may be caused by corrupted grid data,\nincorrect file architecture (wrong grid data file in this run's folder),\nchanged image titles in the folder,\nor the addition of new images into the folder since the last data collection.")
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 8:
			if error:
				print"Error: ",repr(error)	
			errorgd.addMessage("No line found on at least one image.")
			errorgd.addMessage("Please restart FInCH and try again.")
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 9:
			if error:
				print"Error: ",repr(error)
			errorgd.addMessage("No upper beak image found for lower beak image")
			errorgd.addMessage("Please verify image files, restart FInCH, and try again")
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 10:
			if error:
				print"Error: ",repr(error)
			errorgd.addMessage("Unable to create grid for at least one image")
			errorgd.addMessage("Please restart FInCH and try again")
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 11:
			if error:
				print"Error: ",repr(error)
			errorgd.addMessage("Unable to collect data")
			errorgd.addMessage("Grid formation should be complete")
			errorgd.addMessage("Try restarting FInCH, select the option to indicate previous grid data, and try again")			
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 12:
			print"incorrect string format when getting transcription factors from user!"
			if error:
				print"Error: ",repr(error)
			errorgd.addMessage("Incorrect format of entered text!")
			errorgd.addMessage("The text entered did not match the required format. You must only use alphanumeric characters (abc,ABC,123) with entries separated by a comma (,)")
			errorgd.addMessage("Please restart FInCH and try again.")	
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 13:
			print"Unable to read config INI file"
			print"Deleting INI file and starting initial setup"
			if error:
				print"Error: ",repr(error)
			IJ.log("Unable to read FInCH.ini configuration file or values are invalid")
			IJ.log("Deleting file and starting initial setup")
			errorgd.addMessage("FInCH found the FInCH.ini config file but was unable to read it correctly or some values were invalid.")
			errorgd.addMessage("This is most likely caused by incorrect formatting when entering values during initial setup.")
			errorgd.addMessage("For example, when entering the text to search for\nin filenames (transcription factors by default),\nonly alphanumeric characters are allowed,\nentries must be separated by commas only,\nand spaces must be avoided.")
			errorgd.addMessage("This can also be caused by directly changing FInCH.ini using incorrect formatting.")
			errorgd.addMessage("Initial setup must be performed in order to enter valid values or restore default settings.")	
			errorgd.hideCancelButton()
			errorgd.showDialog()
		elif errortype == 14:
			print"Unable to create, verify, or edit colourdeconvolution.txt!"
			if error:
				print"Error: ",repr(error)
				if error != error.args:
					print"{}".format(repr(error.args))
			IJ.log("Unable to create, verify, or edit colourdeconvolution.txt!")
			errorgd.setInsets(5,5,0)
			errorgd.addMessage("FInCH was unable to read, verify, create, or edit the colourdeconvolution.txt file required for color deconvolution!")
			errorgd.setInsets(5,5,0)
			errorgd.addMessage("This file is required for FInCH to collect histogram data!")
			errorgd.setInsets(5,5,0)
			errorgd.addMessage("The option to collect data will be unavailable until this error is fixed.")
			errorgd.setInsets(5,5,0)
			errorgd.addMessage("FInCH is still able to perform grid operations, however.")
			errorgd.setInsets(5,5,0)
			errorgd.addMessage("Please verify that your FIJI installation has the correct file & folder structure.")
			errorgd.setInsets(5,5,0)
			errorgd.addMessage("If this problem continues:")	
			errorgd.setInsets(5,20,0)
			errorgd.addMessage("1) uninstall FIJI (delete your FIJI.app folder),")
			errorgd.setInsets(5,20,0)
			errorgd.addMessage(r"2) download new FIJI files (https://imagej.net/software/fiji/),")
			errorgd.setInsets(5,20,0)
			errorgd.addMessage(r"3) download new FInCH files and reinstall them (https://github.com/Lee-Cody/FInCH),")
			errorgd.setOKLabel("Continue with grid operations only")
			errorgd.setCancelLabel("Exit FInCH")
			errorgd.showDialog()
			if errorgd.wasCanceled():
				dm.data_enabled = 'error'
				exit=True
				cleanExit()
			else:
				dm.data_enabled = False
				return
		elif errortype == 15:
			if error:
				print"Error: ",repr(error)
			errorgd.addMessage("This image does not appear to be open")
	  		errorgd.addMessage("Please open the selected image and try again")
	  		errorgd.addMessage("(verify that it was processed correctly)")
			errorgd.hideCancelButton()
	  		errorgd.showDialog()
	  	elif errortype == 16:
	  		if error:
				print"Error: ",repr(error)
	  		errorgd = GenericDialog("Error")
	  		errorgd.addMessage("Please select an image to toggle grid")
	  		errorgd.hideCancelButton()
	  		errorgd.showDialog()
	  	elif errortype == 17:
	  		IJ.log("Error: unable to open thresholded image for file:")
			IJ.log("[{}]".format(error[0]))
			IJ.log("FInCH was able to locate the thresholded image, but wasn't able to open it.")
			IJ.log("This error may indicate an altered filename for a thresholded image or that the image has been edited directly.")
			IJ.log("This error does not necessarily indicate that collected data is incorrect or corrupted, however.")
			IJ.log("If you would like to open thresholded images in Image Navigator, you should restart FInCH and select the option to collect data.")
			IJ.log("This will overwrite any prior data.csv file, however, so if you would like to preserve it,")
			IJ.log("you should move the data.csv file outside the folder before running FInCH again.")
			print"Error in Interface.fMenu.showImages(): ",repr(error[1])
		elif errortype == 18:
			print"Error: DataManager.getData(): At the end of data collection, there are still cells with empty data or offimage cells with incorrect data."
			if error:
				print"Image that triggered error: ",error[0]
				print"cell that triggered error: ",error[1]
				print"cell data: ",error[2]
				print"cell.offimage is: ",error[3]
			errorgd.addMessage("At the end of data collection, there was an error collecting histogram data for some grid cells.")
			errorgd.addMessage("Please restart FInCH and try again.")
			errorgd.showDialog()
		if exit:
			cleanExit()
		#clears the log window:	
#		IJ.log("\\Clear")
		return	

########################################
	#Image Navigator:
	def showNavMenu(self):
		dm = self.data_manager
		threshimages_not_available = dm.threshimages_not_available
		singlefile = dm.singlefile
		substring = dm.cd_substring
		impicon = dm.impicon
		fimplist = dm.fimplist
		screen = IJ.getScreenSize()
		imps = [[],[]]
		for title in WindowManager.getImageTitles():
			imptemp = WindowManager.getImage(title)
			shorttitle = getNameFromTitle(title,upperlower_ini=dm.upperlower)
			overlayTemp = imptemp.getOverlay()
			for fimp in fimplist:
				if shorttitle in fimp.title:
					if "_T.tif" in title:
						if (fimp.thresh_image is None) or (fimp.thresh_image != imptemp):
							fimp.thresh_image = imptemp
					else:
						if (fimp.imp is None) or (fimp.imp != imptemp):
							fimp.imp = imptemp
					if overlayTemp is None:
						imptemp.setOverlay(fimp.grid.overlay)
			window = ImagePlus.getWindow(imptemp)
			if not imptemp.hideOverlay:
				imptemp.setHideOverlay(True)
		widthT = window.width
		heightT = window.height
		widthMin = int(0.25 * screen.width)
		heightMin = int(0.3 * screen.height)
		#### if you change the frame title, make sure to change the image navigator double click function to find the following window title###
		frame = JFrame("FInCH Image Navigator")
		panel = JPanel()
		grbag = GridBagLayout()
		panel.setLayout(grbag)
		if impicon is not None:
			frame.setIconImage(impicon)
		gbc = GridBagConstraints()
	
		spacer = JLabel("<html>Grid Overlay:<br>Select an image above to view its grid status</html>")
		titleLine = JLabel("Click on an image title to select it:")
		gbc.gridx = 0
		gbc.gridy = 0
		gbc.ipadx = int(widthMin * 0.05)
		gbc.gridwidth = 5
		gbc.gridheight = 1
		gbc.weighty = 0.1
		gbc.weightx = 1
		gbc.anchor = GridBagConstraints.CENTER
		gbc.fill = GridBagConstraints.NONE 
		panel.add(titleLine, gbc)
	
		names = []
		for fimp in fimplist:
			if ".tif" in fimp.title:
				temptitle = fimp.title.split(".tif")[0]
			else:
				temptitle = fimp.title
			names.append(temptitle)
		listModel = JList(names)
		listModel.setSelectionMode(0) # Single selection
		scrollPane = JScrollPane(listModel)
		gbc.gridx = 0
		gbc.gridy = 1
		gbc.ipadx = 0
		gbc.gridwidth = 5
		gbc.gridheight = 2
		gbc.weighty = 0.6
		gbc.weightx = 0.5
		gbc.anchor = GridBagConstraints.CENTER
		gbc.fill = GridBagConstraints.BOTH #VERTICAL, HORIZONTAL, BOTH, or NONE
		panel.add(scrollPane, gbc)
		scroll = scrollPane.createVerticalScrollBar()
		scrollPane.setVerticalScrollBar(scroll)
		frame.add(panel)
	
		spacer_emptyL1 = JLabel(" ")
		gbc.gridx = 0
		gbc.gridy = 3
		gbc.ipadx = 0
		gbc.gridwidth = 1
		gbc.gridheight = 1
		gbc.weighty = 0
		gbc.weightx = 0.1
		gbc.anchor = GridBagConstraints.CENTER
		gbc.fill = GridBagConstraints.HORIZONTAL
		panel.add(spacer_emptyL1, gbc)
	
		spacer_emptyR1 = JLabel(" ")
		gbc.gridx = 4
		gbc.gridy = 3
		gbc.ipadx = 0
		gbc.gridwidth = 1
		gbc.gridheight = 1
		gbc.weighty = 0
		gbc.weightx = 0.1
		gbc.anchor = GridBagConstraints.CENTER
		gbc.fill = GridBagConstraints.HORIZONTAL #VERTICAL, HORIZONTAL, BOTH, or NONE
		panel.add(spacer_emptyR1, gbc)
	
		spacer = JLabel("<html>Grid Overlay:<br>Select an image above to view its grid status</html>")
		gbc.gridx = 1
		gbc.gridy = 3
		gbc.ipadx = int(widthMin * 0.01)
		gbc.gridwidth = 2
		gbc.gridheight = 1
		gbc.weighty = 0.3
		gbc.weightx = 0.55
		gbc.anchor = GridBagConstraints.CENTER
		gbc.fill = GridBagConstraints.HORIZONTAL
		panel.add(spacer, gbc)
		
		spacer_emptyL2 = JLabel(" ")
		gbc.gridx = 0
		gbc.gridy = 4
		gbc.ipadx = 0
		gbc.gridwidth = 1
		gbc.gridheight = 1
		gbc.weighty = 0
		gbc.weightx = 0.1
		gbc.anchor = GridBagConstraints.CENTER
		gbc.fill = GridBagConstraints.HORIZONTAL
		panel.add(spacer_emptyL2, gbc)
	
		spacer_emptyR2 = JLabel(" ")
		gbc.gridx = 4
		gbc.gridy = 4
		gbc.ipadx = 0
		gbc.gridwidth = 1
		gbc.gridheight = 1
		gbc.weighty = 0
		gbc.weightx = 0.1
		gbc.anchor = GridBagConstraints.CENTER
		gbc.fill = GridBagConstraints.HORIZONTAL
		panel.add(spacer_emptyR2, gbc)
	
		spacer2 = JLabel("<html>Thresholded Image:<br>click to toggle the<br>thresholded/nonthresholded image</html>")
		gbc.gridx = 1
		gbc.gridy = 4
		gbc.ipadx = int(widthMin * 0.01)
		gbc.gridwidth = 2
		gbc.gridheight = 1
		gbc.weighty = 0.3
		gbc.weightx = 0.55
		gbc.anchor = GridBagConstraints.CENTER
		gbc.fill = GridBagConstraints.HORIZONTAL
		panel.add(spacer2, gbc)
	
		spacer_emptyL3 = JLabel(" ")
		gbc.gridx = 0
		gbc.gridy = 5
		gbc.ipadx = 0
		gbc.gridwidth = 2
		gbc.gridheight = 1
		gbc.weighty = 0
		gbc.weightx = 0.1
		gbc.anchor = GridBagConstraints.CENTER
		gbc.fill = GridBagConstraints.HORIZONTAL #VERTICAL, HORIZONTAL, BOTH, or NONE
		panel.add(spacer_emptyL3, gbc)
		
		closeWindows = JButton("Close all windows")
		gbc.gridx = 3
		gbc.gridy = 5
		gbc.ipadx = int(widthMin * 0.1)
		gbc.gridwidth = 1
		gbc.gridheight = 1
		gbc.weighty = 0
		gbc.weightx = 0.25
		gbc.anchor = GridBagConstraints.LINE_END
		gbc.fill = GridBagConstraints.NONE #VERTICAL, HORIZONTAL, BOTH, or NONE
		panel.add(closeWindows, gbc)
		closeWindows.setEnabled(True)
		closeWindows.addActionListener(ClickCloseWindows(frame))
		
		spacer_emptyR3 = JLabel(" ")
		gbc.gridx = 4
		gbc.gridy = 5
		gbc.ipadx = 0
		gbc.gridwidth = 1
		gbc.gridheight = 1
		gbc.weighty = 0
		gbc.weightx = 0.1
		gbc.anchor = GridBagConstraints.CENTER
		gbc.fill = GridBagConstraints.HORIZONTAL #VERTICAL, HORIZONTAL, BOTH, or NONE
		panel.add(spacer_emptyR2, gbc)
		
		ListSelectionHandler.list = listModel
		frame.setPreferredSize(Dimension(400, 300))
		frame.setMinimumSize(Dimension(widthMin, heightMin))
		frame.pack()
		frame.setLocationRelativeTo(None)
		frame.setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE)
		frame.addWindowListener(CloseControl()) # handles closing the window
		frame.setVisible(True)
		handler = ListSelectionHandler(spacer, frame, dm)
		listModel.addMouseListener(handler)
		
		toggleOL = JButton("Toggle the grid overlay")
		gbc.gridx = 3
		gbc.gridy = 3
		gbc.ipadx = int(widthMin * 0.1)
		gbc.gridwidth = 1
		gbc.gridheight = 1
		gbc.weighty = 0
		gbc.weightx = 0.25
		gbc.anchor = GridBagConstraints.LINE_END
		gbc.fill = GridBagConstraints.NONE
		panel.add(toggleOL, gbc)
		toggleOL.setEnabled(True)
		toggleOL.addActionListener(ClickToggleOLButton(handler, spacer, fimplist, dm))
		
		toggleThresh = JButton("Toggle Threshold")
		gbc.gridx = 3
		gbc.gridy = 4
		gbc.ipadx = int(widthMin * 0.1)
		gbc.gridwidth = 1
		gbc.gridheight = 1
		gbc.weighty = 0
		gbc.weightx = 0.25
		gbc.anchor = GridBagConstraints.LINE_END
		gbc.fill = GridBagConstraints.NONE #VERTICAL, HORIZONTAL, BOTH, or NONE
		panel.add(toggleThresh, gbc)
		if threshimages_not_available is False:
			toggleThresh.setEnabled(True)
		else:
			toggleThresh.setEnabled(False)
		toggleThresh.addActionListener(ClickToggleThreshButton(frame, handler, spacer2, dm))
		return

########################################
#Image Navigator Suppport Classes:
class ListSelectionHandler(MouseAdapter):

	def __init__(self, spacer, frame, dm):
		self.dm = dm
		self.threshimages_not_available = dm.threshimages_not_available
		self.spacer = spacer
		self.frame = frame
		self.selected_shortname = None
		self.selected_title = None
		self.thresh_title = None
		self.active = "AOI"
		self.overlay_hidden = True

	def mouseClicked(self, event):
#		if event.getClickCount() == 1:
#		if event.getClickCount() > 0:
		dm = self.dm
		indexct = self.list.getModel().getSize()
		impct = WindowManager.getImageCount()
		if (indexct == 0) or (impct == 0):
			self.errorWindow(15,exit=False)
			return
		index = self.list.getSelectedIndex()
		if index == None:
			self.errorWindow(15,exit=False)
			return
		ids = WindowManager.getIDList()
		for ID in ids:
			imp = WindowManager.getImage(ID)
			nameTemp = imp.getTitle()
			name = nameTemp[0:-4]
			indexName = self.list.getModel().getElementAt(index)
			if (indexName in nameTemp):
				if ("Colour" in nameTemp) and (indexName != nameTemp):
					continue
				else:
					overlayTemp = imp.getOverlay()
					if overlayTemp is None:
						self.spacer.setText("<html>Grid Overlay: <br> Not found for the selected file. <br> Should run again for this file. <br> If it was fully processed, make sure there is data present for this file as well.</html>")
					else:
						if imp.hideOverlay is False:
							self.spacer.setText("<html>Grid Overlay: <br> Visible</html>")
							self.overlay_hidden = False
						else:
							self.spacer.setText("<html>Grid Overlay: <br> Hidden</html>")
							self.overlay_hidden = True
				if (indexName != name):
					continue
				else:
					if dm.upperlower:
						if "upper" in indexName:
							shortname = nameTemp.split('per')[0]
						elif "lower" in indexName:
							shortname = nameTemp.split('wer')[0]
						else:
							shortname = getNameFromTitle(nameTemp,upperlower_ini=dm.upperlower)
					else:
						shortname = getNameFromTitle(nameTemp,upperlower_ini=dm.upperlower)
					self.selected_title = shortname
					if self.threshimages_not_available is False:
						for title in WindowManager.getImageTitles():
							if (shortname in title) and ("_T.tif" in title):
								self.thresh_title = title
								threshimp_window = WindowManager.getWindow(title)
								break
					if self.active == "AOI":
						imp.getWindow().toFront()
					else:
						threshimp_window.toFront()
					
					self.frame.toFront()
				if self.thresh_title is None:
					self.thresh_title = "no_threshtitle"
				break 
		return
					
class ClickToggleOLButton(ActionListener):
	def __init__(self, listhandler, spacer, fimps, dm):
		self.spacer = spacer
		self.listhandler = listhandler
		self.fimplist = fimps
		self.dm = dm
		self.threshimages_not_available = dm.threshimages_not_available
		
	def actionPerformed(self, event):
		dm = self.dm
		fimplist = self.fimplist
		indexct = ListSelectionHandler.list.getModel().getSize()
		impct = WindowManager.getImageCount()
		selected_title = self.listhandler.selected_title
		threshtitle = self.listhandler.thresh_title
		imp = None
		imp_t = None
		if threshtitle is None:
			threshtitle = "no_threshtitle"
		active = self.listhandler.active
		overlay_hidden = self.listhandler.overlay_hidden
		if (indexct == 0) or (impct ==0):
			self.errorWindow(15,exit=False)
			return
		index = ListSelectionHandler.list.getSelectedIndex()
	  	if index == None:
	  		self.errorWindow(15,exit=False)
			return
	  	ids = WindowManager.getIDList()
	  	if index < 0:
	  		self.errorWindow(16,exit=False)
	  	else:
	  		for title in WindowManager.getImageTitles():
	  			imptemp = WindowManager.getImage(title)
				if selected_title in title:
					if threshtitle in title:
						imp_t = imptemp
					else:
						imp = imptemp
			for fimp in fimplist:
				if selected_title in fimp.title:
					if imp.getOverlay() is None:
						imp.setOverlay(fimp.grid.overlay)
					if self.threshimages_not_available is False:
						if imp_t is not None:
							if imp_t.getOverlay() is None:
								imp_t.setOverlay(fimp.grid.overlay)
							if (fimp.thresh_image is None):
								fimp.thresh_image = imp_t
					break
			if (imp.getOverlay() is None):
				self.spacer.setText("<html>Grid Overlay: <br> Not Found</html>")
				return
				if self.threshimages_not_available is False:
					if imp_t:
						if (imp_t.getOverlay() is None):
							if imp.getOverlay():
								imp_t.setOverlay(imp.getOverlay())
							else:
								self.spacer.setText("<html>Grid Overlay: <br> Not Found</html>")
								return
			else:
				if (imp.hideOverlay is True):
					imp.setHideOverlay(False)
					if self.threshimages_not_available is False:
						if imp_t:
							imp_t.setHideOverlay(False)
					self.spacer.setText("<html>Grid Overlay: <br> Visible</html>")
					self.listhandler.overlay_hidden = False
				else:
					imp.setHideOverlay(True)
					if self.threshimages_not_available is False:
						if imp_t:
							imp_t.setHideOverlay(True)
					self.spacer.setText("<html>Grid Overlay: <br> Hidden</html>")
					self.listhandler.overlay_hidden = True
		return
		
class ClickToggleThreshButton(ActionListener):
	def __init__(self, frame, listhandler, spacer2, dm):
		self.frame = frame
		self.spacer2 = spacer2
		self.listhandler = listhandler
		self.dm = dm
		self.threshimages_not_available = dm.threshimages_not_available
		self.singlefile = dm.singlefile

	def actionPerformed(self, event):
		if self.threshimages_not_available:
			return
		dm = self.dm
		singlefile = self.singlefile
		selected_title = self.listhandler.selected_title
		threshtitle = self.listhandler.thresh_title
		if threshtitle is None:
			threshtitle = "no_threshtitle"
		active = self.listhandler.active
		
		if active == "AOI":
			for title in WindowManager.getImageTitles():
	  			if threshtitle in title:
	  				matchedwin = WindowManager.getWindow(title)
			self.listhandler.active = "T"
		elif active == "T":
			for title in WindowManager.getImageTitles():
				if threshtitle in title:
					continue
	  			if selected_title in title:
	  				matchedwin = WindowManager.getWindow(title)
			self.listhandler.active = "AOI"
		
		matchedwin.toFront()
		self.frame.toFront()
		return
		
class ClickCloseWindows(ActionListener):
	def __init__(self, frame):
		self.frame = frame
	def actionPerformed(self, event):
		exitgd = GenericDialogPlus("Close All Windows")
		exitgd.addMessage("Are you sure you would like to close all windows?")
		exitgd.showDialog()
		if exitgd.wasOKed():
			for title in WindowManager.getImageTitles():
				impclose = WindowManager.getImage(title)
				impclose.changes = False
				impclose.close()
			rm = add_RoiM()
			rm.close()
			for title in WindowManager.getNonImageTitles():
				if ("Results" in title) or ("Console" in title) or ("Log" in title):
					WindowManager.getWindow(title).close()			
			self.frame.dispose()
			return
		if exitgd.wasCanceled():
			return
		return

class CloseControl(WindowAdapter):
	def windowClosing(self, event):
		answer = JOptionPane.showConfirmDialog(event.getSource(),
			"<html>Are you sure you want to close the menu?<br>You will have to restart FInCH to open it again.</html>",
			"Confirm closing",
			JOptionPane.YES_NO_OPTION)
		if JOptionPane.NO_OPTION == answer:
			return
		else:
			event.getSource().dispose()
		return
