#####################################
# File to house the experimentation
##################################

from krrt.utils import get_file_list, write_file, get_opts
from krrt.utils import experimentation as exp

import os


USAGE = """
    python exp.py <experiment>

     Where <experiment> is one of the following:
        size_time: Compare the runtime / size of ddnnf and c2d compilation.
        bdg_settings: Compare the various settings for the bdg compilation.
        ddnnf_settings: Compare the various settings for the ddnnf compilation.
"""


###################
# Global Settings #
###################

all_domains = ['flat200-479', 'uf200-860', 'blocksworld', 'bmc', 'logistics', 'emptyroom-DRD', 'grid-DRD', 'sortnet-DRD']
#all_domains = ['flat200-479', 'uf200-860', 'blocksworld', 'emptyroom-DRD', 'grid-DRD', 'sortnet-DRD']

TIMEOUT = 1800 # 30min timeout
CORES = 2      # Run on a dual core machine
MEMORY = 1500  # Max of 1.5 gigs RAM



################################
# Runtime and size comparisons #
################################

def test_size_time(domain):

    print "\nTesting domain '%s'." % domain

    problems = get_file_list("exp-input/%s" % domain)
    results_size = {}
    results_time = {}

    print "Doing ddnnf..."

    results_ddnnf = exp.run_experiment(
                    base_command = "./sharpSAT-ddnnf -q",
                    single_arguments = {'problem': problems},
                    time_limit = TIMEOUT,
                    results_dir = "results-%s-ddnnf" % domain,
                    processors = CORES,
                    memory_limit = MEMORY,
                    progress_file = None
                    )

    for result_id in results_ddnnf.get_ids():
        file, size, time = _get_file_size_time_bdg(results_ddnnf[result_id])
        results_size[file] = [size]
        results_time[file] = [time]

    print "\t...done!"
    print "Doing c2d..."

    results_c2d = exp.run_experiment(
                    base_command = "c2d",
                    parameters = {'-in': problems},
                    time_limit = TIMEOUT,
                    results_dir = "results-%s-c2d" % domain,
                    processors = CORES,
                    memory_limit = MEMORY,
                    progress_file = None
                    )

    for result_id in results_c2d.get_ids():
        file, size, time = _get_file_size_time_c2d(results_c2d[result_id])
        results_size[file].append(size)
        results_time[file].append(time)

    print "\t...done!"

    #-- Compile
    file_output = "problem,ddnnf runtime,c2d runtime,ddnnf size,c2d size\n"

    for prob in results_size.keys():
        file_output += "%s,%f,%f,%d,%d\n" % (prob,
                results_time[prob][0], results_time[prob][1],
                results_size[prob][0], results_size[prob][1])

    write_file(domain + '-results.csv', file_output)

    #-- Cleanup
    os.system("rm exp-input/%s/*.nnf" % domain)


def _get_file_size_time_bdg(result):

    file = result.single_args['problem']
    file_name = file.split('/')[-1]
    output = result.output_file

    if result.timed_out:
        return (file_name, -1, result.runtime)
    else:
        size = exp.get_value(output, '.*Compressed Edges: (\d+).*', value_type=int)
        return (file_name, size, result.runtime)

def _get_file_size_time_c2d(result):

    file = result.parameters['-in']
    file_name = file.split('/')[-1]
    output = result.output_file

    if result.timed_out:
        return (file_name, -1, result.runtime)
    else:
        size = exp.get_value(output, '.*nodes and (\d+) edges...done.*', value_type=int)
        return (file_name, size, result.runtime)



######################
# Parameter Analysis #
######################

def test_settings(domain, CMD):

    problems = get_file_list("exp-input/%s" % domain)
    toggles = ['PP', 'CA', 'NCB', 'CC', 'IBCP']

    results = exp.run_experiment(
                    base_command = "%s -q" % CMD,
                    single_arguments = {'problem': problems,
                                        'PP': ['-noPP', ''],
                                        'CA': ['-noCA', ''],
                                        'CC': ['-noCC', ''],
                                        'NCB': ['-noNCB', ''],
                                        'IBCP': ['-noIBCP', '']},
                    time_limit = TIMEOUT,
                    memory_limit = MEMORY,
                    results_dir = "results-%s-settings" % domain,
                    processors = CORES,
                    progress_file = None
                    )

    #-- Compile
    file_output = "%s,problem,size,runtime\n" % ','.join(toggles)

    for result in results.get_ids():
        res = results[result]
        for tog in toggles:
            if '' == res.single_args[tog]:
                file_output += '1,'
            else:
                file_output += '0,'

        file_output += "%s,%d,%f\n" % _get_file_size_time_bdg(res)

    write_file(domain + '-results.csv', file_output)


######################################

opts, flags = get_opts()

did_something = False

if '-domain' in opts:
    all_domains = [opts['-domain']]

if 'size_time' in flags:
    did_something = True

    if not os.path.isdir('size_time_results'):
        os.system('mkdir size_time_results')

    for dom in all_domains:
        test_size_time(dom)
        os.system('mv results-* size_time_results')

    os.system('mv *-results.csv size_time_results/')

if 'bdg_settings' in flags:
    did_something = True

    os.system('mkdir bdg_settings_results')

    for dom in all_domains:
        test_settings(dom, './sharpSAT-bdg')
        os.system('mv results-* bdg_settings_results')

    os.system('mv *-results.csv bdg_settings_results')

if 'ddnnf_settings' in flags:
    did_something = True

    os.system('mkdir ddnnf_settings_results')

    for dom in all_domains:
        test_settings(dom, './sharpSAT-ddnnf')
        os.system('mv results-* ddnnf_settings_results')

    os.system('mv *-results.csv ddnnf_settings_results')

if not did_something:
    print USAGE

