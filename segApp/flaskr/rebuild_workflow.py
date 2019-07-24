# Web dev libs
import os, shutil
import urllib.request

from flask import Flask, flash, request, redirect, render_template, url_for, send_file
from werkzeug.utils import secure_filename

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
from itertools import chain

# Pipped packages
import scipy
import boto3
from scipy.spatial import Delaunay

from stl import *

# Other code
from flaskr.upload_workflow import *
from flaskr.view_workflow import *
from flaskr.class_def import *

from flaskr.auth import login_required
from flaskr.db import get_db

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort



bp = Blueprint('rebuild_workflow', __name__)

############ NOTES: Always triggered for current instance ##########################
############ TO-DO: Figure out how to pass STLs to UI for visualization ############

################################################
############# Build Geoms Workflow #############
################################################

# Get Scan meta data
def get_scan_meta(slices):

    PS=[];
    IPP=[];
    IOP=[];
    ST=[];
    voxel_dims=[];

    for s in range(len(slices)): # Meta data necessary for reconstructing STL
        #print(slices[s].PatientPosition)
        PS.append(slices[s].PixelSpacing)
        IPP.append(slices[s].ImagePositionPatient)
        IOP.append(slices[s].ImageOrientationPatient)
        ST.append(slices[s].SliceThickness)
        voxel_dims.append(np.array([float(slices[0].PixelSpacing[0]), float(slices[0].PixelSpacing[0]), float(slices[0].SliceThickness)]))

    return PS, IPP, IOP, ST, voxel_dims



# Create point clouds
def get_pt_clouds(cids, kk, PS, IPP, IOP, ST, voxel_dims):

    # Scan coordinate directions
    num_slices=kk.shape[2]; num_rows=kk.shape[0]; num_cols=kk.shape[1];

    # Strategy is to generate a point cloud of all possible voxels in the DICOM stack
    # Then find the voxels that have been segmented for each class and use some mathy math to find the correct nodes

    # I HAVE TO GO SLICE BY SLICE!!
    #print('GENERATING POINT CLOUD')
    pt_cloud=[];
    for lol in range(kk.shape[-1]): # Slice dim --> iterate through slice dimension

        IPP_curr=(float(IPP[lol][0]), float(IPP[lol][1]), float(IPP[lol][2]))
        IOP_curr=(float(IOP[lol][0]), float(IOP[lol][1]), float(IOP[lol][2]), float(IOP[lol][3]), float(IOP[lol][4]), float(IOP[lol][5]))

        delta_i=voxel_dims[lol][0];
        delta_j=voxel_dims[lol][1]; 
        delta_k=voxel_dims[lol][2];

        Xx=IOP_curr[0];
        Xy=IOP_curr[1];
        Xz=IOP_curr[2];
        Yx=IOP_curr[3];
        Yy=IOP_curr[4];
        Yz=IOP_curr[5];
        Sx=IPP_curr[0];
        Sy=IPP_curr[1];
        Sz=IPP_curr[2];
        affine_mat=np.array([[Xx*delta_i, Yx*delta_j, 0, Sx], [Xy*delta_i, Yy*delta_j, 0, Sy], [Xz*delta_i, Yz*delta_j, 0, Sz], [0, 0, 0, 1]])  

        pt_temp=[];
        for j in range(num_cols):
            i_vec=j*np.ones((1,num_rows));
            j_vec=1*np.expand_dims(np.array(list(range(num_rows))), axis=0);
            k_vec=np.zeros((1,num_rows));
            ones_vec=np.ones((1,num_rows));

            coord_mat=np.concatenate((i_vec, j_vec, k_vec, ones_vec), axis=0)
            col_nodes=np.matmul(affine_mat,coord_mat);
            col_nodes=col_nodes[:3,:]
            col_nodes=col_nodes.T

            col_nodes_temp=col_nodes
            col_nodes=np.empty((num_rows,3))
            col_nodes[:,0]=col_nodes_temp[:,0];
            col_nodes[:,1]=col_nodes_temp[:,1];
            col_nodes[:,2]=col_nodes_temp[:,2];
 
            if j==0:
                pt_temp=col_nodes; 
            else:
                pt_temp=np.concatenate((pt_temp, col_nodes), axis=0)
        pt_cloud.append(pt_temp) 

    # Now use the segmentation maps to get those dumb ass point clouds
    full_class_pts=[];     print(''); num_class=len(cids);
    for j in range(num_class): # Each class
        class_id=cids[j]; #print('CLASS ID ' + str(class_id))
        class_pts_temp=[];
        for k in range(len(pt_cloud)): # Each slice 
            current_slice=kk[:,:,k]
            idx=np.argwhere(current_slice==class_id)
            #print(idx.shape)
            these_pts=pt_cloud[k][(num_rows*idx[:,1]+idx[:,0]),:]
            #print(these_pts.shape)
            if k==0:
                class_pts_temp=these_pts #Identify points  based on column-major format
            else:
                class_pts_temp=np.concatenate((class_pts_temp,these_pts), axis=0)
        full_class_pts.append(class_pts_temp)
        #print(class_pts_temp.shape)

    #print(len(full_class_pts))
    for klkl in range(num_class):
        if klkl>0:
            points = full_class_pts[klkl]
            np.savetxt(('./' + str(klkl) +  '_PT.csv'), points)

    return full_class_pts # List of point clouds, one point cloud for each class EXCEPT background


def get_edge_lengths(n1,n2):

    subs=n1-n2;
    lens=np.sqrt(np.sum(np.square(subs), axis=1))

    return lens

# Create STLs from point clouds
def get_stls(pt_cloud_list, alpha):
    print('Obtaining STLs')

    stl_list=[];

    for iiii in range(len(pt_cloud_list)):

        if iiii>0 and pt_cloud_list[iiii].shape[0]>0:
            print(iiii)
            n=pt_cloud_list[iiii]
        
            # Delaunay triangulation
            tri = Delaunay(n)
            e=tri.simplices;

            surf_elem_deg=3;

            edge_lengths=[];
            edge_lengths.append(get_edge_lengths(n[e[:,0],:],n[e[:,1],:]))
            edge_lengths.append(get_edge_lengths(n[e[:,1],:],n[e[:,2],:]))
            edge_lengths.append(get_edge_lengths(n[e[:,2],:],n[e[:,3],:]))
            edge_lengths.append(get_edge_lengths(n[e[:,3],:],n[e[:,0],:]))
            edge_lengths.append(get_edge_lengths(n[e[:,0],:],n[e[:,2],:]))
            edge_lengths.append(get_edge_lengths(n[e[:,1],:],n[e[:,3],:]))
            edge_lengths=np.stack(edge_lengths, axis=-1)

            #print(edge_lengths)
            max_lens=np.amax(edge_lengths, axis=1)

            # Subtract elements with edges that exceed a specfied length
            e=e[max_lens<alpha]

            # Extract surface tris for STL
            el1=np.stack((e[:,0], e[:,1], e[:,2]), axis=-1)
            el2=np.stack((e[:,1], e[:,2], e[:,3]), axis=-1)
            el3=np.stack((e[:,3], e[:,0], e[:,1]), axis=-1)
            el4=np.stack((e[:,0], e[:,2], e[:,3]), axis=-1)
            faces=np.concatenate((el1,el2,el3,el4), axis=0)
            faces=np.split(faces, faces.shape[0])
            faces=[set(np.sort(np.squeeze(a))) for a in faces]
            boundary_faces=[j for j in faces if faces.count(j)==1]

            unique_nodes=list(set(chain.from_iterable(boundary_faces)))
            elems_new_old=np.asarray([list(s) for s in boundary_faces])

            elems_new=np.zeros(elems_new_old.shape, np.uint16)
            n_new=[]; # Initialize new node list

            for j in range(len(unique_nodes)):
                n_new.append(n[unique_nodes[j],:])# Add node to new node list
                #print(j, unique_elems[j])
                new_idx=np.argwhere(elems_new_old==unique_nodes[j])
                #print(new_idx)
                elems_new[new_idx[:,0], new_idx[:,1]]=j

            n=np.stack(n_new, axis=-1).T

            # Create stl_geom instance from nodes and elems and add to instance field
            instance_list().inst_list[instance_list().idx].geoms[iiii]=stl_geom(n,elems_new);
            #stl_list.append(stl_geom(n,elems_new))

    return #pass_view()#stl_list



class stl_geom:

    def __init__(self, n, e):
        self.n=n
        self.e=e
        return

    def export(self): # Method for exporting the STL TO-DO
        return


@login_required
@bp.route('/Export_Maps/', methods=['GET'])  
def export_maps(): # Replaces imported DICOMS with segmentation maps for export
    curr_inst=instance_list().inst_list[instance_list().idx]

    slices=curr_inst.slices;
    pxd=curr_inst.pxd;

    for j in range(len(slices)): # Replace slices with segmentation maps
        slices[j].PixelData=pxd[:,:,j].tostring();

        ID=str(j)
        while len(ID)<6:
            ID='0' + ID;
        outtie=out_path+ID + '.dcm'
        ######pydicom.write_file(outtie,slices[j])

    return 'success'

@login_required
@bp.route('/Export_Geoms/', methods=['GET']) 
def export_geoms(): # Downloading geometries

    # FIGURE OUT HOW TO EXPORT PT CLOUDS FOR DOWNLOAD

    return 'success'

@login_required
@bp.route('/Create_Geoms/', methods=['GET'])
def create_geoms(): # Reconstructs geometries from segmentation maps using DICOM metadata
    try:
        curr_inst=instance_list().inst_list[instance_list().idx]
        scan=curr_inst.slices
        pxd=curr_inst.pxd

        PS, IPP, IOP, ST, voxel_dims=get_scan_meta(scan)

        pt_cloud_list=get_pt_clouds(curr_inst.cid, pxd, PS, IPP, IOP, ST, voxel_dims) # Use class id vec as reference

        alpha=np.amax((2*voxel_dims[0][0],2*voxel_dims[0][1],2*voxel_dims[0][2]))
        print('alpha is ' + str(alpha))
        get_stls(pt_cloud_list, alpha)
        
        return 'pass view'
    
    except: 
        if IndexError:
            return 'list index error'
        else: 
            return 'error'
    # FIGURE OUT HOW TO EXPORT PT. CLOUDS FOR RENDERING

    # return pass_view()
    

