make deps
wget http://sourceforge.net/projects/scons/files/scons/2.3.4/scons-2.3.4.tar.gz
wget http://sourceforge.net/projects/boost/files/boost/1.57.0/boost_1_57_0.tar.gz
wget http://www.fftw.org/fftw-3.3.4.tar.gz

tar xzvf scons-2.3.4.tar.gz
tar xzvf boost_1_57_0.tar.gz
tar xzvf fftw-3.3.4.tar.gz

svn checkout http://tmv-cpp.googlecode.com/svn/tags/v0.72/ tmv-cpp
git clone https://github.com/GalSim-developers/GalSim.git

GAL_DIR=/

#=============================
#Install Scons
#=============================

cd scons-2.3.4
python setup.py install --prefix=$GAL_DIR/deps
cd ../

#=============================
#Install FFTW3
#=============================

cd fftw-3.3.4
./configure --prefix=$GAL_DIR/deps CFLAGS='-fPIC'
make
make install
cd ../

#=============================
#Install boost_1_57_0
#=============================

cd boost_1_57_0
./bootstrap.sh
./b2 link=shared
./b2 --prefix=$GAL_DIR/deps link=shared install
cd ../

#=============================
#Install TMV
#=============================

cd tmv-cpp
../deps/bin/scons install PREFIX=$GAL_DIR/deps
cd ../

#=============================
#Install GalSim
#=============================

cd GalSim
$GAL_DIR/deps/bin/scons TMV_DIR=$GAL_DIR/deps FFTW_DIR=$GAL_DIR/deps BOOST_DIR=$GAL_DIR/deps

$GAL_DIR/deps/bin/scons install PREFIX=$GAL_DIR/deps PYPREFIX=$HOME/.local/lib/python2.7/site-packages

$GAL_DIR/deps/bin/scons tests
$GAL_DIR/deps/bin/scons examples
cd ../

#=============================
#Uninstall GalSim
#=============================
#
#scons uninstall
#scons -c
