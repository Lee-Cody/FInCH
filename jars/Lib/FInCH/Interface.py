#Copyright 2024 Cody Lee, All Rights Reserved#
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
						Dimension, Font, Insets, Color, BorderLayout, Panel, Button) 
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
		self.MFont = Font("Courier", Font.BOLD, 30)
		self.LFont = Font("Courier", Font.BOLD, 108)
		self.redo_setup = False
		data_manager.menuObj = self
	
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
	
		#remove any instances of the Image Navigator from previous runs:
		frames = JFrame.getFrames()
		for frame in frames:
			if "Navigator" in frame.getTitle():
				frame.dispose()
			else:
				continue
	
		if (len(WindowManager.getImageTitles()) > 0):
			alertgd =  GenericDialogPlus("Alert")
			alertgd.addMessage("Please close any open images and restart the script")
			alertgd.showDialog()
			errorbool = True
			return errorbool

		#folder or file and grid options
		filegd = GenericDialogPlus("FInCH  v{}".format(dm.version))		
		if implogo is not None:
	#		filegd.setInsets (int top, int left, int bottom)
			filegd.setInsets(5, 5, 5)
			filegd.setIconImage(impicon)
			filegd.addImage(implogo)
			filegd.addToSameRow()
			
		filegd.addMessage("FInCH", self.LFont)
		filegd.setInsets(0, 5, 5)
		filegd.addMessage("File Iterating & Color deconvoluting Histogram", self.MFont)
		filegd.setInsets(0, 5, 5)
		filegd.addMessage("What dimensions would you like for the image grids?\n(Rows and Columns must be at least 1)")
		filegd.setInsets(0, 15, 5)
		filegd.addNumericField("Rows:", 10, 0)
		filegd.addToSameRow()
		filegd.addNumericField("Columns:", 10, 0)
		filegd.setInsets(0, 5, 5)
		filegd.addMessage("Would you like to process a single image?\n(leave un-checked to process an entire folder)")
		filegd.setInsets(0, 15, 5)
		filegd.addCheckbox("Process a single image", False)
		filegd.setInsets(0, 5, 5)
		filegd.addMessage("Processing Options:\nNote: if you just want to apply a grid to an AOI image that has been processed\nand already has a grid text file saved, check option 1 and leave the rest unchecked")
		filegd.setInsets(0, 15, 5)
		filegd.addCheckbox("1. Grid data already exists for image(s)", False)
		filegd.addToSameRow()		
		filegd.addCheckbox("2. Collect Pixel Data", True)
		filegd.setInsets(0, 15, 5)
		filegd.addCheckbox("3. Cell analysis", False)	
		redo_setup_listener = redoSetupListener(dm,self,filegd)
		filegd.addButton("Complete initial setup (change settings)", redo_setup_listener)
		self.redo_setup = False
		filegd.showDialog()
	
		if (filegd.wasOKed()):
	
			#get prefs
			#cast to int; getNextNumber always returns a double
			dm.rows = int(filegd.getNextNumber())
			dm.cols = int(filegd.getNextNumber())
			#booleans from user options:
			#entire folder of images?
			dm.singlefile = filegd.getNextBoolean()
			#grid data already exists?
			dm.gridExist = filegd.getNextBoolean()
			#collect pixel data?
			dm.getDataBool = filegd.getNextBoolean()
			dm.cell_analysis = filegd.getNextBoolean()
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
		tfs = []
		tfs_matched = []
		user_tfs_matched = []
		edited_tfs = []
		for key, value in default_settings['transcriptionFactors'].items():
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
		gd = GenericDialog("Filename Identifiers (setup 1 of 4)")
		impicon = temp_settings['impicon']
		if impicon is not None:
			gd.setIconImage(impicon)
		gd.addMessage("FInCH will look for each of these in filenames. It uses these to:")
		gd.addMessage("   -verify it is processing the correct files")
		gd.addMessage("   -match each to the correct spectra for color deconvolution in FIJI.app/plugins/colourdeconvolution.txt")
		gd.addMessage("Filenames MUST start with one of the following in order for FInCH to recognize them.")
		gd.addMessage("You may change how FInCH identifies filenames by changing the following text (including deleting/adding entries).")
		gd.addMessage("Each entry must be separated by a comma. Please avoid using anything other than alphanumeric characters (abc,ABC,123) for each entry.")
		gd.addMessage("FInCH will attempt to remove any invalid characters (!@#, spaces, etc.) and blank or duplicate entries.")
		gd.setOKLabel("Next")
		tfs = temp_settings['tfs']
		gd.addStringField("Text to look for in filenames: ",",".join(tfs),40)
		gd.showDialog()
		if gd.wasOKed():
			try:
				edited_tfs_temp = str(gd.getNextString()).split(",")
			except Exception as e:
				print"incorrect string format when getting transcription factors from user!"
				print"Error: ",repr(e)
				self.errorWindow(12)
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
				retry_TF_messages.append("No valid entries found! There must be at least one valid entry to continue. Please try again and make sure to follow the formatting rules!")
			if confirm_TF:
				confirmgd = GenericDialog("Invalid Filename Identifier Entries")
				confirmgd.addMessage("Some filename identifiers contained invalid characters, or there were blank or duplicate entries.")
				confirmgd.addMessage("Invalid entries: {}".format(invalid_tfs))
				confirmgd.addMessage("Valid entries: {}".format(edited_tfs))			
				confirmgd.addMessage("These entries will be excluded from the settings file  (FInCH.ini) becuase they are likely to cause errors in FInCH.")
				confirmgd.addMessage("Would you like to continue with only the valid entries or go back and change the invalid entries?")
				confirmgd.enableYesNoCancel("Continue","Back")
				confirmgd.showDialog()
				if confirmgd.wasOKed():
					confirm_TF = False
				elif confirmgd.wasCanceled():
					errorbool = True
					print"User canceled initial setup when getting filename identifiers"
					return temp_settings, errorbool
				else:
					errorbool = "retry"
					return temp_settings,errorbool
			if errorbool == "retry":
				retrygd = GenericDialog("Invalid Filename Identifier Entries")
				for text in retry_TF_messages:
					retrygd.addMessage(text)
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
		gd = GenericDialog("Color Deconvolution Spectra (setup 2 of 4)")
		impicon = temp_settings['impicon']
		if impicon is not None:
			gd.setIconImage(impicon)
		gd.addMessage("FInCH will perform color deconvolution on the images based on the filename.")
		gd.addMessage("The spectra to use are read from FIJI.app/plugins/colourdeconvolution.txt")
		gd.addMessage("You can add additional color spectra to the above file and they will appear here (follow the format shown in colourdeconvolution.txt)")
		for i in range(len(edited_tfs)):
			tf = edited_tfs[i]
			def_spectra = cdtxt_spectra[0]
			for tfmatch in tfs_matched:
				if tfmatch[0] == tf:
					def_spectra = tfmatch[1]
			gd.addChoice(tf,cdtxt_spectra,def_spectra)
		gd.enableYesNoCancel("Next","Back")
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
		gd = GenericDialog("Threshold Cutoff Value (setup 3 of 4)")
		impicon = temp_settings['impicon']
		if impicon is not None:
			gd.setIconImage(impicon)
		gd.addMessage("FInCH will threshold images before collecting data using the following cutoff value (must be a number between 1-255).")
		gd.addMessage("Increasing this value will DECREASE the sensitivity of thresholding, potentially increasing false negative pixels.")
		gd.addMessage("Decreasing this value will INCREASE the sensitivity of thresholding, potentially increasing false positive pixels.")
		gd.addMessage("Generally, you should only change this value if you are experiencing problems with the default value.")
		gd.setInsets(0, 15, 5)
		gd.addNumericField("Thresholding Cutoff Value: ",def_treshvalue)
		gd.enableYesNoCancel("Next","Back")
		gd.showDialog()
		if gd.wasOKed():
			try:
				threshval = int(gd.getNextNumber())
			except:
				threshval = -1
			if (threshval > 255) or (threshval < 1):
				errorbool = "retry"
				retrygd = GenericDialog("Invalid Threshold Cutoff Value")
				retrygd.addMessage("The Threshold Cutoff Value must be a number between 1 and 255.")
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
		gd = GenericDialog("Upper/Lower Image Functionality (setup 4 of 4)")
		impicon = temp_settings['impicon']
		if impicon is not None:
			gd.setIconImage(impicon)		
		gd.addMessage("FInCH will distinguish between upper and lower beaks in order to preserve grid cell resolution between images for the same individual.")
		gd.addMessage("This means that FInCH will:")
		gd.addMessage("   -look for the words 'upper' and 'lower' in filenames")
		gd.addMessage("   -process filenames with upper in the name first")
		gd.addMessage("   -temporarily 'save' grid cell width & height for that 'upper' image")
		gd.addMessage("   -apply those dimensions to images that have the same name (where the only difference in the filename is 'lower' instead of 'upper').")
		gd.addMessage("(This means 'lower' images may not have grids with the user-specified columns/rows in order to have grid cells of the same dimension as their associated 'upper' file. However, the associated 'upper' image will have those user-specific column & row dimensions.)")
		gd.addMessage("So, for an image with the following filename: [Bmp4_individualxyz_upper_4x_AOI.tif], FInCH will look for an image with filename: [Bmp4_individualxyz_lower_4x_AOI.tif]")
		gd.addMessage("Check this checkbox to turn this function ON (make sure you are correctly naming your files!)")
		gd.addCheckbox("Upper/Lower Functionality", uplow)
		gd.enableYesNoCancel("Finish Setup","Back")
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

	def errorWindow(self,errortype,exit=True):
		print"errortype: ",errortype
		dm = self.data_manager
		impicon = dm.impicon
		errorgd = GenericDialogPlus("Error")
		errorgd.addMessage("FInCH encountered a bug but isn't hungry.")
		if impicon is not None: errorgd.setIconImage(impicon)
		if errortype == 0:	
			errorgd.addMessage("Please restart FInCH and try again.")
		elif errortype == 1:
			errorgd.addMessage("Error displaying Main Menu or user canceled a necessary dialog")
			errorgd.addMessage("Please restart FInCH and try again.")
		elif errortype == 2:
			errorgd.addMessage("Error checking for previous grid data or user canceled a necessary dialog")
			errorgd.addMessage("Please restart FInCH and try again.")
		elif errortype == 3:
			errorgd.addMessage("Threshold level must be a number between 1 and 255")
			errorgd.addMessage("Please restart FInCH and select the option to redo initial setup in order to change this value to a valid number.")
		elif errortype == 4:
			errorgd.addMessage("rows and columns can't be less than 1.")
			errorgd.addMessage("Please try again and use a number >= 1 for each.")
		elif errortype == 5:
			errorgd.addMessage("Previous grid data was loaded but at least one image didn't have associated grid data")
			errorgd.addMessage("Please delete the grid data file and restart the program, selecting the option for no previous grid data.")
			errorgd.addMessage("All data for this run may need to be recollected since new grid creation will lead to changing data values")
			errorgd.addMessage("This error may be caused by corrupted grid data,\nincorrect file architecture (wrong grid data file in this run's folder),\nchanged image titles in the folder,\nor the addition of new images into the folder since the last data collection.")
		elif errortype == 6:
			errorgd.addMessage("Couldn't open a file.")
			errorgd.addMessage("Please double check file directories and try again")
		elif errortype == 7:	
			errorgd.addMessage("Previous grid data was loaded but at least one image didn't have associated grid data")
			errorgd.addMessage("Please delete the grid data file and restart the program, selecting the option for no previous grid data.")
			errorgd.addMessage("All data for this run may need to be recollected since new grid creation will lead to changing data values")
			errorgd.addMessage("This error may be caused by corrupted grid data,\nincorrect file architecture (wrong grid data file in this run's folder),\nchanged image titles in the folder,\nor the addition of new images into the folder since the last data collection.")
		elif errortype == 8:	
			errorgd.addMessage("No line found on at least one image.")
			errorgd.addMessage("Please restart the script and try again.")
		elif errortype == 9:
			errorgd.addMessage("No upper beak image found for lower beak image")
			errorgd.addMessage("Please verify image files, restart the script, and try again")
		elif errortype == 10:
			errorgd.addMessage("Unable to create grid for at least one image")
			errorgd.addMessage("Please restart the script and try again")
		elif errortype == 11:
			errorgd.addMessage("Unable to collect data")
			errorgd.addMessage("Grid formation should be complete")
			errorgd.addMessage("Try restarting FInCH, select the option to indicate previous grid data, and try again")			
		elif errortype == 12:
			errorgd.addMessage("Incorrect format of entered text!")
			errorgd.addMessage("The text entered did not match the required format. You must only use alphanumeric characters (abc,ABC,123) with entries separated by a comma (,)")
			errorgd.addMessage("Please restart FInCH and try again.")		
		elif errortype == 13:
			errorgd.addMessage("FInCH found the FInCH.ini config file but was unable to read it correctly.")
			errorgd.addMessage("This is most likely caused by incorrect formatting when entering values during initial setup.")
			errorgd.addMessage("For example, when entering the text to search for in filenames (transcription factors by default), only alphanumeric characters are allowed, entries must be separated by commas only, and spaces must be avoided.")
			errorgd.addMessage("This can also be caused by directly changing FInCH.ini using incorrect formatting.")
			errorgd.addMessage("Initial setup must be performed in order to enter valid values or restore default settings.")	
		elif errortype == 14:
			errorgd.addMessage("FInCH was unable to locate or read the colourdeconvolution.txt file required for color deconvolution!")
			errorgd.addMessage("This file is included in FIJI and an altered version was provided with FInCH's installation files.")
			errorgd.addMessage("Please verify colourdeconvolution.txt was installed correctly by dropping it into your FIJI.app/plugins folder with FInCH_.py and then try again.")
			errorgd.addMessage("If you can't locate the colourdeconvolution.txt file, please download FInCH again and reinstall it.")	
		errorgd.hideCancelButton()
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
			navErrorgd = GenericDialog("Error")
	  		navErrorgd.addMessage("This image does not appear to be open")
	  		navErrorgd.addMessage("Please open the selected image and try again\n(verify that it was processed correctly)")
			navErrorgd.hideCancelButton()
	  		navErrorgd.showDialog()
			return
		index = self.list.getSelectedIndex()
		if index == None:
			navErrorgd = GenericDialog("Error")
	  		navErrorgd.addMessage("This image does not appear to be open")
	  		navErrorgd.addMessage("Please open the selected image and try again\n(verify that it was processed correctly)")
			navErrorgd.hideCancelButton()
	  		navErrorgd.showDialog()
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
			navErrorgd = GenericDialog("Error")
	  		navErrorgd.addMessage("This image does not appear to be open")
	  		navErrorgd.addMessage("Please open the selected image and try again")
			navErrorgd.hideCancelButton()
	  		navErrorgd.showDialog()
			return
	  	index = ListSelectionHandler.list.getSelectedIndex()
	  	if index == None:
			navErrorgd = GenericDialog("Error")
	  		navErrorgd.addMessage("This image does not appear to be open")
	  		navErrorgd.addMessage("Please open the selected image and try again")
			navErrorgd.hideCancelButton()
	  		navErrorgd.showDialog()
			return
	  	ids = WindowManager.getIDList()
	  	if index < 0:
	  		navErrorgd = GenericDialog("Error")
	  		navErrorgd.addMessage("Please select an image to toggle grid")
	  		navErrorgd.hideCancelButton()
	  		navErrorgd.showDialog()
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
#					if (imp.hideOverlay is False) or (imp_t.hideOverlay is False):
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
			"<html>Are you sure you want to close the menu?<br>You will have to restart the script to open it again.</html>",
			"Confirm closing",
			JOptionPane.YES_NO_OPTION)
		if JOptionPane.NO_OPTION == answer:
			return
		else:
			event.getSource().dispose()
		return
