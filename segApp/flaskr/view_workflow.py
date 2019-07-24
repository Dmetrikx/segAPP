# # Web dev libs
import os
import urllib.request


from flask import Flask, flash, request, redirect, render_template, url_for, send_file, make_response, jsonify

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
bp = Blueprint('view_workflow', __name__)


from flaskr.upload_workflow import *
from flaskr.class_def import *


def toggle_seg_view():

    pxd=instance_list().inst_list[instance_list().idx].pxd
    instance_list().inst_list[instance_list().idx].pxd_view=np.empty(pxd.shape)
    instance_list().inst_list[instance_list().idx].pxd_view[:,:,:]=pxd[:,:,:] # Weird mem alloc thing
    pxd_view=instance_list().inst_list[instance_list().idx].pxd_view

    toggle_list=instance_list().inst_list[instance_list().idx].c_toggle


    for j in range(1,len(toggle_list)): # Iterate through toggle list and look for which pixels to black out
        if toggle_list[j]==0:
            cid=instance_list().inst_list[instance_list().idx].cid[j]
            instance_list().inst_list[instance_list().idx].pxd_view[pxd_view==cid]=0; # Mute  class

    return
     

@login_required
@bp.route('/pass_view/')
def pass_view(): # Takes current instance and returns views in all three planes

    if len(instance_list().inst_list)==0: # No instances yet, pass placeholder image
        im4show1=np.zeros((50,50,3), dtype=np.uint8)
        im4show2=np.zeros((50,50,3), dtype=np.uint8)
        im4show3=np.zeros((50,50,3), dtype=np.uint8)

    else: # Otherwise, use current view
        cur_instance=instance_list().inst_list[instance_list().idx]
        im4show1, im4show2, im4show3=cur_instance.get_view() # Call method to return current image

    # Set up view 1
    fig = plt.imshow(im4show1.astype(np.uint8))
    plt.axis('off')
    f = BytesIO()
    plt.savefig(f, format="png")
    encoded_img1 = base64.b64encode(f.getvalue()).decode('utf-8').replace('\n', '')
    f.close(); plt.close('all')

    # Set up view 2
    fig = plt.imshow(im4show2.astype(np.uint8))
    plt.axis('off')
    f = BytesIO()
    plt.savefig(f, format="png")
    encoded_img2 = base64.b64encode(f.getvalue()).decode('utf-8').replace('\n', '')
    f.close(); plt.close('all')

    # Set up view 3
    fig = plt.imshow(im4show3.astype(np.uint8))
    plt.axis('off')
    f = BytesIO()
    plt.savefig(f, format="png")
    encoded_img3 = base64.b64encode(f.getvalue()).decode('utf-8').replace('\n', '')
    f.close(); plt.close('all')

    dict_data={'ax1': '"data:image/png;base64,%s"' % encoded_img1, 'ax2': '"data:image/png;base64,%s"' % encoded_img2, 'ax3': '"data:image/png;base64,%s"' % encoded_img3,}

    # And here with the JsonResponse you catch in the ajax function in your html triggered by the click of a button
    return make_response(jsonify(dict_data))
    
@login_required
@bp.route('/up_1/', methods=['GET'])
def nav_up1():

    if len(instance_list().inst_list)>0: # No instances yet, pass placeholder image
       # Iterate current slice on active instance
       current_instance=instance_list().inst_list[instance_list().idx]
       idx=current_instance.idx_ax1
       imd=current_instance.imd
       if idx<imd.shape[-1]:
           instance_list().inst_list[instance_list().idx].idx_ax1+=1
    
    return pass_view()
    # return 'pass view'

@login_required
@bp.route('/down_1/', methods=['GET'])
def nav_down1():

    if len(instance_list().inst_list)>0: # No instances yet, pass placeholder image
       # Iterate current slice on active instance
       current_instance=instance_list().inst_list[instance_list().idx]
       idx=current_instance.idx_ax1
       imd=current_instance.imd
       if idx>=0:
           instance_list().inst_list[instance_list().idx].idx_ax1-=1

    return pass_view()
    

@login_required
@bp.route('/up_2/', methods=['GET'])
def nav_up2():

    if len(instance_list().inst_list)>0: # No instances yet, pass placeholder image
       # Iterate current slice on active instance
       current_instance=instance_list().inst_list[instance_list().idx]
       idx=current_instance.idx_ax2
       imd=current_instance.imd
       if idx<imd.shape[0]:
           instance_list().inst_list[instance_list().idx].idx_ax2+=1
    
    return pass_view()
  

@login_required
@bp.route('/down_2/', methods=['GET'])
def nav_down2():

    if len(instance_list().inst_list)>0: # No instances yet, pass placeholder image
       # Iterate current slice on active instance
       current_instance=instance_list().inst_list[instance_list().idx]
       idx=current_instance.idx_ax2
       imd=current_instance.imd
       if idx>=0:
           instance_list().inst_list[instance_list().idx].idx_ax2-=1

    return pass_view()
    

@login_required
@bp.route('/up_3/', methods=['GET'])
def nav_up3():

    if len(instance_list().inst_list)>0: # No instances yet, pass placeholder image
       # Iterate current slice on active instance
       current_instance=instance_list().inst_list[instance_list().idx]
       idx=current_instance.idx_ax3
       imd=current_instance.imd
       if idx<imd.shape[1]:
           instance_list().inst_list[instance_list().idx].idx_ax3+=1
    
    return pass_view()


@login_required
@bp.route('/down_3/', methods=['GET'])
def nav_down3():

    if len(instance_list().inst_list)>0: # No instances yet, pass placeholder image
       # Iterate current slice on active instance
       current_instance=instance_list().inst_list[instance_list().idx]
       idx=current_instance.idx_ax3
       imd=current_instance.imd
       if idx>=0:
           instance_list().inst_list[instance_list().idx].idx_ax3-=1

    return pass_view()
    





@login_required
@bp.route('/update_current_instance/', methods=['POST', 'GET'])
def update_current_instance(): # Updates active instance based on a dropdown menu from the front panel, also needs to update view after wards

    a = request.form.get('new_idx')
    try:
        a=int(a)
    except:
        a=instance_list().idx;
        
    print(a)
    if a<len(instance_list().inst_list) and a>-1: # Only update if the requested indeix fits into the list
        instance_list().idx=a;

    # PASS VIEW TO REFRESH VIEW

    return pass_view()
   



@login_required
@bp.route('/del_current_instance/', methods=['GET'])
def del_current_instance(): # Deletes current instance and changes current instance to latest instance in instance list

    if instance_list().idx>-1: # There are instances in the list
        del instance_list().inst_list[instance_list().idx];
        instance_list().idx=len(instance_list().inst_list)-1; # Set current index to latest instance
        
    else: # No instances left  
        [];

    # PASS VIEW TO REFRESH VIEW

    return pass_view()
   

@login_required
@bp.route('/toggle_seg_map/', methods=['POST', 'GET'])
def toggle_seg_map(): # Takes as input an integer that corresponds to the segmentation class that should either be toggled on or off, depending if it is off or on

    a = request.form.get('class_num')
    try:
        a=int(a)
    except:
        a=[];
    class_num=a;
    # MAKE SURE 0 isnt a part of this]
    pxd=instance_list().inst_list[instance_list().idx].pxd
    pxd_view=instance_list().inst_list[instance_list().idx].pxd_view


    if isinstance(class_num, int):
        if class_num>0:
            # Update seg toggle list and pass to another function
            #print('Class to toggle is ' + str(a))
            #print('Toggle list is ' + str(instance_list().inst_list[instance_list().idx].c_toggle))
            old_toggle=instance_list().inst_list[instance_list().idx].c_toggle[class_num]
            if old_toggle==0:
                 instance_list().inst_list[instance_list().idx].c_toggle[class_num]=1;
            else:
                 instance_list().inst_list[instance_list().idx].c_toggle[class_num]=0;


    # Remake segmap view
    toggle_seg_view()

    # PASS VIEW TO REFRESH VIEW

    return pass_view()
    










