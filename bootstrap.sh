#!/bin/bash

MAIN_DIR=/vagrant
MAIN_USER=vagrant
VIRTUAL_ENV=/var/virtualenv/rep0st

sudo apt-get update
sudo apt-get dist-upgrade -y
sudo apt-get install gcc g++ make cmake binutils build-essential unzip checkinstall htop python python-dev python-pip python-virtualenv libopencv-dev libatlas-base-dev gfortran -y

sudo su $MAIN_USER
cd $MAIN_DIR

sudo mkdir -p $VIRTUAL_ENV
sudo chown -R $MAIN_USER:$MAIN_USER $VIRTUAL_ENV
virtualenv $VIRTUAL_ENV
ln -s $VIRTUAL_ENV env

# install python packages
env/bin/pip install -r requirements.txt

#env/bin/pip install numpy==1.9.1
#env/bin/pip install matplotlib==1.4.3
#env/bin/pip install nose==1.3.4
#env/bin/pip install sympy==0.7.6
#env/bin/pip install pandas==0.15.2
#env/bin/pip install scipy==0.15.1

# build opencv and install to virtual env from source
sudo mkdir -p /tmp/opencvbuild
sudo chown -R $MAIN_USER:$MAIN_USER /tmp/opencvbuild
cd /tmp/opencvbuild
wget -O opencv-2.4.9.tar.gz https://github.com/Itseez/opencv/archive/2.4.9.tar.gz
tar xfv opencv-2.4.9.tar.gz
cd opencv-2.4.9
mkdir build
cd build
cmake -D MAKE_BUILD_TYPE=RELEASE -D CMAKE_INSTALL_PREFIX=$VIRTUAL_ENV/local/ -D PYTHON_EXECUTABLE=$VIRTUAL_ENV/bin/python -D PYTHON_PACKAGES_PATH=$VIRTUAL_ENV/lib/python2.7/site-packages -D INSTALL_PYTHON_EXAMPLES=ON ..
make -j8
make install
cd $VIRTUAL_ENV

wget http://files.rene8888.at/rep0st/latest_dump.zip
unzip latest_dump.zip
rm latest_dump.zip
