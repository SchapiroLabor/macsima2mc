from macsima2mc.templates import info_dic
import re
import pandas as pd
import tifffile as tifff
from bs4 import BeautifulSoup
import numpy as np
from pathlib import Path
import macsima2mc.ome_writer as ome_writer
import macsima2mc.exceptions as expt
import macsima2mc.illumination_corr as illumination_corr


def merge_dicts(list_of_dicts):
    """
    This function merges a list of dictionaries into a single dictionary where the values are stored in lists.
    Args:
        list_of_dicts (list): list of dictionaries with common keys
    Returns:
        merged_dict (dict): dictionary with the values stored in lists
    """
    merged_dict = {}
    for d in list_of_dicts:
        for key, value in d.items():
            if key in merged_dict:
                merged_dict[key].append(value)
            else:
                merged_dict[key] = [value]
    return merged_dict

def extract_values(target_pattern,
                   strings,
                   number_cast=True):
    """
    This function extracts the values from a list of strings using a regular expression pattern.
    Args:
        target_pattern (str): regular expression pattern
        strings (list): list of strings to extract the values from
        number_cast (bool): if True, the extracted values are cast to integers
    Returns:
        list: list of extracted values
    """
    return [
        (int(m.group(1)) if number_cast else m.group(1))
        if (m := re.search(target_pattern, s))
        else None
        for s in strings
    ]


def extract_metadata(tile_abs_path):
    """
    This function extracts the metadata from a tiff file using the ome-xml format.
    Args:
        tile_abs_path (Path): full path to the tiff file
    Returns:
        dict: dictionary with the metadata extracted from the tiff file using the ome-xml format.
    """
    with tifff.TiffFile(tile_abs_path) as tif:
            metadata = tif.ome_metadata

    ome = BeautifulSoup(metadata, "xml")
    return {
            "position_x": float(ome.StageLabel["X"]),
            "position_y": float(ome.StageLabel["Y"]),
            "position_x_unit": ome.StageLabel["XUnit"],
            "position_y_unit": ome.StageLabel["YUnit"],
            "physical_size_x": float(ome.Pixels["PhysicalSizeX"]),
            "physical_size_x_unit": ome.Pixels["PhysicalSizeXUnit"],
            "physical_size_y": float(ome.Pixels["PhysicalSizeY"]),
            "physical_size_y_unit": ome.Pixels["PhysicalSizeXUnit"],
            "size_x":ome.Pixels["SizeX"],
            "size_y":ome.Pixels["SizeY"],
            "type": ome.Pixels["Type"],#bit_depth
            "significant_bits": int(ome.Pixels["SignificantBits"]),
            "emission_wavelenght":ome.Channel["EmissionWavelength"],
            "excitation_wavelenght":ome.Channel["ExcitationWavelength"],
            "emission_wavelenght_unit":ome.Channel["EmissionWavelengthUnit"],
            "excitation_wavelenght_unit":ome.Channel["ExcitationWavelengthUnit"]
            }

def cycle_info(cycle_path,
               platform_pattern,
               ref_marker='DAPI'):
    """
    This function reads the images produced by the MACSima device and returns the acquisition information
    specified in the image name.

    Args:
        cycle_path (Path): full path to the cycle folder
        platform_pattern (dict): dictionary with the pattern to search in the image name.
        ref_marker (str): marker of reference used for registration

    Returns:
        df (pd.DataFrame): dataframe with the acquisition information, ROI, rack, exposure time etc.
    """

    full_image_paths = list(cycle_path.glob("*.tif"))
    file_names = [x.name for x in full_image_paths]

    info=info_dic(platform_pattern)

    info['full_path'] = full_image_paths
    info['img_name'] = file_names

    for feat,value in platform_pattern.items():
        info[feat]=extract_values(target_pattern=value, strings=file_names,number_cast=False)

    df = pd.DataFrame(info)
    df.loc[df['filter']==ref_marker,'marker'] = ref_marker

    df.insert(loc=df.shape[1], column="exposure_level", value=0)
    df["exposure_time"] = df["exposure_time"].astype(float)
    df["exposure_level"] = ( df.groupby(["source","marker","filter"])["exposure_time"].rank(method="dense")).astype(int)

    return df


def append_metadata(cycle_info_df):
    """
    This function appends the metadata extracted from the tiff files to the cycle_info dataframe.
    Args:
        cycle_info_df (pd.DataFrame): dataframe with the acquisition information
    Returns:
        pd.DataFrame: dataframe with the metadata appended to the cycle_info dataframe as new columns.
    """
    meta_feats=list( map(extract_metadata, cycle_info_df['full_path'].values) )

    for key, val in merge_dicts(meta_feats).items():
        cycle_info_df.insert(loc=cycle_info_df.shape[1], column=key, value=val)

    return cycle_info_df


def conform_markers(mf_tuple,
                    ref_marker='DAPI'):
    """
    This function reorders the markers in the mf_tuple so that the reference marker is the first element.
    Args:
        mf_tuple (tuple): tuple with the markers and filters
        ref_marker (str): reference marker used for registration
    Returns:
        list: list with the markers and filters reordered so that the reference marker is the first element.
    """

    markers = [tup for tup in mf_tuple if tup[0]!=ref_marker]
    markers.insert(0,(ref_marker,ref_marker))
    return markers

def init_stack(group,
               no_of_channels):
    """
    This function initializes the stack array with the dimensions of the tiles.
    Args:
        ref_tile_index (int): index of the reference tile
        groupby_obj (pd.DataFrame.groupby): groupby object with the tiles
        marker_filter_map (list): list with the markers and filters
    Returns:
        np.ndarray: array with the dimensions of the stack array (depth, height, width) and the dtype of the
        reference tile.
    """
    aux_array=[ group['size_x'].unique() , group['size_y'].unique(), group['type'].unique() ]
    check_array=np.array( [ len(element) for element in aux_array ] )
    if np.any(check_array>1):
        print("Warning:tiles of these acquisition have no unique value for the following columns: xy-size or data type")
    width, height, data_type = [ element[0] for element in aux_array  ]
    total_tiles = group['tile'].nunique()
    depth = total_tiles * no_of_channels
    
    stack = np.zeros( (depth,int(height),int(width)), dtype=data_type)

    return stack

def cast_stack_name(cycle_no,
                    acq_group_index,
                    marker_filter_map):
    """
    This function creates the name of the stack file.
    Args:
        cycle_no (int): cycle number
        acq_group_index (tuple): tuple with the acquisition information
        marker_filter_map (list): list with the markers and filters
    Returns:
        str: name of the stack file.
    """
    markers='__'.join([element[0] for element in marker_filter_map ])
    filters='__'.join([element[1] for element in marker_filter_map ])
    cycle_no = int(cycle_no)

    c = f'{cycle_no:03d}'
    s = acq_group_index[0]
    e = acq_group_index[4]
    r = acq_group_index[1]
    w = acq_group_index[2]
    roi = acq_group_index[3]
    m = markers
    f = filters
    img_format = 'ome.tiff'

    # Nicer way to format strings
    name = f'cycle-{c}-src-{s}-rack-{r}-well-{w}-roi-{roi}-exp-{e}-markers-{m}-filters-{f}.{img_format}'

    return name


def cast_outdir_name(tup):
    """
    This function creates the name of the output directory.
    Args:
        tup (tuple): tuple with the acquisition information
    Returns:
        str: name of the output directory.
    """
    r = tup[1]
    w = tup[2]
    roi = tup[3]
    e = tup[4]

    # Nicer way to format strings
    name = f'rack-{r}-well-{w}-roi-{roi}-exp-{e}'

    return name


def outputs_dic():
    """
    This function initializes the dictionary used to store the outputs of the create_stack function.
    Returns:
        dict: dictionary with the keys 'index', 'array', 'full_path', 'ome' and empty lists as values
    """

    out={
        'index':[],
        'array':[],
        'full_path':[],
        'ome':[],
        }

    return out


def select_by_exposure(list_indices,
                       exp_index,
                       target='max'):
    """
    This function selects the indices with the maximum or minimum exposure time.
    Args:
        list_indices (list): list of indices
        exp_index (int): index of the exposure time
        target (str): 'max' or 'min'
    Returns:
        list: list of selected indices
    """
    selected_indices = []
    df_aux = pd.DataFrame( np.row_stack(list_indices) )
    group_by_indices = np.setdiff1d( range(0, len(list_indices[0]) ), exp_index ).tolist()

    for key, frame in df_aux.groupby( group_by_indices ):
        if target == 'max':
            selected_indices.append( key + ( int(frame[exp_index].max() ), ) )
        elif target == 'min':
            selected_indices.append( key + ( int( frame[exp_index].min()), ) )

    return selected_indices

def append_reference(frame,frame_index,groups,aux_reference_exp_level,ref_marker_name):

    aux_index = list(frame_index)
    aux_index[-1] = aux_reference_exp_level
    aux_index = tuple(aux_index)
    aux_group = groups.get_group(aux_index)
    aux_group = aux_group.loc[aux_group['marker']==ref_marker_name]
    frame_ = pd.concat([frame, aux_group])
    return frame_

def append_missing_channels(group, exception_table ):
    #exception_table.cols=["tile","missing_ch","channels","aux_tile"]
    tiles=group.groupby(['tile'])
    incomplete_tiles=exception_table.loc[exception_table['missing_ch']==True ] 
    add_tiles=[]
    for row in incomplete_tiles.itertuples(index=False):
        aux_tile_df=tiles.get_group( (row.aux_tile,) )
        missing_markers=[ tuple(element.split(',')) for element in row.channels.split(':') ]
        for marker, filt in missing_markers:
            df=aux_tile_df.loc[ (aux_tile_df['marker']==marker) & (aux_tile_df['filter']==filt) ]
            #df['tile']=row.tile
            df.loc[:,'tile']=row.tile
            add_tiles.append(df)

    aux_group=pd.concat(add_tiles)
    aux_group[ ['full_path','img_name'] ]='missing'
    group_=pd.concat([group,aux_group])

    return group_

def conform_acquisition_group(group,conformed_markers):
    aux=[]
    for tile_id,frame in group.groupby(['tile']):
        aux.extend([ frame.loc[ (frame['marker']==marker) & (frame['filter']==filt)] for marker, filt in conformed_markers ]) 
    group_conformed=pd.concat(aux)

    return group_conformed



def create_stack(cycle_info_df,
                 output_dir,
                 ref_marker='DAPI',
                 hi_exp=False,
                 ill_corr=False,
                 out_folder='raw',
                 extended_outputs=False):
    """
    This function creates the stack of images from the cycle_info dataframe.
    Args:
        cycle_info_df (pd.DataFrame): dataframe with the acquisition information
        output_dir (Path): full path to the output directory
        ref_marker (str): reference marker used for registration
        hi_exp (bool): if True, only the tiles with the highest exposure time are selected
        ill_corr (bool): if True, the illumination correction is applied
        out_folder (str): name of the output folder
        extended_outputs (bool): if True, the function returns a dictionary with the stack arrays, full paths and ome-xml metadata
    Returns:
        np.ndarray or list: stack array or list with the full paths of the stack files created in the output directory.
    """

    if extended_outputs:
        out = outputs_dic()
    else:
        out = {'output_paths':[]}

    #'exposure_level' should always be the last element of the dimensions list
    dimensions=['source','rack','well','roi','exposure_level']
    
    acq_group = cycle_info_df.groupby(dimensions)
    acq_index = list( acq_group.indices.keys() )
    expt_matrix_roi=expt.at_roi(acq_group,dimensions,ref_marker).groupby(dimensions)#exceptions matrix

    if hi_exp:
        exp_level_index=np.argwhere( np.asarray(dimensions)=='exposure_level' ).flatten()[0]
        acq_index = select_by_exposure(acq_index,exp_level_index,target='max')

    for index in acq_index:
        stack_output_dir = output_dir / cast_outdir_name(index) / out_folder
        stack_output_dir.mkdir(parents=True, exist_ok=True)
        group = acq_group.get_group(index)

        exist_ref, aux_reference= expt_matrix_roi.get_group(index )[ ['ref_marker','aux_exp_level'] ].iloc[0].values
        if not exist_ref:
            group=append_reference(group, index, acq_group, aux_reference, ref_marker)
        #extract list of unique pairs (marker,filter)
        marker_filter_map=group[['marker','filter']].value_counts().index.values
        #conform the pairs (marker,filter) as to have the reference marker in the first place (1st channel) of the list 
        conformed_markers = conform_markers(marker_filter_map, ref_marker)
        
        expt_matrix_tiles=expt.at_tile(group,conformed_markers)
        if expt_matrix_tiles['missing_ch'].any():
            group=append_missing_channels(group,expt_matrix_tiles)

        stack = init_stack(group, len( conformed_markers))
        conformed_group=conform_acquisition_group(group,conformed_markers)
        #ome = ome_writer.create_ome(group, conformed_markers)
        ome = ome_writer.create_ome(conformed_group, conformed_markers)
        counter = 0
        groups_of_tiles = conformed_group.groupby(['tile'])
        #for tile_no, frame in groups_of_tiles:
        #    for marker, filter in conformed_markers:
        #        target_path = frame.loc[ (frame['marker']==marker) & (frame['filter']==filter) ].full_path.values[0]
        #       stack[counter,:,:] = tifff.imread(Path(target_path))
        #      counter += 1
        for tile_id,frame in groups_of_tiles:
            for img_path in frame['full_path'].values:
                try:
                    stack[counter,:,:] = tifff.imread(Path(img_path))
                except:
                    if img_path=='missing':
                        pass
                counter += 1
                


        stack_name = cast_stack_name(frame.cycle.iloc[0], index, conformed_markers)

        if ill_corr:
            tag = 'corr_'
            no_of_channels = len(conformed_markers)
            stack = illumination_corr.apply_corr(stack,no_of_channels)
        else:
            tag = ''

        stack_file_path = stack_output_dir / f'{tag}{stack_name}'

        if extended_outputs:
            out['index'].append(index)
            out['array'].append(stack)
            out['full_path'].append(stack_file_path)
            out['ome'].append(ome)
        else:
            out['output_paths'].append(stack_output_dir)
            tifff.imwrite( stack_file_path , stack, photometric='minisblack' )
            ome,ome_xml = ome_writer.create_ome(group, conformed_markers)
            tifff.tiffcomment(stack_file_path, ome_xml)
        
    if extended_outputs:
        return out
    else:
        return np.unique( out['output_paths'] )
