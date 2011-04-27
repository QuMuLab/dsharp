echo "-{ Solving Problem }-"
#./sharpSAT -noPP -noIBCP -noCA -noCC -noNCB -Fbdg graph.out $1
./sharpSAT-bdg -Fgraph graph.bdg.dot $1
./sharpSAT-ddnnf -Fgraph graph.ddnnf.dot $1
echo "-{ Converting to d-DNNF }-"
python src/extra/utils.py bdg-to-ddnnf -bdg graph.bdg.dot -ddnnf graph.conv.dot -cnf $1
echo "-{ Creating Images }-"
dot -Tpng graph.out > graph.png
dot -Tpng cgraph.out > cgraph.png
dot -Tpng graph.ddnnf.out > graph.ddnnf.png
echo "-{ Verifying Converted d-DNNF }-"
python src/extra/utils.py confirm-ddnnf -ddnnf graph.conv.dot -cnf $1
echo "-{ Verifying Natural d-DNNF }-"
python src/extra/utils.py confirm-ddnnf -ddnnf graph.ddnnf.dot -cnf $1
rm graph.*

