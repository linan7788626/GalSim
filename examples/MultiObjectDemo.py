#!/usr/bin/env python
"""
Some example scripts to make multi-object images using the GalSim library.
"""

import sys
import os
import subprocess
import math
import logging

# This machinery lets us run Python examples even though they aren't positioned
# properly to find galsim as a package in the current directory.
try:
    import galsim
except ImportError:
    path, filename = os.path.split(__file__)
    sys.path.append(os.path.abspath(os.path.join(path, "..")))
    import galsim

# Script 1: Something along the lines of a Great08 image
def Script1():
    """
    Make images similar to that done for the Great08 challenge:
      - Each fits file is 100 x 100 postage stamps
      - Each postage stamp is 40 x 40 pixels
      - One set of files is all stars
      - Another set of files is all galaxies
      - Applied shear is the same for each file
      - Galaxies are oriented randomly, but in pairs to cancel shape noise.
      - Noise is poisson using a nominal sky value of 1.e6
      - Galaxies are sersic profiles
    """
    logger = logging.getLogger("Script1") 

    # Define some parameters we'll use below.
    # Normally these would be read in from some parameter file.

    # Not using 100 x 100 because very slow currently.
    #nx_stamps = 100                 #
    #ny_stamps = 100                 #
    nx_stamps = 10                  #
    ny_stamps = 10                  #
    nx_pixels = 40                  #
    ny_pixels = 40                  #

    random_seed = 6424512           #

    pixel_scale = 1.0               # arcsec
    sky_level = 1.e6                # ADU

    psf_file_name = os.path.join('output','g08_psf.fits')
    psf_beta = 3                    #
    psf_fwhm = 2.85                 # arcsec (=pixels)
    psf_trunc = 20.                 # FWHM (so beyond the edge of the postage stamp. 
                                    #       i.e. no truncation.)
    psf_g1 = -0.019                 #
    psf_g2 = -0.007                 #
    psf_centroid_shift = 1.0        # arcsec (=pixels)

    gal_file_name = os.path.join('output','g08_gal.fits')
    gal_signal_to_noise = 200       # Great08 "Low-noise" run
    gal_n = 2.5                     #
    gal_resolution = 1.4            # fwhm_gal_obs / fwhm_psf
    gal_centroid_shift = 1.0        # arcsec (=pixels)
    gal_ellip_rms = 0.2             # using "shear" definition of ellipticity.
    gal_ellip_max = 0.6             #
    gal_g1 = 0.013                  #
    gal_g2 = -0.008                 #

    logger.info('Starting multi-object script 1 using:')
    logger.info('    - image with %d x %d postage stamps',nx_stamps,ny_stamps)
    logger.info('    - postage stamps of size %d x %d pixels',nx_pixels,ny_pixels)
    logger.info('    - Moffat PSF (beta = %.1f, FWHM = %.2f, trunc = %.2f),', 
            psf_beta,psf_fwhm,psf_trunc)
    logger.info('    - PSF ellipticity = (%.3f,%.3f)',psf_g1,psf_g2)
    logger.info('    - PSF centroid shifts up to = %.2f pixels',psf_centroid_shift)
    logger.info('    - Sersic galaxies (n = %.1f)',gal_n)
    logger.info('    - Resolution (fwhm_obs / fwhm_psf) = %.2f',gal_resolution)
    logger.info('    - Ellipticities have rms = %.1f, max = %.1f',
            gal_ellip_rms, gal_ellip_max
    logger.info('    - Applied gravitational shear = (%.3f,%.3f)',gal_g1,gal_g2)
    logger.info('    - Poisson noise (sky level = %.1e).', sky_level)


    # Initialize the random number generator we will be using.
    rng = galsim.UniformDeviate(random_seed)

    # Define the PSF profile
    #psf = galsim.Moffat(beta=psf_beta, flux=1., fwhm=psf_fwhm)
    psf = galsim.Moffat(beta=psf_beta, flux=1., re=psf_fwhm/2, truncationFWHM=psf_trunc)
    psf.applyShear(psf_g1,psf_g2)
    logger.info('Made PSF profile')

    pix = galsim.Pixel(xw=pixel_scale, yw=pixel_scale)
    logger.info('Made pixel profile')

    final_psf = galsim.Convolve(psf,pix)
    logger.info('Made final_psf profile')

    # This profile is placed with different noise realizations at each postage
    # stamp in the psf image.
    psf_image = galsim.ImageF(nx_pixels * nx_stamps , ny_pixels * ny_stamps)
    psf_image.setOrigin(0,0) # For my convenience -- switch to C indexing convention.
    psf_centroid_shift_sq = psf_centroid_shift**2
    logger.info('i,j,x,y')
    for ix in range(nx_stamps):
        for iy in range(ny_stamps):
            # The -1's in the next line are to provide a 
            b = galsim.BoundsI(ix*nx_pixels , (ix+1)*nx_pixels -1,
                               iy*ny_pixels , (iy+1)*ny_pixels -1)
            sub_image = psf_image[b]

            # apply a random centroid shift:
            rsq = 2 * psf_centroid_shift_sq
            while (rsq > psf_centroid_shift_sq):
                dx = (2*rng()-1) * psf_centroid_shift
                dy = (2*rng()-1) * psf_centroid_shift
                rsq = dx**2 + dy**2

            this_psf = final_psf.createShifted(dx,dy)

            # No noise on PSF images.  Just draw it as is.
            this_psf.draw(sub_image, dx=pixel_scale)

            x = b.center().x
            y = b.center().y
            logger.info('%d,%d,%.0f,%0.f',ix,iy,x,y)

    logger.info('Done making images of PSF postage stamps')

    # Now write the image to disk.
    psf_image.write(psf_file_name, clobber=True)
    logger.info('Wrote PSF file %s',psf_file_name)
            
    # Define the galaxy profile

    # First figure out the size we need from the resolution
    # great08 resolution was defined as Rgp / Rp where Rp is the FWHM of the PSF
    # and Rgp is the FWHM of the convolved galaxy.
    # We make the approximation here that the FWHM adds in quadrature during the 
    # convolution, so we can get the unconvolved size as:
    # Rg^2 = Rgp^2 - Rp^2 = Rp^2 * (resolution^2 - 1)
    gal_fwhm = psf_fwhm * math.sqrt( gal_resolution**2 - 1)

    # Next, determine what flux we need.
    # TODO: Need a better mechanism for determining flux given S/N
    # We make the approximation here that the noise is essentially the noise in the 
    # pixels within a radius of fwhm/2.  
    # The variance per pixel is given by the sky value.
    # The relevant number of pixels is pi (fwhm/2)^2
    # So the total noise is sqrt(sky * pi (fwhm/2)^2)
    gal_noise = math.sqrt(sky_level * math.pi) * gal_fwhm/2.
    gal_flux = gal_signal_to_noise * gal_noise
    ## Note from Rachel: we could use GREAT08 S/N definition by uncommenting all the lines starting
    ## with ### below (note, I don't know a general way to do this, has to be done empirically as
    ## I've done it here); and comment out the line that currently creates the Sersic galaxy

    # Make the galaxy profile starting with flux = 1.
    #gal = galsim.Sersic(gal_n, flux=gal_flux, fwhm=gal_fwhm)
    gal = galsim.Sersic(gal_n, flux=gal_flux, re=gal_fwhm/2)
    ### gal = galsim.Sersic(gal_n, flux=1., fwhm=gal_fwhm)
    ### tmp_gal_image = gal.draw(dx = pixel_scale)
    ### sqrt_tot_i2 = np.sqrt(np.sum(tmp_gal_image.array**2))
    ## note, we want sqrt_tot_i2 to equal SNR * sqrt(background); so, rescale the image flux by the
    ## ratio of desired sqrt_tot_i2 to real one
    ### rescale_fac = gal_signal_to_noise * math.sqrt(sky_level) / sqrt_tot_i2
    ### gal.setFlux(rescale_fac)
    logger.info('Made galaxy profile')

    # This profile is placed with different orientations and noise realizations 
    # at each postage stamp in the gal image.
    gal_image = galsim.ImageF(nx_pixels * nx_stamps , ny_pixels * ny_stamps)
    gal_image.setOrigin(0,0) # For my convenience -- switch to C indexing convention.
    gal_centroid_shift_sq = gal_centroid_shift**2
    first_in_pair = True
    gd = galsim.GaussianDeviate(rng, sigma=gal_ellip_rms)
    logger.info('i,j,x,y,ellip,theta')
    for ix in range(nx_stamps):
        for iy in range(ny_stamps):
            # The -1's in the next line are to provide a 
            b = galsim.BoundsI(ix*nx_pixels , (ix+1)*nx_pixels -1,
                               iy*ny_pixels , (iy+1)*ny_pixels -1) 
            sub_image = gal_image[b]

            # Great08 randomized the locations of the two galaxies in each pair,
            # but for simplicity, we just do them in sequential postage stamps.
            if first_in_pair:
                # Determine the ellipticity to use for this galaxy.
                ellip = 1
                while (math.fabs(ellip) > gal_ellip_max):
                    ellip = gd()

                # Apply a random orientation:
                #theta = rng() * 2. * math.pi * galsim.radians
                theta = rng() * 2. * math.pi 
                first_in_pair = False
            else:
                #theta += math.pi/2 * galsim.radians
                theta += math.pi/2
                first_in_pair = True

            this_gal = gal.createSheared(ellip,0)
            this_gal.applyRotation(theta * galsim.radians)

            # Apply the gravitational shear
            this_gal.applyShear(gal_g1,gal_g2)

            # Apply a random centroid shift:
            rsq = 2 * gal_centroid_shift_sq
            while (rsq > gal_centroid_shift_sq):
                dx = (2*rng()-1) * gal_centroid_shift
                dy = (2*rng()-1) * gal_centroid_shift
                rsq = dx**2 + dy**2

            this_gal.applyShift(dx,dy)

            # Draw the image
            this_gal.draw(sub_image, dx=pixel_scale)

            # Add Poisson noise
            sub_image += sky_level
            sub_image.addNoise(galsim.CCDNoise(rng))
            sub_image -= sky_level

            x = b.center().x
            y = b.center().y
            logger.info('%d,%d,%.0f,%.0f,%.4f,%.3f',ix,iy,x,y,ellip,theta)

    logger.info('Done making images of Galaxy postage stamps')

    # Now write the image to disk.
    gal_image.write(gal_file_name, clobber=True)
    logger.info('Wrote image to %r',gal_file_name)  # using %r adds quotes around filename for us

    print

# Script 2: Read many of the relevant parameters from an input catalog
def Script2():
    """
    Make a fits image cube using parameters from an input catalog
      - The number of images in the cube matches the number of rows in the catalog.
      - Each image size is computed automatically by GalSim based on the Nyquist size.
      - Only galaxies.  No stars.
      - PSF is Moffat
      - Each galaxy is bulge plus disk: deVaucouleurs + Exponential.
      - Parameters taken from the input catalog:
        - PSF beta
        - PSF FWHM
        - PSF g1
        - PSF g2
        - PSF trunc
        - Bulge half-light-radius
        - Bulge g1
        - Bulge g2
        - Bulge flux
        - Disc half-light-radius
        - Disc g1
        - Disc g2
        - Disc flux
        - Galaxy dx (two components have same center)
        - Galaxy dy
      - Applied shear is the same for each file
      - Noise is poisson using a nominal sky value of 1.e6
    """
    logger = logging.getLogger("Script2") 

    # Define some parameters we'll use below.

    cat_file_name = os.path.join('input','galsim_default_input.asc')
    out_file_name = os.path.join('output','cube.fits')

    random_seed = 8241573
    sky_level = 1.e6                # ADU
    pixel_scale = 0.2               # arcsec
    gal_flux = 2000                 #
    gal_g1 = -0.009                 #
    gal_g2 = 0.011                  #

    logger.info('Starting multi-object script 2 using:')
    logger.info('    - parameters taken from catalog ',cat_file_name)
    logger.info('    - Moffat PSF (parameters from catalog)')
    logger.info('    - pixel scale = ',pixel_scale)
    logger.info('    - Bulge + Disc galaxies (parameters from catalog)')
    logger.info('    - Galaxy S/N = ',gal_signal_to_noise)
    logger.info('    - Applied gravitational shear = (%.3f,%.3f)',gal_g1,gal_g2)
    logger.info('    - Poisson noise (sky level = %.1e).', sky_level)

    # Initialize the random number generator we will be using.
    rng = galsim.UniformDeviate(random_seed)

    # Setup the config object

    # MJ: Could we maybe call this just Config(), rather than AttributeDict()?
    config = AttributeDict()

    config.psf.type = 'Moffat'
    config.psf.beta.type = 'InputCatalog'
    config.psf.beta.col = 5
    config.psf.fwhm.type = 'InputCatalog'
    config.psf.fwhm.col = 6
    config.psf.g1.type = 'InputCatalog'
    config.psf.g1.col = 7
    config.psf.g2.type = 'InputCatalog'
    config.psf.g2.col = 8
    config.psf.trunc.type = 'InputCatalog'
    config.psf.trunc.col = 9
    config.gal.type = 'Sum'
    config.gal.nitems = 2
    config.gal.item[0].type = 'Exponential'
    config.gal.item[0].half_light_radius.type = 'InputCatalog'
    config.gal.item[0].half_light_radius.col = 10
    config.gal.item[0].g1.type = 'InputCatalog'
    config.gal.item[0].g1.col = 11
    config.gal.item[0].g2.type = 'InputCatalog'
    config.gal.item[0].g2.col = 12
    config.gal.item[0].flux = 0.6
    config.gal.item[0].type = 'DeVaucouleurs'
    config.gal.item[1].half_light_radius.type = 'InputCatalog'
    config.gal.item[1].half_light_radius.col = 13
    config.gal.item[1].g1.type = 'InputCatalog'
    config.gal.item[1].g1.col = 14
    config.gal.item[1].g2.type = 'InputCatalog'
    config.gal.item[1].g2.col = 15
    config.gal.item[1].flux = 0.4
    config.gal.shift.type = 'DXDY'
    # TODO: These aren't currently in the catalog
    config.gal.shift.dx.type = 'InputCatalog'
    config.gal.shift.dx.col = 16
    config.gal.shift.dy.type = 'InputCatalog'
    config.gal.shift.dy.col = 17

    # Read the catalog
    # TODO: switch these function names to CamelCase?  
    # Or should we switch the style specification for python to use lower_case?  
    # We don't have many free functions in python yet, so we can easily switch if
    # people prefer that.
    input_cat = galsim.io.read_input_cat(cat_file_name, config)

    # Build the images
    all_images = []
    for i in range(input_cat.nobjects):
        psf = galsim.build_psf_image(config, input_cat, logger)
        logger.info('Made PSF profile')

        pix = galsim.Pixel(pixel_scale)
        logger.info('Made pixel profile')

        gal = galsim.build_gal_image(config, input_cat, logger, flux=gal_flux)
        logger.info('Made galaxy profile')

        im = gal.draw()

        # Add Poisson noise
        im += sky_level
        im.addNoise(galsim.CCDNoise(rng))
        im -= sky_level
        logger.info('Drew image')

        # Store that into the list of all images
        all_images[i] = im

    logger.info('Done making images of galaxies')

    # Now write the image to disk.
    # TODO: This function doesn't exist yet.
    galsim.fits.writeCube(out_file_name, all_images, clobber=True)
    logger.info('Wrote image to %r',out_file_name)  # using %r adds quotes around filename for us

    print


def main(argv):
    try:
        # If no argument, run all scripts (indicated by scriptNum = 0)
        scriptNum = int(argv[1]) if len(argv) > 1 else 0
    except Exception as err:
        print __doc__
        raise err
    
    # Output files are put in the directory output.  Make sure it exists.
    if not os.path.isdir('output'):
        os.mkdir('output')

    # Setup logging here, rather than at module scope, so the user can do it
    # differently if they import the module and run the scripts as functions.
    # If this isn't called at all, no logging is done.
    # For fancy logging setups (e.g. when running on a big cluster) we could
    # use logging.fileConfig to use a config file to control logging.
    logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG,
        stream=sys.stdout
    )
    # We do some fancier logging for Script3, just to demonstrate that we can:
    # - we log to both stdout and to a log file
    # - the log file has a lot more (mostly redundant) information
    logFile = logging.FileHandler(os.path.join("output", "script3.log"))
    logFile.setFormatter(logging.Formatter("%(name)s[%(levelname)s] %(asctime)s: %(message)s"))
    logging.getLogger("Script3").addHandler(logFile)

    # Script 1: Great08-like image
    if scriptNum == 0 or scriptNum == 1:
        Script1()


if __name__ == "__main__":
    main(sys.argv)
