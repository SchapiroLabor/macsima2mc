import argparse
import pathlib

#---CLI-BLOCK---#
def get_args():
    """
    This function parses the command line arguments and returns them as a namespace object.

    returns: namespace object with the arguments.
    """
    parser=argparse.ArgumentParser()

    #Mandatory arguments
    parser.add_argument('-i',
                    '--input',
                    required=True,
                    type=pathlib.Path,
                    help='Path to the cycle folder'
                    )

    parser.add_argument('-o',
                    '--output',
                    required=True,
                    type=pathlib.Path,
                    help='Path where the stacks will be saved. If directory does not exist it will be created.'
                    )
    #Optional arguments
    parser.add_argument('-rm',
                    '--reference_marker',
                    default='DAPI',
                    help='string specifying the name of the reference marker'
                    )
    
    parser.add_argument('-osd',
                    '--output_subdir',
                    default='raw',
                    help='string specifying the name of the subfolder in which the staged images will be saved'
                    )

    parser.add_argument('-ic',
                    '--illumination_correction',
                    action='store_true',
                    help='Applies illumination correction to all tiles, the illumination profiles are created with basicpy'
                    )


    parser.add_argument('-he',
                    '--hi_exposure_only',
                    action='store_true',
                    help='Activate this flag to extract only the set of images with the highest exposure time.'
                    )

    parser.add_argument('-rr',
                    '--remove_reference_marker',
                    action='store_true',
                    help='It will mark the removal of the reference markers in the markers.csv file except for the first cycle.  Use this when you \
                        dont want to keep e.g. the DAPI images of the other cycles.'
                    )
    
    parser.add_argument('-qc',
                    '--qc_metrics',
                    action='store_true',
                    help='measure features of contrast, intensity and sharpness of each image'
                    )
    
    parser.add_argument('-oqc',
                    '--only_qc_file',
                    action='store_true',
                    help='skips the stacking of the tiles and only calculates the qc table. Still flag -wt is required to write the table. '
                    )
    
    parser.add_argument('-wt',
                    '--write_table',
                    action='store_true',
                    help='writes a table in --output/cycle_info. Content of table is acquisition parameters, metadata and, if enabled, qc metrics of each tile'
                    )

    args=parser.parse_args()

    return args
#---END_CLI-BLOCK---#



