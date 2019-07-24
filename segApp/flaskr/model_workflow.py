# Web dev libs
import os, shutil
import urllib.request

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('model_workflow', __name__)


# Other libs
import uuid
import time
import numpy as np
import cv2
import pydicom

# Preconfigured packages
import time
import os
import pickle
import zlib

# Pipped packages
import scipy
import boto3


# Other code

from flaskr.upload_workflow import *
from flaskr.view_workflow import *
from flaskr.class_def import *


def get_model_specs(model_string):      
    # Get specs for model based on model name from API call

    model_dict={

                 'MRI_KNEE_2D_SAGITTAL': {'path': 'frozen_2d.pb',
 'function': model_call_MRI_KNEE_2D_SAGITTAL,
 'clusters': (1,1,1,1,1,1,2),
 'class_names': ('Background','Femur','Femoral_Cartilage','Patella','Patellar_Cartilage','Tibia','Tibial_Cartilage')},

                'MRI_KNEE_3D_SAGITTAL': {'path': 'frozen_3d.pb', 
'function': model_call_MRI_KNEE_3D_SAGITTAL, 
'clusters': (1,1,1,1,1,1,2),
 'class_names': ('Background','Femur','Femoral_Cartilage','Patella','Patellar_Cartilage','Tibia','Tibial_Cartilage')}

	}

    # Define inference function, graph, and custer vec for now, maybe more later
    return model_dict[model_string]["path"], model_dict[model_string]["function"], model_dict[model_string]["clusters"], model_dict[model_string]["class_names"]


#######################################################
############## MODEL SEND WORKFLOW #########
############################################


def create_object_name(object_pre):
    # Gets random digits to append to a string to create an "unlikely-to-copy" name
    return ''.join([object_pre, str(uuid.uuid4())])





def bucket_upload(scan, model_name, user_name, debug_mode):
    # Uploads object to job bucket

    # Inputs:
    # Model_name -- is a string that identifies what kind of model will be accessed
    # Wrap_data -- is a [h, w, d] numpy array that represents the voxels of a medical imaging scan

    # Bucket and name of object to upload
    upload_bucket_name='segai6969jobbucket'
    upload_key_name= create_object_name(user_name) + '.pkl'
    print('Upload KEY is ' + upload_key_name)

    # Clients and resources
    s3_client=boto3.client('s3')
    s3_resource=boto3.resource('s3')

    #scan=np.zeros((300,100,50))
    print('Scan is ')
    print(scan.shape)
    wrap_data=[scan, model_name]

    # Put an object to an S3 bucket in order to trigger Lambda function
    pickle_byte_obj=pickle.dumps(wrap_data) 
    compressed=zlib.compress(pickle_byte_obj)
    print('Uploading scan')
    t1=time.time()
    s3_client.put_object(Body=compressed, Bucket=upload_bucket_name, Key=upload_key_name)
    print('Uploading took ' + str(time.time()-t1))

    # Print objects in bucket
    print('Printing object in bucket')
    BUCKET_OBJ=s3_resource.Bucket(name=upload_bucket_name)
    for my_buck_obj in BUCKET_OBJ.objects.all():
        print(my_buck_obj) # prints summary

    return upload_key_name








##########################################
########### MODEL RETRIEVE WORKFLOW ######
##########################################





def retrieval_wrapper2(upload_key_name, model_string, scan, debug_mode):


    # Name of results bucket
    bucket_name='segai6969resultsbucket'

    proceed_flag=0;

    # Get results bucket
    s3_client=boto3.client('s3')
    s3_resource=boto3.resource('s3')
    BUCKET_OBJ=s3_resource.Bucket(name=bucket_name)

    tb=time.time()
    while proceed_flag==0:
        item_list=[]; 
        for my_buck_obj in BUCKET_OBJ.objects.all():
            item_list.append(my_buck_obj.key) # prints summary
        if upload_key_name in item_list:
            proceed_flag=1;
        time.sleep(7)
        print('ELAPSED TIME IS ' + str(time.time() - tb))
        
    # Retrieve scan from results bucket
    results = retrieve_results(upload_key_name, model_string, bucket_name, debug_mode) # [h,w,d]

    # Export results
    #_=export_results(scan, results, export_path, debug_mode)

    return results;




def retrieve_results(object_key, model_string, bucket_name, debug_mode):
    # Wrapper for retrieving and post-processing results

    out=download_result(object_key, bucket_name, debug_mode)

    if debug_mode==False:
        out=postprocess(out, model_string, debug_mode)

    return out






def download_result(object_key, bucket_name, debug_mode):

    # Clients and resources
    s3_client=boto3.client('s3')
    s3_resource=boto3.resource('s3')

    # Download object
    print('Downloading Results')
    s3_response_object=s3_client.get_object(Bucket=bucket_name, Key=object_key)
    kk=s3_response_object['Body'].read()

    # Delete object that was uploaded
    print('DELETING OBJECT')
    if debug_mode==False:
        s3_resource.Object(bucket_name, object_key).delete()

    # Print objects in bucket
    print('PRINTING OBJECTS AFTER DELETING')
    BUCKET_OBJ=s3_resource.Bucket(name=bucket_name)
    for my_buck_obj in BUCKET_OBJ.objects.all():
        print(my_buck_obj) # prints summary
        
    # Decode objects
    print('Decompressing object')
    arr=pickle.loads(zlib.decompress(kk))
    print('ARRAY IS ' )
    print(arr.shape)
    # arr is [h,w,d]

    return arr.astype(np.int)





def postprocess(results, model_string, debug_mode):

    # Get model specs
    _, _, custer_vec = get_model_specs(model_string)

    # Put results in one-hot format
    num_classes=len(custer_vec)   
    hardmax=np.zeros((results.shape[0], results.shape[1], results.shape[2], num_classes))
    temp=results
    temp_shape=temp.shape
    targets = np.array(temp).reshape(-1)
    targets=np.eye(num_classes)[targets]
    targets=targets.reshape(temp_shape[0],temp_shape[1],temp_shape[2],num_classes)
    hardmax=targets
    print('ONEHOT SHAPE IS' + str(hardmax.shape))
    print(hardmax.shape)

    # Connected components algorithm
    print('Connected Components Algorithm');   
    neighbor_structure=np.ones((3,3,3))
    seg_new=np.zeros((hardmax[:,:,:,:].shape[0], hardmax[:,:,:,:].shape[1], hardmax[:,:,:,:].shape[2], hardmax[:,:,:,:].shape[-1]))
    # Apply SCAN clustering to each structure to get rid of false positive clusters
    for mk in range(1,hardmax.shape[-1]): # EACH CLASS --> SKIP BACKGROUND
        current_im=hardmax[:,:,:,mk]
        labeled, ncomponents = scipy.ndimage.measurements.label(current_im)
        unique, counts = np.unique(labeled, return_counts=True) # Automatically returns sorted
        unique=unique[1:]; counts=counts[1:] # Get rid of first element --> background
        comps=dict(zip(unique,counts))
        ind = np.argpartition(counts, -custer_vec[mk])[-custer_vec[mk]:] # Returns indices to components with top volumes
        clusts=unique[ind] # labels of said components
        for jk in range(clusts.shape[0]):
            where_vec=np.asarray(np.where(np.asarray(labeled)==clusts[jk])) # Find pixels that belong to component of interest
            seg_new[where_vec[0],where_vec[1],where_vec[2],mk]=1
    sums=np.sum(seg_new,axis=-1)
    idx=np.asarray(np.where(sums==0)) # Indices to zeros
    seg_new[idx[0],idx[1],idx[2],0]=1 # Classless voxels get assigned background class
    hardmax=seg_new;

    hardmax=np.argmax(hardmax, axis=-1) # Convert back to absolute
    return hardmax.astype(np.int)
       
       

'''
def export_results(scan, hardmax, export_path, debug_mode):
    # Takes scans and segmentation maps and exports segmentation overlays

    # EXPORT
    print('Exporting')
    tot_ct=0;
    #color_vec=((0,0,0),(255,0,255),(0,255,0),(255,0,0),(255,255,0),(0,100,100),(0,0,255))

    # Create random colors with background being blank
    color_vec=[]; color_vec.append((0,0,0))
    for j in range(int(np.amax(hardmax))):
        color_vec.append((np.random.randint(low=0, high=255),np.random.randint(low=0, high=255),np.random.randint(low=0, high=255)))
    
    for kkkk in range(hardmax.shape[2]): # Depth dimension
        ID=str(kkkk)
        while len(ID)<6:
            ID='0' + ID
        tot_ct+=1;
        # Set up image --> 2 RBG images
        img1=np.expand_dims(scan[:,:,kkkk], axis=2)
        img1=np.concatenate((img1,img1,img1), axis=-1).astype(int) # RGB channels now
        img2=hardmax[:,:,kkkk]
        seg_map=np.empty((img2.shape[0],img2.shape[1],3)).astype(int)
        for ll in range(img2.shape[0]):
            for jj in range(img2.shape[1]):
                seg_map[ll,jj,:]=color_vec[img2[ll,jj]]
        temp=cv2.addWeighted(img1, 0.7, seg_map, 0.3, 0)
        cv2.imwrite(export_path + '/' + str(ID) + ".jpg", temp.astype(np.uint8))

    return 'We out here'''




##########################################
########### RESULTS MERGE WORKFLOW ######
##########################################



def merge_results(results, class_name_vec):

    # Takes seg results, class names, and appends seg classes to instance
    new_cids_temp=np.unique(results) # Returns sorted so we good
    for jj in range(len(new_cids_temp)):
        if new_cids_temp[jj]!=0: # Exclude background class

            new_name=class_name_vec[jj];
            instance_list().inst_list[instance_list().idx].num_classes+=1;
            num_classes=instance_list().inst_list[instance_list().idx].num_classes

            names=instance_list().inst_list[instance_list().idx].c_names # Get list of names
            b=0; a=new_name;

            while new_name in names:
                b+=1
                new_name=a + '_' + b
                print(new_name)

            instance_list().inst_list[instance_list().idx].c_names.append(new_name)
            instance_list().inst_list[instance_list().idx].c_toggle.append(1)

            # Get new color
            instance_list().inst_list[instance_list().idx].cvec.append((np.random.randint(low=0, high=255),np.random.randint(low=0, high=255),np.random.randint(low=0, high=255)))

            # Add new ID to class ID list of current instance
            new_cid_seg=np.amax(instance_list().inst_list[instance_list().idx].cid)+1 # ID of new class IN MAP
            instance_list().inst_list[instance_list().idx].cid.append(new_cid_seg)

            # Make current class be the new class --> Therefore it is the end of the list
            num_classes=instance_list().inst_list[instance_list().idx].num_classes
            instance_list().inst_list[instance_list().idx].curr_class=num_classes-1
            instance_list().inst_list[instance_list().idx].geoms.append([]);

            # Finally, add segmentation results to seg map, assign using new class_id
            instance_list().inst_list[instance_list().idx].pxd[results==new_cids_temp[jj]]=new_cid_seg
            
    return 

@login_required
@bp.route('/call_model/', methods=['POST', 'GET'])
def call_model():

    # Prepare for takeoff
    a = request.form.get('model_string') # A string that is associated with the selected model 
    b = request.form.get('user_name') # A string that is associated with the selected model 
    model_string=a#'MRI_KNEE_3D_SAGITTAL' # OR 'MRI_KNEE_3D_SAGITTAL' # string that IDs  model
    user_name=b# Username, used for naming the object that is uploaded for inference
    debug_mode=True
    inst_idx=instance_list().idx; #print(inst_idx)
    scan=instance_list().inst_list[inst_idx].imd # Scan of current instance

    ####### LIVE VERSION ####################
    # Send to be uploaded to job bucket
    #upload_key_name=bucket_upload(scan, model_string,  user_name, debug_mode)
    #print(upload_key_name)
    # Retrieval workflow
    #retrieval_wrapper(upload_key_name, model_string, scan, export_path, debug_mode)
    ########################################

    # Local debugging environment
    results=np.zeros_like(scan); #retrieval_wrapper(upload_key_name, model_string, scan, export_path, debug_mode)
    results[7:11,5:8,6:9]=1;
    results[2:7,5:8,6:9]=2;
    results[0:2,0:4,0:6]=7;
    class_vec_name=('Background','PLACEHOLDER1','PLACEHOLDER2','PLACEHOLDER3')
    print(np.argwhere(results==1).shape)
    print(np.argwhere(results==2).shape)
    print(np.argwhere(results==7).shape)

    # Update current segmentation map with returned segmentation map
    merge_results(results, class_vec_name)
    toggle_seg_view() 

    return pass_view()