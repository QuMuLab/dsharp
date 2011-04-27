###########################################
# General utils for Implicant Search
######################################
import os
import sys
import time

from kr.sat.CNF import *
from kr.sat.Dimacs import *
from kr.sat.DPLL import unit_prop
from kr.utils import load_CSV, save_CSV, write_file, read_file

#from pylab import scatter, plot, xlabel, ylabel, title, show
#from scipy.stats import f_oneway, ttest_ind as ttest
#from numpy import corrcoef, mean, std, max, array
#from random import randint

USAGE_STRING = "\n\
Usage: python utils.py <command> -<option> <argument> -<option> <argument> ... <FLAG> <FLAG> ...\n\n\
    Where commands are:\n\n\
      confirm-ddnnf:\n\
          -cnf   <cnf file>\n\
          -ddnnf <d-DNNF dot file>\n\n\
      bdg-to-ddnnf:\n\
          -bdg   <bdg dot file>\n\
          -ddnnf <d-DNNF dot file>\n\
          -cnf   <cnf file>\n\n\
        "

###############################
# Convert from BDG -> d-DNNF
############################
def bdg_to_ddnnf(bdgFile, cnfFile, ddnnfFile):
    #--- Get the bdg file
    print "Reading the backdoor graph..."
    nodes, edges, lookup = _read_dot_graph(bdgFile)
    
    print "Performing AND-OR validation...",
    print _and_or_validate(nodes, edges, lookup, 'root')
    
    print "Writing the first read-in to file..."
    _write_dot_graph(nodes, edges, "cgraph.out")
    
    #--- Get the cnf
    print "Parsing the cnf file..."
    theory = parseFile(cnfFile)
    
    #--- Perform the propagation on all of the AND nodes
    print "Propagating the backdoor graph AND nodes..."
    if len(nodes) > 1:
        _prop_graph(nodes, edges, lookup, 'root', None, theory)
    
    #--- Write the d-DNNF file
    print "Writing the resulting d-DNNF graph to file..."
    _write_dot_graph(nodes, edges, ddnnfFile)


def _and_or_validate(nodes, edges, lookup, node):
    if node not in ['AND', 'OR']:
        return True
    
    for child in edges[node]:
        if nodes[node] == nodes[child]:
            return False
        
        if not _and_or_validate(nodes, edges, lookup, child):
            return False
    
    return True

def _prop_graph(nodes, edges, lookup, node, parent, theory):
    #--- If the node is a literal, it means we've reached it from an OR node.
    #     In this case, we check to see if it causes propagation, and then add
    #     an AND node with the literal (and it's propagated literals) to the
    #     graph.
    if nodes[node] not in ['AND', 'OR']:
        origUnit = theory.getUnitClauses()
        
        #--- Add the new literal
        newTheory = theory.copy()
        if '-' in nodes[node]:
            ch_sign = -1
        else:
            ch_sign = 1
                
        ch_num = int(nodes[node]) * ch_sign
        newTheory.addClause(Clause([Literal(ch_num, ch_sign)]))
        
        #--- Unit Prop
        unit_prop(newTheory)
        
        #--- Find the newly prop'd literals
        newUnit = newTheory.getUnitClauses()
        deltaUnit = set(newUnit) - set(origUnit)
        
        
        #--- If there /are/ prop'd literals (ie more than just the single literal),
        #     then we add an AND node with the deltaUnit literals as children.
        if len(deltaUnit) > 1:
            #-- Remove the old edge link to the literal
            edges[parent].remove(node)
            
            #-- Create a new AND node
            if '-' == nodes[node][0]:
                and_id = 'andN' + nodes[node][1:] + '_' + parent + '_' + node
            else:
                and_id = 'and' + nodes[node] + '_' + parent + '_' + node
                
            nodes[and_id] = 'AND'
            edges[parent].append(and_id)
            edges[and_id] = []
            
            #-- Add the newly propagated literals to the and node
            for newLit in deltaUnit:
                lit_name = str(newLit.literals[0])
                
                if lit_name not in lookup:
                    if '-' == lit_name[0]:
                        lit_id = 'pN' + lit_name[1:]
                    else:
                        lit_id = 'p' + lit_name
                        
                    nodes[lit_id] = lit_name
                    lookup[lit_name] = lit_id
                
                edges[and_id].append(lookup[lit_name])
        
        return
    
    #--- If it's an OR node, then we just pass it down to the children unmodified
    if 'OR' == nodes[node]:
        #- Note: We do this array copy since the literal children of OR nodes
        #         could try and remove the links.
        children = [item for item in edges[node]]
        for child in children:
            _prop_graph(nodes, edges, lookup, child, node, theory)
        
        return
    
    #--- Finally deal with the AND node
    origUnit = theory.getUnitClauses()
    newTheory = theory.copy()
    
    #-- Add all of the literals on this and node to the theory
    for child in edges[node]:
        if nodes[child] not in ['AND', 'OR']:
            if '-' in nodes[child]:
                ch_sign = -1
            else:
                ch_sign = 1
                
            ch_num = int(nodes[child]) * ch_sign
            
            newTheory.addClause(Clause([Literal(ch_num, ch_sign)]))
    
    #-- Perform unitprop
    unit_prop(newTheory)
    
    #-- Find the newly propagated literals
    newUnit = newTheory.getUnitClauses()
    deltaUnit = set(newUnit) - set(origUnit)
    
    #-- Add the newly propagated literals to the and node
    for newLit in deltaUnit:
        lit_name = str(newLit.literals[0])
        
        if lit_name not in lookup:
            if '-' == lit_name[0]:
                lit_id = 'pN' + lit_name[1:]
            else:
                lit_id = 'p' + lit_name
                
            nodes[lit_id] = lit_name
            lookup[lit_name] = lit_id
        
        if lookup[lit_name] not in edges[node]:
            edges[node].append(lookup[lit_name])
    
    #-- Finally recurse on the non-literal children of AND node
    for child in edges[node]:
        if 'OR' == nodes[child]:
            _prop_graph(nodes, edges, lookup, child, node, newTheory)

    
    

def _read_dot_graph(file_name):
    nodes = {}
    edges = {}
    dups = {}
    lits = {}
    
    lines = read_file(file_name)
    
    #--- First line is boiler plate
    lines.pop(0)
    
    #--- Grab all of the nodes
    while '>' not in lines[0]:
        node_text = lines.pop(0)
        
        #-- Check if we have an unsat graph
        if '}' in node_text:
            return (nodes, edges, lits)
        
        node_id = node_text.split(' ')[0]
        node_val = node_text.split('"')[1]
        
        if node_val not in ['AND', 'OR']:
            if node_val in lits:
                dups[node_id] = lits[node_val]
            else:
                lits[node_val] = node_id
                nodes[node_id] = node_val
        
        else:
            nodes[node_id] = node_val
        
    
    #--- Grapb all of the edges
    while '}' not in lines[0]:
        edge_text = lines.pop(0)
        edge_from = edge_text.split()[0]
        edge_to = edge_text.split()[2][:-1]
        
        if edge_to in dups:
            edge_to = dups[edge_to]
        
        if edge_from in edges:
            if edge_to not in edges[edge_from]:
                edges[edge_from].append(edge_to)
        else:
            edges[edge_from] = [edge_to]
    
    return (nodes, edges, lits)


def _write_dot_graph(nodes, edges, file_name):
    output = 'digraph backdoorgraph {\n'
    
    for n in nodes.keys():
        output += n + ' [label="' + nodes[n] + '"];\n'
    
    for e_from in edges.keys():
        for e_to in edges[e_from]:
            output += e_from + ' -> ' + e_to + ';\n'
    
    output += '}\n'
    
    write_file(file_name, output)
        
    

########################
# Validate the d-DNNF
#####################
def validate_ddnnf(ddnnfFile, cnfFile):
    #--- Get the ddnnf file
    nodes, edges, lookup = _read_dot_graph(ddnnfFile)
    
    #--- Check for the UNSAT ddnnf
    if 1 == len(nodes.keys()) and nodes['root'] == 'F':
        print "Cannot validate the UNSAT d-DNNF."
        return
    
    #--- Get all of the implicants from the d-DNNF
    implicants = _get_implicants(nodes, edges, 'root')
    
    #--- Save into a temporary file
    saveCSV(implicants, 'implicants.tmp')
    
    #--- Confirm the validity of the implicants
    confirmImplicants(cnfFile, 'implicants.tmp')
    
    #--- Cleanup
    os.system('rm implicants.tmp')


def _get_implicants(nodes, edges, node):
    # Base case is the literal
    if nodes[node] not in ['AND', 'OR']:
        return [[nodes[node]]]
    
    # If the node is an OR, we add the combination of the children
    if 'OR' == nodes[node]:
        allImplicants = []
        for child in edges[node]:
            allImplicants += _get_implicants(nodes, edges, child)
        
        return allImplicants
    
    # If the node is an AND, we cross product all of the children
    if 'AND' == nodes[node]:
        # Set the running implicants as the first one
        allImplicants = _get_implicants(nodes, edges, edges[node][0])
        
        for child in edges[node][1:]:
            childImplicants = _get_implicants(nodes, edges, child)
            combinedImplicants = []
            for i in allImplicants:
                for j in childImplicants:
                    combinedImplicants.append(i + j)
            
            allImplicants = combinedImplicants
        
        return allImplicants
    
    print "Invalid node: " + node + "(" + nodes[node] + ")"


#######################
# Confirm Implicants
####################

def confirmImplicants(sourceFile, implicantFile):
    # Get the theory
    theory = parseFile(sourceFile)
    
    # Get the implicants
    f = open(implicantFile, 'r')
    file_lines = f.readlines()
    f.close()
    
    implicants = []
    for line in file_lines:
        implicants.append(line.rstrip('\n').split(','))
    
    confirmed = True
    badImplicants = []
    
    # For each clause, every implicant should satisfy it
    for cls in theory.clauses:
        if validClause(cls):
            for imp in implicants:
                if not checkImp(cls, imp):
                    confirmed = False
                    badImplicants.append((imp, cls))
    
    
    print "Implicants satisfy theory: ", str(confirmed)
    if not confirmed:
        print "Bad Implicants:"
        print badImplicants
    
def validClause(cls):
    for lit in cls.literals:
        num = lit.sign * lit.num
        for lit2 in cls.literals:
            num2 = lit2.sign * lit2.num * - 1
            if num == num2:
                return False
    
    return True

def checkImp(cls, imp):
    for lit1 in cls.literals:
        for lit2 in imp:
            if (lit1.sign * lit1.num) == int(lit2):
                return True
    
    return False




#######################
# Anova Test
####################

#  F_oneway
#
#      Performs a 1-way ANOVA, returning an F-value and probability given
#      any number of groups.  From Heiman, pp.394-7.
#
#      Usage:   F_oneway(*lists)    where *lists is any number of lists, one per
#                                        treatment group
#      Returns: F value, one-tailed p-value

def anova_test(infile):
    #--- Load the data
    data = loadCSV(infile)
    
    #--- Get rid of the header line
    data.pop(0)
    
    #--- Collect the stats
    arrays = []
    for i in range(32):
        arrays.append([])
    
    for line in data:
        (file, PP, CA, NCB, CC, IBCP, numVars, numClauses, numImplicants, numSolutions, impCacheSize, cacheHits, runtime) = line
        arrays[get_code_index(PP, CA, NCB, CC, IBCP)].append(float(runtime))
    
    #--- Calculate the value
    (fval, prob) = f_oneway(*arrays)
    
    print "f-value: ", fval
    print "probability: ", prob

def get_code_index(PP, CA, NCB, CC, IBCP):
    return (2**4 * int(PP)) + (2**3 * int(CA)) + (2**2 * int(NCB)) + (2**1 * int(CC)) + (2**0 * int(IBCP))


#######################
# Correlation Test
####################

def correlation_test(srcFile, dstFile):
    #--- Load the data
    data1 = loadCSV(srcFile)
    data2 = loadCSV(dstFile)
    
    #--- Get rid of the header line
    data1.pop(0)
    data2.pop(0)
    
    if len(data1) != len(data2):
        print "Error: src has ", len(data1), " lines and dst has ", len(data2), " lines."
        os._exit(1)
        
    #--- Collect the stats
    counter = 0
    vals1, vals2, coeffs = [], [], []
    allVals1, allVals2 = [], []
    results = []
    maxVal = 0
    for i in range(len(data1)):
        vals1.append(float(data1[i][-1]))
        vals2.append(float(data2[i][-1]))
        
        allVals1.append(float(data1[i][-1]))
        allVals2.append(float(data2[i][-1]))
        
        if counter == 31:
            #--- Calculate the value
            matrix = corrcoef(vals1, vals2)
            coeffs.append(matrix[0,1])
            
            maxVal = max([maxVal, std(vals1)])
            results.append((data1[i][0], std(vals1), matrix[0,1]))
            
            vals1, vals2 = [], []
            counter = 0
        else:
            counter += 1
    
    #exp3ShowCoefGraph(results, maxVal)
    exp3PlotAll(allVals1, allVals2)
    
    print "total correlation: ", corrcoef(allVals1, allVals2)[0,1]
    print "avg correlation coefficient: ", mean(coeffs)
    print "std correlation coefficient: ", std(coeffs)
    
def exp3ShowCoefGraph(results, maxVal):
	
    results.sort(secondCompare)
    
    dataArray1 = []
    dataArray2 = []
    for res in results:
        dataArray1.append(res[2])
        dataArray2.append(float(res[1]) / float(maxVal))
    
    print "correlation between std of 32 values (original) and the corr coef of 32 vals: ", corrcoef(dataArray1, dataArray2)[0,1]
    
    plot(dataArray1, 'kx')
    plot(dataArray2)
    xlabel('problem instance')
    ylabel('correlation')
    title('Runtime Correlation')
    show()
    
def exp3PlotAll(vals1, vals2):
	    
    print "correlation between all vals: ", corrcoef(vals1, vals2)[0,1]
    
    plot(vals1, vals2, 'kx')
    plot([0,0.7], 'k')
    xlabel('#ODNF Run-Time (seconds)')
    ylabel('sharpSAT Run-Time (seconds)')
    title('Runtime Correlation')
    show()
    
    
def secondCompare((name1,run1,val1), (name2,run2,val2)):
    return int(float(val2 - val1) * float(1000000))

####################
# Compile Stats
#################
def compile_stats(srcFile1, srcFile2, dstFile):
    #--- Load the data
    data1 = loadCSV(srcFile1)
    data2 = loadCSV(srcFile2)
    
    #--- Get rid of the header line
    data1.pop(0)
    data2.pop(0)
    
    if len(data1) != len(data2):
        print "Error: src has ", len(data1), " lines and dst has ", len(data2), " lines."
        os._exit(1)
    
    #--- Start the new output
    new_output = []
    new_output.append(['file','#vars','#clauses','#implicants','#solutions','avg-runtime','std-runtime','avg-realruntime','std-realruntime'])
    
    #--- Collect the stats
    counter = 0
    runtimes, realruntimes = [], []
    for i in range(len(data1)):
        (file, PP, CA, NCB, CC, IBCP, numVars, numClauses, numImplicants, numSolutions, impCacheSize, cacheHits, runtime) = data1[i]
        (file2, PP2, CA2, NCB2, CC2, IBCP2, realruntime) = data2[i]
        
        runtimes.append(float(runtime))
        realruntimes.append(float(realruntime))
        
        if counter == 31:
            new_output.append([file, numVars, numClauses, numImplicants, numSolutions, str(mean(runtimes)), str(std(runtimes)), str(mean(realruntimes)), str(std(realruntimes))])
            
            runtimes, realruntimes = [], []
            counter = 0
        
        else:
            counter += 1
        
    
    #--- Write the results
    saveCSV(new_output, dstFile)


####################
# Experiment 1
#################
def run_exp1():
    #--- Load the data
    data100 = loadCSV('RESULTS/100-horse-race.csv')
    data150 = loadCSV('RESULTS/150-horse-race.csv')
    data175 = loadCSV('RESULTS/175-horse-race.csv')
    data200 = loadCSV('RESULTS/200-horse-race.csv')
    
    primMeans = []
    sodnfMeans = []
    c2dMeans = []
    
    primStds = []
    sodnfStds = []
    c2dStds = []
    
    (primMean, primStd, sodnfMean, sodnfStd, c2dMean, c2dStd) = exp1GetStats(data100)
    
    primMeans.append(primMean)
    sodnfMeans.append(sodnfMean)
    c2dMeans.append(c2dMean)
    
    primStds.append(primStd)
    sodnfStds.append(sodnfStd)
    c2dStds.append(c2dStd)
    
    (primMean, primStd, sodnfMean, sodnfStd, c2dMean, c2dStd) = exp1GetStats(data150)
    
    primMeans.append(primMean)
    sodnfMeans.append(sodnfMean)
    c2dMeans.append(c2dMean)
    
    primStds.append(primStd)
    sodnfStds.append(sodnfStd)
    c2dStds.append(c2dStd)
    
    (primMean, primStd, sodnfMean, sodnfStd, c2dMean, c2dStd) = exp1GetStats(data175)
    
    primMeans.append(primMean)
    sodnfMeans.append(sodnfMean)
    c2dMeans.append(c2dMean)
    
    primStds.append(primStd)
    sodnfStds.append(sodnfStd)
    c2dStds.append(c2dStd)
    
    (primMean, primStd, sodnfMean, sodnfStd, c2dMean, c2dStd) = exp1GetStats(data200)
    
    primMeans.append(primMean)
    sodnfMeans.append(sodnfMean)
    c2dMeans.append(c2dMean)
    
    primStds.append(primStd)
    sodnfStds.append(sodnfStd)
    c2dStds.append(c2dStd)
    
    exp1TTest(data100)
    exp1TTest(data150)
    exp1TTest(data175)
    exp1TTest(data200)
    
    exp1PrintLatex(primMeans,sodnfMeans,c2dMeans)
    exp1Histogram(primMeans, primStds, sodnfMeans, sodnfStds, c2dMeans, c2dStds)
    
def exp1Histogram(pM, pS, sM, sS, cM, cS):
    import numpy as np
    import matplotlib.pyplot as plt
    
    N = 4
    
    ind = np.arange(N)  # the x locations for the groups
    width = 0.26       # the width of the bars
    
    fig = plt.figure()
    ax = fig.add_subplot(111)
    
    rects1 = ax.bar(ind, pM, width, color='0.25', ecolor='k', yerr=pS)
    rects2 = ax.bar(ind+width, sM, width, color='0.85', ecolor='k', yerr=sS)
    rects3 = ax.bar(ind+width+width, cM, width, color='0.5', ecolor='k', yerr=cS)
    
    # add some
    ax.set_xlabel('Problem Size (# variables)')
    ax.set_ylabel('Run-time (seconds)')
    ax.set_title('Mean Runtime Results')
    ax.set_xticks(ind+width+(width / 2))
    ax.set_xticklabels( ('100', '150', '175', '200') )
    
    ax.legend( (rects1[0], rects2[0], rects3[0]), ('Primeii', '#ODNF', 'c2d'), loc='upper center' )
    
    def autolabel(rects):
        # attach some text labels
        for rect in rects:
            height = rect.get_height()
            ax.text(rect.get_x()+rect.get_width()/2., 1.05*height, '%.3f'%float(height),
                    ha='center', va='bottom')
    
    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)
        
    plt.show()


def exp1PrintLatex(primMeans,sodnfMeans,c2dMeans):
    
    print """
\\begin{table}[ht]
\caption{Mean Run-time Results}
\\begin{center}
\\begin{tabular}{|c|c|c|c|}
\hline variables $\setminus$ solver & primeii & \sodnf & c2d \\\\
\hline 100 & """, primMeans[0], ' & ', sodnfMeans[0], ' & ', c2dMeans[0], """\\\\
\hline 150 & $\infty$ & """, sodnfMeans[1], ' & ', c2dMeans[1], """\\\\
\hline 175 & $\infty$ & $""", sodnfMeans[2], '^*$ & ', c2dMeans[2], """\\\\
\hline 200 & $\infty$ & $""", sodnfMeans[3], '^*$ & ', c2dMeans[3], """\\\\\
\hline 
\end{tabular}
\end{center}
\label{tbl:horserace}
\end{table}
    """
    
def exp1GetStats(data):
    #--- Get rid of the header line
    data.pop(0)
    
    primeiiVals = []
    sodnfVals = []
    c2dVals = []
    
    for entry in data:
        (file, primeiiRuntime, sodnfRuntime, c2dRuntime) = entry
        if primeiiRuntime != 0:
            primeiiVals.append(float(primeiiRuntime))
            
        if sodnfRuntime != 0:
            sodnfVals.append(float(sodnfRuntime))
        
        if c2dRuntime != 0:
            c2dVals.append(float(c2dRuntime))
    
    return (mean(primeiiVals), std(primeiiVals), mean(sodnfVals), std(sodnfVals), mean(c2dVals), std(c2dVals))
    
def exp1TTest(data):
    #--- Get rid of the header line
    data.pop(0)
    
    sodnfVals = []
    c2dVals = []
    
    for entry in data:
        (file, primeiiRuntime, sodnfRuntime, c2dRuntime) = entry
            
        if sodnfRuntime != 0 and c2dRuntime != 0:
            sodnfVals.append(float(sodnfRuntime))
            c2dVals.append(float(c2dRuntime))
    
    print ttest(sodnfVals, c2dVals)
    
    diffs = array(sodnfVals) - array(c2dVals)
    
    origMean = mean(diffs)
    
    numLess = 0
    TRIALS = 10000
    
    for i in range(TRIALS):
        sum = 0.0
        for val in diffs:
            if randint(0,1) == 0:
                sum += val
            else:
                sum -= val
                
        if mean(sum / float(len(diffs))) < origMean:
            numLess += 1
            
    print "mean diff: ", origMean
    print "significant at p <= ", (float(numLess + 1) / float(TRIALS + 1)), "\n"
    


####################
# Experiment 2
#################
def run_exp2(srcFile):
	#--- Load the data
    data = loadCSV(srcFile)
    
    #--- Get rid of the header line
    data.pop(0)
    
    #--- Collect the stats
    arrays = []
    
    for line in data:
    	PP = line[1]
    	CA = line[2]
    	NCB = line[3]
    	CC = line[4]
    	IBCP = line[5]
    	runtime = line[-1]
        arrays.append([PP, CA, NCB, CC, IBCP, runtime])
    
    saveCSV(arrays, 'anova.in', delimiter='\t')
    
    os.system('more anova.R | R --quiet --vanilla > anova.out')
    os.system('rm anova.in')





##############################

def getopts(argv):
    opts = {}
    flags = []
    command = argv[1]
    argv = argv[2:]
    while argv:
        if argv[0][0] == '-':                  # find "-name value" pairs
            opts[argv[0]] = argv[1]            # dict key is "-name" arg
            argv = argv[2:]                    
        else:
            flags.append(argv[0])
            argv = argv[1:]
    return opts, flags, command

if __name__ == '__main__':        
    from sys import argv
    import os
    
    if len(argv) < 2:
        print USAGE_STRING
        os._exit(1)
    
    myargs, flags, command = getopts(argv)
    
    if command == 'confirm-ddnnf':
        if not myargs.has_key('-cnf'):
            print "Must specify cnf:"
            print USAGE_STRING
            os._exit(1)
        
        if not myargs.has_key('-ddnnf'):
            print "Must specify d-DNNF:"
            print USAGE_STRING
            os._exit(1)
        
        validate_ddnnf(myargs['-ddnnf'], myargs['-cnf'])
    
    elif command == 'bdg-to-ddnnf':
        if not myargs.has_key('-bdg'):
            print "Must specify backdoor graph file:"
            print USAGE_STRING
            os._exit(1)
            
        if not myargs.has_key('-ddnnf'):
            print "Must specify d-DNNF file:"
            print USAGE_STRING
            os._exit(1)
            
        if not myargs.has_key('-cnf'):
            print "Must specify cnf file:"
            print USAGE_STRING
            os._exit(1)
        
        bdg_to_ddnnf(myargs['-bdg'], myargs['-cnf'], myargs['-ddnnf'])
        
    elif command == 'anova':
        if not myargs.has_key('-srcCSV'):
            print "Must specify csv file:"
            print USAGE_STRING
            os._exit(1)
            
        anova_test(myargs['-srcCSV'])
        
    elif command == 'correlation':
        if not myargs.has_key('-srcCSV'):
            print "Must specify csv file:"
            print USAGE_STRING
            os._exit(1)
            
        if not myargs.has_key('-dstCSV'):
            print "Must specify csv file:"
            print USAGE_STRING
            os._exit(1)
            
        correlation_test(myargs['-srcCSV'], myargs['-dstCSV'])
        
    elif command == 'compile-stats':
        if not myargs.has_key('-srcCSV1'):
            print "Must specify csv file:"
            print USAGE_STRING
            os._exit(1)
            
        if not myargs.has_key('-srcCSV2'):
            print "Must specify csv file:"
            print USAGE_STRING
            os._exit(1)
        
        if not myargs.has_key('-dstCSV'):
            print "Must specify csv file:"
            print USAGE_STRING
            os._exit(1)
            
        compile_stats(myargs['-srcCSV1'], myargs['-srcCSV2'], myargs['-dstCSV'])
    
    elif command == 'run-exp1':
                
        run_exp1()
        
    elif command == 'run-exp2':
        if not myargs.has_key('-srcCSV'):
            print "Must specify csv file:"
            print USAGE_STRING
            os._exit(1)
            
        run_exp2(myargs['-srcCSV'])
        
    else:
        print USAGE_STRING
        os._exit(1)
