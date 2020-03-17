#!/bin/bash
docker run --rm -v $PWD/data:/data -it rosetta/lofar-prefactor3 /bin/bash
