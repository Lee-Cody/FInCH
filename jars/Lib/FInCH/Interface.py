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
import os, sys, math, csv, copy, json, time
from java import net
from java.awt import 	(Color, GridLayout, GridBagLayout, GridBagConstraints,
						Dimension, Font, Insets, Color, BorderLayout, Panel, Button) 
from java.awt.event import ActionListener, MouseAdapter, WindowAdapter
from javax.swing import ImageIcon,JFrame,JDialog,JLabel,JButton,JList,JPanel,JScrollPane,JOptionPane
########################################
class fMenu():
	def __init__(self,versionNumber,threshlevel,cd_substring, stains):
		self.version = versionNumber
		self.threshlevel = threshlevel
		self.cd_substring = cd_substring
		self.stains = stains
		self.cols = 0
		self.rows = 0
		self.singlefile = False
		self.gridExist = False
		self.getGrid = False
		self.CDBool = False
		self.CDExist = False
		self.getDataBool = False
		self.data_overwrite = False
		self.lower_override = False
		self.filename = None
		self.filepath = None
		self.folderpath = None
		self.savefolderpath = None
		self.CDFolder = None
		self.dataManager = None
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
		self.rm = add_RoiM()
	
	def loadFiles(self):
	
		return
	
	def getDirectories(self):
	
		errorbool = False
	#---dialog to choose directory based on if user selected to process a single file or entire folder:
		#singlefile: filename, savefolderpath, filepath, folderpath
		#entire folder: folderpath, savefolderpath (filepath/filename are None)
		dcgd = GenericDialogPlus("Notice")
		if self.singlefile: 
			dcgd.addMessage("Please click OK and then select the AOI image to process.")
		else: 
			dcgd.addMessage("Please click OK and then select the folder with the AOI images to process.")
		if self.impicon is not None: 
			dcgd.setIconImage(self.impicon)
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
				self.savefolderpath = os.path.join(self.folderpath, "Processed")
				if not os.path.exists(self.savefolderpath): 
					os.mkdir(self.savefolderpath)
				if self.singlefile: 
					self.filepath = self.folderpath + self.filename
				else:
					self.filepath = None
					self.filename = None
		else:
			print"The file select dialog was canceled."
			print"Please restart FInCH and try again."
			errorbool = True
			return errorbool
		#---dialog to select folder with deconvoluted images
		if self.CDExist: 
			CDgd = GenericDialogPlus("Notice")
			CDgd.addMessage("Please click OK and then select the folder that contains the color deconvoluted AOI images.")
			if self.implogo is not None: CDgd.setIconImage(self.impicon)
			CDgd.showDialog()
			if CDgd.wasOKed():
				CDdc = DirectoryChooser("Choose a folder that contains the deconvoluted images")
				if self.implogo is not None: CDdc.setIconImage(self.impicon)
				self.CDfolder = CDdc.getDirectory()
			else:
				print "User canceled"
				errorbool = True
				return errorbool
		else:
			self.CDfolder = None
		return errorbool
	
	def displayMenu(self):
	#substring is the end of the image title we want after colour deconvolution
		threshlevel = self.threshlevel
		substring = self.cd_substring
		rm = self.rm
		errorbool = False
		
		scriptpath = os.path.dirname(__file__)
		logopath = os.path.join(scriptpath,"FInCHminilogo.png")
		rm.reset()
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
		self.implogo = implogo
		self.impicon = impicon
	
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
	
		mFont = Font("Courier", Font.BOLD, 30)
		LFont = Font("Courier", Font.BOLD, 108)
		#folder or file and grid options
		filegd = GenericDialogPlus("FInCH  v{}".format(self.version))		
		if implogo is not None:
	#		filegd.setInsets (int top, int left, int bottom)
			filegd.setInsets(5, 5, 5)
			filegd.setIconImage(impicon)
			filegd.addImage(implogo)
			filegd.addToSameRow()
			
		filegd.addMessage("FInCH", LFont)
		filegd.setInsets(0, 5, 5)
		filegd.addMessage("File Iterating & Color deconvoluting Histogram", mFont)
		filegd.setInsets(0, 5, 5)
		filegd.addMessage("What dimensions would you like for the image grids?\n(Rows and Columns must be at least 1)")
		filegd.setInsets(0, 15, 5)
		filegd.addNumericField("Rows:", 10, 0)
		filegd.addToSameRow()
		filegd.addNumericField("Columns:", 10, 0)
		filegd.setInsets(0, 5, 5) #5
		filegd.addMessage("Would you like to process a single image?\n(leave un-checked to process an entire folder)")
		filegd.setInsets(0, 15, 5) #15
		filegd.addCheckbox("Process a single image", False)
		filegd.setInsets(0, 5, 5) #5
	
		filegd.addMessage("Processing Options:\nNote: if you just want to apply a grid to an AOI image that has been processed\nand already has a grid text file saved, check option 1 and leave the rest unchecked")
		filegd.setInsets(0, 15, 5)
		filegd.addCheckbox("1. Grid data already exists for image(s)", False)
		filegd.addToSameRow()
#		filegd.addCheckbox("2. Perform Color Deconvolution", True)
#		filegd.setInsets(0, 15, 5)
#		filegd.addCheckbox("3. Collect Pixel Data", True)
#		filegd.addToSameRow()
#		filegd.addNumericField("4. Threshold Value", threshlevel, 0)
#		filegd.addMessage("Threshold Value must be a number >= 1 and <= 255.\nOnly change the threshold value if testing indicates it needs to be changed.\nIf you do change the threshold value, strongly consider recollecting any previously collected data using the new value.")
#		filegd.setInsets(0, 15, 5)
#		filegd.addCheckbox("5. Cell analysis", False) 
		
		filegd.addCheckbox("2. Collect Pixel Data", True)
		filegd.setInsets(0, 15, 5)
		filegd.addNumericField("3. Threshold Value", threshlevel, 0)
		filegd.addToSameRow()
		filegd.addCheckbox("4. Cell analysis", False)
	#	filegd.addToSameRow()
	
		filegd.showDialog()
	
		if (filegd.wasOKed()):
	
			#store grid prefs
			#cast to int; getNextNumber always returns a double
			gridRows_og = int(filegd.getNextNumber())
			gridCols_og = int(filegd.getNextNumber())
			#booleans from user options:
			#entire folder of images?
			self.singlefile = filegd.getNextBoolean()
			#grid data already exists?
			self.gridExist = filegd.getNextBoolean()
			#perform color deconvolution?
#			self.CDBool = filegd.getNextBoolean()
			#collect pixel data?
			self.getDataBool = filegd.getNextBoolean()
			self.threshlevel = filegd.getNextNumber()
			self.cell_analysis = filegd.getNextBoolean()
#			self.lower_override = filegd.getNextBoolean()
			if self.getDataBool:
				self.CDBool = True
			self.rows = gridRows_og
			self.cols = gridCols_og
			
			if (threshlevel > 255) or (threshlevel < 0) or (threshlevel != threshlevel):
				self.errorWindow(3)
				errorbool = True
				return errorbool
			if (gridRows_og < 1) or (gridCols_og < 1):
				self.errorWindow(4)
				errorbool = True
				return errorbool
			if self.gridExist and self.getDataBool:
				errorset = GenericDialogPlus("Previous grid data and data collection")
				if implogo is not None: errorset.setIconImage(impicon)
				errorset.addMessage("You selected data collection and indicated that there is previous grid data.\nThis will attempt to load a grid from a previous grid file and then will collect data using that file.")
				errorset.addMessage("Any previous data file in this folder will be overwritten")
				errorset.addMessage("Are you sure you'd like to continue?")
				errorset.enableYesNoCancel()
				errorset.showDialog()
				if errorset.wasCanceled():
#					clean_exit()
					errorbool = True
					return errorbool
				elif errorset.wasOKed():
					print "Applying grid from prior grid.csv and overwriting data"
					self.gridExist = True
					self.getDataBool = True
					self.data_overwrite = True
				else:
#					clean_exit()
					errorbool = True
					return Errorbool
		else:
			print "User canceled"
			errorbool = True
			return errorbool		
		errorbool = self.getDirectories()
		errorbool = self.gatherImages()
		
		#filename for singlefile, savefolderpath/processed_folder is saved folder for CD images, filepath is for singlefile it is path + filename, 
		#folderpath is folder w/AOI imgs, CDfolderpath is where previously processed CD images are located retrieved from dialog from user
		#generally, CDfolderpath should = savefolderpath

		return errorbool
	
	def gatherImages(self):
		errorbool = False
		invalid_filename = False
		upperfilelist = []
		lowerfilelist = []
		filelist = []
		lower_images_present = False
		for foundfile in os.listdir(self.folderpath):
			fname = str(foundfile)
			if fname.endswith(".tif") is False:
				continue
			if self.singlefile:
				if foundfile != fname:
					continue
			fname_split = fname.split("_")
			if fname_split[0][:3].lower() not in '\t'.join(self.stains):
				invalid_filename = True
			if invalid_filename:
				errorbool = True
				print"invalid filename found: ",fname
				print"Please check documentation for required file naming conventions!"
				return errorbool
			if "lower" in fname:
				lowerfilelist.append(fname)
				lower_images_present = True
			else:
				upperfilelist.append(fname)
		filelist = upperfilelist + lowerfilelist
		self.upperlist = upperfilelist
		self.lowerlist = lowerfilelist
		self.filelist = filelist
		self.lower_images_present = lower_images_present
		return errorbool
	
###########################################################################################
	def processImages(self,dm):
		errorbool = False
		grid_data_load = dm.griddata
		grid_loaded = dm.gridloaded
		singlefile = self.singlefile
		gridExist = self.gridExist
		CDBool = self.CDBool
		substring = self.cd_substring
		getDataBool = self.getDataBool
		threshlevel = self.threshlevel
		cell_analysis = self.cell_analysis
		lower_override = self.lower_override
		gridCols = self.cols
		gridRows = self.rows
		impicon = self.impicon
		implogo = self.implogo
		processed_folder = self.savefolderpath
		folder = self.folderpath
		CDfolder = self.CDfolder
		filename = self.filename
		filepath = self.filepath
		folderend = processed_folder
		upperlist = self.upperlist
		lowerlist = self.lowerlist
		filelist = self.filelist
		uppercount = len(upperlist)
		lowercount = len(lowerlist)
		fimplist = []
		rm = self.rm
		
		grid_verified = False
		if gridExist and ((grid_data_load == []) or (grid_data_load is None)):
			found_data_file = GenericDialogPlus("Grid Data File Empty")
			found_data_file.addMessage("You selected the option to indicate that grid data already exists.\nFInCH found a data file but was unable to read any grid data.")
			found_data_file.addMessage("Press Continue to generate new grid data")
			found_data_file.addMessage("Press Cancel to end the script")
			found_data_file.setOKLabel("Continue")
			if impicon is not None: found_data_file.setIconImage(impicon)
			found_data_file.showDialog()
			if found_data_file.wasOKed():
#				print"Generating new grid data..."
				gridExist = False
			if found_data_file.wasCanceled():
				print "User canceled"
				errorbool = True
				return errorbool
		if grid_loaded:
			if len(grid_data_load) != len(filelist):
				self.errorWindow(5)
				errorbool = True
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
				self.errorWindow(6)
				errorbool = True
				return errorbool
			fimp = fImp(imp)
			fimplist.append(fimp)
			errorbool = fimp.findStain(impicon)
			if errorbool:
				print"couldn't find stain for: ",fimp.name
				return errorbool
			#pair upper and lower images:
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
			#check for prev grid data:
			if grid_loaded:
				for ii in range(len(grid_data_load)):
					if grid_data_load[ii][0] in fimp.title:
						fimp.loadgriddata = grid_data_load[ii]				
						break
				if (fimp.loadgriddata is None) or (not fimp.name in fimp.loadgriddata[0]):
					self.errorWindow(7)
					errorbool = True
					return errorbool
			imp.changes = False
			imp.close()
			if singlefile: break
		if singlefile and (len(fimplist) > 1):
			self.errorWindow(0)
			errorbool = True
			print"Error: singlefile is True but fimplist has more than 1 FInCH image in the list!"
			return errorbool
		if grid_loaded:
			grid_verified = True
			dm.grid_verified = True
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
				self.errorWindow(0)
				errorbool = True
				print"Error: unable to open at least one image before creating/loading grids!"
				return errorbool
			#get lines for each image:	
			if singlefile:
				rm.reset()
				fimp = fimplist[0]
#				if fimp.isOpen() is False:
#					imp, errorbool = fimp.getfImp()
#					if errorbool:
#						print"Error: unable to open singlefile before getting user line!"
#						return errorbool
				imp = fimp.imp
				try:
					uline, angle, errorbool = get_user_line(imp, rm)
					if errorbool:
						print"error in get_user_line(legacy) or user canceled"
						return errorbool
				except:
					self.errorWindow(8)
					errorbool = True
					return errorbool
				userline = fLine(imp,uline)
				fimp.userline = userline
			else:
				rm.reset()
				IJ.setTool(Toolbar.LINE)
				lineWait = WaitForUserDialog("Waiting for user input","Draw a line on EACH image\nPress TAB key to cycle through images.\nClick OK when finished to continue.")
				lineWait.show()
				fimp = None
				for title in WindowManager.getImageTitles():
					for fimptemp in fimplist:
						if (title in fimptemp.title) or (fimptemp.title in title):
							fimp = fimptemp
					if fimp is None:
						self.errorWindow(8)	
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
						self.errorWindow(8)	
						errorbool = True
						cleanExit()
						return errorbool
					fimp.userline = fLine(imp,uline)
					imp.changes=False
					imp.close()
			#verify that each image has userline info before continuing:		
			for fimp in fimplist:
				if fimp.userline is None:
					self.errorWindow(8)	
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
#				imp = fimp.imp
#				if fimp.isOpen() is False:
#					print"fimp {} is not open!".format(fimp.name)
#					errorbool = fimp.getfImp()
#					if errorbool:
#						print"Error: unable to get or open image: ",fimp.title
#						return errorbool
				temp_gridresolution = [0,0]
				if fimp.upper is False:
					#if processing lower beak, get grid resolution from upper beak (fimp.pairedImage)
					if fimp.pairedImage is None:
						self.errorWindow(9)
						print"No upper beak image found for lower beak image: ",fimp.title
						errorbool = True
						return errorbool
					elif fimp.pairedImage.grid is None:
						self.errorWindow(9)
						print"No upper beak image found for lower beak image: ",fimp.title
						errorbool = True
						return errorbool
					elif (fimp.pairedImage.grid.res is None) or (fimp.pairedImage.grid.res == [0,0]):
						self.errorWindow(9)
						print"No upper beak image found for lower beak image: ",fimp.title
						errorbool = True
						return errorbool
					temp_gridresolution = fimp.pairedImage.grid.res
				errorbool = fimp.createGrid(gridCols,gridRows,temp_gridresolution)
				if errorbool:
					self.errorWindow(10)
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
				fimp.grid = restoreGrid(imp,processed_folder,grid_cols,grid_rows,fimp.upper,coordinates = grid_boxcoords,resolution=grid_resolution)
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
				stain = fimp.stain
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
					if stain == "dab":
						try:
							IJ.run(imp, "Colour Deconvolution", "vectors=[DAB with blue]")
						except:
							self.errorWindow(0)
							IJ.log( "Could not load or process file:", fimp.title)
							print sys.exc_info()
							errorbool = True
							return errorbool
					elif stain == "vr":
						try:
							IJ.run(imp, "Colour Deconvolution", "vectors=[VectorRed with Blue]")
						except:
							self.errorWindow(0)
							IJ.log( "Could not load or process file:", fimp.title)
							print sys.exc_info()
							errorbool = True
							return errorbool
					for title in WindowManager.getImageTitles():
						if (substring in title) and (fimp.name in title):
							cd_imp = WindowManager.getImage(title)
						else:
							imptemp = WindowManager.getImage(title)
							imptemp.changes = False
							imptemp.close()
				fimp.CD_image = cd_imp
				#save color deconvoluted image:
				fs = FileSaver(cd_imp)
				if not os.path.exists(savepath):
					fs.saveAsTiff(savepath)
				if "AOI" in cd_imp.getTitle():
					thresh_savename = (cd_imp.getTitle().split("_AOI")[0] + "_T")
				else:
					thresh_savename = (cd_imp.getTitle().split(".tif")[0] + "_T")
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
						fs = FileSaver(cd_imp)
						fs.saveAsTiff(threshSavePath)
						cd_imp.setTitle(thresh_savename)
						fimp.thresh_image = cd_imp
					except:
						print"Could not threshold image or could not load/process file:", fimp.title
						print sys.exc_info()
						errorbool = True
						return errorbool
				fimp.thresh_savepath = threshSavePath
				progresstracker += 1
				IJ.log("Step {} out of {} complete.".format(progresstracker, todo))
			closeImages()
			for fimp in fimplist:
				try:
					errorbool = dm.getData(fimp)
				except Exception as e:
					print"(Interface.processImages() > dm.getData(fimp):"
					print"Error collecting data: ",repr(e)
					errorbool = True
				if errorbool:
					self.errorWindow(11)
					print"Error collecting data!"
					return errorbool
				progresstracker += 1
				IJ.log("Step {} out of {} complete.".format(progresstracker, todo))
			try:
				errorbool = dm.storeData()
			except Exception as e:
				print"Interface.processImages() > dm.storeData():"
				print"Error storing data: ",repr(e)
				errorbool = True
			if errorbool:
				#need error
				self.errorWindow(11)
				print"Error storing data!"
				return errorbool
			progresstracker += 1
			IJ.log("Step {} out of {} complete.".format(progresstracker, todo))
					
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
				if getDataBool:
					imp_thresh = fimp.thresh_image		
			else:
				try:
					imp = IJ.openImage(fimp.path)
					if (getDataBool) and (fimp.thresh_savepath is not None):
						if os.path.exists(fimp.thresh_savepath):
							imp_thresh = IJ.openImage(fimp.thresh_savepath)
							imp_thresh.show()
				except Exception as e:
					errorgd = GenericDialogPlus("Error")
					errorgd.addMessage("FInCH encountered a bug but isn't hungry.")
					errorgd.addMessage("Couldn't open file.")
					if impicon is not None: errorgd.setIconImage(impicon)
					errorgd.addMessage("Please double check file location and try again")
					errorgd.hideCancelButton()
					errorgd.showDialog()
					print"Error in Interface.fMenu.showImages(): ",repr(e)
					errorbool = True
					return errorbool
			if imp_thresh is None:
				if fimp.thresh_image is not None:
					imp_thresh = fimp.thresh_image
					thresh_title = imp_thresh.getTitle()
					if WindowManager.getImage(thresh_title) is not None:
						imp_thresh.show()
					elif fimp.thresh_savepath is not None:
						if os.path.exists(fimp.thresh_savepath):
							try:
								imp_thresh = IJ.openImage(thresh_save_path)
								imp_thresh.show()
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
							threshimages_not_available = True
					else:
						imp_thresh = None
						threshimages_not_available = True
				else:
					threshpath = os.path.join(self.savefolderpath, "Saved")
					if os.path.exists(threshpath):
						for foundfile in os.listdir(threshpath):
							fname = str(foundfile)
							if fname.endswith(".tif") is False:
								continue
							if fimp.name in fname:
								imp_thresh_filename = fname
								thresh_save_path = os.path.join(threshpath, foundfile)
								try:
									imp_thresh = IJ.openImage(thresh_save_path)
									imp_thresh.show()
								except:
									self.errorWindow(6)
									errorbool = True
									return errorbool
								fimp.thresh_image = imp_thresh
								fimp.thresh_savepath = thresh_save_path
					else:
						imp_thresh = None
						threshimages_not_available = True
			if fimp.thresh_image is None:
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
	
	def errorWindow(self,errortype):
		print"errortype: ",errortype
		impicon = self.impicon
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
			errorgd.addMessage("Please try again and use valid number for the threshold level")
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
				
		errorgd.hideCancelButton()
		errorgd.showDialog()
		#clears the log window:	
#		IJ.log("\\Clear")
		return	

########################################
	#Image Navigator:
	def showNavMenu(self):
		threshimages_not_available = self.threshimages_not_available
		singlefile = self.singlefile
		substring = self.cd_substring
		impicon = self.impicon
		fimplist = self.fimplist
		screen = IJ.getScreenSize()
		for title in WindowManager.getImageTitles():
			imptemp = WindowManager.getImage(title)
			window = ImagePlus.getWindow(imptemp)
			overlayTemp = imptemp.getOverlay()
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
		toggleOL.addActionListener(ClickToggleOLButton(spacer, fimplist))
	
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
		handler = ListSelectionHandler(spacer, frame)
		listModel.addMouseListener(handler)
		
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
		toggleThresh.addActionListener(ClickToggleThreshButton(frame, handler, spacer2, singlefile))
		return

########################################
#Image Navigator Suppport Classes:
class ListSelectionHandler(MouseAdapter):

	def __init__(self, spacer, frame):
		self.spacer = spacer
		self.frame = frame
		self.selected_shortname = None
		self.selected_title = None
		self.thresh_title = None
		self.active = "AOI"

	def mouseClicked(self, event):
		if event.getClickCount() == 1:
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
				indexName = self.list.getModel().getElementAt(index)
				if (indexName in nameTemp):
					if ("Colour" in nameTemp) and (indexName != nameTemp):
						continue
					else:
						overlayTemp = imp.getOverlay()
						if overlayTemp is None:
							self.spacer.setText("<html>Grid Overlay: <br> Not found for the selected file. <br> Should run again for this file. <br> If it was fully processed, make sure there is data present for this file as well.</html>")
						else:
							if not imp.hideOverlay:
								self.spacer.setText("<html>Grid Overlay: <br> Visible</html>")
							else:
								self.spacer.setText("<html>Grid Overlay: <br> Hidden</html>")
#			return
#		if event.getClickCount() == 2:
#			indexct = self.list.getModel().getSize()
#			impct = WindowManager.getImageCount()
#			if (indexct == 0) or (impct ==0):
#				return
#			index = self.list.getSelectedIndex()
#			if index == None:
#				return
#			ids = WindowManager.getIDList()
			for ID in ids:
				imp = WindowManager.getImage(ID)
				nameTemp = str(imp.getTitle())
				name = nameTemp[0:-4]
				indexName = self.list.getModel().getElementAt(index)
				if (indexName != name):
					continue
				else:
					if "upper" in indexName:
						shortname = nameTemp.split('per')[0]
					elif "lower" in indexName:
						shortname = nameTemp.split('wer')[0]
					else:
						shortname = getNameFromTitle(nameTemp)
					self.selected_title = shortname
					for title in WindowManager.getImageTitles():
						if (shortname in title) and ("_T" in title):
							self.thresh_title = title
							threshimp_window = WindowManager.getWindow(title)
							break
					if self.active == "AOI":
						imp.getWindow().toFront()
					else:
						threshimp_window.toFront()
					
					self.frame.toFront()
			return 
		else:
			return
					
class ClickToggleOLButton(ActionListener):
	def __init__(self, spacer, fimps):
		self.spacer = spacer
		self.fimplist = fimps
		
	def actionPerformed(self, event):
		fimplist = self.fimplist
		indexct = ListSelectionHandler.list.getModel().getSize()
		impct = WindowManager.getImageCount()
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
	  	if index == None or index < 0:
	  		navErrorgd = GenericDialog("Error")
	  		navErrorgd.addMessage("Please select an image to toggle grid")
	  		navErrorgd.hideCancelButton()
	  		navErrorgd.showDialog()
	  	else:
	  		for ID in ids:
				imp = WindowManager.getImage(ID)
				nameTemp = imp.getTitle()
				indexName = ListSelectionHandler.list.getModel().getElementAt(index)
				if ("upper" in indexName) and ("lower" in nameTemp):
					continue
				elif ("lower" in indexName) and ("upper" in nameTemp):
					continue
				indexstr = str(indexName)
				indexshort = indexstr[0:-7]
				if indexshort in nameTemp:
					if ("Colour" in nameTemp) and (indexName != nameTemp):
						continue
					else:
						for fimptemp in fimplist:
							if fimptemp.name in nameTemp:
								fimp = fimptemp
						overlay = imp.getOverlay()
						if overlay is None:
							imp.setOverlay(fimp.grid.overlay)
							if not imp.hideOverlay:
								imp.setHideOverlay(True)
								self.spacer.setText("<html>Grid Overlay: <br> Hidden</html>")
							else:
								imp.setHideOverlay(False)
								self.spacer.setText("<html>Grid Overlay: <br> Visible</html>")
							if imp.getOverlay() is None:
								self.spacer.setText("<html>Grid Overlay: <br> Not Found</html>")
								return
						else:
							if not imp.hideOverlay:
								imp.setHideOverlay(True)
								self.spacer.setText("<html>Grid Overlay: <br> Hidden</html>")
							else:
								imp.setHideOverlay(False)
								self.spacer.setText("<html>Grid Overlay: <br> Visible</html>")
		return

class ClickToggleThreshButton(ActionListener):
	def __init__(self, frame, listhandler, spacer2,singlefile):
		self.frame = frame
		self.spacer2 = spacer2
		self.listhandler = listhandler
		self.singlefile = singlefile

	def actionPerformed(self, event):
		singlefile = self.singlefile
		selected_title = self.listhandler.selected_title
		threshtitle = self.listhandler.thresh_title
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
