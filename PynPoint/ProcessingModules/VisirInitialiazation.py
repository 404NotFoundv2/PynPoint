'''
Create from a table-like fits file a 3-D cube with the number
of the frame as 3rd axis. Sort them on timestamps written in
every image header. Output gives 2 files, ChopA and ChopB.

The first HDU is not included(it contains no data) just as
the last one, which is an average all chop images (see the manual).

Use the mode 'v' for details about the output fits files

Input can be .fits files or compressed .fits.Z

Default overwrite=True on the output files

Recommended not to specify image_outa and image_outb to keep the
different chop positions in the naming.

To make use of multiprocessing, install pathos '$ pip install pathos'. The
multiprocessing package from python has trouble with pickling.

Run the module by running VisirInitializationModule(image_in_tag).run()

@Jasper Jonker
'''

import numpy as np
from astropy.io import fits
import sys
import subprocess
import glob
import multiprocessing as mp
import time
# from functools import partial


class VisirInitializationModule():

    def __init__(self,
                 image_in_tag,
                 image_outa='chopa.fits',
                 image_outb='chopb.fits',
                 mode=None):
        '''
        Constructor of preparing VISIR data in PynPoint

        :param image_in_tag: Tags of the database entries (.fits or .fits.Z)
                             that are read as input.
        :type image_in_tags: str
        :param image_outa: Tag of the database entry that is written as output.
                           This is the first chop position
        :type image_outa: str
        :param image_outb: Tag of the database netry that is written as output.
                           This is the second chop position
        :type image_outb: str
        :param mode: Mode that displays information about the output files.
        :type mode: 'v' or None

        :return: None
        '''

        # sys.stdout.write("Running VISIRInitializationModule... \n")
        self.image_in_tag = image_in_tag
        self.image_out_1 = image_outa
        self.image_out_2 = image_outb
        self.mode = mode

    def uncompress_multi(self, i):
        '''
        Subfunction of uncompression that is used for multiprocessing
        '''

        command = "uncompress " + self.image_folder[i]
        subprocess.check_call(command.split())

    def uncompress(self,):
        '''
        Check whether the input file is compressed or not.
        If the file is compressed by unix (.Z), uncompress
        and place the output in the same folder. This function
        removes the compressed files.
        '''

        self.image_folder = glob.glob(self.image_in_tag + "*.fits.Z")

        # Import the package pathos.multiprocessing if it is available. If this
        # is not the case, run the process on a single core
        if len(self.image_folder) is not 0:
            try:
                from pathos.multiprocessing import ProcessPool

                start_time = time.time()
                pool = ProcessPool(mp.cpu_count())

                sys.stdout.write('\rRunning VISIRInitializationModule... ' +
                                 'Uncompressing files...')
                sys.stdout.flush()

                pool.map(self.uncompress_multi, range(len(self.image_folder)))

                sys.stdout.write('\rRunning VISIRInitializationModule... ' +
                                 'Uncompressing files... [DONE]\n')
                sys.stdout.flush()

                # print '\t--- Uncompressed in {} seconds ---'.format(
                #                            time.time() - start_time)
            except ImportError:
                # Run it on a single core
                sys.stdout.write('\rFor multiprocessing install pathos:')
                sys.stdout.write('"pip install pathos"\n')

                for i in range(len(self.image_folder)):
                    percentage = int(float(i)/len(self.image_folder)*100)
                    sys.stdout.write(
                        '\rRunning VISIRInitializationModule... ' +
                        'Uncompressing files... ({})%'.format(percentage))
                    sys.stdout.flush()
                    command = "uncompress " + self.image_folder[i]
                    subprocess.check_call(command.split())

                sys.stdout.write('\rRunning VISIRInitializationModule... ' +
                                 'Uncompressing files... [DONE]\n')
                sys.stdout.flush()
        else:
            pass

        return None

    def rewrite(self,
                image_in,
                image_outa='chop_a.fits',
                image_outb='chop_b.fits',
                mode=None):
        '''
        Write the input files as two seperate files based on timestamp
        and on the chop positions.
        '''

        # Read FITS file and open it
        offset = 32768.
        hdulist = fits.open(image_in)
        head = hdulist[0].header
        xpixel = head['ESO DET ACQ1 WIN NX']
        ypixel = head['ESO DET ACQ1 WIN NY']

        # [OPTIONAL] Change the header
        # head['NAXIS'] = 3

        # Initialize arrays that will contain the data
        lenf_min = len(hdulist) - 2
        hour = np.zeros((lenf_min), dtype=int)
        minute = np.zeros((lenf_min), dtype=int)
        second = np.zeros((lenf_min), dtype=float)
        time = np.zeros((lenf_min), dtype=float)
        lista = np.zeros(shape=(lenf_min, ypixel, xpixel), dtype=np.float32)
        listb = np.zeros(shape=(lenf_min, ypixel, xpixel), dtype=np.float32)

        # Find the values of TIME in the header and save in x
        # Not considering the first and last one (see manual)
        for a in range(0, lenf_min):
            x = hdulist[a+1].header['HIERARCH ESO DET EXP UTC'][11:]
            hour[a] = int(x[:2])
            minute[a] = int(x[3:5])
            second[a] = float(x[6:])
            time[a] = hour[a]*60*60 + minute[a]*60 + second[a]

        time_s = np.sort(time)

        '''
        This loop will do the sorting on time and find the correct chop
        position from the header data. lista will contain chopA and listb will
        contain chopB
        '''

        a, b = 0, 0

        for i in range(lenf_min):
            for ii in range(lenf_min):
                x = hdulist[ii+1].header['HIERARCH ESO DET EXP UTC'][11:]
                x = float(x[:2])*60*60 + float(x[3:5])*60 + float(x[6:])

                if time_s[i] == x:
                    if (hdulist[ii+1].header['HIERARCH ESO DET FRAM TYPE'] ==
                            'HCYCLE1'):
                        lista[a, :, :] = hdulist[ii+1].data
                        a += 1
                        break

                    if (hdulist[ii+1].header['HIERARCH ESO DET FRAM TYPE'] ==
                            'HCYCLE2'):
                        listb[b, :, :] = hdulist[ii+1].data
                        b += 1
                        break

                    else:
                        raise ValueError("Didn't find Frame type in header, "
                                         "couldn't find separate different "
                                         "chop positions. Please check "
                                         "'DET FRAM TYPE'")

        # Remove the empty lists
        lista = lista[lista[:, 0, 0] != 0, :, :] + offset
        listb = listb[listb[:, 0, 0] != 0, :, :] + offset

        # Create primary/another HDU that will encapsulate the header + data
        hdua = fits.PrimaryHDU(header=head, data=lista)
        hdub = fits.PrimaryHDU(header=head, data=listb)
        hdula = fits.HDUList([hdua])
        hdulb = fits.HDUList([hdub])
        hdula.writeto(image_outa, overwrite=True)
        hdulb.writeto(image_outb, overwrite=True)

        # Display format output .fits files
        if mode == 'v':
            hdulista = fits.open(image_outa)
            hdulistb = fits.open(image_outb)
            print
            print '###########################################################'
            print(repr(hdulista.info()))
            print
            print '###########################################################'
            print(repr(hdulistb.info()))
            print '\n'
            hdulista.close()
            hdulistb.close()
            # print "Shape of original FITS is: hdulist.info()
        elif mode is None:
            pass
        else:
            raise ValueError("Choose mode to be verbose: 'v', or None")

        hdulist.close()
        return None

    def run(self):
        '''
        Run method of the module. First it checks for any compressed files
        present, then it will produce for every .fits file 2 files, chopA and
        chopB

        :return: None
        '''

        sys.stdout.write("Running VISIRInitializationModule...")
        sys.stdout.flush()

        self.uncompress()

        self.files = glob.glob(self.image_in_tag + '*.fits')

        for j in range(len(self.files)):
            percentage = int(float(j)/len(self.files)*100)
            sys.stdout.write('\rRunning VISIRInitializationModule... ' +
                             '({})%'.format(percentage))
            sys.stdout.flush()

            self.rewrite(image_in=self.files[j],
                         image_outa=self.image_out_1[:-5] + '_nod' +
                         str(j) + '.fits',
                         image_outb=self.image_out_2[:-5] + '_nod' +
                         str(j) + '.fits',
                         mode=self.mode)

        sys.stdout.write('\rRunning VISIRInitializationModule... ' +
                         '[DONE]\n')
        sys.stdout.flush()
        return None
