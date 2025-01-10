import numpy as np
import pandas as pd


def any_ref(mf_tuple,
            ref_marker='DAPI'):
    """
    This function checks if the reference marker is present in the mf_tuple.
    Args:
        mf_tuple (tuple): tuple with the markers and filters
        ref_marker (str): reference marker used for registration
    Returns:
        bool: True if the reference marker is present in the mf_tuple, False otherwise.
    """

    exist_ref = False
    for m in mf_tuple:
        if m[0] == ref_marker:
            exist_ref = True
            break
    return exist_ref

def miss_channel(chann_index,chans_meta,conformed_markers):
    
    if chans_meta[ chann_index ].size:
        pass
    else:

        ref_index=np.argwhere([meta.size > 0 for meta in chans_meta ]).flatten()[0]
        chann_meta=chans_meta[ ref_index ]
        edit_feats={'marker':conformed_markers[ chann_index ][0], 
                    'filter':conformed_markers[ chann_index ][1]}
                    #'exposure?':}
                    #how are conformed markers formed?
    return True



def at_roi(grouped,dimensions,ref_marker):
    #for dimensions is expected that the last element of the list is the exposure_level
    rows=[]
    for index,frame in grouped:
        marker_filter_map = list( frame.groupby(["marker","filter"]).indices.keys() )
        ref_exists=any_ref(marker_filter_map,ref_marker)
        subst_exp_level=index[-1]
        rows.append( list(index) + [ ref_exists, subst_exp_level ] )

    df=pd.DataFrame(rows,columns=dimensions+['ref_marker','aux_exp_level'])

    frames=[]
    for index,frame in df.groupby(dimensions[:-1]):
        substitute=frame.loc[ frame['ref_marker']==True,'exposure_level'].max()
        frame['aux_exp_level']=frame['aux_exp_level'].where(frame['ref_marker'],substitute)
        frames.append(frame)

    return pd.concat(frames)

def at_tile(group,marker_filter_map):
    rows=[]
    for tile_id,frame in group.groupby(['tile']):
        aux_array = [   frame.loc[ (frame['marker']==marker) & (frame['filter']==filt)].size
                        for marker, filt in marker_filter_map 
                    ]

        aux_array =np.array(aux_array)==0
        missing_channel=np.any(aux_array)

        if missing_channel:
            channel_indices=np.argwhere(aux_array).flatten()
            #Each missing (marker,filter) pair will be separated by a colon ":", i.e. marker1,filter1:marker2,filter2
            channel= ':'.join( [ ','.join(marker_filter_map[i]) for i in channel_indices] )
        else:
            channel=''
            
        qc_data=[tile_id[0],missing_channel,channel,tile_id[0]]
        cols=['tile','missing_ch','channels','aux_tile']
        rows.append(   qc_data )

    df=pd.DataFrame(rows,columns=cols)
    auxiliary_tile_index=df.loc[df['missing_ch']==False ][['tile']].values[0]
    df.loc[ df['missing_ch']==True, ['aux_tile']]=auxiliary_tile_index
    
    return df 









