# Web dev libs
import os
import urllib.request
# from appp import app
from flask import Flask, flash, request, redirect, render_template, url_for, send_file, make_response
from werkzeug.utils import secure_filename

# Other libraries
import matplotlib.pyplot as plt
from io import BytesIO
from io import StringIO
import base64
import numpy as np
import random

from flaskr.auth import login_required
from flaskr.db import get_db

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

bp = Blueprint('manual_worflow', __name__)


from flaskr.upload_workflow import *
from flaskr.class_def import *

from flaskr.view_workflow import *
# from flaskr.class_def import *

    

# New class
@login_required
@bp.route('/manual_new_class/', methods=['GET'])
def manual_new_class():


    if instance_list().idx>-1: # There are instances in the list

        # Add to number of classes
        instance_list().inst_list[instance_list().idx].num_classes+=1; # Add to number of classes
        num_classes=instance_list().inst_list[instance_list().idx].num_classes

        # Iterate through names until we get one
        names=instance_list().inst_list[instance_list().idx].c_names # Get list of names
        new_cid=instance_list().inst_list[instance_list().idx].num_classes-1;
        new_name_id=new_cid; new_name='Untitled_' + str(new_name_id)
        while new_name in names:
            new_cid+=1
            new_name_id=new_cid; new_name='Untitled_' + str(new_name_id)
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

    return pass_view()
    # return 'success'

                
# @singleton
class instance_list(object):
    def __init__(self, inst_list=[], idx=-1):
        self.inst_list = inst_list
        self.idx = idx
    def clear_insts(self):
        self.inst_list = []
        self.idx = -1


# Change current class
@login_required
@bp.route('/manual_change_class/', methods=['GET', 'POST'])
def manual_change_class(): # retrieves name of class to be taken as current, return index in class list associated with that class string

    if instance_list().idx>-1: # There are instances in the list

        a = request.form.get('class_string') # String from request that represents the requested name of the new class
        #curr_class=instance_list().inst_list[instance_list().idx].curr_class
        names=instance_list().inst_list[instance_list().idx].c_names

        if len(names)>0:
            matching = [s for s in range(len(names)) if a == names[s]]
            if len(matching)>0:
                instance_list().inst_list[instance_list().idx].curr_class=matching[0]

        return make_response(str(matching[0]))
        # return('responce 1 ')

    else:

        # return make_response(' ')
        return('responce 2 ')

# Delete class
@login_required
@bp.route('/manual_delete_class/', methods=['GET', 'POST'])
def manual_delete_class():

    if instance_list().idx>-1: # There are instances in the list

        # Get current class ID
        curr_class=instance_list().inst_list[instance_list().idx].curr_class

        # Lower num classes
        instance_list().inst_list[instance_list().idx].num_classes-=1;

        # Remove name from list
        del instance_list().inst_list[instance_list().idx].c_names[curr_class]

        # Remove color from list
        del instance_list().inst_list[instance_list().idx].cvec[curr_class]

        # Remove geometry from list
        del instance_list().inst_list[instance_list().idx].geoms[curr_class]

        # Remove ID from list
        del instance_list().inst_list[instance_list().idx].cid[curr_class]

        # Remove toggle integer from list
        del instance_list().inst_list[instance_list().idx].c_toggle[curr_class]

        # Make ID be mopst recent class
        num_classes=instance_list().inst_list[instance_list().idx].num_classes
        instance_list().inst_list[instance_list().idx].curr_class=num_classes-1

    return pass_view()
    # return 'pass view'

# Rename class
@login_required
@bp.route('/manual_rename_class/', methods=['GET', 'POST'])
def rename_class(): # Retrieve string of new class name, updates instance

    if instance_list().idx>-1: # There are instances in the list

        a = request.form.get('name_string') # String from request that represents the requested name of the new class

        curr_class=instance_list().inst_list[instance_list().idx].curr_class

        # Make sure name doesn't already exist for this instance
        names=instance_list().inst_list[instance_list().idx].c_names # Get list of names
        new_name=a; b=0;
        while new_name in names:
            b+=1
            new_name=a + '_' + b
            print(new_name)

        instance_list().inst_list[instance_list().idx].c_names[curr_class]=new_name

    # return make_response(new_name) # Returns string of ACTUAL NEW NAME OF NEW CLASS
    # return 'make responce'
    return 'make responce'


# Add/subtract
@login_required
@bp.route('/manual_segment_plane1/', methods=['GET','POST'])
def manual_segment_plane1():
    print('we made it this far 1')

    if instance_list().idx>-1: # There are instances in the list

        print('we made it this far 1')
        idx_str=request.form.get('pix') # A string of numbers separated by commas corresponding to chosen pixels --  EX: "x1,y1,x2,y2,x3,y3"
        b=int(request.form.get('seg_mode'))
        print('we made it this far 2')

        # Decode string of pixels indices back into a matrix
        kk=idx_str.split(',')
        x_list=[int(kk[ii]) for ii in range(0,len(kk),2)]
        y_list=[int(kk[ii]) for ii in range(1,len(kk),2)]
        a=np.stack((x_list,y_list), axis=-1)

        cur_slice=instance_list().inst_list[instance_list().idx].idx_ax1
        cur_im=instance_list().inst_list[instance_list().idx].imd[:,:,cur_slice]

        pix_mat=np.empty((0,0));
        try:
            pix_mat=np.asarray(a)
        except:
            [];

        if pix_mat.shape[0] > 0 and pix_mat.shape[1] > 0:
            print(pix_mat)
            pix_mat[pix_mat<0]=0;
            x_trunc=np.argwhere(pix_mat[:,0]>=cur_im.shape[1])
            pix_mat[x_trunc,0]=cur_im.shape[1];
            y_trunc=np.argwhere(pix_mat[:,1]>=cur_im.shape[0])
            pix_mat[y_trunc,1]=cur_im.shape[0];
            y_pos=pix_mat[:,1]
            x_pos=pix_mat[:,0]
            print(pix_mat)

            if b==0: # Erase, change segmented pixels to background ONLY ERASE PIXELS OF GIVEN CLASS
                curr_class=instance_list().inst_list[instance_list().idx].curr_class # Get index to current class
                cid=instance_list().inst_list[instance_list().idx].cid[curr_class]
                for k in range(len(x_pos.shape[0])):
                    if instance_list().inst_list[instance_list().idx].pxd[y_pos[k], x_pos[k], cur_slice] == cid:
                        instance_list().inst_list[instance_list().idx].pxd[y_pos[k], x_pos[k], cur_slice] = 0

            else: # Add, change segmented pixels to current class
                curr_class=instance_list().inst_list[instance_list().idx].curr_class # Get index to current class
                cid=instance_list().inst_list[instance_list().idx].cid[curr_class] # Get class ID of current class
                instance_list().inst_list[instance_list().idx].pxd[y_pos, x_pos, cur_slice] = cid   # Update seg map of current class

            toggle_seg_view()      

    return pass_view()

    # return 'pass view'


# Add/subtract
@login_required
@bp.route('/manual_segment_plane2/', methods=['GET','POST'])
def manual_segment_plane2():

    if instance_list().idx>-1: # There are instances in the list

        idx_str=request.form.get('pix') # A string of numbers separated by commas corresponding to chosen pixels --  EX: "x1,y1,x2,y2,x3,y3"
        b=int(request.form.get('seg_mode'))

        # Decode string of pixels indices back into a matrix
        kk=idx_str.split(',')
        x_list=[int(kk[ii]) for ii in range(0,len(kk),2)]
        y_list=[int(kk[ii]) for ii in range(1,len(kk),2)]
        a=np.stack((x_list,y_list), axis=-1)

        cur_slice=instance_list().inst_list[instance_list().idx].idx_ax2
        cur_im=instance_list().inst_list[instance_list().idx].imd[cur_slice,:,:]

        pix_mat=np.empty((0,0));
        try:
            pix_mat=np.asarray(a)
        except:
            [];

        if pix_mat.shape[0] > 0 and pix_mat.shape[1] > 0:
            print(pix_mat)
            pix_mat[pix_mat<0]=0;
            x_trunc=np.argwhere(pix_mat[:,0]>=cur_im.shape[1])
            pix_mat[x_trunc,0]=cur_im.shape[1];
            y_trunc=np.argwhere(pix_mat[:,1]>=cur_im.shape[0])
            pix_mat[y_trunc,1]=cur_im.shape[0];
            y_pos=pix_mat[:,1]
            x_pos=pix_mat[:,0]
            print(pix_mat)

            if b==0: # Erase, change segmented pixels to background ONLY ERASE PIXELS OF GIVEN CLASS
                curr_class=instance_list().inst_list[instance_list().idx].curr_class # Get index to current class
                cid=instance_list().inst_list[instance_list().idx].cid[curr_class]
                for k in range(len(x_pos.shape[0])):
                    if instance_list().inst_list[instance_list().idx].pxd[cur_slice, y_pos[k], x_pos[k]] == cid:
                        instance_list().inst_list[instance_list().idx].pxd[cur_slice, y_pos[k], x_pos[k]] = 0

            else: # Add, change segmented pixels to current class
                curr_class=instance_list().inst_list[instance_list().idx].curr_class # Get index to current class
                cid=instance_list().inst_list[instance_list().idx].cid[curr_class] # Get class ID of current class
                instance_list().inst_list[instance_list().idx].pxd[cur_slice, y_pos, x_pos] = cid   # Update seg map of current class

            toggle_seg_view()      

    return pass_view()
    # return 'pass view'

# Add/subtract
@login_required
@bp.route('/manual_segment_plane3/', methods=['GET','POST'])
def manual_segment_plane3():

    if instance_list().idx>-1: # There are instances in the list

        idx_str=request.form.get('pix') # A string of numbers separated by commas corresponding to chosen pixels --  EX: "x1,y1,x2,y2,x3,y3"
        b=int(request.form.get('seg_mode'))

        # Decode string of pixels indices back into a matrix
        kk=idx_str.split(',')
        x_list=[int(kk[ii]) for ii in range(0,len(kk),2)]
        y_list=[int(kk[ii]) for ii in range(1,len(kk),2)]
        a=np.stack((x_list,y_list), axis=-1)

        cur_slice=instance_list().inst_list[instance_list().idx].idx_ax3
        cur_im=instance_list().inst_list[instance_list().idx].imd[:,cur_slice,:]

        pix_mat=np.empty((0,0));
        try:
            pix_mat=np.asarray(a)
        except:
            [];

        if pix_mat.shape[0] > 0 and pix_mat.shape[1] > 0:
            print(pix_mat)
            pix_mat[pix_mat<0]=0;
            x_trunc=np.argwhere(pix_mat[:,0]>=cur_im.shape[1])
            pix_mat[x_trunc,0]=cur_im.shape[1];
            y_trunc=np.argwhere(pix_mat[:,1]>=cur_im.shape[0])
            pix_mat[y_trunc,1]=cur_im.shape[0];
            y_pos=pix_mat[:,1]
            x_pos=pix_mat[:,0]
            print(pix_mat)

            if b==0: # Erase, change segmented pixels to background ONLY ERASE PIXELS OF GIVEN CLASS
                curr_class=instance_list().inst_list[instance_list().idx].curr_class # Get index to current class
                cid=instance_list().inst_list[instance_list().idx].cid[curr_class]
                for k in range(len(x_pos.shape[0])):
                    if instance_list().inst_list[instance_list().idx].pxd[y_pos[k], cur_slice, x_pos[k]] == cid:
                        instance_list().inst_list[instance_list().idx].pxd[y_pos[k], cur_slice, x_pos[k]] = 0

            else: # Add, change segmented pixels to current class
                curr_class=instance_list().inst_list[instance_list().idx].curr_class # Get index to current class
                cid=instance_list().inst_list[instance_list().idx].cid[curr_class] # Get class ID of current class
                instance_list().inst_list[instance_list().idx].pxd[y_pos, cur_slice, x_pos] = cid   # Update seg map of current class

            toggle_seg_view()      

    return pass_view()
    # return 'pass view'
@login_required
@bp.route('/reset_seg/', methods=['GET'])
def reset_seg(): # Deletes all classes and meta data associated with an instance

    inst_idx=instance_list().idx; 
    instance_list().inst_list[inst_idx].pxd=np.zeros((instance_list().inst_list[inst_idx].imd.shape))
    instance_list().inst_list[inst_idx].pxd_view=np.zeros_like(instance_list().inst_list[inst_idx].pxd)

    # Delete all classes
    num_classes=instance_list().inst_list[instance_list().idx].num_classes
    for kkkk in range(num_classes-1,0,-1):
        instance_list().inst_list[instance_list().idx].curr_class=kkkk
        manual_delete_class()
    
    return pass_view()
    # return 'pass view'