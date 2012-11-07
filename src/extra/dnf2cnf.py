import sys

f = open(sys.argv[1], 'r')

old_lines = f.readlines()
new_lines = []
f.close()

num_clauses = -1
num_vars = -1
cur_var = -1

def invert(lit):
    if '-' == lit[0]:
        return lit[1:]
    else:
        return '-' + lit

# First, get the clause sizes
sizes = []
for line in old_lines:
    if ('c' != line[0]) and ('p' != line[0]):
        assert '0' == line.rstrip()[-1]
        sizes.append(len(line.split(' ')) - 1)

# Next, rewrite the theory
for line in old_lines:
    if 'c' == line[0]:
        new_lines.append(line)
    elif 'p' == line[0]:
        (_, _, num_vars, num_clauses) = line.rstrip().split(' ')
        cur_var = int(num_vars) + 1
        new_lines.append("p cnf %d %d\n" % ((int(num_vars) + int(num_clauses)), (int(num_clauses) + sum(sizes))))
    else:
        assert '0' == line.rstrip()[-1]
        lits = line.split(' ')[:-1]
        for l in lits:
            new_lines.append("-%d %s 0\n" % (cur_var, l))
        new_lines.append("%d %s 0\n" % (cur_var, ' '.join(map(invert, lits))))
        cur_var += 1


f = open(sys.argv[1] + '.cnf', 'w')
f.writelines(new_lines)
f.close()
