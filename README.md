# DSHARP

![dsharp logo](logo.png)

DSHARP is an open source CNF -> d-DNNF compiler based on sharpSAT. Similar to the c2d software, DSHARP takes a boolean theory in conjunctive normal form as input, and compiles it into deterministic decomposable negation normal form.

## Usage

If you would like the solver to use infinite precision numbers for the counting,
you must have the GMP library (libgmp-dev) installed. To use the version with GMP,
copy the Makefile_gmp to Makefile. Otherwise, copy Makefile_nogmp to Makefile and
proceed normally.

To compile this version of DSHARP simply run `make`

## Citing
```
@inproceedings{Muise2012,
    author = {Muise, Christian and McIlraith, Sheila A. and Beck, J. Christopher and Hsu, Eric},
    booktitle = {Canadian Conference on Artificial Intelligence},
    title = {{DSHARP: Fast d-DNNF Compilation with sharpSAT}},
    keywords = {sat, knowledge compilation},
    year = {2012}
}
```
