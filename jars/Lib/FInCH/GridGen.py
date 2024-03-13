#https://github.com/Lee-Cody/FInCH
#Copyright 2024 Cody Lee
#Licensed under GPL-3.0
#See FInCH_.py for colour deconvolution attribution
import os,sys,time,math
import decimal as dec
from decimal import Decimal as dz
from ij import IJ,ImagePlus,WindowManager,ImageStack
from ij.process import ImageProcessor,ImageConverter
from ij.gui import (Toolbar,GenericDialog,TextRoi,Overlay,Roi,Line,PolygonRoi)
from ij.plugin.frame import RoiManager
from fiji.util.gui import GenericDialogPlus
from java.awt import Color
from FInCH.Utils import *
###########################
#FInCH CLASSES - fLine, fPoly, fGrid, fImp

class fLine:
	def __init__(self, imp, points, name="line"):
		self.imp = imp
		self.name = name
		self.p1 = [di(points[0][0]),di(points[0][1])]
		self.p2 = [di(points[1][0]),di(points[1][1])]
		self.x1 = self.p1[0]
		self.y1 = self.p1[1]
		self.x2 = self.p2[0]
		self.y2 = self.p2[1]
		self.points = [[self.x1,self.y1],[self.x2,self.y2]]
		self.dy = self.y2 - self.y1
		self.dx = self.x2 - self.x1
		self.length = dsqrt(dexp(self.dx,2) + dexp(self.dy,2))
		self.center = [((self.x1 + self.x2) / 2), ((self.y1 + self.y2) / 2)]
		self.roi = Line(self.x1, self.y1, self.x2, self.y2)
		self.roi.setName(self.name)
		self.angle = self.roi.getAngle(self.x1, self.y1, self.x2, self.y2)
		self.vertical = False
		self.horizontal = False
		self.yint = None

		if ((self.y2 - self.y1) == d(0)):
			self.horizontal = True
			self.slope = d(0)
			self.pslope = float('inf')
		elif ((self.x2 - self.x1) == d(0)):
			self.vertical = True
			self.slope = float('inf')
			self.pslope = d(0)
		else:
			self.slope = d(self.y2 - self.y1) / d(self.x2 - self.x1)
			self.pslope = d(-1) / self.slope
		if (self.vertical == False):
			self.yint = self.y1 - (self.slope * self.x1)

	def scale(self, scale, center=True):
		imp = self.imp
		rm = add_RoiM()
		rm.reset()
		rm.addRoi(self.roi)
		rm.scale(float(scale),float(scale),center)
		scaledlineroi = rm.getRoi(0)
		rm.reset()
		xpts = scaledlineroi.getPolygon().xpoints
		ypts = scaledlineroi.getPolygon().ypoints
		scaledline = fLine(imp, [[xpts[0], ypts[0]], [xpts[1], ypts[1]]], self.name+"_scaled")
		return scaledline

	def getIntersection(self, fLine2):
		#relies on the line passed here to be a fLine class object
		parallel = False
		if (self.slope == fLine2.slope):
			parallel = True
			print"Can't get intersection of two parallel lines!"
			print"Passed lines:"
			print"line1: ", self.__dict__
			print"line2: ",fLine2.__dict__
			return
		op1 = fLine2.p1
		op2 = fLine2.p2
		xi = None
		yi = None
		if (self.vertical):
			xi = self.x1
			yi = di((fLine2.slope * xi) + fLine2.yint)
		elif (fLine2.vertical):
			xi = op1[0]
			yi = di((self.slope * xi) + self.yint)
		else:
			xi = di((fLine2.yint - self.yint) / (self.slope - myLint2.slope))
			yi = di((self.slope * xi) + self.yint)
		return [xi,yi]

class fPoly:
	def __init__(self, imp, points, name="poly"):
		#points: top left, top right, bottom right, bottom left
		self.imp = imp
		self.name = name
		self.p1 = [di(points[0][0]),di(points[0][1])]
		self.p2 = [di(points[1][0]),di(points[1][1])]
		self.p3 = [di(points[2][0]),di(points[2][1])]
		self.p4 = [di(points[3][0]),di(points[3][1])]
		self.points = [self.p1, self.p2, self.p3, self.p4]
		self.xs = [self.p1[0], self.p2[0], self.p3[0], self.p4[0]]
		self.ys = [self.p1[1], self.p2[1], self.p3[1], self.p4[1]]
		self.side1 = fLine(imp, [self.p1, self.p2])
		self.side2 = fLine(imp, [self.p2, self.p3])
		self.side3 = fLine(imp, [self.p3, self.p4])
		self.side4 = fLine(imp, [self.p4, self.p1])
		self.roi = PolygonRoi(self.xs, self.ys, 4, Roi.POLYGON)
		self.roi.setName(self.name)
		self.slopew = self.side1.slope
		self.slopeh = self.side2.slope
		self.offimage = self._checkCoords()
		self.got_data = False
		self.data = None
		self.data_aoi = None
		
	def _checkCoords(self):
		h = self.imp.getHeight()
		w = self.imp.getWidth()
		offimage_point = 0
		offimage = False
		for point in self.points:
			x = point[0]
			y = point[1]
			if (x < 0) or (x > w) or (y < 0) or (y > h):
				offimage_point += 1
		if offimage_point == 4:
			offimage = True
		return offimage

class fGrid:
	def __init__(self,imp,cols,rows,upper=True,bounding_box=None,grid_res=[0,0],name="grid"):
		dt = time.localtime()
		self.time = "[{}/{}/{} {}:{}:{}]".format(dt[1],dt[2],dt[0],dt[3],dt[4],dt[5])
		self.imp = imp
		self.name = name
		self.cols = cols
		self.rows = rows
		self.upper = upper
		self.res = grid_res
		self.bounding_box = bounding_box
		self.corner1 = None
		self.corner2 = None
		self.corner3 = None
		self.corner4 = None
		self.width = None
		self.height = None
		self.slopec = None
		self.sloper = None
		self.column_points = None
		self.row_points = None
		self.overlay = None
		self.cells = None
		self.cell_data = None
		self.total_data = None
		self.cell_rois = None
		self.cell_coordinates = None
		self.comparison_points = None
	
	def restoreFromCSV(self,cell_coord_list):
		imp = self.imp
		upper = self.upper
		poly_list = []
		poly_roi_list = []
		rm = add_RoiM()
		rm.reset()
		imp.setOverlay(None)
		overlay_temp = Overlay()
		self.cell_coordinates = cell_coord_list
		
		boxpt1 = cell_coord_list[0][0]
		#if 100 selboxes, then (p_cols * p_rows) - (p_rows) = index 90 or selbox number 91 (Top "right")
		boxpt2 = cell_coord_list[(self.cols * self.rows) - (self.rows)][1]
		boxpt3 = cell_coord_list[(self.cols * self.rows) - 1][2]
		boxpt4 = cell_coord_list[self.rows - 1][3]
		box_corners_temp = [boxpt1, boxpt2, boxpt3, boxpt4]
		AOI_box = fPoly(imp,box_corners_temp)
		
		self.bounding_box = AOI_box
		self.corner1 = AOI_box.p1
		self.corner2 = AOI_box.p2
		self.corner3 = AOI_box.p3
		self.corner4 = AOI_box.p4
		self.width = AOI_box.side1.length
		self.height = AOI_box.side2.length
		self.slopec = AOI_box.slopeh
		self.sloper = AOI_box.slopew	
		self.comparison_points = [[boxpt1],[cell_coord_list[0][1]],[cell_coord_list[0][3]]]	
		
		intct = 1
		alphact = 0
		alpha = list(map(chr,range(ord('A'),ord('Z')+1)))
		for i in range(len(cell_coord_list)):
			if alphact > (self.rows - 1):
				alphact = 0
				intct += 1
				#new column
			intname = str(intct)
			alphaname = alpha[alphact]
			tempname = alphaname+intname
			selbox = cell_coord_list[i]
			
			cell_poly = fPoly(imp,selbox,tempname)
			setattr(self,tempname,cell_poly)
			
			poly_list.append(cell_poly)
			
			poly_roi_list.append(cell_poly.roi)
			
			overlay_temp.add(cell_poly.roi)
			
			if (i == 0) or (i % self.rows == 0):
				selbox_top = selbox
				selbox_bot = cell_coord_list[i + (self.rows - 1)]
				top_midpt = getCenterPt(imp, selbox_top[0], selbox_top[1])
				bot_midpt = getCenterPt(imp, selbox_bot[3], selbox_bot[2])
				troi = TextRoi(top_midpt[0], top_midpt[1], intname)
				troi.setColor(Color(255,255,0))
				if upper:
					troi.setFontSize(96)
				else:
					troi.setFontSize(48)
				troi2 = TextRoi(bot_midpt[0], bot_midpt[1], intname)
				troi2.setColor(Color(255,255,0))
				if upper:
					troi2.setFontSize(96)
				else:
					troi2.setFontSize(48)
				overlay_temp.add(troi)
				overlay_temp.add(troi2)
			if (i < self.rows):
				selbox_left = selbox
				rightindex = ((len(cell_coord_list) - self.rows) + i)
				selbox_right = cell_coord_list[rightindex]
				left_midpt = getCenterPt(imp, selbox_left[0], selbox_left[3])
				right_midpt = getCenterPt(imp, selbox_right[1], selbox_right[2])
				troi = TextRoi(left_midpt[0], left_midpt[1], alphaname)
				troi.setColor(Color(255,255,0))
				if upper:
					troi.setFontSize(96)
				else:
					troi.setFontSize(48)
				troi2 = TextRoi(right_midpt[0], right_midpt[1], alphaname)
				troi2.setColor(Color(255,255,0))
				if upper:
					troi2.setFontSize(96)
				else:
					troi2.setFontSize(48)
				overlay_temp.add(troi)
				overlay_temp.add(troi2)
			alphact += 1
		self.overlay = overlay_temp
		self.cells = poly_list
		self.cell_rois = poly_roi_list
		return
	
	def saveRois(self,path):
		rm = add_RoiM()
		rm.reset()
		cells_on_screen = self.getOnscreenCells()
		for cell in cells_on_screen:
			roi = cell.roi
			rm.addRoi(roi)
		if rm.getCount() == 0:
			print"Error trying to save grid Roi's: No Roi's in Roi Manager"
			return
		if rm.selected() > 0:
			rm.select(None)	
		rm.save(path)
		rm.reset()
		return
		
	def getOnscreenCells(self):
		onscreen_cells = []
		for cell in self.cells:
			if cell.offimage:
				continue
			else:
				onscreen_cells.append(cell)
		return onscreen_cells
	
	def generate(self):
		imp = self.imp
		cs = self.cols
		rs = self.rows
		cellct = cs * rs
		poly = self.bounding_box
		clength = 0
		rlength = 0
		csegmentlength = 0
		rsegmentlength = 0
		grid_col_check = 0
		grid_row_check = 0
		self.corner1 = poly.p1
		self.corner2 = poly.p2
		self.corner3 = poly.p3
		self.corner4 = poly.p4
		for i in range(2):
			if i == 0:
				#side1
				x1 = self.corner1[0]
				y1 = self.corner1[1]
				x2 = self.corner2[0]
				y2 = self.corner2[1]
				clength = poly.side1.length
			elif i == 1:
				#side4 reversed
				x1 = self.corner1[0]
				y1 = self.corner1[1]
				x2 = self.corner4[0]
				y2 = self.corner4[1]
				rlength = poly.side4.length
		if self.upper:
			#upper columns
			grid_col_check = d(cs)
			csegmentlength = dceil(clength/grid_col_check)
			#upper rows
			grid_row_check = d(rs)
			rsegmentlength = dceil(rlength/grid_row_check)
		else:
			#lower columns
			col_width_p = d(self.res[0])
			grid_col_check = di(dceil(clength/col_width_p))
			csegmentlength = int(dceil(clength/grid_col_check))
			self.cols = grid_col_check
			#lower rows
			row_height_p = d(self.res[1])
			grid_row_check = di(dceil(rlength/row_height_p))
			rsegmentlength = int(dceil(rlength/grid_row_check))
			self.rows = grid_row_check
		csegmentcount = grid_col_check
		rsegmentcount = grid_row_check
		#top-side1, bot-side3, 
		toppoints = segments(self.corner1[0],self.corner1[1],self.corner2[0],self.corner2[1],csegmentlength,csegmentcount)
		bottompoints = segments(self.corner4[0],self.corner4[1],self.corner3[0],self.corner3[1],csegmentlength,csegmentcount)
		points = []
		column_points = []
		row_points = []
		row_points_temp = []
		for i in range(len(toppoints)):
			xt1 = toppoints[i][0]
			yt1 = toppoints[i][1]
			xt2 = bottompoints[i][0]
			yt2 = bottompoints[i][1]
			column_points.append([xt1,yt1,xt2,yt2])
			points_temp = segments(xt1,yt1,xt2,yt2,rsegmentlength,rsegmentcount)
			if i == 0:
				row_points_temp.append(points_temp)
			if i == (len(toppoints) - 1):
				row_points_temp.append(points_temp)
			points.append(points_temp)
		#generate row points array for overlay:
		for i in range(len(row_points_temp[0])):
			xt1 = row_points_temp[0][i][0]
			yt1 = row_points_temp[0][i][1]
			xt2 = row_points_temp[1][i][0]
			yt2 = row_points_temp[1][i][1]
			row_points.append([xt1,yt1,xt2,yt2])
		self.column_points = column_points
		self.row_points = row_points
		cellcoords = []	
		cells = []
		alpha = list(map(chr,range(ord('A'),ord('Z')+1)))
		coord_index = 0
		for i in range(len(points) - 1):
			for j in range(len(points[i]) - 1):
				cellcoords.append([])
				p1 = points[i][j]
				p2 = points[i+1][j]
				p3 = points[i+1][j+1]
				p4 = points[i][j+1]
				cellnamealpha = alpha[j]
				cellname = cellnamealpha + str(i + 1)
				cctemp = [p1,p2,p3,p4]
				cellcoords[coord_index] = cctemp
				celltemp = fPoly(imp,cctemp,cellname)
				setattr(self,cellname,celltemp)
				cells.append(celltemp)
				coord_index += 1
		self.cell_coordinates = cellcoords
		self.cells = cells
		self.overlay = self.generateOverlay()
		if self.upper:
			resolution_cell = cells[0]
			column_width = float(resolution_cell.side1.length)
			row_height = float(resolution_cell.side2.length)
			self.res = [column_width, row_height]
		return
		
	def generateOverlay(self):
		imp = self.imp
		overlay = Overlay()
		grid_rois = [[],[]]
		grid_labels = [[],[]]
		column_lines = self.column_points
		row_lines = self.row_points
		alpha = list(map(chr,range(ord('A'),ord('Z')+1)))
		for i in range(len(column_lines) - 1):
			line1 = column_lines[i]
			line2 = column_lines[i+1]
			pt1 = [line1[0],line1[1]]
			pt2 = [line2[0],line2[1]]
			pt3 = [line2[2],line2[3]]
			pt4 = [line1[2],line1[3]]
			namestr = str(i + 1)
			poly = fPoly(self.imp,[pt1,pt2,pt3,pt4],namestr)
			roi = poly.roi
			templine1 = fLine(self.imp,[pt1,pt2])
			templine2 = fLine(self.imp,[pt4,pt3])
			labelpt1 = templine1.center
			labelpt2 = templine2.center
			troi = TextRoi(labelpt1[0], labelpt1[1], namestr)
			troi.setColor(Color(255,255,0))
			troi.setFontSize(96)
			troi2 = TextRoi(labelpt2[0], labelpt2[1], namestr)
			troi2.setColor(Color(255,255,0))
			troi2.setFontSize(96)
			overlay.add(roi)
			overlay.add(troi)
			overlay.add(troi2)
		for j in range(len(row_lines) - 1):
			line1 = row_lines[j]
			line2 = row_lines[j + 1]
			pt1 = [line1[0],line1[1]]
			pt2 = [line2[0],line2[1]]
			pt3 = [line2[2],line2[3]]
			pt4 = [line1[2],line1[3]]
			namestr = alpha[j]
			poly = fPoly(self.imp,[pt1,pt2,pt3,pt4],namestr)
			roi = poly.roi
			templine1 = fLine(self.imp,[pt1,pt2])
			templine2 = fLine(self.imp,[pt4,pt3])
			labelpt1 = templine1.center
			labelpt2 = templine2.center
			troi = TextRoi(labelpt1[0], labelpt1[1], namestr)
			troi.setColor(Color(255,255,0))
			troi.setFontSize(96)
			troi2 = TextRoi(labelpt2[0], labelpt2[1], alpha[j])
			troi2.setColor(Color(255,255,0))
			troi2.setFontSize(96)
			overlay.add(roi)
			overlay.add(troi)
			overlay.add(troi2)
		return overlay

class fImp:
	instances = []
	def __init__(self,imp,uline=None,grid=None,upperlower_ini=True):
		self.imp = imp
		self.window = ImagePlus.getWindow(self.imp)
		self.ip = imp.getProcessor()
		self.w = imp.getWidth()
		self.h = imp.getHeight()
		self.title = imp.getTitle()
		self.upperlower = upperlower_ini
		self.name = getNameFromTitle(self.title,upperlower_ini=upperlower_ini)
		self.userline = uline
		self.upper = self._getUpper()
		self.individual = self.name.split("_")[1]
		self.bg = self.getBackground()
		self.folder = imp.getOriginalFileInfo().directory
		self.path = os.path.join(self.folder, self.title)
		self.savepath = None
		self.thresh_savepath = None
		self.thresh_image = None
		self.CD_image = None
		self.stain = None
		self.thresholded = False
		self.grid = grid
		self.overlay = None
		self.gridverified = False
		self.loadgriddata = None
		self.pairedImage = None
		self.FInCH = True
		fImp.instances.append(self)
		
	def _getUpper(self):
		if self.upperlower is False:
			return True
		elif "lower" in self.title:
			return False
		return True
		
	def isOpen(self):
		if WindowManager.getImage(self.title) is None:
			return False
		return True
		
	def getfImp(self, path=None):
		errorbool = False
		imp_get = None
		if path is None:
			path = self.path
		openfimp = self.isOpen()
		if openfimp is False:
			#open
			if os.path.exists(path):
				try:
					imp_get = IJ.openImage(path)
					if (self.imp is None) or (self.imp != imp_get):
						self.imp = imp_get
					self.imp.show()
				except Exception as e:
					errorgd = GenericDialogPlus("Error")
					errorgd.addMessage("FInCH ran into a bug but wasn't hungry.")
					errorgd.addMessage("Please restart FInCH and try again.")
					if impicon is not None: errorgd.setIconImage(impicon)
					errorgd.hideCancelButton()
					errorgd.showDialog()
					print"unable to open image: {}; path: {}".format(self.title, path)
					print"Error: ",repr(e)
					errorbool = True
					return None, errorbool
			else:
				errorgd = GenericDialogPlus("Error")
				errorgd.addMessage("FInCH ran into a bug but wasn't hungry.")
				errorgd.addMessage("Please restart FInCH and try again.")
				if impicon is not None: errorgd.setIconImage(impicon)
				errorgd.hideCancelButton()
				errorgd.showDialog()
				print"path for image [{}] doesn't exist. Path: {}".format(self.title,path)
				errorbool = True
				return None, errorbool
		else:
			imp_get = WindowManager.getImage(self.title)
			if (self.imp is None) or (self.imp != imp_get):
				self.imp = imp_get
			imp_get.show()
		return imp_get, errorbool
	
	def createBoundingBox(self):
		imp = self.imp
		line = self.userline
		w = self.w
		h = self.h
		diag = fLine(imp, [[0, 0], [w, h]], "diagline")
		diaglen = diag.length
		ulinelen = line.length
		scale = diaglen / ulinelen
		scaledline = line.scale(scale)
		impcent = [int(dd(w)/2), int(dd(h)/2)]
		scalemovex = impcent[0] - scaledline.center[0]
		scalemovey = impcent[1] - scaledline.center[1]
		if (scaledline.x1 < scaledline.x2):
			scalex = scaledline.x1
		else:
			scalex = scaledline.x2
		if (scaledline.y1 < scaledline.y2):
			scaley = scaledline.y1
		else:
			scaley = scaledline.y2
		scaledline.roi.setLocation((scalex + scalemovex),(scaley + scalemovey))
		scaledline = fLine(imp, [[scaledline.roi.x1, scaledline.roi.y1],[scaledline.roi.x2,scaledline.roi.y2]],"scaledline")
		moveline1 = fLine(imp, scaledline.points)
		moveline2 = fLine(imp, scaledline.points)
		rotatedshape, rotatedpoints, temp, temp1 = rotateRoi(imp, scaledline.roi, 90)
		rotatedline = fLine(imp, rotatedpoints, "rotatedline")
		xr1 = rotatedline.x1
		yr1 = rotatedline.y1
		xr2 = rotatedline.x2
		yr2 = rotatedline.y2
		ulinecent = scaledline.center
		move1x = xr1 - ulinecent[0]
		move1y = yr1 - ulinecent[1]
		move2x = xr2 - ulinecent[0]
		move2y = yr2 - ulinecent[1]
		move1roi = moveline1.roi
		move2roi = moveline2.roi
		x1n1 = (scaledline.x1 + move1x)
		y1n1 = (scaledline.y1 + move1y)
		x2n1 = (scaledline.x2 + move1x)
		y2n1 = (scaledline.y2 + move1y)
		x1n2 = (scaledline.x1 + move2x)
		y1n2 = (scaledline.y1 + move2y)
		x2n2 = (scaledline.x2 + move2x)
		y2n2 = (scaledline.y2 + move2y)
	
		nmove1 = fLine(imp, [[x1n1,y1n1],[x2n1,y2n1]],"moved1")
		nmove2 = fLine(imp, [[x1n2,y1n2],[x2n2,y2n2]],"moved2")
		move1roi = nmove1.roi
		move2roi = nmove2.roi
		startcorners = [nmove1.p1, nmove1.p2,nmove2.p2,nmove2.p1]
		initialbox = fPoly(imp, startcorners, "initialbox")
		
		return initialbox
	
	def createAOIBox(self, boundingbox):
		#if upper = false, then processing a lower beak
		imp = self.imp
		bg = self.bg
		w = self.w
		h = self.h
		s1 = boundingbox.side1
		s2 = boundingbox.side2
		s3 = boundingbox.side3
		s4 = boundingbox.side4
		slopew = s1.slope
		slopeh = s2.slope
		for i in range(4):
			if i == 0:
				line1temp = Line(s4.x2,s4.y2,s4.x1,s4.y1)
				line2temp = Line(s2.x1,s2.y1,s2.x2,s2.y2)
				stop1 = s4.center
				targetslope = slopew
			pixiter1 = Line.PointIterator(line1temp)
			pixiter2 = Line.PointIterator(line2temp)
			foundAOI = False
			first = True
			while pixiter1.hasNext():
				p1 = pixiter1.next()
				p2 = pixiter2.next()
				xp1 = p1.x
				yp1 = p1.y
				if ((di(xp1) == stop1[0]) and (di(yp1) == stop1[1])):
					fError(m=["createAOIBox() made it to stop point at i={} without finding the AOI".format(i)],pm=["stop point reached: [{},{}]".format(xp1,yp1)],close=True)
					break
				xp2 = p2.x
				yp2 = p2.y
				if (first):
					x1prev = xp1
					y1prev = yp1
					x2prev = xp2
					y2prev = yp2
				first = False
				newline = Line(xp1,yp1,xp2,yp2)
				pixitert = Line.PointIterator(newline)
				while pixitert.hasNext():
					p = pixitert.next()
					xp = p.x
					yp = p.y
					if (xp < 0) or (xp > (w - 1)) or (yp < 0) or (yp > (h - 1)):
						continue
					pixel_value = imp.getPixel(xp, yp)
					if ((pixel_value[0] != bg) and (pixel_value[1] != bg) and (pixel_value[2] != bg)):
						foundAOI = True
						break
					else:
						continue
				if foundAOI:
					AOIline = fLine(imp,[[x1prev,y1prev],[x2prev,y2prev]])
					foundAOI = False
					break
				x1prev = xp1
				y1prev = yp1
				x2prev = xp2
				y2prev = yp2
			if i == 0:
				line1 = AOIline
				line1temp = Line(s2.x2,s2.y2,s2.x1,s2.y1)
				line2temp = Line(s4.x1,s4.y1,s4.x2,s4.y2)
				stop1 = s2.center
				targetslope = slopew
			elif i == 1:
				line3 = AOIline
				line1temp = Line(line1.x2,line1.y2,line1.x1,line1.y1)
				line2temp = Line(line3.x1, line3.y1,line3.x2,line3.y2)
				stop1 = line1.center
				targetslope = slopeh
			elif i == 2:
				line2 = AOIline
				line1temp = Line(line3.x2,line3.y2,line3.x1,line3.y1)
				line2temp = Line(line1.x1, line1.y1, line1.x2,line1.y2)
				stop1 = line3.center
				targetslope = slopeh
			elif i == 3:
				line4 = AOIline
		newside1 = fLine(imp, [line4.p2, line2.p1],"line1Top")
		newside2 = fLine(imp, [line2.p1, line2.p2],"line2Right")
		newside3 = fLine(imp, [line2.p2, line4.p1],"line3Bottom")
		newside4 = fLine(imp, [line4.p1, line4.p2],"line4Left")
		AOICorners = [line4.p2, line2.p1, line2.p2, line4.p1]
		aoibox = fPoly(imp, AOICorners, "AOIBox")
		return aoibox
	
	def createGrid(self,cols,rows,grid_res=[0,0]):
		errorbool = False
		cols = cols
		rows = rows
		gridname="grid_"+self.name
		try:
			poly = self.createBoundingBox()
		except Exception as e:
			errorbool = True
			print"Error creating bounding box for image: ",self.title
			print"Error: ",repr(e)
		try:
			aoipoly = self.createAOIBox(poly)
		except Exception as e:
			errorbool = True
			print"Error creating AOIBox for image: ",self.title
			print"Error: ",repr(e)
		try:
			newgrid = fGrid(self.imp,cols,rows,upper=self.upper,bounding_box=aoipoly,grid_res=grid_res,name=gridname)
		except Exception as e:
			errorbool = True
			print"Error creating fGrid for image: ",self.title
			print"Error: ",repr(e)
		try:
			newgrid.generate()
		except Exception as e:
			errorbool = True
			print"Error GENERATING grid for image: ",self.title
			print"Error: ",repr(e)
		self.grid = newgrid
		if self.grid is None:
			errorbool = True
			print"Error creating grid for image: ",self.title
		return errorbool
		
	def getBackground(self):
		#black or white background?
		imp = self.imp
		width = self.w
		height = self.h
	
		background = 0
		pt1 = [0,0]
		pt2 = [(width - 1), 0]
		pt3 = [(width - 1), (height - 1)]
		pt4 = [0, (height - 1)]
		evalpts = [pt1, pt2, pt3, pt4]
		for point in evalpts:
			pointpixel = imp.getPixel(int(point[0]), int(point[1]))
			if ((pointpixel[0] != 0) and (pointpixel[1] != 0) and (pointpixel[2] != 0)) and ((pointpixel[0] != 255) and (pointpixel[1] != 255) and (pointpixel[2] != 255)):
				continue
			if ((pointpixel[0] == 0) and (pointpixel[1] == 0) and (pointpixel[2] == 0)):
				break
			elif ((pointpixel[0] == 255) and (pointpixel[1] == 255) and (pointpixel[2] == 255)):
				background = 255
				break
		return background
		
	def toggleOverlay(self):
		if self.grid:
			overlay_temp = self.imp.getOverlay()
			if overlay_temp is None:
				self.imp.setOverlay(self.grid.overlay)
			else:
				self.imp.setOverlay(None)
		return
	
	def scale(self, scale,show=True):
		imp = self.imp
		imp2 = imp.duplicate()
		if scale != (1 or 1.0 or "1" or "1.0"):
			ip = imp2.getProcessor()
			w = ip.getWidth()
			h = ip.getHeight()
			ip = ip.resize((w*scale),(h*scale))
			imp2.setProcessor(ip)
		if show:
			imp2.show()
		return imp2
	
	def findStain(self,stain_options,impicon=None):
		errorbool = False
		stain = None
		colors = []
		ftitle = self.title.lower()
		filename_split = self.title.split("_")
#		for key, value in stain_options.items():
#			if key == "stains":
#				continue
#			elif filename_split[0][:3].lower() in '\t'.join(value):
#				stain = key
#			colors.append(key)
		for key, value in stain_options.items():
			if filename_split[0][:3].lower() in key:
				stain = value
			if value not in '\t'.join(colors):
				colors.append(value)
		if stain is None or (stain == ""):
			if (len(colors) == 0):
				alertgd =  GenericDialogPlus("Error")
				alertgd.addMessage("FInCH encountered a bug but isn't hungry.")
				alertgd.addMessage("Error: Function: getStain()")
				alertgd.addMessage("Unable to determine color deconvolution strings")
				alertgd.addMessage("If you have changed the default settings during inital setup (or altered the FInCH.ini file), please double check that the values are correctly entered or go through setup again from the main menu.")
				alertgd.showDialog()
				errorbool = True
				return errorbool
			print("couldn't figure out the stain for: ", self.title)
			gd = GenericDialogPlus("Stain Selection")
			gd.addMessage("FInCH encountered a bug but isn't hungry.")
			gd.addMessage("Couldn't detect the stain for file: "+self.title)
			gd.addMessage("Please select the correct stain for this file")
			if impicon is not None:
				gd.setIconImage(impicon)
			gd.addChoice("Select Stain", colors, colors[0])
			gd.showDialog()
			if gd.wasCanceled():
				print("User canceled stain selection dialog.")
				IJ.log("User canceled stain selection dialog. Please restart FInCH and try again.")
				errorbool = True
				return errorbool
			stainsel = gd.getNextChoice()
			if stainsel is None:
				stain = ""
				print("There was a problem with the user stain selection in findStain()")
				IJ.log("There was a problem with user stain selection. Please restart FInCH and try again.")
				errorbool = True
				return errorbool
			else:
				stain = stainsel
		self.stain = stain
		return errorbool

##Not yet implemented
#class fStack:
#	def __init__(self,implist):
#	#accepts a list/array of imps and FInCH imps
#	#can also pass None as implist param and specify a directory, instead; this will open all images in dir as an image plus stack
#		self.FInCH = True
#		self.w = None
#		self.h = None
#		self.stack, self.fimps, self.imps, self.error = self.createStack(implist)
#		
#		
#	def createStack(self,images):
#		errorbool = False
#		fimplist = []
#		implist = []
#		maxH = 0
#		maxW = 0
#		gotCM = False
#		
#		if len(images) < 1:
#			print "GridGen.fStack.createStack(): tried to create a stack from an empty list/array."
#			errorbool = True
#			return None, None, None, errorbool
#		for img in images:
#			try:
#				img_is_fimp = img.FInCH
#				#img is FInCH image (fImp)
#				fimp = img
#				imp = fimp.imp
#				if fimp.h > maxH:
#					maxH = fimp.h
#				if fimp.w > maxW:
#					maxW = fimp.w
#			except:
#				#img is likely not FInCH image
#				try:
#					imp = img
#					fimp = fImp(imp)
#					if fimp.h > maxH:
#						maxH = fimp.h
#					if fimp.w > maxW:
#						maxW = fimp.w
#				except Exception as e:
#					print"GridGen.fStack.createStack(): very likely that an object other than an imp or FInCH imp (fImp) was included in the list parameter."
#					print"Error: ",repr(e)
#					if img is None:
#						print"obj is an empty index in the array/list (images[i] = None)"
#					else:
#						print"obj: ",img.__dict__
#					errorbool = True
#					return None, None, None, errorbool
#			if gotCM is False:
#				colormodel = fimp.ip.getColorModel()
#				gotCM = True
#			fimplist.append(fimp)
#			implist.append(imp)
#		if colormodel is None:
#			errorbool = True
#			print"unable to get colormodel"
#			return None, None, None, errorbool
#		if maxH == 0:
#			errorbool = True
#			print"unable to get max H"
#			return None, None, None, errorbool
#		if maxW == 0:
#			errorbool = True
#			print"unable to get maxW"
#			return None, None, None, errorbool
#		stack = ImageStack(maxW,maxH,colormodel)
#		for fimp in fimplist:
#			stack.addSlice(fimp.title,fimp.ip)
#			if fimp.imp.getWindow() is not None:
#				fimp.imp.changes = False
#				fimp.imp.close()
#		stackP = ImagePlus('FInCH Stack',stack)
#		self.w = stackP.getWidth()
#		self.h = stackP.getHeight()
#		stackP.show()		
#		return stackP,fimplist,implist,errorbool
		
