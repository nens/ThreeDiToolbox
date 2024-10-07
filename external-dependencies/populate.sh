#!/bin/bash
export LANG=C.UTF-8

# Fail immediately upon error exit code.
set -e

# Cleanup, we don't want old stuff to linger around.
rm -f *.whl
rm -rf *.egg
rm -f *.gz
rm -rf SQLAlchemy*
rm -rf build

# Download pure python dependencies and convert them to wheels.
pip3 wheel --constraint ../constraints.txt --no-deps \
GeoAlchemy2 \
alembic \
cached-property \
click \
colorama \
condenser \
h5netcdf \
hydxlib \
importlib-resources \
mako \
networkx \
packaging \
pyqtgraph \
python-editor \
threedi-mi-utils \
threedi-modelchecker \
threedi-schema \
threedidepth \
threedigrid \
typing-extensions \
zipp \

# Start a build/ directory for easier later cleanup.
mkdir build
cd build

# Download the custom compiled qgis version tar of h5py, create a tar from the distro subfolder
wget http://download.osgeo.org/osgeo4w/v2/x86_64/release/python3/python3-h5py/python3-h5py-3.8.0-1.tar.bz2
tar -xvf python3-h5py-3.8.0-1.tar.bz2
tar -cf h5py-3.8.0.tar -C ./apps/Python39/Lib/site-packages/ .
cp h5py-3.8.0.tar ..

# as well as scipy
wget http://download.osgeo.org/osgeo4w/v2/x86_64/release/python3/python3-scipy/python3-scipy-1.10.1-1.tar.bz2
tar -xvf python3-scipy-1.10.1-1.tar.bz2
tar -cf scipy-1.10.1.tar -C ./apps/Python39/Lib/site-packages/ .
cp scipy-1.10.1.tar ..

# Back up a level and clean up the build/ directory.
cd ..
rm -rf build

# Copy the compiled windows scipy to external dependencies
cp scipy/scipy-1.6.2-cp39-cp39-win_amd64.whl .

# Also copy the custom compiled windows h5py to external dependencies for QGis versions before 3.28.6
cp h5py/h5py-2.10.0-cp39-cp39-win_amd64.whl .

# Copy pure wheels to prevent pip in docker (or Windows) to select platform dependent version
wget https://files.pythonhosted.org/packages/cd/84/66072ee12c3e79061f183c09a24be24f45bb1286600589640363d9d416b0/SQLAlchemy-2.0.6-py3-none-any.whl#sha256=c5d754665edea1ecdc79e3023659cb5594372e10776f3b3734d75c2c3ce95013

# Download windows wheels (cp39, win, amd64)

wget https://files.pythonhosted.org/packages/b2/8e/83d9e3bff5c0ff7a0ec7e850c785916e616ab20d8793943f9e1d2a987fab/shapely-2.0.0-cp39-cp39-win_amd64.whl
wget https://files.pythonhosted.org/packages/fe/e3/15a630b4cfd787bba84fb43beac7a25ae29c2b417ad7c4cfadae129a0819/threedigrid_builder-1.17.1-cp39-cp39-win_amd64.whl#sha256=24e06c136e399e1d6299c0a9b3e4c869084aba5878c833487fb13390aec10af8
wget https://files.pythonhosted.org/packages/b3/89/1d3b78577a6b2762cb254f6ce5faec9b7c7b23052d1cdb7237273ff37d10/greenlet-2.0.2-cp39-cp39-win_amd64.whl#sha256=db1a39669102a1d8d12b57de2bb7e2ec9066a6f2b3da35ae511ff93b01b5d564
wget https://files.pythonhosted.org/packages/5f/d6/5f59a5e5570c4414d94c6da4c97731deab832cbd14eaf23189d54a92d1e1/cftime-1.6.2-cp39-cp39-win_amd64.whl#sha256=86fe550b94525c327578a90b2e13418ca5ba6c636d5efe3edec310e631757eea


# Download linux wheels (both cp38 and cp310)
wget https://files.pythonhosted.org/packages/06/07/0700e5e33c44bc87e19953244c29f73669cfb6f19868899170f9c7e34554/shapely-2.0.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
wget https://files.pythonhosted.org/packages/4e/03/f3bcb7d96aef6d56b62e2f25996f161c05f92a45d452165be2007b756e0f/shapely-2.0.0-cp38-cp38-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
wget https://files.pythonhosted.org/packages/53/67/a3f7e0ec8936a2882c97eb1e595ea91c3a5de4869d023064bbc8886d6ab7/threedigrid_builder-1.17.1-cp38-cp38-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
wget https://files.pythonhosted.org/packages/d0/6f/19252e21244e19adf6816cbc6b9d5f1f3cae72b9bd62f1f7da1bc484c9b1/threedigrid_builder-1.17.1-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
wget https://files.pythonhosted.org/packages/6e/11/a1f1af20b6a1a8069bc75012569d030acb89fd7ef70f888b6af2f85accc6/greenlet-2.0.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl#sha256=d75209eed723105f9596807495d58d10b3470fa6732dd6756595e89925ce2470
wget https://files.pythonhosted.org/packages/e1/17/d8042d82f44c08549b535bf2e7d1e87aa1863df5ed6cf1cf773eb2dfdf67/cftime-1.6.2-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl#sha256=acb294fdb80e33545ae54b4421df35c4e578708a5ffce1c00408b2294e70ecef
wget https://files.pythonhosted.org/packages/44/51/bc9d47beee47afda1d335f05efa848dc403bd183344f03d431281518e8ab/cftime-1.5.0-cp38-cp38-manylinux_2_5_x86_64.manylinux1_x86_64.whl#sha256=7a820e16357dbdc9723b2059f7178451de626a8b2e5f80b9d91a77e3dac42133

touch .generated.marker
