import tools
from templates import macsima_pattern
import CLI
import mc_tools

def main():
    # Get arguments
    args = CLI.get_args()

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
    output_dirs = tools.create_stack(cycle_info,
                                     output,
                                     ref_marker=ref,
                                     hi_exp=args.hi_exposure_only,
                                     ill_corr=basicpy_corr,
                                     out_folder=out_folder_name)
    # Save markers file in each output directory
    for path in output_dirs:
        mc_tools.write_markers_file(path,args.remove_reference_marker)

    cycle_number=int(cycle_info['cycle'].unique()[0])
    message_1='staging for cycle {c} is done'.format( c=f'{ cycle_number:03d}' )
    print(message_1)
    # Calculate and append ome metadata info contained in each file
    if args.qc_metrics:
        import qc
        print("image qc is being calculated")
        cycle_info=qc.append_qc(cycle_info)

    if args.write_table:
        qc_output_dir=output / "cycle_info"
        qc_output_dir.mkdir(parents=True, exist_ok=True)
        cycle_info.to_csv( qc_output_dir / 'cycle_{c}.csv'.format( c=f'{ cycle_number:03d}' ), index=False )
    
    
        

if __name__ == '__main__':
    main()
