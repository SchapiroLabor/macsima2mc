import pandas as pd
from skimage.measure import blur_effect
from tifffile import imread
from tools import merge_dicts
import numpy as np
from multiprocessing import Pool


def contrast(img):


    #the dictionary below gives the arguments of the np.roll function to
    #shift the array in the elemental angle specified by the dictionary keys

    angles={0  : [(-1,0),(1,0)],
            45 : [(-1,1),(1,0)],
            90 : [(0,1),(0,0)],
            135: [(1,1),(1,0)],
            180: [(1,0),(1,0)],
            225: [(-1,1),(0,1)],
            270: [(0,-1),(0,0)],
            315: [(-1,-1),(0,1)]
            }
    diff=np.zeros(img.shape)
    for key,val in angles.items():
        diff+= ( img-np.roll(img,val[0],axis=val[1]) )**2

    contrast_arr=np.sqrt(diff)
    med=np.median(contrast_arr)
    iqr=np.percentile(contrast_arr, 75)-np.percentile(contrast_arr, 25)
    
    return med,iqr
    



def calculate_img_qc(img_path):
    """
    This function extracts the metadata from a tiff file using the ome-xml format.
    Args:
        img_path (Path): full path to the tiff file
    Returns:
        dict: dictionary with qc_metrics for the input file (img_path)
    """
    img=imread(img_path)
    intensity_med=np.median(img)
    intensity_iqr=np.percentile(img, 75)-np.percentile(img, 25)
    contrast_med,contrast_iqr=contrast(img)
    blur=blur_effect(img)

    return {
            "intensity_median" : intensity_med ,
            "intensity_iqr"    : intensity_iqr ,
            "contrast_median"  :contrast_med,
            "contrast_iqr"     :contrast_iqr,
            "blur"             :blur
            }



def append_qc(cycle_info_df,append=False):

    with Pool() as pool:
        qc_feats=pool.map(calculate_img_qc, cycle_info_df['full_path'].values)

    for key, val in merge_dicts(qc_feats).items():
        cycle_info_df.insert(loc=cycle_info_df.shape[1], column=key, value=val)
        
    return cycle_info_df








