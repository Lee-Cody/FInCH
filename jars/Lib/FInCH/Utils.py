from ij import IJ, ImageListener, WindowManager, ImagePlus, ImageStack
import ij.util
from ij.io import FileSaver
from ij.plugin.frame import RoiManager
from ij.process import ImageProcessor, ImageConverter
from ij.measure import Measurements
from ij.gui import GenericDialog, TextRoi, Overlay, Roi,Line, WaitForUserDialog, Toolbar, PolygonRoi
from ij.gui.Line import PointIterator
from fiji.util.gui import GenericDialogPlus
import os, math, csv, copy, time
import decimal as dec
from decimal import Decimal as dz
from FInCH import GridGen
########################################
#decimal fxs for decimal precision:
#dz = dec.Decimal 
dec.getcontext().prec=15
dec.getcontext().rounding="ROUND_HALF_UP"
decc = dec.getcontext()
decf = dec.Context(prec=15,rounding="ROUND_DOWN")
pup = dec.Context(prec=15,rounding="ROUND_HALF_UP")
def d(num):
	if isinstance(num,float):
		numf = decf.create_decimal_from_float(num)
		numd = numf * dz(1)
	else:
		numd = dz(num) * dz(1)
	return numd
def dd(num):
	numd = d(num).quantize(dz("1"), rounding="ROUND_HALF_UP")
	return numd
def di(num):
	numd = dd(num)
	numi = int(numd)
	return numi
def dexp(num,exp):
	numd = d(num)
	nume = d(exp)
	res = numd**nume
	return res
def dsqrt(num):
	res = d(num).sqrt()
	return res
def dceil(num):
	numd = d(num).quantize(d("1"), rounding="ROUND_UP")
	return numd
#################################################
def add_RoiM():
	rm = RoiManager.getInstance()
	if not rm:
		RM = RoiManager()
		rm = RM.getRoiManager()
	return rm

def getCenterPt(imp, pt1, pt2):
	x1 = d(pt1[0])
	y1 = d(pt1[1])
	x2 = d(pt2[0])
	y2 = d(pt2[1])
	cx = di((x1+x2)/2)
	cy = di((y1+y2)/2)
	center = [cx,cy]
	return center

def get_user_line(image, rm):
	errorbool = False
	image.show()
	IJ.setTool(Toolbar.LINE)
	lineWait = WaitForUserDialog("Waiting for user input","Draw a line on the image.")
	lineWait.show()
	roiUserLine = image.getRoi()
	if roiUserLine is None:
		errorbool = True
		return None,None,errorbool
	angle = roiUserLine.getAngle()
	pointsX = roiUserLine.getPolygon().xpoints
	pointsY = roiUserLine.getPolygon().ypoints
	line = [[pointsX[0],pointsY[0]],[pointsX[1],pointsY[1]]]
	rm.reset()
	image.setRoi(None)
	return line, angle, errorbool

def find_intersection(line1, line2):
	# Extract coordinates from input arrays
	x1 = d(line1[0][0])
	y1 = d(line1[0][1])
	x2 = d(line1[1][0])
	y2 = d(line1[1][1])
	x3 = d(line2[0][0])
	y3 = d(line2[0][1])
	x4 = d(line2[1][0])
	y4 = d(line2[1][1])
	if (x2 - x1) == 0:
	#line 1 is vert
		slope1 = 1e6
	else:
		slope1 = (y2 - y1) / (x2 - x1)
	if (x4-x3) == 0:
	#line2 is vert
		slope2 = 1e6
	else:
		slope2 = (y4 - y3) / (x4 - x3)
	# Handle vertical line
	y_intercept1 = (y1 - slope1 * x1) if slope1 != 1e6 else None  # Handle vertical line
	y_intercept2 = (y3 - slope2 * x3) if slope2 != 1e6 else None  # Handle vertical line
	# Check if lines are parallel
	if slope1 == slope2:
		return None  # Lines are parallel, no intersection
	if slope1 == 1e6:
		x_intersect_temp = x1
		y_intersect_temp = (slope2 * x_intersect + y_intercept2)
	elif slope2 == 1e6:
		x_intersect_temp = x3
		y_intersect_temp = (slope1 * x_intersect + y_intercept1)
	else:
		x_intersect_temp = ((y_intercept2 - y_intercept1) / (slope1 - slope2))
		y_intersect_temp = (slope1 * x_intersect + y_intercept1)
	x_intersect = di(x_intersect_temp)
	y_intersect = di(y_intersect_temp)
	return [x_intersect, y_intersect]

def find_intersection_points(line1, line2, line3, line4):
	p1 = line4[0]
	p2 = line4[1]
	p3 = line1[0]
	p4 = line1[1]
	p5 = line2[0]
	p6 = line2[1]
	p7 = line3[0]
	p8 = line3[1]
	corner1 = find_intersection(line4, line1)
	corner2 = find_intersection(line1, line2)
	corner3 = find_intersection(line2, line3)
	corner4 = find_intersection(line3, line4)
	box_corners = [corner1, corner2, corner3, corner4]
	return box_corners

def restoreGrid(imp,processed_folder,cols,rows,upper,coordinates = None,resolution=[0,0]):
	rm = add_RoiM()
	fimptemp = GridGen.fImp(imp)
	impgrid = GridGen.fGrid(imp,cols,rows,upper=upper,grid_res=resolution,name="grid_"+fimptemp.name)
	try:
		impgrid.restoreFromCSV(coordinates)
	except Exception as e:
		print"Unable to restore grid for: ",fimptemp.title
		print"May need to re-create the grid file"
		print"Error Utils.restoreGrid(): ",repr(e)
	return impgrid

def getNameFromTitle(title):
	if ("upper" in title):
		nametemp = title.split("_upper")
		name = nametemp[0] + "_upper"
	elif ("lower" in title):
		nametemp = title.split("_lower")
		name = nametemp[0] + "_lower"
	else:
		name_split = title.split("_AOI")[0]
		name = name_split[:-3]
	return name

def getFImpByTitle(title):
	fimps = fImp.instances
	fimp = None
	if len(fimps) == 0:
		print"Utils.getFImpByTitle(): No FInCH image instances (fImps) were found!"
	else:
		for fimptemp in fimps:
			if (title in fimptemp.title) or (fimptemp.title in title):
				fimp = fimptemp
	return fimp

def rotateRoi(imp, roi, angle):
	rm = add_RoiM()
	rm.reset()
	rm.addRoi(roi)
	rm.rotate(angle)
	rotatedroi = rm.getRoi(0)
	rm.reset()
	x = rotatedroi.getPolygon().xpoints
	y = rotatedroi.getPolygon().ypoints
	points = []
	if len(x) == 4:
		shape = "POLYGON"
		rotatedshape = [[x[0],y[0]], [x[1],y[1]], [x[2],y[2]], [x[3],y[3]]]
		points = [[x[0],y[0]], [x[1],y[1]], [x[2],y[2]], [x[3],y[3]]]
	elif len(x) == 2:
		shape = "LINE"
		rotatedshape = Line(x[0], y[0], x[1], y[1])
		points = [[x[0], y[0]], [x[1], y[1]]]
	return rotatedshape, points, rotatedroi, shape
		
def segments(x1,y1,x2,y2,seglength,segcount):
	#seglength is either col_width or row_height
	#segcount is either grid_col_check or grid_row_check
	points = []
	startpoint = [di(x1),di(y1)]
	endpoint = [di(x2),di(y2)]
	points.append(startpoint)
	dx = x2 - x1
	dy = y2 - y1
	xs = di(x1)
	ys = di(y1)
	length = dsqrt(dexp(dx,2) + dexp(dy,2))
	if dx == 0:  # Vertical line
		if dy > 0:
			theta = math.pi / 2
		else:
			theta = -math.pi / 2
	else:
		theta = math.atan2(di(dy),di(dx))
	for i in range(segcount - 1):
			xn = di(d(x1) + (d(seglength) * (d(i) + d(1))) * d(math.cos(theta)))
			yn = di(d(y1) + (d(seglength) * (d(i) + d(1))) * d(math.sin(theta)))
			pt = [xn,yn]
			points.append(pt)
	points.append(endpoint)
	return points

def fError(m=None,pm=None,t=None,close=False):
	if pm is not None:
		for message in pm:
			print(message)
	if t is not None:
		alertgd =  GenericDialogPlus(errorTitle)
	else:
		alertgd =  GenericDialogPlus("Error")
	alertgd.addMessage("FInCH encountered a bug but isn't hungry.")
	if m is not None:
		for message in m:
			alertgd.addMessage(message)
	else:
		alertgd.addMessage("FInCH encountered an error and had to close")
		alertgd.addMessage("Please restart Fiji and try again")
	alertgd.hideCancelButton()
	alertgd.showDialog()
	if close:
		cleanExit()
	return
	
def openFInCHImps(fimplist):
	errorbool = False
	for fimp in fimplist:
		if fimp.isOpen() is False:
			imp, errorbool = fimp.getfImp()
		if errorbool:
			print"Error: unable to open one of multiple files! file: ",fimp.title
	return errorbool
	
def closeImages():
	for title in WindowManager.getImageTitles():
		imptemp = WindowManager.getImage(title)
		imptemp.changes = False
		imptemp.close()
	return

def cleanExit(all=False):
	for wintitle in WindowManager.getImageTitles():
		winimp = WindowManager.getImage(wintitle)
		winimp.close()
	if all:
		WindowManager.closeAllWindows()
	return
	
def analyzeCells(fimp,imagefolder,savefolder):
	saved_cells=[]
	imp = fimp.imp
	title = fimp.title
	rm = add_RoiM()
	height = imp.getHeight()
	width = imp.getWidth()
	gridname = fimp.grid.name
	gridfile = gridname + '.zip'
	grid_folder_path=os.path.join(savefolder, "Grids")
	if not os.path.exists(grid_folder_path):
		os.mkdir(grid_folder_path)
	cell_data_folder = os.path.join(imagefolder, "cell_data")
	if not os.path.exists(cell_data_folder):
		os.mkdir(cell_data_folder)
	image_subfolder = os.path.join(cell_data_folder, fimp.name)
	if not os.path.exists(image_subfolder):
		os.mkdir(image_subfolder)
	roi_path = os.path.join(grid_folder_path,gridfile)
	save_directory = image_subfolder
	
	IJ.selectWindow(title)
	ic = ImageConverter(imp)
	ic.convertToGray8()
	IJ.run(imp, "Subtract Background...", "rolling=10 light separate")
	IJ.setAutoThreshold(imp, "Default")
	IJ.run(imp, "Convert to Mask", "")
	IJ.run(imp, "Watershed", "")
	time.sleep(0.001)
	imp.setRoi(None)
	for cell in fimp.grid.cells:
		if cell.offimage:
#			print"cell is offimage: ",cell.name
			continue
#		print"cell name: ",cell.name
		roi = cell.roi
		imp.setRoi(roi)
		roi_name = cell.name
		distance = 0
		known = 0
		unit = "pixel"
		IJ.run("Set Scale...", "distance={} known={} unit={}".format(distance, known, unit))
		time.sleep(0.001)
		IJ.run("Set Measurements...", "area centroid perimeter bounding fit shape feret's integrated limit redirect=None decimal=3")
		time.sleep(0.001)
		IJ.selectWindow(title)
#		time.sleep(0.001)
		IJ.run(imp, "Analyze Particles...", "display")
		time.sleep(0.001)
		save_path = os.path.join(save_directory, "{}.csv".format(roi_name))
		IJ.saveAs("Results", save_path)
		time.sleep(0.001)
		if os.path.exists(save_path):
			saved_cells.append(cell)
		else:
			if WindowManager.getWindow("Results") is None:
				IJ.run(imp, "Analyze Particles...", "display")
				time.sleep(0.002)
				IJ.saveAs("Results", save_path)
		IJ.run("Clear Results")	
	if len(saved_cells) != len(fimp.grid.cells):
		for cell in fimp.grid.cells:
			if (cell in saved_cells) or cell.offimage:
				continue
			roi = cell.roi
			imp.setRoi(roi)
			roi_name = cell.name
			distance = 0
			known = 0
			unit = "pixel"
			IJ.run("Set Scale...", "distance={} known={} unit={}".format(distance, known, unit))
			time.sleep(0.001)
			IJ.run("Set Measurements...", "area centroid perimeter bounding fit shape feret's integrated limit redirect=None decimal=3")
			time.sleep(0.002)
			IJ.selectWindow(title)
			IJ.run(imp, "Analyze Particles...", "display")
			time.sleep(0.005)
			save_path = os.path.join(save_directory, "{}.csv".format(roi_name))
			IJ.saveAs("Results", save_path)
			time.sleep(0.001)
			if not os.path.exists(save_path):
				print"NO SAVE PATH FOR ROI: ",roi_name
				IJ.saveAs("Results", save_path)
				time.sleep(0.002)
				if not os.path.exists(save_path):
					print"NO SAVE PATH FOR ROI: ",roi_name
					IJ.saveAs("Results", save_path)
					time.sleep(0.02)
			if os.path.exists(save_path):
				saved_cells.append(cell)
			IJ.run("Clear Results")	
	save_path_image = os.path.join(save_directory, title)
	fs = FileSaver(imp)
	fs.saveAsTiff(save_path_image)
	imp.changes = False
	imp.close()
	rm.reset()
	return
