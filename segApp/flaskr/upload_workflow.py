# Web dev libs
import os, shutil
import urllib.request
# from appp import app
from flask import Flask, flash, request, redirect, render_template, url_for, send_file
from werkzeug.utils import secure_filename

# Other libs
import uuid
import time
import numpy as np
import cv2
import pydicom

ALLOWED_EXTENSIONS = set(['dcm',''])



from flaskr.auth import login_required
from flaskr.db import get_db


from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
bp = Blueprint('upload_workflow', __name__)

# # Other code


from flaskr.view_workflow import *
from flaskr.class_def import *



def allowed_file(filename): # Check if file is of allowed type
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



def del_temp_dir(folder): # Deletes temp directory of uploaded files after they've been loaded into memory
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e:
            print(e)

    os.rmdir(folder)
    return

#################################
#### IMPORT WORKFLOW ############
#################################

def import_scan_wrapper(S):
    # Wrapper to take as input some files names and imports and preprocesses the scan and initialized segmentation  map

    # Takes as input a string directory and a list of all files in that directory

    # import directory
    S.imd, S.slices=mri_import(S.dir)
    S.imd=preprocess(S.imd)

    # initialize idx, and segmaps and view
    S.idx_ax1, S.idx_ax2, S.idx_ax3, S.pxd_view, S.pxd, S.imd_view = init(S.imd)

    return S


def mri_import(dir_path,  debug_mode=False):
    # Takes a list of files (list of strings) and finds, imports, and sorts DICOMS
    # inputs: dir_path is a string, dir_list is a list of strings of the file names
    # output: numpy array of [h,w,d], represents the medical imaging scan POTENTIALLY BUGGY
    dir_list=os.listdir(dir_path)

    print (str(len(dir_list)) + " SLICES FOUND")
    slices=[];
    #slices = [pydicom.read_file(dir_path + '/' + s) for s in os.listdir(dir_path)]
    for s in dir_list:
        try: 
            slices.append(pydicom.read_file(dir_path + '/' + s))
            #slices.append(pydicom.read_file(dir_path + '/' + s))
        except:
            [] #print(' FAILED IMPORT FOR ' + str(s))
            time.sleep(0.1)

    try:
        slices.sort(key = lambda x: float(x.SliceLocation))
    except:
        try:
            slices.sort(key = lambda x: float(x.InstanceNumber))        
        except:
            slices.sort(key = lambda x: float(x.ImagePositionPatient[2]))

    #print(slices[0].pixel_array)
    # Convert to Hounsfield units (HU)
    for slice_number in range(len(slices)):
        try:   
            slope = slices[slice_number].RescaleSlope
            if slope != 1:
                slices[slice_number] = slope * slices[slice_number].astype(np.float64)
                slices[slice_number] = slices[slice_number].astype(np.int16) 
        except:
            [];
        try:
            intercept = slices[slice_number].RescaleIntercept
            slices[slice_number] += np.int16(intercept)
            #print('Intercept found')
        except:
            [];

    image = np.stack([s.pixel_array for s in slices], axis=2)
    # Convert to int16 (from sometimes int16), 
    # should be possible as values should always be low enough (<32k)
    image = image.astype(np.int16)

    if not slices:
        print('WARNING: NO SLICES FOR ' + dir_path)
    return image, slices



def preprocess(scan, debug_mode=False):
    # Preprocesses scans for inference--> thresholding values, resizing
    # inputs: scan is numpy array of [h,w,d]

    m=np.mean(scan)
    s=np.std(scan)
    n_std=2.5
    trunc=m+n_std*s
    scan=scan.astype(np.float32)
    scan[scan>(trunc)]=trunc
    scan=((scan/trunc)*255).astype(np.uint8)
    #scan=np.expand_dims(scan, axis=0) # [h, w, d]

    idx=np.where(np.isnan(scan)) # remove nans
    scan[idx]=0
    idx=np.where(np.isinf(scan)) # remove infs
    scan[idx]=0

    return scan



def init(scan): 
    # initializes segmentation map and view index of imported scan
    # inputs: scan is numpy array of [h,w,d]
    # output: idx is a scalar that represents the slice to be viewed
    # map_cur and map_o are numpy arrays of [h,w,d]
    # They are all zeros because the segmentation map is all background at first
 
    num_slices=scan.shape[-1]
    if num_slices<1:
        idx1=0
    else:
        idx1=int(num_slices/2)

    if scan.shape[0]<1:
        idx2=0
    else:
        idx2=int(scan.shape[0]/2)

    if scan.shape[1]<1:
        idx3=0
    else:
        idx3=int(scan.shape[1]/2)

    map_cur=np.zeros(scan.shape, dtype=np.int)
    map_o=np.zeros(scan.shape, dtype=np.int)
    imd_view=scan

    return idx1, idx2, idx3, map_cur, map_o, imd_view




# @bp.route('/') # Flask render template
# def upload_form():
# 	return render_template('base.html')

@login_required
@bp.route('/upload/', methods=['POST', 'GET'])
def upload_file():
	if request.method == 'POST':
		print(request)
		print(request.files)

		# check if the post request has the files part
		if 'files[]' not in request.files:
			flash('No file part'); print('No file part')
			return redirect(request.url)

		# Create directory to upload files to
		files = request.files.getlist('files[]')
		print('CREATING UPLOAD DIR')
		upload_dir=str(uuid.uuid4())
		instance_dir=app.config['UPLOAD_FOLDER'] + upload_dir; print(instance_dir)
		os.mkdir(instance_dir); 

		# Upload and save
		ct=0
		for file in files:
			if file and allowed_file(file.filename):
				print(file)
				filename = secure_filename(file.filename)
				print(filename)
				file.save(os.path.join(instance_dir, filename)); ct+=1
		print('CT is ' + str(ct))

		# If we found slices, proceed with import workflow
		if ct>0:
			# Get instance
			S=Subject_instance(instance_dir) # Initialize instance
			S=import_scan_wrapper(S)
			flash('File(s) successfully uploaded')
			print(S.dir)
			print(S.imd.shape, S.pxd.shape, S.imd_view.shape, S.pxd_view.shape, S.idx)
            # Update instance list
			instance_list().inst_list.append(S); # 
			instance_list().idx=len(instance_list().inst_list)-1; # Put idk to latest uploaded instance
			print(len(instance_list().inst_list), instance_list().idx)
			
			pass_view()
			
		else: # If we didn't upload any files, just delete the directory
			os.rmdir(instance_dir)
			flash('No appropriate files found')

		del_temp_dir(instance_dir)


		
	return pass_view()
    # return redirect('/') # render_template('upload.html')#

















