# This tool combines the burst data made every Chop
# @Jasper Jonker
#
import numpy as np
import sharedmem
from astropy.io import fits
import glob
import math
import timeit
import os
import sys
from pynpoint.core.processing import ProcessingModule
from pynpoint.util.module import progress
import multiprocessing as mp
from multiprocessing import Pool
import functools
#from pathos.multiprocessing import ProcessingPool
#os.system('taskset -p 0x48 %d' % os.getpid())
#print("Restricted to ... cpu: ", os.sched_getaffinity(0))
#print("Number of cpu: ", mp.cpu_count())
#import psutil
#all_cpus = list(range(psutil.cpu_count()))
#p = psutil.Process()
#p.cpu_affinity(all_cpus)
#os.system("taskset -p 0xff %d" % os.getpid())


class VisirBurstModule(ProcessingModule):
    def __init__(self,
                 name_in="burst",
                 image_in_dir="im_in",
                 image_out_tag_1="chopa",
                 image_out_tag_2="chopb",
                 method="median"):
        '''
        Constructor of the VisirBurtModule
        :param name_in: Unique name of the instance
        :type name_in: str
        :param image_in_tag: Entry of the database used as input of the module
        :type image_in_tag: str
        :param image_out_tag: Entry written as output
        :type image_out_tag: str
        :param method: Method used for combining the frames, median, mean or None to use no
        averaging.
        :type method: str

        return None
        '''

        super(VisirBurstModule, self).__init__(name_in)

        # Port
        self.m_image_out_port_1 = self.add_output_port(image_out_tag_1)
        self.m_image_out_port_2 = self.add_output_port(image_out_tag_2)

        # Parameters
        self.m_method = method
        self.m_im_dir = image_in_dir

    def _initialize(self):
        if self.m_image_out_port_1 is not None or self.m_image_out_port_2 is not None:
            if self.m_image_out_port_1.tag == self.m_image_out_port_2.tag:
                raise ValueError("Output ports should have different tags")

        if self.m_method != "median" and self.m_method != "mean" and self.m_method != None:
            raise ValueError("The parameter method should be set to "
                             "'median', 'mean' or None")

        if self.m_image_out_port_1 is not None:
            self.m_image_out_port_1.del_all_data()
            self.m_image_out_port_1.del_all_attributes()

        if self.m_image_out_port_2 is not None:
            self.m_image_out_port_2.del_all_data()
            self.m_image_out_port_2.del_all_attributes()

        return None

    def chop_splitting(self, ndit, images, chopa, chopb, i):
        a = i % (2*ndit)
        b = math.floor(i / (2*ndit))
        c = int(b*ndit)

        if a < ndit:
            chopa[c+a, :, :] = images[i, :, :]
        elif a >= ndit and a < 2*ndit:
            chopb[c+a, :, :] = images[i, :, :]

        return None

    def open_fit(self, image_file):
        hdulist = fits.open(image_file)

        head = hdulist[0].header
        head_small = hdulist[1].header

        nimages = int(head_small['NAXIS3'])
        ndit = int(head['ESO DET NDIT'])
        nod = head['ESO SEQ NODPOS']

        images = hdulist[1].data.byteswap().newbyteorder()

        # Put them in different fit/chop files
        chopa = np.zeros((int(images.shape[0]/2 + ndit), images.shape[1], images.shape[2]))
        chopb = np.zeros((int(images.shape[0]/2 + ndit), images.shape[1], images.shape[2]))
        shareda = sharedmem.empty(chopa.shape)
        sharedb = sharedmem.empty(chopb.shape)

        start_time = timeit.default_timer()

        ''' Multiprocessing, but in this case slower
        processes = []
        for i in range(nimages):
            process = mp.Process(target=self.chop_splitting, args=(ndit, images, shareda, sharedb, i))
            processes.append(process)
            process.start()

        for process in processes:
            process.join()
        '''

        for i in range(nimages):
            self.chop_splitting(ndit, images, shareda, sharedb, i)

        elapsed = timeit.default_timer() - start_time
        print("Time it took to evaluate: \t", np.round(elapsed, 2), "seconds")

        chopa[:, :, :] = shareda[:, :, :]
        chopb[:, :, :] = sharedb[:, :, :]
        chopa = chopa[chopa[:, 0, 0] != 0, :, :]
        chopb = chopb[chopb[:, 0, 0] != 0, :, :]
        #print(chopa[:, 0, 0])
        #print(chopa.shape)
        #print(chopb.shape)

        hdulist.close()

        return chopa, chopb, nod, head

    def _none(self, images):

        return images_comb

    def _mean(self, images):

        return images_comb

    def _median(self, images):

        return images_comb

    def run(self):
        # Check if input tags are correct
        self._initialize()

        sys.stdout.write("Running VirirBurstModule...")
        sys.stdout.flush()

        countera = 0
        counterb = 0

        # Open each fit file
        image_in = glob.glob(self.m_im_dir + '*.fits')
        image_in = np.sort(image_in)

        assert(image_in), "No FITS files found in {}".format(self.m_im_dir)

        for i, im in enumerate(image_in):
            progress(i, len(image_in), "\rRunnig VisirBurstModule...")

            chopa, chopb, nod, header = self.open_fit(im)

            if nod == "A":
                if countera == 0:
                    chopa_noda = chopa
                    chopb_noda = chopb
                    countera = 1
                else:
                    chopa_noda = np.append(chopa_noda, chopa, axis=0)
                    chopb_noda = np.append(chopb_noda, chopb, axis=0)

            if nod == "B":
                if counterb == 0:
                    chopa_nodb = chopa
                    chopb_nodb = chopb
                    counterb = 1
                else:
                    chopa_nodb = np.append(chopa_nodb, chopa, axis=0)
                    chopb_nodb = np.append(chopb_nodb, chopb, axis=0)

            # Collect header data
            self._static_attributes(im, header)

        print("Shape of chopa_noda: ", chopa_noda.shape)
        print("Shape of chopb_noda: ", chopb_noda.shape)
        #print("Shape of chopa_nodb: ", chopa_nodb.shape)
        #print("Shape of chopb_nodb: ", chopb_nodb.shape)

        sys.stdout.write("\rRunning VirirBurstModule...[DONE]\n")
        sys.stdout.flush()

        self.m_image_out_port_1.set_all(chopa_noda, data_dim=3)
        self.m_image_out_port_2.set_all(chopb_noda, data_dim=3)
        #self.m_image_out_port_1.add_history_information("VisirBurstModule", self.m_method)
        #self.m_image_out_port_2.add_history_information("VisirBurstModule", self.m_method)
        self.m_image_out_port_1.flush()
        self.m_image_out_port_2.flush()
        self.m_image_out_port_1.close_port()
        self.m_image_out_port_2.close_port()
