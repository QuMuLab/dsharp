#####################################
# File to house the validation
##################################

from kr.utils import get_file_list, write_file
from kr.utils import experimentation as exp

import os

optArr1 = ['', ' -noPP']
optArr2 = ['', ' -noCA']
optArr3 = ['', ' -noNCB']
optArr4 = ['', ' -noCC']
optArr5 = ['', ' -noIBCP']

options = []

for opt1 in optArr1:
    for opt2 in optArr2:
        for opt3 in optArr3:
            for opt4 in optArr4:
                for opt5 in optArr5:
                    options.append(opt1 + opt2 + opt3 + opt4 + opt5)
                    

def validate(dir_loc):
    domain = dir_loc.split('/')[-1]

    problems = get_file_list(dir_loc)
    
    errors = ['-{ Errors }-']
    
    for prob in problems:
        for opt in options:
            print "Problem: " + prob
            print "Settings: " + opt
            print "-{ Solving Problem }-"
            os.system('./sharpSAT-ddnnf -q' + opt + ' -t 300 -Fbdg graph.out ' + prob)
            
            print "-{ Verifying d-DNNF }-"
            os.system('python src/extra/utils.py confirm-ddnnf -ddnnf graph.out -cnf ' + prob + ' > output')
            
            # Get the timing
            if not exp.match_value('output', '.*Implicants satisfy theory:  True.*'):
                errors.append("Problem: " + prob + "\nSettings: " + opt + "\n")
        
    
    write_file('errors.csv', errors)
    os.system('rm graph.out output')
        
validate('exp-testing')
