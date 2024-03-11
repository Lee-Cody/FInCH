#Copyright 2024 Cody Lee, All Rights Reserved#
from FInCH.Interface import *
from FInCH.Utils import *
from FInCH.FInCHPlugins import *
from ij import IJ, Prefs, ImageListener, WindowManager, ImagePlus, ImageStack
from ij.gui import GenericDialog,Overlay,Roi,WaitForUserDialog,Toolbar
from fiji.util.gui import GenericDialogPlus
import os,sys,csv,json,time,re
from sets import Set
from ij.io import DirectoryChooser, FileSaver, OpenDialog
from sc.fiji.colourDeconvolution import Colour_Deconvolution
from ij.plugin.frame import RoiManager
from java import net
from javax.swing import JFrame,ImageIcon
import ConfigParser

########################################
class dataManager():
	def __init__(self,version,ini_name,default_ini_settings):
		self.menuObj = None
		self.plugins_dir = os.path.join(Prefs.getImageJDir(),'plugins')
		self.modules_dir = os.path.join(Prefs.getImageJDir(),'jars','Lib','FInCH')
		self.version = version
		self.ini_name = ini_name
		self.default_ini_settings = default_ini_settings
		self.ini_path = os.path.join(self.plugins_dir, self.ini_name)
		self.ini_exists = os.path.exists(self.ini_path)
		self.config = ConfigParser.ConfigParser()
		self.cdtxt_spectra = None
		self.default_cd = None
		self.default_cd_bool = None
		self.threshold_value = None
		self.upperlower = False
		self.impicon, self.implogo = self._getIcon()
		self.cd_substring = "Colour_2"
		##
		self.ini_settings = None
		self.stains = None
		##
		self.rm = add_RoiM()
		self.cols = 0
		self.rows = 0
		self.singlefile = False
		self.gridExist = False
		self.dataExist = False
		self.getGrid = False
		self.CDBool = False
		self.CDExist = False
		self.getDataBool = False
		self.cell_analysis = False
		self.data_overwrite = False
		self.lower_override = False
		self.filename = None
		self.filepath = None
		self.folderpath = None
		self.processedfolderpath = None
		self.imptotal = None
		self.imp_info = None
		self.overlays = None
		self.cd_info = None
		self.grid_info = None
		self.upperlist = None
		self.lowerlist = None
		self.filelist = None
		self.lower_images_present = None
		self.threshimages_not_available = False
		self.fimplist = None		
		self.time = None
#		self.uGridExist = menuObj.gridExist
		self.dataExist = False
		self.data_overwrite = False
		self.grid_overwrite = False
#		self.gridExist = menuObj.gridExist
		self.uNewGrid = False
		self.newGrid = False
		self.grid_data = None
		self.histData = None
		self.grid_loaded = False
		self.load_grid = False
		self.grid_verified = False
	
	def _getIcon(self):
		logopath = os.path.join(self.modules_dir,"FInCHminilogo.png")
		implogo = None
		try:
			implogo = IJ.openImage(logopath)
			impicon = implogo.getImage()
			if impicon is None:
				implogo = IJ.openImage("https://i.ibb.co/dbQW6wn/FIn-CH-mini-logo.png")
				logoURL = net.URL("https://i.ibb.co/dbQW6wn/FIn-CH-mini-logo.png")
				impicon = ImageIcon(logoURL).getImage()
		except Exception as e:
			print"error getting logo"
			print"Error fMenu.displayMenu(): ",repr(e)
			implogo = None
			impicon = None
		return impicon,implogo
	
	def checkINI(self,force_new_ini = False):
		errorbool = False
		self.config = ConfigParser.ConfigParser()
		if force_new_ini:
			errorbool = self._generateINI()
			return errorbool
		if self.ini_exists:
			errorbool = self._getINISettings()
		else:
			errorbool = self._generateINI()
		return errorbool
		
	def _getINISettings(self):
		errorbool = False
		ini_settings = {}
		tfs = []
		tfs_matched = []
		spectra = []
		ini_path = self.ini_path
		default_settings = self.default_ini_settings
		try:
			self.cdtxt_spectra,self.default_cd_bool = self._getColourDeconvolutionTxtFile(default_settings['defaultSpectra'])
		except Exception as e:
			print"Unable to read colourdeconvolution.txt!"
			print"Error: ",repr(e)
			errorbool = True
			self.menuObj.errorWindow(14)
			return errorbool
		cfg = self.config
		cfg_sections_temp = cfg.sections()
		if len(cfg_sections_temp) > 0:
			for section in cfg_sections_temp:
				cfg.remove_section(section)
		try:
			cfg.read(ini_path)
		except Exception as e:
			self.menuObj.errorWindow(13,exit=False)
			print"Unable to read config INI file"
			print"Error: ",repr(e)
			print"Deleting INI file and starting initial setup"
			if len(cfg_sections_temp) > 0:
				for section in cfg_sections_temp:
					cfg.remove_section(section)
			errorbool = self._generateINI()
			return errorbool
		ini_settings['transcriptionFactors'] = {}
		try:
			cfg_tf_items = cfg.items('transcriptionFactors')
			cfg_thresh = cfg.getint('Settings','thresholdCutoffValue')
			cfg_upperlower = cfg.getboolean('Settings','useUpperAndLowerFiles')
		except Exception as e:
			self.menuObj.errorWindow(13,exit=False)
			print"Unable to read config INI file"
			print"Error: ",repr(e)
			print"Deleting INI file and starting initial setup"
			if len(cfg_sections_temp) > 0:
				for section in cfg_sections_temp:
					cfg.remove_section(section)
			errorbool = self._generateINI()
			return errorbool
		if (cfg_thresh < 1) or (cfg_thresh > 255):
			self.menuObj.errorWindow(3,exit=False)
			print"thresholdCutoffValue in FInCH.ini is invalid!"
			print"Deleting INI file and starting initial setup"
			if len(cfg_sections_temp) > 0:
				for section in cfg_sections_temp:
					cfg.remove_section(section)
			errorbool = self._generateINI()
			return errorbool
		for key, value in cfg.items('transcriptionFactors'):
			found_tf = False
			found_spectra = False
			for tf_temp in tfs:
				if key == tf_temp:
					found_tf = True
					break
			for spectra_temp in spectra:
				if value == spectra_temp:
					found_spectra = True
					break
			if found_spectra is False:
				spectra.append(value)
			if found_tf is False:
				tfs.append(key)
				tfs_matched.append([key,value])
				ini_settings['transcriptionFactors'][key] = value
			if (found_tf) or ((r"\n" or "=") in (repr(key) or repr(value))):
				print"Error loading ini values: invalid entries found in INI file."
				self.menuObj.errorWindow(13,exit=False)
				print"Deleting INI file and starting initial setup"
				cfg_sections_temp = cfg.sections()
				if len(cfg_sections_temp) > 0:
					for section in cfg_sections_temp:
						cfg.remove_section(section)
				errorbool = self._generateINI()
				return errorbool
		ini_settings['tfs'] = tfs
		ini_settings['tfs_matched'] = tfs_matched
		ini_settings['thresholdCutoffValue'] = cfg.getint('Settings','thresholdCutoffValue')
		self.threshold_value = ini_settings['thresholdCutoffValue']
		ini_settings['useUpperAndLowerFiles'] = cfg.getboolean('Settings','useUpperAndLowerFiles')
		self.upperlower = ini_settings['useUpperAndLowerFiles']
		self.stains = ini_settings['transcriptionFactors']
		self.ini_settings = ini_settings
		for spectrum in spectra:
			if spectrum not in ';;;'.join(self.cdtxt_spectra):
				print"Error creating ini with default values: at least one of the spectra in FInCH.ini were not found in the colourdeconvolution.txt file!"
				self.menuObj.errorWindow(13,exit=False)
				print"Deleting INI file and starting initial setup"
				cfg_sections_temp = cfg.sections()
				if len(cfg_sections_temp) > 0:
					for section in cfg_sections_temp:
						cfg.remove_section(section)
				errorbool = self._generateINI()
				return errorbool
		print"Loaded INI settings from file: ",ini_settings
		IJ.log("FInCH.ini file loaded successfully!")
		return errorbool
	
	def _generateINI(self):
		errorbool = False
		fm = self.menuObj
		cfg = self.config
		cfg_sections_temp = cfg.sections()
		if len(cfg_sections_temp) > 0:
			for section in cfg_sections_temp:
				cfg.remove_section(section)
		create_ini = False
		defaults = False
		fm = self.menuObj
		impicon = self.impicon
		implogo = self.implogo
		default_settings = self.default_ini_settings
		ini_settings = {}
		
		setupconfirm = GenericDialogPlus("FInCH  v{}".format(self.version))		
		if implogo is not None:
			setupconfirm.setInsets(5, 5, 5)
			setupconfirm.setIconImage(impicon)
			setupconfirm.addImage(implogo)
			setupconfirm.addToSameRow()
		setupconfirm.addMessage("FInCH", fm.LFont)
		setupconfirm.setInsets(0, 5, 5)
		setupconfirm.addMessage("File Iterating & Color deconvoluting Histogram", fm.MFont)
		setupconfirm.setInsets(0, 5, 5)
		setupconfirm.addMessage("FInCH didn't find previous user settings and would like to perform initial setup.")
		setupconfirm.setInsets(0, 5, 5)
		setupconfirm.addMessage("Initial setup will walk you through the basic settings of FInCH.")
		setupconfirm.setInsets(0, 5, 5)
		setupconfirm.addMessage("While the default settings will likely work for most users, the setup dialogs will also help explain a bit about how FInCH works.")
		setupconfirm.setInsets(0, 5, 5)
		setupconfirm.addMessage("Would you like to perform initial setup?")
		setupconfirm.enableYesNoCancel("Setup FInCH","Use Default Settings")
	
		setupconfirm.showDialog()
	
		if (setupconfirm.wasOKed()):
			create_ini = True
		elif setupconfirm.wasCanceled():
			errorbool = "cancel"
			print"User canceled initial setup dialog."
			return errorbool
		else:
			create_ini = True
			defaults = True
		
		if create_ini:
			if defaults:
				#create FInCH.ini file with default settings:
				TF_settings = self._parseTFSettings(default_settings)
				def_spectra = TF_settings[2]
				self.cdtxt_spectra,self.default_cd_bool = self._getColourDeconvolutionTxtFile(def_spectra)
				tfs = []
				spectra = []
				tfs_matched = []
				cfg.add_section('transcriptionFactors')
				ini_settings['transcriptionFactors'] = {}
				for key, value in default_settings['transcriptionFactors'].items():
					found_tf = False
					found_spectra = False
					for tf_temp in tfs:
						if key == tf_temp:
							found_tf = True
							print"Duplicate file identifier entries are invalid and will be skipped"
							print"Duplicate entry: ",key
							break
					for spectra_temp in spectra:
						if value == spectra_temp:
							found_spectra = True
							break
					if found_spectra is False:
						spectra.append(value)
					if found_tf is False:
						tfs.append(key)
						tfs_matched.append([key,value])
						cfg.set('transcriptionFactors',key,value)
						ini_settings['transcriptionFactors'][key] = value
				ini_settings['tfs'] = tfs
				ini_settings['tfs_matched'] = tfs_matched
				ini_settings['thresholdCutoffValue'] = default_settings['thresholdCutoffValue']
				ini_settings['useUpperAndLowerFiles'] = default_settings['useUpperAndLowerFiles']
				self.stains = ini_settings['transcriptionFactors']
				self.ini_settings = ini_settings
				cfg.add_section('Settings')
				cfg.set('Settings','useUpperAndLowerFiles',str(default_settings['useUpperAndLowerFiles']))
				cfg.set('Settings','thresholdCutoffValue',str(default_settings['thresholdCutoffValue']))
				with open(self.ini_path, 'w') as configfile:
					cfg.write(configfile)
			else:
				#initial FInCH.ini setup with user settings:
				def_spectra = None
				self.cdtxt_spectra,self.default_cd_bool = self._getColourDeconvolutionTxtFile(def_spectra)
				user_ini_settings,errorbool = fm.userINISetupMenu(default_settings,self.cdtxt_spectra)
				if errorbool:
					return errorbool
				cfg.add_section('transcriptionFactors')
				ini_settings['tfs'] = user_ini_settings['tfs']
				ini_settings['tfs_matched'] = user_ini_settings['tfs_matched']
				ini_settings['thresholdCutoffValue'] = user_ini_settings['def_threshvalue']
				ini_settings['useUpperAndLowerFiles'] = user_ini_settings['upperlower']
				ini_settings['transcriptionFactors'] = {}
				for tf_match in user_ini_settings['tfs_matched']:
					cfg.set('transcriptionFactors',tf_match[0],tf_match[1])
					ini_settings['transcriptionFactors'][tf_match[0]] = tf_match[1]
				cfg.add_section('Settings')
				cfg.set('Settings','useUpperAndLowerFiles',str(user_ini_settings['upperlower']))
				cfg.set('Settings','thresholdCutoffValue',str(user_ini_settings['def_threshvalue']))
				self.stains = ini_settings['transcriptionFactors']
				self.ini_settings = ini_settings
				with open(self.ini_path, 'w') as configfile:
					cfg.write(configfile)
		if os.path.exists(self.ini_path):
			IJ.log("FInCH.ini settings file created successfully!")
		return errorbool
	
	def _parseTFSettings(self,settings):
		tfmatched = []
		tfs = []
		spectra = []
		for key, value in settings['transcriptionFactors'].items():
			if key not in tfs:
				tfs.append(key)
				tfmatched.append([key,value])
			if value not in spectra:
				spectra.append(value)
		parsed_TF_sets = [tfs,tfmatched,spectra]
		return parsed_TF_sets
	
	def _getColourDeconvolutionTxtFile(self,default_cds):
		cdtxt_path = os.path.join(self.plugins_dir,"colourdeconvolution.txt")
		cdtxt_lines = []
		default_cd = []
		default_cd_bool = []
		for line in open(cdtxt_path):
			found_def_spectra = False
			if "#" in str(line)[0:8]:
				continue
			linesplit = str(line).rstrip('\n').split(',')[0]
			if default_cds is not None:
				for spectra in default_cds:
					if spectra.lower() in str(linesplit).lower():
						found_def_spectra = True
			if found_def_spectra:
				default_cd_bool.append(True)
			else:
				default_cd_bool.append(False)
			cdtxt_lines.append(str(linesplit))
			
		return cdtxt_lines, default_cd_bool
	
	def getDirectories(self):
		fm = self.menuObj
		impicon = self.impicon
		errorbool = False
	#---dialog to choose directory based on if user selected to process a single file or entire folder:
		#singlefile: filename, processedfolderpath, filepath, folderpath
		#entire folder: folderpath, processedfolderpath (filepath/filename are None)
		dcgd = GenericDialogPlus("Notice")
		if self.singlefile: 
			dcgd.addMessage("Please click OK and then select the AOI image to process.")
		else: 
			dcgd.addMessage("Please click OK and then select the folder with the AOI images to process.")
		if impicon is not None: 
			dcgd.setIconImage(impicon)
		dcgd.showDialog()
		if dcgd.wasOKed():
			if self.singlefile:
				od = OpenDialog("Choose a file to process")
				self.filename = od.getFileName()
				if self.filename is None: errorbool = True
			else:
				dc = DirectoryChooser("Choose a folder to process")
				self.folderpath = dc.getDirectory()
				if self.folderpath is None: errorbool = True
			if errorbool:
				errorbool = True
				return errorbool
			else:
				if self.singlefile: 
					self.folderpath = od.getDirectory()
				self.processedfolderpath = os.path.join(self.folderpath, "Processed")
				if not os.path.exists(self.processedfolderpath): 
					os.mkdir(self.processedfolderpath)
				if self.singlefile: 
					self.filepath = self.folderpath + self.filename
				else:
					self.filepath = None
					self.filename = None
		else:
			print"The file select dialog was canceled."
			print"Please restart FInCH and try again."
			errorbool = "cancel"
			return errorbool
		return errorbool
	
	def gatherImages(self):
		errorbool = False
		found_identifier = False
		upperfilelist = []
		lowerfilelist = []
		filelist = []
		filename_identifiers = self.ini_settings['tfs']
		lower_images_present = False
		for foundfile in os.listdir(self.folderpath):
			fname = str(foundfile)
			if fname.endswith(".tif") is False:
				continue
			if self.singlefile:
				if foundfile != self.filename:
					continue
			fname_split = fname.split("_")
			for ident in filename_identifiers:
				if fname.lower().startswith(ident.lower()):
					found_identifier = True
			if found_identifier is False:
				errorbool = True
				print"invalid filename found: ",fname
				print"Please check documentation for required file naming conventions!"
				return errorbool
			if self.upperlower:
				if "lower" in fname:
					lowerfilelist.append(fname)
					lower_images_present = True
				else:
					upperfilelist.append(fname)
			else:
				upperfilelist.append(fname)
		filelist = upperfilelist + lowerfilelist
		self.upperlist = upperfilelist
		self.lowerlist = lowerfilelist
		self.filelist = filelist
		self.lower_images_present = lower_images_present
		return errorbool
	
	def loadData(self):
		errorbool = False
		errorbool = self.checkPreviousData()
		if self.gridExist:
			self.grid_data, self.grid_loaded, errorbool= self._loadDataInternal()
		return errorbool

	def checkPreviousData(self):
		errorbool = False
		fm = self.menuObj
		processed_folder = self.processedfolderpath
		impicon = self.impicon
		gridExist = self.gridExist
		getDataBool = self.getDataBool
		gridCols = self.cols
		gridRows = self.rows
		data_overwrite = self.data_overwrite
		grid_overwrite = self.grid_overwrite
		self.datapath = os.path.join(processed_folder,"data.csv")
		self.gridpath = os.path.join(processed_folder,"grid.csv")
		newdata = self.getDataBool
		loadgrid = self.gridExist
		if os.path.exists(self.datapath):
			if (newdata) and (data_overwrite is False):
				found_data_file = GenericDialogPlus("Data File Already Exists")
				found_data_file.addMessage("Histogram data file already exists")
				found_data_file.addMessage("If you continue, the data will be overwritten")
				found_data_file.addMessage("Select No to continue the script without overwriting")
				found_data_file.addMessage("Select Cancel to exit the script")
				found_data_file.enableYesNoCancel("Overwrite","Don't Overwrite")
				if impicon is not None: found_data_file.setIconImage(impicon)
				found_data_file.showDialog()	
				if found_data_file.wasOKed():	
					data_overwrite = True
					self.data_overwrite = True
				elif found_data_file.wasCanceled():
					print "user canceled at overwrite dialog"
#						cleanExit()
					errorbool = "cancel"
					return errorbool
				else:
					self.getDataBool = False
		
		if os.path.exists(self.gridpath):
			if(loadgrid is False) and (grid_overwrite is False):
				found_grid_file = GenericDialogPlus("Previous Grid Data File Found")
				found_grid_file.addMessage("Previous grid file found.")
				found_grid_file.addMessage("Would you like to overwrite previous grid file or load the previous grid file without overwriting?")
				found_grid_file.addMessage("Select Cancel to exit the script")
				found_grid_file.enableYesNoCancel("Overwrite","Don't Overwrite (Load prev. grid)")
				if impicon is not None: found_grid_file.setIconImage(impicon)
				found_grid_file.showDialog()	
				if found_grid_file.wasOKed():
					self.newGrid = True
					self.grid_overwrite = True
					self.gridExist = False
				elif found_grid_file.wasCanceled():
					print "user canceled at overwrite dialog"
					errorbool = "cancel"
					return errorbool
				else:
					self.newGrid = False
					gridExist = True
					self.gridExist = True
		else:
			if loadgrid:
				found_grid_file = GenericDialogPlus("Grid Data File Not Found")
				found_grid_file.addMessage("You selected the option to indicate that\ngrid data already exists")
				found_grid_file.addMessage("Press Continue to generate new grid data")
				found_grid_file.addMessage("Press Cancel to end the script")
				found_grid_file.setOKLabel("Continue")
				if impicon is not None: found_grid_file.setIconImage(impicon)
				found_grid_file.showDialog()
				if found_grid_file.wasOKed():
					self.newGrid = True
					self.gridExist = False
				if found_grid_file.wasCanceled():
					errorbool = "cancel"
					return errorbool
		return errorbool

	def _loadDataInternal(self):
		fm = self.menuObj
		processed_folder = self.processedfolderpath
		impicon = self.impicon
		gridExist = self.gridExist
		gridCols = self.cols
		gridRows = self.rows
		data_overwrite = self.data_overwrite
		errorbool = False
		self.datapath = os.path.join(processed_folder,"data.csv")
		self.gridpath = os.path.join(processed_folder,"grid.csv")
		grid_loaded = False
		if self.gridExist:
			fields = []
			rows = []
			emptyrows = []
			grid_data_load = []
			firstrow = True
			with open(self.gridpath, 'r') as csvfile:
				csvreader = csv.reader(csvfile, delimiter=',')
				i = 0
				for row in csvreader:
					if firstrow:
						fields.append(row)
						firstrow = False
					else:
						grid_data_load.append([])
						grid_data_load[i] = row
						if len(row) == 0:
							IJ.log("empty csv row at i = {} : {}".format(i,row))
						i += 1
			#format data:
			for i in range(len(grid_data_load)):
				#The previous selection box coordinates are loaded as a STRING obj
				#must parse it into a multidimensional array 
				#([ [gridcell_coords1], [gridcell_coords2]... ] -> [ [ [pt1], [pt2], [pt3], [pt4] ], [gridcell_coords2]...] 
				try:
					prev_grid_dimensions = json.loads(grid_data_load[i][1])
					grid_data_load[i][1] = prev_grid_dimensions
					prev_grid_res = json.loads(grid_data_load[i][2])
					grid_data_load[i][2] = prev_grid_res
					prev_coords = json.loads(grid_data_load[i][3])
					grid_data_load[i][3] = prev_coords
				except:
					errorgd = GenericDialogPlus("Error")
					errorgd.addMessage("Previous grid data was loaded but was unable to be parsed")
					errorgd.addMessage("This error indicates that the grid data has been altered or corrupted. This can be caused by\nediting and saving the grid file in another program (such as excel) and not saving with the proper settings.\nEditing grid data is not recommended but if it must be done, make sure to use something like Notepad or Wordpad.")
					if impicon is not None: errorgd.setIconImage(impicon)
					errorgd.addMessage("Press Continue to generate new grid data")
					errorgd.addMessage("Press Cancel to end the script")
					errorgd.setOKLabel("Continue")
					errorgd.showDialog()
					if errorgd.wasOKed():
						grid_loaded = False
						self.newGrid = True
						self.gridExist = False
						return None,grid_loaded,errorbool
					if errorgd.wasCanceled():
						errorbool = "cancel"
						return None,None,errorbool
				if ((grid_data_load[i][1][0] != gridCols) or (grid_data_load[i][1][1] != gridRows)) and ((self.upperlower is False) or ((self.upperlower is True) and (not "lower" in grid_data_load[i][0]))):
					errorgd = GenericDialogPlus("Error")
					errorgd.addMessage("Previous grid data column and row counts don't match current settings")
					errorgd.addMessage("Current grid settings: Columns: {}  Rows: {}".format(gridCols,gridRows))
					errorgd.addMessage("Saved grid file settings: Columns: {}  Rows: {}".format(grid_data_load[i][1][0],grid_data_load[i][1][1]))
					errorgd.addMessage("Press OK to continue (generates new grid; should then restart FInCH to collect new histogram data to match new grid).\nPress Cancel to exit script. Can then restart to enter matching Column/Row numbers.")
					if impicon is not None: errorgd.setIconImage(impicon)
					errorgd.showDialog()
					if errorgd.wasOKed():
						print"Generating new grid data..."
						grid_loaded = False
						self.newGrid = True
						self.gridExist = False
						return None,grid_loaded,errorbool
					if errorgd.wasCanceled():
						errorbool = "cancel"
						return None,None,errorbool
				else: 
					grid_loaded = True
		else: 
			self.newGrid = True
			grid_data_load = None
		return grid_data_load, grid_loaded, errorbool
	
	def getData(self,fimp):

		#imp is thresholded CD image
		#imp_aoi is non-processed aoi image
		errorbool = False
		grid_verified = self.grid_verified
		imp_aoi = IJ.openImage(fimp.path)
		imp = IJ.openImage(fimp.thresh_savepath)
		bg = fimp.bg
		overlay = imp.getOverlay()
		aoi_overlay = imp_aoi.getOverlay()
		if aoi_overlay is not None:
			imp_aoi.setHideOverlay(True)
		if overlay is not None:
			imp.setHideOverlay(True)
		imp.show()
		ip = imp.getProcessor()
		ip_aoi = imp_aoi.getProcessor()
		ipbyte = ip.convertToByteProcessor()
		ipbyte_aoi = ip_aoi.convertToByteProcessor()
		width = imp.getWidth()
		height = imp.getHeight()
		gridCols = fimp.grid.cols
		gridRows = fimp.grid.rows
		grid = fimp.grid
		cells = grid.cells
		histCt = 0
		data_total = [0,0,0]
		hist_offimage = [-1,-1,-1]
		data_all_cells = []
		for cell in cells:
			hist = []
			hist_aoi = []
			if cell.offimage:
				cell.data = [cell.name, hist_offimage]
				histCt += 1
				continue
			else:
				ipbyte.setRoi(cell.roi)
				hist = ipbyte.getHistogram()
				hist_data = [hist[0],hist[len(hist)-1]]
				ipbyte_aoi.setRoi(cell.roi)
				hist_aoi = ipbyte_aoi.getHistogram()
				hist_data_aoi = [hist_aoi[0],hist_aoi[len(hist_aoi)-1]]
				if bg == 0:
					#black background
					data_background = hist_data[0] - hist_data_aoi[0]
				else:
					#white background (bg = 255)
					data_background = hist_data[0] - hist_data_aoi[len(hist_data_aoi)-1]
				data_hist_total = data_background + hist_data[1]
				data_cell_temp = [data_background, hist_data[1], data_hist_total]
				cell.data = [cell.name, data_cell_temp]
				data_total[0] += data_cell_temp[0]
				data_total[1] += data_cell_temp[1]
				data_total[2] += (data_cell_temp[0] + data_cell_temp[1])
				histCt += 1
		for cell in cells:
			if (cell.data == None):
				alertgd =  GenericDialogPlus("Error")
				alertgd.addMessage("FInCH encountered a bug but isn't hungry.")
				alertgd.addMessage("Error description:")
				alertgd.addMessage("At the end of data collection, there are still cells with empty data.")
				alertgd.showDialog()
				print"Error: DataManager.getData(): At the end of data collection, there are still cells with empty data or offimage cells with incorrect data."
				print"Image that triggered error: ",fimp.title
				print"cell that triggered error: ",cell.name
				print"cell data: ",cell.data
				print"cell.offimage is: ",cell.offimage
				errorbool = True
				return errorbool
			data_all_cells.append(cell.data)
		grid.cell_data = data_all_cells
		grid.total_data = data_total
		imp_aoi.changes = False
		imp_aoi.close()
		imp.changes = False
		imp.close()
		return errorbool
		
	def storeData(self):
		errorbool = False
		fm = self.menuObj
		fimplist = self.fimplist
		impicon = self.impicon
		gridExist = self.gridExist
		data_overwrite = self.data_overwrite
		grid_overwrite = self.grid_overwrite
		processed_folder = self.processedfolderpath
		final_data = self.histData
		grid_info = self.grid_data
		dataname = "data.csv"
		datapath = os.path.join(processed_folder,dataname)
		g_dataname = "grid.csv"
		g_datapath = os.path.join(processed_folder,g_dataname)
		save_grid = False
		if (gridExist is False) or (grid_overwrite):
			save_grid = True
		save_data = self.getDataBool
		dt = time.localtime()
		timestamp = "[{}/{}/{} {}:{}:{}]".format(dt[1],dt[2],dt[0],dt[3],dt[4],dt[5])
		if save_data:
			if os.path.exists(datapath):
				if data_overwrite is False:
					found_data_file = GenericDialogPlus("data.csv File Already Exists")
					found_data_file.addMessage("Histogram data file already exists")
					found_data_file.addMessage("Would you like to overwrite the data.csv file for this entire folder?")
					found_data_file.enableYesNoCancel("Overwrite","Continue without saving data")
					found_data_file.setCancelLabel("Exit Script")
					if impicon is not None: found_data_file.setIconImage(impicon)
					found_data_file.showDialog()
					if found_data_file.wasOKed():
						IJ.log("Overwriting previous histogram data (data.csv).")
						print"Overwriting previous histogram data (data.csv)."
						save_data = True
					elif found_data_file.wasCanceled():
						errorbool = "cancel"
						return errorbool
					else:
						save_data = False
				else:
					IJ.log("Overwriting previous histogram data (data.csv).")
					print"Overwriting previous histogram data (data.csv)."
		if save_grid:
			if os.path.exists(g_datapath):
				if grid_overwrite is False:
					found_grid_file = GenericDialogPlus("grid.csv File Already Exists")
					found_grid_file.addMessage("Grid data file already exists")
					found_grid_file.addMessage("Would you like to overwrite the grid data file for this entire folder?")
					found_grid_file.enableYesNoCancel("Overwrite","Continue without saving data")
					found_grid_file.setCancelLabel("Exit Script")
					if impicon is not None: found_grid_file.setIconImage(impicon)
					found_grid_file.showDialog()
					if found_grid_file.wasOKed():
						IJ.log("Overwriting previous grid data (grid.csv).")
						print"Overwriting previous grid data (grid.csv)."
						save_grid = True
					elif found_grid_file.wasCanceled():
						errorbool = "cancel"
						return errorbool
					else:
						save_grid = False
				else:
					IJ.log("Overwriting previous grid data (grid.csv).")
					print"Overwriting previous grid data (grid.csv)."
		firstheader = "Image Title {}".format(timestamp)
		if save_data:
			try:
				with open(datapath,'w') as csvfile:
					writer = csv.writer(csvfile)
					writer.writerow([firstheader, "Whole Image Total AOI Pixels", "Whole Image Black Pixels", "Whole Image White Pixels (TF signal)", "Gridbox Histogram Counts [box id, black, white, total]"])
					for fimp in fimplist:
						grid = fimp.grid
						row = [fimp.title,grid.total_data[2], grid.total_data[0], grid.total_data[1], grid.cell_data]
						writer.writerow(row)
			except Exception as e:
				print"error storing cell histogram data"
				print"datapath: ",datapath
				print"The path exists: ",os.path.exists(datapath)
				print"Error storeData(): ",repr(e)
				IJ.log("FInCH encountered a bug but isn't hungry.")
				IJ.log("Unable to save histogram data (data.csv)!")
		if save_grid:
			try:
				with open(g_datapath,'w') as csvgridfile:
					gwriter = csv.writer(csvgridfile)
					gwriter.writerow([firstheader, "Grid Columns x Rows", "Grid ColWidth RowHeight", "Gridbox Coordinates"])
					for fimp in fimplist:
						grid = fimp.grid
						row = [fimp.title,[grid.cols,grid.rows],grid.res,grid.cell_coordinates]	
						gwriter.writerow(row)
			except Exception as e:
				print"error storing grid data"
				print"grid.csv - g_datapath: ",g_datapath
				print"Error storeData(): ",repr(e)
				IJ.log("FInCH encountered a bug but isn't hungry.")
				IJ.log("Unable to save histogram data (data.csv)!")
		print "data stored: ",timestamp
		IJ.log("data stored: ".format(timestamp))
		return errorbool
		
###########################################################################################		
	def processImages(self):
		fm = self.menuObj
		errorbool = False
		grid_data_load = self.grid_data
		grid_loaded = self.grid_loaded
		singlefile = self.singlefile
		gridExist = self.gridExist
		CDBool = self.CDBool
		substring = self.cd_substring
		getDataBool = self.getDataBool
		threshlevel = self.threshold_value
		cell_analysis = self.cell_analysis
		lower_override = self.lower_override
		gridCols = self.cols
		gridRows = self.rows
		impicon = self.impicon
		implogo = self.implogo
		processed_folder = self.processedfolderpath
		folder = self.folderpath
		CDfolder = processed_folder
		filename = self.filename
		filepath = self.filepath
		folderend = processed_folder
		upperlist = self.upperlist
		lowerlist = self.lowerlist
		filelist = self.filelist
		upperlower = self.upperlower
		uppercount = len(upperlist)
		lowercount = len(lowerlist)
		fimplist = []
		rm = self.rm
		
		grid_verified = False
		grid_read_error = False
		if gridExist and ((grid_data_load == []) or (grid_data_load is None)):
			grid_read_error = True
		if grid_loaded:
			if len(grid_data_load) != len(filelist):
				grid_read_error = True
		if grid_read_error:
			found_data_file = GenericDialogPlus("Grid Data File Error")
			found_data_file.addMessage("FInCH was unable to read grid data from the grid.csv file or the data didn't match the image(s).")
			found_data_file.addMessage("Press Continue to generate new grid data")
			found_data_file.addMessage("Press Cancel to end the script")
			found_data_file.setOKLabel("Continue")
			if impicon is not None: found_data_file.setIconImage(impicon)
			found_data_file.showDialog()
			if found_data_file.wasOKed():
#				print"Generating new grid data..."
				gridExist = False
				grid_loaded = False
				self.grid_loaded = False
				self.gridExist = False
				self.grid_overwrite = True
			if found_data_file.wasCanceled():
				print "User canceled"
				errorbool = "cancel"
				return errorbool
			
#################################################################################################
	#fMenu.processImages()
	#PART1 - SETUP
		imp_info = []
		imp_p_grid = []
		upper = True
		for i in range(len(filelist)):
			if i < uppercount:
				imagefile = upperlist[i]
			else:
				imagefile = lowerlist[i-uppercount]
				upper = False
				if (i == uppercount) and (imagefile != lowerlist[0]) and not lower_override:
					print"upper vs lower isn't assigning files correctly"
			imagename = str(imagefile)
			if singlefile:
				if imagename != str(filename):
					continue
			path = os.path.join(folder, imagefile)
			try:
				imp = IJ.openImage(path)
			except:
				fm.errorWindow(6)
				errorbool = True
				return errorbool
			fimp = fImp(imp,upperlower_ini=upperlower)
			fimplist.append(fimp)
			errorbool = fimp.findStain(self.stains,impicon)
			if errorbool:
				print"couldn't find stain for: ",fimp.name
				return errorbool
			#pair upper and lower images:
			if upperlower:
				if "lower" in imagename:
					tempname = imagename.split("_lower")[0]
					for fimptemp in fimplist:
						if fimptemp.upper is False:
							continue
						else:
							tempname = fimp.title.split("_lower")[0]
							if tempname in fimptemp.title:
								fimp.pairedImage = fimptemp
								fimptemp.pairedImage = fimp
			else:
				fimp.upper = True
			#check for prev grid data:
			if grid_loaded:
				for ii in range(len(grid_data_load)):
					if grid_data_load[ii][0] in fimp.title:
						fimp.loadgriddata = grid_data_load[ii]				
						break
				if (fimp.loadgriddata is None) or (not fimp.name in fimp.loadgriddata[0]):
					fm.errorWindow(7)
					errorbool = True
					return errorbool
			imp.changes = False
			imp.close()
			if singlefile: break
		if singlefile and (len(fimplist) > 1):
			fm.errorWindow(0)
			errorbool = True
			print"Error: singlefile is True but fimplist has more than 1 FInCH image in the list!"
			return errorbool
		if grid_loaded:
			grid_verified = True
			self.grid_verified = True
		self.fimplist = fimplist
#################################################################################################
	#fMenu.processImages()
	#PART2 - Grids
		totalimagecount = len(fimplist)
		progresstracker = 0
		if getDataBool:
			todo = ((totalimagecount * 3)+1)
		else:
			todo = totalimagecount
		if cell_analysis:
			todo += totalimagecount
		rm.reset()
		
		if not grid_verified:
		#previous grid info doesn't exist or wasn't able to be verified
		#create new grids:
			#try to make sure all images are open:
			errorbool = openFInCHImps(fimplist)
			if errorbool:
				return errorbool
			imp_count = WindowManager.getImageCount()
			if (imp_count != totalimagecount):
				fm.errorWindow(0)
				errorbool = True
				print"Error: unable to open at least one image before creating/loading grids!"
				return errorbool
			#get lines for each image:	
			if singlefile:
				rm.reset()
				fimp = fimplist[0]
				imp = fimp.imp
				try:
					uline, angle, errorbool = get_user_line(imp, rm)
					if errorbool:
						print"error in get_user_line(legacy) or user canceled"
						return errorbool
				except:
					fm.errorWindow(8)
					errorbool = True
					return errorbool
				userline = fLine(imp,uline)
				fimp.userline = userline
			else:
				rm.reset()
				IJ.setTool(Toolbar.LINE)
				lineWait = WaitForUserDialog("Waiting for user input","Draw a line on EACH image to indicate the angle of the grid.\nThe direction in which you draw the line will determine grid orientation (such as the numbering of grid columns).\nPress TAB key to cycle through images.\nClick OK when finished to continue.")
				lineWait.show()
				fimp = None
				for title in WindowManager.getImageTitles():
					for fimptemp in fimplist:
						if (title in fimptemp.title) or (fimptemp.title in title):
							fimp = fimptemp
					if fimp is None:
						fm.errorWindow(8)	
						errorbool = True
						cleanExit()
						return errorbool
					imp = fimp.imp
					windowtemp = ImagePlus.getWindow(imp)
					imp_count = WindowManager.getImageCount()
					try:
						roiUserLine = imp.getRoi()
						angle = roiUserLine.getAngle()
						pointsX = roiUserLine.getPolygon().xpoints
						pointsY = roiUserLine.getPolygon().ypoints
						uline = [[pointsX[0],pointsY[0]],[pointsX[1],pointsY[1]]]
						imp.setRoi(None)
					except Exception as e:
						print"Error: ",repr(e)
						fm.errorWindow(8)	
						errorbool = True
						cleanExit()
						return errorbool
					fimp.userline = fLine(imp,uline)
					imp.changes=False
					imp.close()
			#verify that each image has userline info before continuing:		
			for fimp in fimplist:
				if fimp.userline is None:
					fm.errorWindow(8)	
					errorbool = True
					cleanExit()
					return errorbool
			IJ.log("Verified User Lines")
			rm.reset()
			for fimp in fimplist:
				imp, errorbool = fimp.getfImp()
				if errorbool:
					print"Error: unable to get or open image: ",fimp.title
					return errorbool
				#create grid:
				temp_gridresolution = [0,0]
				if upperlower and (fimp.upper is False):
					#if processing lower beak, get grid resolution from upper beak (fimp.pairedImage)
					if fimp.pairedImage is None:
						fm.errorWindow(9)
						print"No upper beak image found for lower beak image: ",fimp.title
						errorbool = True
						return errorbool
					elif fimp.pairedImage.grid is None:
						fm.errorWindow(9)
						print"No upper beak image found for lower beak image: ",fimp.title
						errorbool = True
						return errorbool
					elif (fimp.pairedImage.grid.res is None) or (fimp.pairedImage.grid.res == [0,0]):
						fm.errorWindow(9)
						print"No upper beak image found for lower beak image: ",fimp.title
						errorbool = True
						return errorbool
					temp_gridresolution = fimp.pairedImage.grid.res
				errorbool = fimp.createGrid(gridCols,gridRows,temp_gridresolution)
				if errorbool:
					fm.errorWindow(10)
					print"Unable to create new grid for image: ",fimp.title
					return errorbool
				imp.changes=False
				imp.close()
				progresstracker += 1
				IJ.log("Step {} out of {} complete.".format(progresstracker, todo))
		else:
			print"restoring grids from prior grid CSV"
			#load grids from previous grid data:
			for fimp in fimplist:
				imp, errorbool = fimp.getfImp()
				if errorbool:
					print"Error: unable to get or open image: ",fimp.title
					return errorbool
#				imp = fimp.imp
#				imp.show()
				prev_grid = fimp.loadgriddata
				grid_cols = prev_grid[1][0]
				grid_rows = prev_grid[1][1]
				grid_resolution = [prev_grid[2][0],prev_grid[2][1]]
				grid_boxcoords = prev_grid[3]
				if upperlower:
					upper = fimp.upper
				else:
					upper = True
				fimp.grid = restoreGrid(imp,processed_folder,grid_cols,grid_rows,upper,coordinates = grid_boxcoords,resolution=grid_resolution)
				overlay_temp = fimp.grid.overlay
				grid_rois = fimp.grid.cell_rois
				box_corners_temp = fimp.grid.bounding_box.points
				imp.changes=False
				imp.close()
				progresstracker += 1
				IJ.log("Step {} out of {} complete.".format(progresstracker, todo))
		#save grid roi's:
		for fimp in fimplist:
			if fimp.grid.cells is not None:
				roi_grid_name = fimp.grid.name + ".zip"
				gridfolder = os.path.join(processed_folder,"Grids")
				if not os.path.exists(gridfolder): 
					os.mkdir(gridfolder)
				roipath = os.path.join(gridfolder,roi_grid_name)
				if not os.path.exists(roipath):
					fimp.grid.saveRois(roipath)
		closeImages()
#################################################################################################
	#fMenu.processImages()
	#PART3 - Get Data
		if getDataBool:
			for fimp in fimplist:
				imp, errorbool = fimp.getfImp()
				if errorbool:
					print"Error: unable to get or open image: ",fimp.title
					return errorbool
#				imp = fimp.imp
				cd_imp = None
				cd_imp_title = ""
				# stain = fimp.stain
				savename = fimp.name
				if not ".tif" in savename:
					savename += ".tif"
				savepath = os.path.join(processed_folder, savename)
				fimp.savepath = savepath
				if os.path.exists(savepath):
					try:
						cd_imp = IJ.openImage(savepath)
						cd_imp.show()
						cd_imp_title = cd_imp.getTitle()
					except Exception as e:
						print"unable to open existing deconvoluted file for: {}  path: {}".format(savename, savepath)
						print"Error: ",repr(e)
				else:
					try:
						IJ.run(imp, "Colour Deconvolution", "vectors=[{}]".format(fimp.stain))
					except Exception as e:
						IJ.log("Could not load or process file:", fimp.title)
						print"Could not perform cd on file: {} stain: {}".format(fimp.title,fimp.stain)
						print sys.exc_info()
						print"Error: ",repr(e)
						errorbool = True
						fm.errorWindow(0)
						return errorbool
					for title in WindowManager.getImageTitles():
						if (substring in title) and (fimp.name in title):
							cd_imp = WindowManager.getImage(title)
						else:
							imptemp = WindowManager.getImage(title)
							imptemp.changes = False
							imptemp.close()
					#save color deconvoluted image:
					fs = FileSaver(cd_imp)
					fs.saveAsTiff(savepath)
				fimp.CD_image = cd_imp
				thresh_savename = (fimp.name + "_T")
#				if "AOI" in cd_imp.getTitle():
#					thresh_savename = (fimp.name + "_T")
#				else:
#					thresh_savename = (cd_imp.getTitle().split(".tif")[0] + "_T")
				if not ".tif" in thresh_savename:
					thresh_savename += ".tif"
				threshSaveDir = os.path.join(processed_folder, "Saved")
				if not os.path.exists(threshSaveDir):
					os.mkdir(threshSaveDir)
				threshSavePath = os.path.join(threshSaveDir, thresh_savename)
				if not os.path.exists(threshSavePath):
					try:
						IJ.setThreshold(cd_imp, threshlevel, 255)
						IJ.run(cd_imp, "Convert to Mask", "")
						IJ.run(cd_imp, "Invert", "")
						cd_imp.setTitle(thresh_savename)
						fs = FileSaver(cd_imp)
						fs.saveAsTiff(threshSavePath)
						fimp.thresh_image = cd_imp
					except Exception as e:
						IJ.log("Could not threshold image or could not load/process file:", fimp.title)
						print"Could not threshold image or could not load/process file:", fimp.title
						print"Image file: ",cd_imp
						print"threshold cutoff value: ",threshlevel
						print"threshold save path: ",threshSavePath
						print"Error: ",repr(e)
						print sys.exc_info()
						errorbool = True
						return errorbool
				fimp.thresh_savepath = threshSavePath
				progresstracker += 1
				IJ.log("Step {} out of {} complete.".format(progresstracker, todo))
				closeImages()
			for fimp in fimplist:
				try:
					errorbool = self.getData(fimp)
				except Exception as e:
					print"(dataManager.processImages() > dataManager.getData(fimp):"
					print"Error collecting data: ",repr(e)
					errorbool = True
				if errorbool:
					fm.errorWindow(11)
					print"Error collecting data!"
					return errorbool
				progresstracker += 1
				IJ.log("Step {} out of {} complete.".format(progresstracker, todo))
			progresstracker += 1
			IJ.log("Step {} out of {} complete.".format(progresstracker, todo))
		#save data and/or grids:
		if self.getDataBool or (self.gridExist is False) or self.grid_overwrite or self.data_overwrite:
			try:
				errorbool = self.storeData()
			except Exception as e:
				print"dataManager.processImages() > dataManager.storeData():"
				print"Error storing data: ",repr(e)
				errorbool = True
			if errorbool:
				#need error
				fm.errorWindow(11)
				print"Error storing data!"
				return errorbool			
#################################################################################################
	#fMenu.processImages()
	#PART4 - Analyze Cells
		
		if cell_analysis:
			for fimp in fimplist:
				imp, errorbool = fimp.getfImp()
				if errorbool:
					print"Error: unable to get or open image: ",fimp.title
					return errorbool
				try:
					analyzeCells(fimp,folder,processed_folder)
				except Exception as e:
					print"Interface.processImages() > analyzeCells(fimp,imagefolder,savefolder):"
					print"Error analyzing cells: ",repr(e)
				progresstracker += 1
				IJ.log("Step {} out of {} complete.".format(progresstracker, todo))
			for title in WindowManager.getNonImageTitles():
				if "Results" in title:
					WindowManager.getWindow(title).close()
		return errorbool
#################################################################################################
	##End of fMenu.processImages()
#################################################################################################

	def openImages(self):
		fm = self.menuObj
		errorbool = False
		rm = add_RoiM()
		rm.reset()
		singlefile = self.singlefile
		imptotal = self.imptotal
		imp_info = self.imp_info
		overlays = self.overlays
		cd_info = self.cd_info
		grid_info = self.grid_info
		gridExist = self.gridExist
		getDataBool = self.getDataBool
		processed_folder = self.processedfolderpath
		threshSaveDir = os.path.join(processed_folder, "Saved")
		impicon = self.impicon
		opentitles = []
		threshimages_not_available = self.threshimages_not_available
		for title in WindowManager.getImageTitles():
			opentitles.append(title)
		for fimp in self.fimplist:
			title = fimp.title
			imp = None
			imp_thresh = None
			if title in opentitles:
				imp = fimp.imp
				if fimp.thresh_image is not None:
					imp_thresh = fimp.thresh_image		
			else:
				try:
					imp = IJ.openImage(fimp.path)
					if (getDataBool) and (fimp.thresh_savepath is not None):
						if os.path.exists(fimp.thresh_savepath):
							imp_thresh = IJ.openImage(fimp.thresh_savepath)
							imp_thresh.show()
							if (fimp.thresh_image is None) or (fimp.thresh_image != imp_thresh):
								fimp.thresh_image = imp_thresh
				except Exception as e:
					print"Error in Interface.fMenu.showImages(): ",repr(e)
					errorbool = True
					fm.errorWindow(6)
					return errorbool
			if (imp_thresh is None) and (fimp.thresh_image is not None):
				imp_thresh = fimp.thresh_image
				thresh_title = imp_thresh.getTitle()
				if WindowManager.getImage(thresh_title) is not None:
					imp_thresh.show()
				elif fimp.thresh_savepath is not None:
					if os.path.exists(fimp.thresh_savepath):
						try:
							imp_thresh = IJ.openImage(thresh_save_path)
							imp_thresh.show()
							if fimp.thresh_image != imp_thresh:
								fimp.thresh_image = imp_thresh
						except Exception as e:
							IJ.log("Error: unable to open thresholded image for file:")
							IJ.log("[{}]".format(fimp.title))
							IJ.log("This error may indicate an altered filename for a thresholded image")
							IJ.log("This error does not necessarily indicate that collected data is incorrect or corrupted, however.")
							print"Error in Interface.fMenu.showImages(): ",repr(e)
							imp_thresh = None
							threshimages_not_available = True
					else:
						imp_thresh = None
				else:
					imp_thresh = None
			if (imp_thresh is None) and (os.path.exists(threshSaveDir)):
				thresh_savename = (fimp.name + "_T")
				if not ".tif" in thresh_savename:
					thresh_savename += ".tif"
				imp_thresh_savepath = os.path.join(threshSaveDir,thresh_savename)
				if os.path.exists(imp_thresh_savepath):
					try:
						imp_thresh = IJ.openImage(thresh_save_path)
						imp_thresh.show()
						if (fimp.thresh_image is None) or (fimp.thresh_image != imp_thresh):
							fimp.thresh_image = imp_thresh
							fimp.thresh_savepath = imp_thresh_savepath
					except Exception as e:
						IJ.log("Error: unable to open thresholded image for file:")
						IJ.log("[{}]".format(fimp.title))
						IJ.log("FInCH was able to locate the thresholded image, but wasn't able to open it.")
						IJ.log("This error may indicate an altered filename for a thresholded image or that the image has been edited directly.")
						IJ.log("This error does not necessarily indicate that collected data is incorrect or corrupted, however.")
						IJ.log("If you would like to open thresholded images in Image Navigator, you should restart FInCH and select the option to collect data.")
						IJ.log("This will overwrite any prior data.csv file, however, so if you would like to preserve it,")
						IJ.log("you should move the data.csv file outside the folder before running FInCH again.")
						print"Error in Interface.fMenu.showImages(): ",repr(e)
						imp_thresh = None
						threshimages_not_available = True
				else:
					for foundfile in os.listdir(threshSaveDir):
						fname = str(foundfile)
						if fname.endswith(".tif") is False:
							continue
						if fimp.name in fname:
							imp_thresh_filename = fname
							thresh_save_path = os.path.join(threshSaveDir, foundfile)
							if os.path.exists(thresh_save_path):
								try:
									imp_thresh = IJ.openImage(thresh_save_path)
									imp_thresh.show()
								except Exception as e:
									IJ.log("Error: unable to open thresholded image for file:")
									IJ.log("[{}]".format(fimp.title))
									IJ.log("FInCH was able to locate the thresholded image, but wasn't able to open it.")
									IJ.log("This error may indicate an altered filename for a thresholded image or that the image has been edited directly.")
									IJ.log("This error does not necessarily indicate that collected data is incorrect or corrupted, however.")
									IJ.log("If you would like to open thresholded images in Image Navigator, you should restart FInCH and select the option to collect data.")
									IJ.log("This will overwrite any prior data.csv file, however, so if you would like to preserve it,")
									IJ.log("you should move the data.csv file outside the folder before running FInCH again.")
									print"Error in Interface.fMenu.showImages(): ",repr(e)
									imp_thresh = None
									threshimages_not_available = True
								if (fimp.thresh_image is None) or (fimp.thresh_image != imp_thresh):
									fimp.thresh_image = imp_thresh
									fimp.thresh_savepath = thresh_save_path
							else:
								imp_thresh = None
								threshimages_not_available = True
			
			if (imp_thresh is not None):
				if (fimp.thresh_image is None) or (fimp.thresh_image != imp_thresh):
					fimp.thresh_image = imp_thresh
			else:
				threshimages_not_available = True
			imp.show()
			overlay_temp = imp.getOverlay()
			if overlay_temp is None:
				imp.setOverlay(fimp.grid.overlay)
			if threshimages_not_available is False:
					overlay_thresh_temp = imp_thresh.getOverlay()
					if overlay_thresh_temp is None:
						imp_thresh.setOverlay(fimp.grid.overlay)
			self.threshimages_not_available = threshimages_not_available
		return errorbool
	
