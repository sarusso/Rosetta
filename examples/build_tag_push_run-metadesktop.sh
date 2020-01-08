#!/bin/bash
set -e


# Build
cd ../Software/MetaDesktop
docker build . -t rosetta/metadesktop
cd ../../

# Tag
docker tag rosetta/metadesktop localhost:5000/rosetta/metadesktop

# Push
docker push localhost:5000/rosetta/metadesktop

# Run
rosetta/shell slurmclustermaster-main "SINGULARITY_NOHTTPS=true singularity run --pid --writable-tmpfs --containall --cleanenv docker://dregistry:5000/rosetta/metadesktop"

# Run variants/tests
# rosetta/shell slurmclustermaster-main "SINGULARITY_NOHTTPS=true singularity run docker://dregistry:5000/rosetta/metadesktop"
# rosetta/shell slurmclustermaster-main "rm -rf tmp && mkdir tmp  && SINGULARITYENV_HOME=/metauser SINGULARITY_NOHTTPS=true singularity run -B ./tmp:/tmp,./tmp:/metauser --writable-tmpfs --containall --cleanenv docker://dregistry:5000/rosetta/metadesktop"

cd examples
