// -*- c++ -*-
/*
 * Copyright 2012, 2013 The GalSim developers:
 * https://github.com/GalSim-developers
 *
 * This file is part of GalSim: The modular galaxy image simulation toolkit.
 *
 * GalSim is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * GalSim is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with GalSim.  If not, see <http://www.gnu.org/licenses/>
 */

//#define DEBUGLOGGING

#include "SBShapelet.h"
#include "SBShapeletImpl.h"

#ifdef DEBUGLOGGING
#include <fstream>
std::ostream* dbgout = new std::ofstream("debug.out");
int verbose_level = 2;
#endif

namespace galsim {

    SBShapelet::SBShapelet(double sigma, LVector bvec) :
        SBProfile(new SBShapeletImpl(sigma, bvec)) {}

    SBShapelet::SBShapelet(const SBShapelet& rhs) : SBProfile(rhs) {}

    SBShapelet::~SBShapelet() {}

    const LVector& SBShapelet::getBVec() const
    { 
        assert(dynamic_cast<const SBShapeletImpl*>(_pimpl.get()));
        return static_cast<const SBShapeletImpl&>(*_pimpl).getBVec(); 
    }

    double SBShapelet::getSigma() const 
    {
        assert(dynamic_cast<const SBShapeletImpl*>(_pimpl.get()));
        return static_cast<const SBShapeletImpl&>(*_pimpl).getSigma();
    }

    double SBShapelet::SBShapeletImpl::maxK() const 
    {
        // Start with value for plain old Gaussian:
        double maxk = sqrt(-2.*std::log(sbp::maxk_threshold))/_sigma; 
        // Grow as sqrt of (order+1)
        // Note: this is an approximation.  The right value would require looking at
        // the actual coefficients and doing something smart with them.
        maxk *= sqrt(double(_bvec.getOrder()+1));
        return maxk;
    }

    double SBShapelet::SBShapeletImpl::stepK() const 
    {
        // Start with value for plain old Gaussian:
        double R = std::max(4., sqrt(-2.*std::log(sbp::alias_threshold)));
        // Grow as sqrt of (order+1)
        R *= sqrt(double(_bvec.getOrder()+1));
        return M_PI / (R*_sigma);
    }

    double SBShapelet::SBShapeletImpl::xValue(const Position<double>& p) const 
    {
        LVector psi(_bvec.getOrder());
        psi.fillBasis(p.x/_sigma, p.y/_sigma, _sigma);
        double xval = _bvec.dot(psi);
        return xval;
    }

    std::complex<double> SBShapelet::SBShapeletImpl::kValue(const Position<double>& k) const 
    {
        int N=_bvec.getOrder();
        LVector psi(N);
        psi.fillBasis(k.x*_sigma, k.y*_sigma);  // Fourier[Psi_pq] is unitless
        // rotate kvalues of Psi with i^(p+q)
        // dotting b_pq with psi in k-space:
        double rr=0.;
        double ii=0.;
        for (PQIndex pq(0,0); !pq.pastOrder(N); pq.nextDistinct()) {
            int j = pq.rIndex();
            double x = _bvec[j]*psi[j] + (pq.isReal() ? 0 : _bvec[j+1]*psi[j+1]);
            switch (pq.N() % 4) {
              case 0: 
                   rr += x;
                   break;
              case 1: 
                   ii -= x;
                   break;
              case 2: 
                   rr -= x;
                   break;
              case 3: 
                   ii += x;
                   break;
            }
        }  
        // difference in Fourier convention with FFTW ???
        return std::complex<double>(2.*M_PI*rr, 2.*M_PI*ii);
    }

    double SBShapelet::SBShapeletImpl::getFlux() const 
    {
        double flux=0.;
        for (PQIndex pp(0,0); !pp.pastOrder(_bvec.getOrder()); pp.incN())
            flux += _bvec[pp].real();  // _bvec[pp] is real, but need type conv.
        return flux;
    }

    Position<double> SBShapelet::SBShapeletImpl::centroid() const 
    {
        std::complex<double> cen(0.);
        double n = 1.;
        for (PQIndex pq(1,0); !pq.pastOrder(_bvec.getOrder()); pq.incN(), n+=2)
            cen += sqrt(n+1.) * _bvec[pq];
        cen *= sqrt(2.)*_sigma/getFlux();
        return Position<double>(real(cen),-imag(cen));
    }

    double SBShapelet::SBShapeletImpl::getSigma() const { return _sigma; }
    const LVector& SBShapelet::SBShapeletImpl::getBVec() const { return _bvec; }

    template <typename T>
    double SBShapelet::SBShapeletImpl::fillXImage(ImageView<T>& image, double gain) const 
    {
        dbg<<"Start fillXImage\n";
        dbg<<"sigma = "<<_sigma<<std::endl;
        dbg<<"bvec = "<<_bvec<<std::endl;
        dbg<<"image.bounds = "<<image.getBounds()<<std::endl;
        dbg<<"image.scale = "<<image.getScale()<<std::endl;
        dbg<<"gain = "<<gain<<std::endl;
        double dx = image.getScale();
        double scale = dx / _sigma;
        dbg<<"dx = "<<dx<<std::endl;
        dbg<<"scale = "<<scale<<std::endl;
        const int nx = image.getXMax() - image.getXMin() + 1;
        const int ny = image.getYMax() - image.getYMin() + 1;
        const int npts = nx * ny;
        dbg<<"nx, ny, npts = "<<nx<<','<<ny<<','<<npts<<std::endl;
        tmv::Vector<double> x(npts);
        tmv::Vector<double> y(npts);
        int i=0;
        for (int ix = image.getXMin(); ix <= image.getXMax(); ++ix) {
            for (int iy = image.getYMin(); iy <= image.getYMax(); ++iy) {
                x[i] = ix * scale;
                y[i] = iy * scale;
                ++i;
            }
        }

        tmv::Matrix<double> psi(npts,_bvec.size(),0.);
        LVector::basis(psi,x,y,_bvec.getOrder(),_sigma);

        tmv::Vector<double> I = psi * _bvec.rVector();
        double totalflux = I.sumElements();

        i=0;
        for (int ix = image.getXMin(); ix <= image.getXMax(); ++ix) {
            for (int iy = image.getYMin(); iy <= image.getYMax(); ++iy) {
                image(ix,iy) = I[i++]/gain;
            }
        }

        return totalflux * dx*dx;
    }

    void SBShapelet::SBShapeletImpl::fillXGrid(XTable& xt) const 
    {
        int N = xt.getN();
        double scale = xt.getDx() / _sigma;
        const int npts = N*N;
        tmv::Vector<double> x(npts);
        tmv::Vector<double> y(npts);
        int i=0;
        for (int iy = -N/2; iy < N/2; iy++) {
            for (int ix = -N/2; ix < N/2; ix++) {
                x[i] = ix * scale;
                y[i] = iy * scale;
                ++i;
            }
        }

        tmv::Matrix<double> psi(npts,_bvec.size(),0.);
        LVector::basis(psi,x,y,_bvec.getOrder(),_sigma);

        tmv::VectorViewOf(xt.getArray(),npts) = psi * _bvec.rVector();
    }

    void SBShapelet::SBShapeletImpl::fillKGrid(KTable& kt) const 
    {
        int N = kt.getN();
        double scale = kt.getDk() * _sigma;
        const int npts = N*(N/2+1);
        tmv::Vector<double> kx(npts);
        tmv::Vector<double> ky(npts);
        int i=0;
        for (int iy = 0; iy < N/2; iy++) {
            // Negative ix are just the conjugate of positive ix, and are not stored
            // in the array.
            for (int ix = 0; ix <= N/2; ix++) {
                kx[i] = ix * scale;
                ky[i] = iy * scale;
                ++i;
            }
        }
        // Negative iy are wrapped to after 0..N/2
        for (int iy = -N/2; iy < 0; iy++) {
            for (int ix = 0; ix <= N/2; ix++) {
                kx[i] = ix * scale;
                ky[i] = iy * scale;
                ++i;
            }
        }

        tmv::Matrix<std::complex<double> > psi_k(npts,_bvec.size(),0.);
        LVector::kBasis(psi_k,kx,ky,_bvec.getOrder(),_sigma);

        tmv::VectorViewOf(kt.getArray(),npts) = psi_k * _bvec.rVector();
    }

    template <typename T>
    void ShapeletFitImage(double sigma, LVector& bvec, const BaseImage<T>& image,
                          const Position<double>& center)
    {
        double scale = image.getScale() / sigma;
        double cenx = center.x / sigma;
        double ceny = center.y / sigma;
        const int nx = image.getXMax() - image.getXMin() + 1;
        const int ny = image.getYMax() - image.getYMin() + 1;
        const int npts = nx * ny;
        tmv::Vector<double> x(npts);
        tmv::Vector<double> y(npts);
        tmv::Vector<double> I(npts);
        int i=0;
        for (int ix = image.getXMin(); ix <= image.getXMax(); ++ix) {
            for (int iy = image.getYMin(); iy <= image.getYMax(); ++iy) {
                x[i] = ix * scale - cenx;
                y[i] = iy * scale - ceny;
                I[i] = image(ix,iy);
                ++i;
            }
        }

        tmv::Matrix<double> psi(npts,bvec.size(),0.);
        LVector::basis(psi,x,y,bvec.getOrder(),sigma);
        // I = psi * b
        // TMV solves this by writing b = I/psi.
        // We use QRP in case the psi matrix is close to singular (although it shouldn't be).
        psi.divideUsing(tmv::QRP);
        bvec.rVector() = I/psi;
    }

    template void ShapeletFitImage(
        double sigma, LVector& bvec, const BaseImage<double>& image,
        const Position<double>& center);
    template void ShapeletFitImage(
        double sigma, LVector& bvec, const BaseImage<float>& image,
        const Position<double>& center);
    template void ShapeletFitImage(
        double sigma, LVector& bvec, const BaseImage<int32_t>& image,
        const Position<double>& center);
    template void ShapeletFitImage(
        double sigma, LVector& bvec, const BaseImage<int16_t>& image,
        const Position<double>& center);
}

