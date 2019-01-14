# This tool combines the burst data made every Chop
# @Jasper Jonker
#
import numpy as np
import sharedmem
from astropy.io import fits
import glob
import os
import math
import timeit
import sys
import six
from pynpoint.core.processing import ProcessingModule, ReadingModule
from pynpoint.util.module import progress
from pynpoint.core.attributes import get_attributes
from pynpoint.readwrite.fitsreading import FitsReadingModule
#_static_attributes, _non_static_attributes, _extra_attributes

#import os
#import multiprocessing as mp
#from multiprocessing import Pool
#import functools
#from pathos.multiprocessing import ProcessingPool
#os.system('taskset -p 0x48 %d' % os.getpid())
#print("Restricted to ... cpu: ", os.sched_getaffinity(0))
#print("Number of cpu: ", mp.cpu_count())
#import psutil
#all_cpus = list(range(psutil.cpu_count()))
#p = psutil.Process()
#p.cpu_affinity(all_cpus)
#os.system("taskset -p 0xff %d" % os.getpid())


class VisirBurstModule(ReadingModule, ProcessingModule):
    def __init__(self,
                 name_in="burst",
                 image_in_dir="im_in",
                 image_out_tag_1="chopa",
                 image_out_tag_2="chopb",
                 method="median",
                 check=True,
                 overwrite=True):
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
        self.m_check = check
        self.m_overwrite = overwrite

        # Arguments
        self.m_static = []
        self.m_non_static = []

        self.m_attributes = get_attributes()

        for key, value in six.iteritems(self.m_attributes):
            if value["config"] == "header" and value["attribute"] == "static":
                self.m_static.append(key)

        for key, value in six.iteritems(self.m_attributes):
            if value["attribute"] == "non-static":
                self.m_non_static.append(key)

        self.m_count = 0

    def _initialize(self):
        """
        Function that clears the __init__ tags if they are not
        empty given incorrect input
        """

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

    def _static_attributes(self, fits_file, header):
        """
        Internal function which adds the static attributes to the central database.

        :param fits_file: Name of the FITS file.
        :type fits_file: str
        :param header: Header information from the FITS file that is read.
        :type header: astropy FITS header

        :return: None
        """

        for item in self.m_static:

            if self.m_check:
                fitskey = self._m_config_port.get_attribute(item)

                if isinstance(fitskey, np.bytes_):
                    fitskey = str(fitskey.decode("utf-8"))

                if fitskey != "None":
                    if fitskey in header:
                        status = self.m_image_out_port_1.check_static_attribute(item,
                                                                              header[fitskey])

                        if status == 1:
                            self.m_image_out_port_1.add_attribute(item,
                                                                header[fitskey],
                                                                static=True)

                        if status == -1:
                            warnings.warn("Static attribute %s has changed. Possibly the current "
                                          "file %s does not belong to the data set '%s'. Attribute "
                                          "value is updated." \
                                          % (fitskey, fits_file, self.m_image_out_port_1.tag))

                        elif status == 0:
                            pass

                    else:
                        warnings.warn("Static attribute %s (=%s) not found in the FITS header." \
                                      % (item, fitskey))

        return None

    def _non_static_attributes(self, header):
        """
        Internal function which adds the non-static attributes to the central database.

        :param header: Header information from the FITS file that is read.
        :type header: astropy FITS header

        :return: None
        """

        for item in self.m_non_static:
            if self.m_check:
                if item in header:
                    self.m_image_out_port_1.append_attribute_data(item, header[item])

                else:
                    if self.m_attributes[item]["config"] == "header":
                        fitskey = self._m_config_port.get_attribute(item)

                        # if type(fitskey) == np.bytes_:
                        #     fitskey = str(fitskey.decode("utf-8"))

                        if fitskey != "None":
                            if fitskey in header:
                                self.m_image_out_port_1.append_attribute_data(item, header[fitskey])

                            elif header['NAXIS'] == 2 and item == 'NFRAMES':
                                self.m_image_out_port_1.append_attribute_data(item, 1)

                            else:
                                warnings.warn("Non-static attribute %s (=%s) not found in the "
                                              "FITS header." % (item, fitskey))

                                self.m_image_out_port_1.append_attribute_data(item, -1)

        return None

    def _extra_attributes(self, fits_file, location, shape):
        """
        Internal function which adds extra attributes to the central database.

        :param fits_file: Name of the FITS file.
        :type fits_file: str
        :param location: Directory where the FITS file is located.
        :type location: str
        :param shape: Shape of the images.
        :type shape: tuple(int)

        :return: None
        """

        pixscale = self._m_config_port.get_attribute('PIXSCALE')

        if len(shape) == 2:
            nimages = 1
        elif len(shape) == 3:
            nimages = shape[0]

        index = np.arange(self.m_count, self.m_count+nimages, 1)

        for _, item in enumerate(index):
            self.m_image_out_port_1.append_attribute_data("INDEX", item)

        self.m_image_out_port_1.append_attribute_data("FILES", location+fits_file)
        self.m_image_out_port_1.add_attribute("PIXSCALE", pixscale, static=True)

        self.m_count += nimages

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

        fits_header = []
        for key in head:
            fits_header.append(str(key)+" = "+str(head[key]))

        hdulist.close()

        header_out_port = self.add_output_port('fits_header/'+image_file)
        header_out_port.set_all(fits_header)

        return chopa, chopb, nod, head, images.shape

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

        location = os.path.join(self.m_im_dir, '')

        files = []
        for filename in os.listdir(location):
            if filename.endswith('.fits'):
                files.append(filename)

        files.sort()

        assert(image_in), "No FITS files found in {}".format(self.m_im_dir)

        for i, im in enumerate(image_in):
            progress(i, len(image_in), "\rRunnig VisirBurstModule...")

            chopa, chopb, nod, header, shape = self.open_fit(im)

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
            self._static_attributes(files[i], header)
            self._non_static_attributes(header)
            self._extra_attributes(files[i], location, shape)
            #FitsReadingModule._static_attributes(self, files[i], header)
            #FitsReadingModule._non_static_attributes(self, header)
            #FitsReadingModule._extra_attributes(self, files[i], location, shape)

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
