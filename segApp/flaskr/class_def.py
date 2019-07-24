# Other libs
import uuid
import time
import numpy as np
import cv2
import pydicom
from io import BytesIO
from io import StringIO
import base64
import matplotlib.pyplot as plt



########### USE METACLASS to keep a single accessable list of all instances ##########
def singleton(cls, *args, **kw):
    instances = {}
    def _singleton():
       if cls not in instances:
            instances[cls] = cls(*args, **kw)
       return instances[cls]
    return _singleton

@singleton
class instance_list(object):
    def __init__(self, inst_list=[], idx=-1):
        self.inst_list = inst_list
        self.idx = idx
    def clear_insts(self):
        self.inst_list = []
        self.idx = -1
        

#### IMPORTANT! ALL UPLOADED SUBJECTS LOOK LIKE THIS
# Create instance class
class Subject_instance:

    def __init__(self, upload_dir):
        self.dir=upload_dir # Directory that scans were uploaded to

        # Imaging
        self.imd = []; # [h,w,d] numpy array of the scan
        self.pxd = [];  # [h,w,d] numpy array of the segmentation map
        self.pxd_view = [];  # [h,w,d] numpy array of the segmentation map that is toggled ON
        self.slices=[]; # actual slices of instance

        # Navigation
        self.idx_ax1 = []; # index to be viewed on plane 1--> integer value in the range [0,d]
        self.idx_ax2 = []; # index to be viewed on plane 2 --> integer value in the range [0,h]
        self.idx_ax3 = []; # index to be viewed on plane 3 --> integer value in the range [0,w]

        # Meta attributes
        self.num_classes=1; # number of classes
        self.cid=[]; self.cid.append(0) # class IDs --> integers corresponding to classes on segmentation map
        self.c_names=[]; self.c_names.append('____background____') # class names, strings for each cid
        self.cvec=[]; self.cvec.append((0,0,0)) # class colors for each cid
        self.c_toggle=[]; self.c_toggle.append(1); # list of integers related to if current class is visible or not
        self.curr_class=0 # Initialize current class to 0

        # Geometries
        self.geoms=[]; self.geoms.append([]); # Allocate geoms. Geoms will be a list of STL class geometries for each segmentation class 
        
        return

    def get_view(self): 

        # Set up color vec
        color_vec=[]; # Aggregate class colors for current instance
        num_classes=instance_list().inst_list[instance_list().idx].num_classes
        for j in range(num_classes):
            color_vec.append(self.cvec[j])
        

        # View 1
        slice_cur=self.imd[:,:,self.idx_ax1]
        seg_cur=self.pxd_view[:,:,self.idx_ax1] # slice of segmentation map
        # Set up images for alpha blending
        img1=np.expand_dims(slice_cur, axis=2); img1=np.concatenate((img1,img1,img1), axis=-1).astype(int) # RGB channels now
        seg_map=np.empty((img1.shape[0],img1.shape[1],3))
        for ll in range(img1.shape[0]): # TODO: Make faster
           for jj in range(img1.shape[1]):
                spot=np.where(seg_cur[ll,jj]==self.cid) # Find index of class ID that current pixel equals
                seg_map[ll,jj,:]=color_vec[spot[0][0]]
        # Create alpha blended overlay for current slice
        temp1=cv2.addWeighted(img1.astype(np.int), 0.7, seg_map.astype(np.int), 0.3, 0)


        # View 2
        slice_cur=self.imd[self.idx_ax2,:,:]
        seg_cur=self.pxd_view[self.idx_ax2,:,:] # slice of segmentation map
        # Set up images for alpha blending
        img1=np.expand_dims(slice_cur, axis=2); img1=np.concatenate((img1,img1,img1), axis=-1).astype(int) # RGB channels now
        seg_map=np.empty((img1.shape[0],img1.shape[1],3))
        for ll in range(img1.shape[0]): # TODO: Make faster
           for jj in range(img1.shape[1]):
                spot=np.where(seg_cur[ll,jj]==self.cid) # Find index of class ID that current pixel equals
                seg_map[ll,jj,:]=color_vec[spot[0][0]]
        # Create alpha blended overlay for current slice
        temp2=cv2.addWeighted(img1.astype(np.int), 0.7, seg_map.astype(np.int), 0.3, 0)        


        # View 3
        slice_cur=self.imd[:,self.idx_ax3,:]
        seg_cur=self.pxd_view[:,self.idx_ax3,:] # slice of segmentation map
        # Set up images for alpha blending
        img1=np.expand_dims(slice_cur, axis=2); img1=np.concatenate((img1,img1,img1), axis=-1).astype(int) # RGB channels now
        seg_map=np.empty((img1.shape[0],img1.shape[1],3))
        for ll in range(img1.shape[0]): # TODO: Make faster
           for jj in range(img1.shape[1]):
                spot=np.where(seg_cur[ll,jj]==self.cid) # Find index of class ID that current pixel equals
                seg_map[ll,jj,:]=color_vec[spot[0][0]]
        # Create alpha blended overlay for current slice
        temp3=cv2.addWeighted(img1.astype(np.int), 0.7, seg_map.astype(np.int), 0.3, 0)

        # temp is a [h,w,3] image that represents the scan with segmentation map current overlay


        return temp1, temp2, temp3
















def get_im(im,ov):

    return 'return image'




















