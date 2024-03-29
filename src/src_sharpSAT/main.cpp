#include <iostream>

#include <ctime> // To seed random generator
#include <sys/time.h> // To seed random generator
#include <string>
//include shared files
#include <SomeTime.h>
#include <Interface/AnalyzerData.h>

#include "MainSolver/MainSolver.h"
#include "Basics.h"

using namespace std;

CMainSolver theSolver;

// No description
void finalcSATEvaluation()
{
	const AnalyzerData &rAda = theRunAn.getData();

	if (rAda.theExitState == TIMEOUT)
	{
		toSTDOUT(endl << " TIMEOUT !"<<endl);
		return;
	}

	toSTDOUT(endl<<endl);
	toSTDOUT("#Variables:\t\t"<< rAda.nVars<<endl);

	if (rAda.nVars != rAda.nUsedVars)
		toSTDOUT("#used Variables:\t"<< rAda.nUsedVars<<endl);
	toSTDOUT("#Clauses:\t\t"<< rAda.nOriginalClauses<<endl);
	toSTDOUT("#Clauses removed:\t"<< rAda.nRemovedClauses<<endl);
	toSTDOUT("\n#added Clauses: \t"<< rAda.nAddedClauses<<endl);

	toSTDOUT("\n# of all assignments:\t" << rAda.getAllAssignments()
			<< " = 2^(" << rAda.nVars<<")" <<endl);

	toSTDOUT("Pr[satisfaction]:\t" << rAda.rnProbOfSat <<endl);

	toSTDOUT("# of solutions:\t\t" << rAda.getNumSatAssignments() <<endl);
	toSTDOUT("#SAT (full):   \t\t");
	if (!CSolverConf::quietMode)
		rAda.printNumSatAss_whole();
	toSTDOUT(endl);

	toDEBUGOUT(".. found in:\t\t" << rAda.nReceivedSatAssignments << " units"<<endl);

	toSTDOUT(endl);

	toSTDOUT("Num. conflicts:\t\t" << rAda.nConflicts<<endl);
	toSTDOUT("Num. implications:\t" << rAda.nImplications<<endl);
	toSTDOUT("Num. decisions:\t\t" << rAda.nDecisions<<endl);
	toSTDOUT("max decision level:\t" << rAda.maxDecLevel<<"\t\t");
	toSTDOUT("avg decision level:\t"<< rAda.get(AVG_DEC_LEV)<<endl);
	toSTDOUT("avg conflict level:\t"<< rAda.get(AVG_CONFLICT_LEV)<<endl);
	toSTDOUT("avg solution level:\t"<< rAda.get(AVG_SOLUTION_LEV)<<endl);

	toSTDOUT("CCLLen 1stUIP - max:\t"<< rAda.get(LONGEST_CCL_1stUIP));
	toSTDOUT("\t avg:\t"<< rAda.get(AVG_CCL_1stUIP)<<endl);
	toSTDOUT("CCLLen lastUIP - max:\t"<< rAda.get(LONGEST_CCL_lastUIP));
	toSTDOUT("\t avg:\t"<< rAda.get(AVG_CCL_lastUIP)<<endl);

	toSTDOUT(endl);
	toSTDOUT("FormulaCache stats:"<<endl);
	toSTDOUT("memUse:\t\t\t"<<rAda.get(FCACHE_MEMUSE) <<endl);
	toSTDOUT("cached:\t\t\t"<<rAda.get(FCACHE_CACHEDCOMPS)<<endl);
	toSTDOUT("used Buckets:\t\t"<<rAda.get(FCACHE_USEDBUCKETS)<<endl);
	toSTDOUT("cache retrievals:\t"<<rAda.get(FCACHE_RETRIEVALS)<<endl);
	toSTDOUT("cache tries:\t\t"<<rAda.get(FCACHE_INCLUDETRIES)<<endl);

	toSTDOUT("\n\nTime: "<<rAda.elapsedTime<<"s\n\n");

	cout << "Runtime:" << rAda.elapsedTime << endl;

}

int main(int argc, char *argv[])
{
	char *s;
	char dataFile[1024];
	memset(dataFile, 0, 1024);
	strcpy(dataFile, "data.txt");
	bool fileout = false;

	char graphFile[1024];
	memset(graphFile, 0, 1024);
	strcpy(graphFile, "bdg.txt");
	bool graphFileout = false;

	char nnfFile[1024];
	memset(nnfFile, 0, 1024);
	strcpy(nnfFile, "nnf.txt");
	bool nnfFileout = false;

        //Dimitar Shterionov:
        bool smoothNNF = false;
        
	CSolverConf::analyzeConflicts = true;
	CSolverConf::doNonChronBackTracking = true;
	CSolverConf::nodeCount = 0;

	if (argc <= 1)
	{

		cout << "Usage: dsharp [options] [CNF_File]" << endl;
		cout << "Options: " << endl;
		cout << "\t -priority [v1,v2,..] \t\t use the priority variables as the first decision nodes" << endl;
		cout << "\t -noPP  \t\t turn off preprocessing" << endl;
		cout << "\t -noCA  \t\t turn off conflict analysis" << endl;
		cout << "\t -noCC  \t\t turn off component caching" << endl;
		cout << "\t -noNCB \t\t turn off nonchronological backtracking" << endl;
		cout << "\t -noIBCP\t\t turn off implicit BCP" << endl;
		cout << "\t -noDynDecomp\t\t turn off dynamic decomposition" << endl;
		cout << "\t -q     \t\t quiet mode" << endl;
		cout << "\t -t [s] \t\t set time bound to s seconds" << endl;
		cout << "\t -cs [n]\t\t set max cache size to n MB" << endl;
		cout << "\t -FrA [file] \t\t file to output the run statistics" << endl;
		cout << "\t -Fgraph [file] \t file to output the backdoor or d-DNNF graph" << endl;
		cout << "\t -Fnnf [file] \t\t file to output the nnf graph to" << endl;

        //Dimitar Shterionov:
        cout << "\t -smoothNNF \t\t post processing to smoothed d-DNNF" << endl;
        cout << "\t -disableAllLits \t when producing a smooth d-DNNF, don't bother enforcing every literal" << endl;
		cout << "\t" << endl;

		return -1;
	}

	for (int i = 1; i < argc; i++)
	{
		if (strcmp(argv[i], "-noNCB") == 0)
			CSolverConf::doNonChronBackTracking = false;
		if (strcmp(argv[i], "-noCC") == 0)
			CSolverConf::allowComponentCaching = false;
		if (strcmp(argv[i], "-noIBCP") == 0)
			CSolverConf::allowImplicitBCP = false;

		//Dimitar Shterionov:
		if (strcmp(argv[i], "-smoothNNF") == 0)
			CSolverConf::smoothNNF = true;
		
		if (strcmp(argv[i], "-disableAllLits") == 0)
			CSolverConf::ensureAllLits = false;
		
		if (strcmp(argv[i], "-noDynDecomp") == 0)
		    CSolverConf::disableDynamicDecomp = true;
              
		if (strcmp(argv[i], "-noPP") == 0)
			CSolverConf::allowPreProcessing = false;
		else if (strcmp(argv[i], "-noCA") == 0)
		{
			CSolverConf::analyzeConflicts = false;
		}
		else if (strcmp(argv[i], "-q") == 0)
			CSolverConf::quietMode = true;
		else if (strcmp(argv[i], "-FrA") == 0)
		{
			memset(dataFile, 0, 1024);
			fileout = true;
			if (argc <= i + 1)
			{
				toSTDOUT("wrong parameters"<<endl);
				return -1;
			}
			strcpy(dataFile, argv[i + 1]);
		}
		else if (strcmp(argv[i], "-Fgraph") == 0)
		{
			memset(graphFile, 0, 1024);
			graphFileout = true;
			if (argc <= i + 1)
			{
				toSTDOUT("wrong parameters"<<endl);
				return -1;
			}
			strcpy(graphFile, argv[i + 1]);
		}
		else if (strcmp(argv[i], "-Fnnf") == 0)
		{
			memset(nnfFile, 0, 1024);
			nnfFileout = true;
			if (argc <= i + 1)
			{
				toSTDOUT("wrong parameters"<<endl);
				return -1;
			}
			strcpy(nnfFile, argv[i + 1]);
		}
		else if (strcmp(argv[i], "-t") == 0)
		{
			if (argc <= i + 1)
			{
				toSTDOUT("wrong parameters"<<endl);
				return -1;
			}
			CSolverConf::secsTimeBound = atoi(argv[i + 1]);
			toSTDOUT("time bound:" <<CSolverConf::secsTimeBound<<"s\n");
			theSolver.setTimeBound(CSolverConf::secsTimeBound);
		}
		else if (strcmp(argv[i], "-priority") == 0)
		{
			if (argc <= i + 1)
			{
				toSTDOUT("wrong parameters"<<endl);
				return -1;
			}
			
			size_t pos = 0;
			string s = string(argv[i+1]);
			string token;
            while ((pos = s.find(",")) != string::npos) {
                token = s.substr(0, pos);
                theSolver.priorityVars.insert(atoi(token.c_str()));
                s.erase(0, pos + 1);
            }
            theSolver.priorityVars.insert(atoi(s.c_str()));
			toSTDOUT("Using " << theSolver.priorityVars.size() << " priority variables.\n");
		}
		else if (strcmp(argv[i], "-cs") == 0)
		{
			if (argc <= i + 1)
			{
				toSTDOUT("wrong parameters"<<endl);
				return -1;
			}
			CSolverConf::maxCacheSize = ((size_t) atoi(argv[i + 1])) * 1024 * 1024;
			//cout <<"maxCacheSize:" <<CSolverConf::maxCacheSize<<"bytes\n";
		}
		else
			s = argv[i];
	}

	toSTDOUT("cachesize Max:\t"<<CSolverConf::maxCacheSize/1024 << " kbytes"<<endl);

	// first: delete all data in the output
	if (fileout)
		theRunAn.getData().writeToFile(dataFile);

	theRunAn = CRunAnalyzer();

	theSolver.solve(s);

	theRunAn.finishcountSATAnalysis();
	finalcSATEvaluation();
	if (fileout)
		theRunAn.getData().writeToFile(dataFile);

		bool falsify = false;
        if (0 == theRunAn.getData().getNumSatAssignments()) {
            cout << "\nTheory is unsat. Resetting d-DNNF to empty Or.\n" << endl;
			falsify = true;
        }

	if (graphFileout)
		theSolver.writeBDG(graphFile, falsify);

	if (nnfFileout)
		theSolver.writeNNF(nnfFile, falsify);

	return 0;
}
