#Copyright 2024 Cody Lee, All Rights Reserved#
from FInCH.Interface import *
from FInCH.Utils import *
from FInCH.FInCHPlugins import *
from ij import IJ, ImageListener, WindowManager, ImagePlus, ImageStack
from ij.gui import GenericDialog
from fiji.util.gui import GenericDialogPlus
import os,csv,json,time
########################################
class dataManager():
	def __init__(self,menuObj):
		self.menuObj = menuObj
		self.time = None
		self.uGridExist = menuObj.gridExist
		self.dataExist = False
		self.gridExist = menuObj.gridExist
		self.uNewGrid = False
		self.newGrid = False
		self.gridData = None
		self.histData = None
		self.griddataloaded = False
		self.load_grid = False
		self.grid_verified = False
		
	def loadData(self):
		errorbool = False
		self.griddata, self.gridloaded, errorbool= self._loadDataInternal()
		return errorbool

	def _loadDataInternal(self):
		fm = self.menuObj
		processed_folder = fm.savefolderpath
		impicon = fm.impicon
		gridExist = fm.gridExist
		gridCols = fm.cols
		gridRows = fm.rows
		data_overwrite = fm.data_overwrite
		if gridExist:
			self.load_grid = True
		else:
			self.load_grid = False
		grid_loaded = False
		errorbool = False
		self.datapath = os.path.join(processed_folder,"data.csv")
		self.gridpath = os.path.join(processed_folder,"grid.csv")
		histdataOW_OK = False
		p_grid_verified = False
		if os.path.exists(self.datapath) and fm.getDataBool and (data_overwrite is False):
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
				fm.data_overwrite = True
			elif found_data_file.wasCanceled():
				print "user canceled at overwrite dialog"
#				clean_exit()
				errorbool = True
				return None, None, errorbool
			else:
				fm.getDataBool = False
				
		if self.gridExist and (gridExist is False):
			found_grid_file = GenericDialogPlus("Previous Grid Data File Found")
			found_grid_file.addMessage("Previous grid file found.")
			found_grid_file.addMessage("Would you like to overwrite previous grid file or load the previous grid file without overwriting?")
			found_grid_file.addMessage("Select Cancel to exit the script")
			found_grid_file.enableYesNoCancel("Overwrite","Don't Overwrite (Load prev. grid)")
			if impicon is not None: found_grid_file.setIconImage(impicon)
			found_grid_file.showDialog()	
			if found_grid_file.wasOKed():	
				self.uNewGrid = True
				self.newGrid = True
				grid_data_load = None
				return grid_data_load, grid_loaded, False
			elif found_data_file.wasCanceled():
				print "user canceled at overwrite dialog"
				errorbool = True
				return None,grid_loaded,errorbool
			else:
				self.uNewGrid = False
				self.newGrid = False
				self.load_grid = True
				gridExist = True
				fm.gridExist = True
		if gridExist:
			if not os.path.exists(self.gridpath):
				found_grid_file = GenericDialogPlus("Grid Data File Not Found")
				found_grid_file.addMessage("You selected the option to indicate that\ngrid data already exists")
				found_grid_file.addMessage("Press Continue to generate new grid data")
				found_grid_file.addMessage("Press Cancel to end the script")
				found_grid_file.setOKLabel("Continue")
				if impicon is not None: found_grid_file.setIconImage(impicon)
				found_grid_file.showDialog()
				if found_grid_file.wasOKed():
					self.uNewGrid = True
					self.newGrid = True
					self.load_grid = False
					grid_data_load = None
					fm.gridExist = False
					return grid_data_load, grid_loaded, False
				if found_grid_file.wasCanceled():
					errorbool = True
					return None,grid_loaded,errorbool
		if self.load_grid:
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
					errorgd.addMessage("Please delete the grid data file and restart the program, selecting the option for no previous grid data.")
					errorgd.addMessage("All data for this run may need to be recollected since new grid creation will lead to changing data values")
					errorgd.addMessage("This error indicates that the grid data has been altered or corrupted. This can be caused by\nediting and saving the grid file in another program (such as excel) and not saving with the proper settings.\nEditing grid data is not recommended but if it must be done, make sure to use something like Notepad or Wordpad.")
					if impicon is not None: errorgd.setIconImage(impicon)
					errorgd.hideCancelButton()
					errorgd.showDialog()
					errorbool = True
					return None,None,errorbool
					return
				if ((grid_data_load[i][1][0] != gridCols) or (grid_data_load[i][1][1] != gridRows)) and not "lower" in grid_data_load[i][0]:
					errorgd = GenericDialogPlus("Error")
					errorgd.addMessage("Previous grid data column and row counts don't match current settings")
					errorgd.addMessage("Current grid settings: Columns: {}  Rows: {}".format(gridCols,gridRows))
					errorgd.addMessage("Saved grid file settings: Columns: {}  Rows: {}".format(grid_data_load[i][1][0],grid_data_load[i][1][1]))
					errorgd.addMessage("Press OK to continue (generates new grid; should also collect new histogram data to match new grid).\nPress Cancel to exit script. Can then restart to enter matching Column/Row numbers.")
					if impicon is not None: errorgd.setIconImage(impicon)
					errorgd.showDialog()
					if errorgd.wasOKed():
						print"Generating new grid data..."
					if errorgd.wasCanceled():
						errorbool = True
						return None,None,errorbool
				else: 
					grid_loaded = True
		else: 
			self.newGrid = True
			grid_data_load = None
		return grid_data_load, grid_loaded, errorbool
	
	def getData(self,fimp):
#		for title in WindowManager.getImageTitles():
#			imptemp = WindowManager.getImage(title)
#			imptemp.changes = False
#			imptemp.close()
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
		fm = self.menuObj
		fimplist = fm.fimplist
		impicon = fm.impicon
		gridExist = fm.gridExist
		processed_folder = fm.savefolderpath
		final_data = self.histData
		grid_info = self.gridData
		errorbool = False
		dataname = "data.csv"
		datapath = os.path.join(processed_folder,dataname)
		g_dataname = "grid.csv"
		g_datapath = os.path.join(processed_folder,g_dataname)
		dataSave = True
		dt = time.localtime()
		timestamp = "[{}/{}/{} {}:{}:{}]".format(dt[1],dt[2],dt[0],dt[3],dt[4],dt[5])
		if gridExist:
			g_dataSave = True
		else:
			g_dataSave = False
		if (os.path.exists(datapath)) and (os.path.exists(g_datapath)) and not gridExist:
			found_data_file = GenericDialogPlus("Data File Already Exists")
			found_data_file.addMessage("Data file already exists")
			found_data_file.addMessage("Would you like to overwrite the data and grid files for this entire folder?")
			found_data_file.addMessage("Select Continue to continue without saving data.")
			found_data_file.addMessage("Exiting the script will close all windows.")
			found_data_file.enableYesNoCancel("Overwrite","Continue (Don't Save)")
			found_data_file.setCancelLabel("Exit Script")
			if impicon is not None: found_data_file.setIconImage(impicon)
			found_data_file.showDialog()
			if found_data_file.wasOKed():
				print "Overwriting Data File."
				dataSave = True
				g_dataSave = True
			elif found_data_file.wasCanceled():
				errorbool = True
				return errorbool
			else:
				dataSave = False
				g_dataSave = False
		elif (os.path.exists(datapath)) or (os.path.exists(g_datapath) and not gridExist):
			found_data_file = GenericDialogPlus("Data File Already Exists")
			if (os.path.exists(datapath)):
				found_data_file.addMessage("Data file already exists")
				found_data_file.addMessage("Would you like to overwrite the histogram data file for this entire folder?")
				found_data_file.addMessage("Select No to continue without saving histogram data.")
			elif (os.path.exists(g_datapath)):
				found_data_file.addMessage("Grid file already exists")
				found_data_file.addMessage("Would you like to overwrite the grid data file for this entire folder?")
				found_data_file.addMessage("Select Continue to continue without saving grid data.")
			found_data_file.addMessage("Exiting the script will close all windows.")
			found_data_file.enableYesNoCancel("Overwrite","Continue (Don't Save)")
			found_data_file.setCancelLabel("Exit Script")
			if impicon is not None: found_data_file.setIconImage(impicon)
			found_data_file.showDialog()
			if found_data_file.wasOKed():
				print "Overwriting Data File."
				dataSave = True
				g_dataSave = True
			elif found_data_file.wasCanceled():
				errorbool = True
				return errorbool
			else:
				dataSave = False
				g_dataSave = False
		else:
			print "No data or grid file found for this folder. Saving data."
			dataSave = True
			g_dataSave = True
		debug_datacount = 0
		firstheader = "Image Title {}".format(timestamp)
		if dataSave:
			try:
				with open(datapath,'w') as csvfile:
					writer = csv.writer(csvfile)
					writer.writerow([firstheader, "Whole Image Total AOI Pixels", "Whole Image Black Pixels", "Whole Image White Pixels (TF signal)", "Gridbox Histogram Counts [box id, black, white, total]"])
					for fimp in fimplist:
						grid = fimp.grid
						row = [fimp.title,grid.total_data[2], grid.total_data[0], grid.total_data[1], grid.cell_data]
						writer.writerow(row)
						debug_datacount += 1
			except Exception as e:
				print"error storing cell histogram data"
				print"datapath: ",datapath
				print"The path exists: ",os.path.exists(datapath)
				print"Error storeData(): ",repr(e)
		debug_gridcount = 0
		if g_dataSave and not gridExist:
			try:
				with open(g_datapath,'w') as csvgridfile:
					gwriter = csv.writer(csvgridfile)
					gwriter.writerow([firstheader, "Grid Columns x Rows", "Grid ColWidth RowHeight", "Gridbox Coordinates"])
					for fimp in fimplist:
						grid = fimp.grid
						row = [fimp.title,[grid.cols,grid.rows],grid.res,grid.cell_coordinates]	
						gwriter.writerow(row)
						debug_gridcount += 1
			except Exception as e:
				print"error storing grid data"
				print"g_datapath: ",g_datapath
				print"Error storeData(): ",repr(e)
		print "data stored: ",timestamp
		IJ.log("data stored: ".format(timestamp))
		return errorbool
