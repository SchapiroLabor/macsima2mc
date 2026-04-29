#public libraries
import argparse
import pathlib
#local scripts
from . import tools
from . import mc_tools
from . import qc
from .templates import macsima_pattern
from .version import __version__




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
    
    parser.add_argument('-v',
                    '--version',
                    dest='version',
                    action='version',
                    version=f"{__version__}"
                    )

    args=parser.parse_args()

    return args
#---END_CLI-BLOCK---#

def main():
    # Get arguments
    args = get_args()

    # Assign arguments to variables
    input = args.input
    output = args.output
    ref = args.reference_marker
    basicpy_corr = args.illumination_correction
    out_folder_name = args.output_subdir

    # Extract acquisition info of the cycle from file name,e.g. rack,well,markers,filters, etc.
    cycle_info = tools.cycle_info(input, macsima_pattern(version=2), ref_marker= ref)
    
    # Extract and append ome metadata info contained in each file
    cycle_info = tools.append_metadata( cycle_info )
    
    # Create stack
    cycle_number=int(cycle_info['cycle'].unique()[0])
    if args.only_qc_file:
        pass
    else:
        output_dirs = tools.create_stack(cycle_info,
                                     output,
                                     ref_marker=ref,
                                     hi_exp=args.hi_exposure_only,
                                     ill_corr=basicpy_corr,
                                     out_folder=out_folder_name)
        # Save markers file in each output directory
        for path in output_dirs:
            mc_tools.write_markers_file(path,args.remove_reference_marker)

    # Calculate and append ome metadata info contained in each file
    if (args.qc_metrics or args.only_qc_file) :
        cycle_info=qc.append_qc(cycle_info)

    if args.write_table:
        qc_output_dir=output / "cycle_info"
        qc_output_dir.mkdir(parents=True, exist_ok=True)
        cycle_info.to_csv( qc_output_dir / 'cycle_{c}.csv'.format( c=f'{ cycle_number:03d}' ), index=False )
    

if __name__ == '__main__':
    main()
