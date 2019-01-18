# This tool combines the burst data made every Chop
# @Jasper Jonker

import numpy as np
import sharedmem
from astropy.io import fits
import os
import subprocess
import math
import timeit
import sys
import six
import warnings
from pynpoint.core.processing import ReadingModule
from pynpoint.util.module import progress
from pynpoint.core.attributes import get_attributes
import threading


class VisirBurstModule(ReadingModule):
    def __init__(self,
                 name_in="burst",
                 image_in_dir="im_in",
                 image_out_tag_1="noda_chopa",
                 image_out_tag_2="noda_chopb",
                 image_out_tag_3="nodb_chopa",
                 image_out_tag_4="nodb_chopb",
                 burst=False,
                 pupilstabilized=True,
                 check=True,
                 overwrite=True):
        '''
        Constructor of the VisirBurtModule
        :param name_in: Unique name of the instance
        :type name_in: str
        :param image_in_dir: Entry directory of the database used as input of the module
        :type image_in_dir: str
        :param image_out_tag_1: Entry written as output, Nod A -> Chop A
        :type image_out_tag_1: str
        :param image_out_tag_1: Entry written as output, Nod A -> Chop B
        :type image_out_tag_2: str
        :param image_out_tag_1: Entry written as output, Nod B -> Chop A
        :type image_out_tag_3: str
        :param image_out_tag_1: Entry written as output, Nod B -> Chop B
        :type image_out_tag_4: str
        :param burst: Whether the data is taken in burst mode or not
        :type burst: bool
        :param pupilstabilized: Define whether the dataset is pupilstabilized (TRUE) or
            fieldstabilized (FALSE)
        :type pupilstabilized: bool
        :param check: Check all the listed non-static attributes or ignore the attributes that
                      are not always required (e.g. PARANG_START, DITHER_X).
        :type check: bool
        :param overwrite: Overwrite existing data and header in the central database.
        :type overwrite: bool

        return None
        '''

        super(VisirBurstModule, self).__init__(name_in)

        # Port
        self.m_image_out_port_1 = self.add_output_port(image_out_tag_1)
        self.m_image_out_port_2 = self.add_output_port(image_out_tag_2)
        self.m_image_out_port_3 = self.add_output_port(image_out_tag_3)
        self.m_image_out_port_4 = self.add_output_port(image_out_tag_4)

        # Parameters
        self.m_im_dir = image_in_dir
        self.m_burst = burst
        self.m_pupil_stabilized = pupilstabilized
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
        tag = [self.m_image_out_port_1.tag,
               self.m_image_out_port_2.tag,
               self.m_image_out_port_3.tag,
               self.m_image_out_port_4.tag]

        seen = set()
        for i in tag:
            if i in seen:
                raise ValueError("Output ports should have different tags")
            if i not in seen:
                seen.add(i)

        if not isinstance(self.m_burst, bool):
            raise ValueError("Burst port should be set to 'True' or 'False'")

        if not isinstance(self.m_pupil_stabilized, bool):
            raise ValueError("Pupilstabilized port should be set to 'True' or 'False'")

        if not isinstance(self.m_check, bool):
            raise ValueError("Check port should be set to 'True' or 'False'")

        if not isinstance(self.m_overwrite, bool):
            raise ValueError("Overwrite port should be set to 'True' or 'False'")

        if self.m_image_out_port_1 is not None:
            self.m_image_out_port_1.del_all_data()
            self.m_image_out_port_1.del_all_attributes()

        if self.m_image_out_port_2 is not None:
            self.m_image_out_port_2.del_all_data()
            self.m_image_out_port_2.del_all_attributes()

        if self.m_image_out_port_3 is not None:
            self.m_image_out_port_3.del_all_data()
            self.m_image_out_port_3.del_all_attributes()

        if self.m_image_out_port_4 is not None:
            self.m_image_out_port_4.del_all_data()
            self.m_image_out_port_4.del_all_attributes()

        return None

    def _static_attributes(self, fits_file, header, iteration, end):
        """
        Internal function which adds the static attributes to the central database.

        :param fits_file: Name of the FITS file.
        :type fits_file: str
        :param header: Header information from the FITS file that is read.
        :type header: astropy FITS header

        :return: None
        """

        a, b, c, d = 0, 0, 0, 0

        for item in self.m_static:

            if self.m_check:
                fitskey = self._m_config_port.get_attribute(item)

                if isinstance(fitskey, np.bytes_):
                    fitskey = str(fitskey.decode("utf-8"))

                if fitskey != "None":
                    if fitskey in header:
                        try:
                            status = self.m_image_out_port_1.check_static_attribute(item,
                                                                                    header[fitskey])
                        except KeyError:
                            # This only outputs the error for the last fits file,otherwise it spawns
                            if iteration == end and a == 0:
                                sys.stdout.write(
                                    "\n \033[93m The output tag {} is empty. There is no nodding "
                                    "postion A. Add input fit files that contain both nod A and "
                                    "nod B.\033[00m\n".format(self.m_image_out_port_1.tag))
                                sys.stdout.flush()

                                a = 1
                            else:
                                pass
                        try:
                            status = self.m_image_out_port_2.check_static_attribute(item,
                                                                                    header[fitskey])
                        except KeyError:
                            if iteration == end and b == 0:
                                sys.stdout.write(
                                    "\n \033[93m The output tag {} is empty. There is no nodding "
                                    "postion A. Add input fit files that contain both nod A and "
                                    "nod B.\033[00m\n".format(self.m_image_out_port_2.tag))
                                sys.stdout.flush()

                                b = 1
                            else:
                                pass
                        try:
                            status = self.m_image_out_port_3.check_static_attribute(item,
                                                                                    header[fitskey])
                        except KeyError:
                            if iteration == end and c == 0:
                                sys.stdout.write(
                                    "\n \033[93m The output tag {} is empty. There is no nodding "
                                    "postion B. Add input fit files that contain both nod A and "
                                    "nod B.\033[00m\n".format(self.m_image_out_port_3.tag))
                                sys.stdout.flush()

                                c = 1
                            else:
                                pass
                        try:
                            status = self.m_image_out_port_4.check_static_attribute(item,
                                                                                    header[fitskey])
                        except KeyError:
                            if iteration == end and d == 0:
                                sys.stdout.write(
                                    "\n \033[93m The output tag {} is empty. There is no nodding "
                                    "postion B. Add input fit files that contain both nod A and "
                                    "nod B.\033[00m\n".format(self.m_image_out_port_4.tag))
                                sys.stdout.flush()

                                d = 1
                            else:
                                pass

                        if status == 1:
                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore")

                                self.m_image_out_port_1.add_attribute(item, header[fitskey],
                                                                      static=True)
                                self.m_image_out_port_2.add_attribute(item, header[fitskey],
                                                                      static=True)
                                self.m_image_out_port_3.add_attribute(item, header[fitskey],
                                                                      static=True)
                                self.m_image_out_port_4.add_attribute(item, header[fitskey],
                                                                      static=True)

                        if status == -1:
                            warnings.warn("Static attribute %s has changed. Possibly the current "
                                          "file %s does not belong to the data set '%s'. Attribute "
                                          "value is updated."
                                          % (fitskey, fits_file, self.output.tag))

                        elif status == 0:
                            pass

                    else:
                        warnings.warn("Static attribute %s (=%s) not found in the FITS header."
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
                    self.m_image_out_port_2.append_attribute_data(item, header[item])
                    self.m_image_out_port_3.append_attribute_data(item, header[item])
                    self.m_image_out_port_4.append_attribute_data(item, header[item])

                else:
                    if self.m_attributes[item]["config"] == "header":
                        fitskey = self._m_config_port.get_attribute(item)

                        if type(fitskey) == np.bytes_:
                            fitskey = str(fitskey.decode("utf-8"))

                        if fitskey != "None":
                            if fitskey in header:
                                self.m_image_out_port_1.append_attribute_data(item, header[fitskey])
                                self.m_image_out_port_2.append_attribute_data(item, header[fitskey])
                                self.m_image_out_port_3.append_attribute_data(item, header[fitskey])
                                self.m_image_out_port_4.append_attribute_data(item, header[fitskey])

                            elif header['NAXIS'] == 2 and item == 'NFRAMES':
                                self.m_image_out_port_1.append_attribute_data(item, 1)
                                self.m_image_out_port_2.append_attribute_data(item, 1)
                                self.m_image_out_port_3.append_attribute_data(item, 1)
                                self.m_image_out_port_4.append_attribute_data(item, 1)

                            elif self.m_pupil_stabilized is False:
                                if fitskey == "ESO ADA POSANG END" or fitskey == "ESO ADA POSANG":
                                    self.m_image_out_port_1.append_attribute_data(
                                        "PARANG_START", 0.)
                                    self.m_image_out_port_1.append_attribute_data(
                                        "PARANG_END", 0.)
                                    self.m_image_out_port_2.append_attribute_data(
                                        "PARANG_START", 0.)
                                    self.m_image_out_port_2.append_attribute_data(
                                        "PARANG_END", 0.)
                                    self.m_image_out_port_3.append_attribute_data(
                                        "PARANG_START", 0.)
                                    self.m_image_out_port_3.append_attribute_data(
                                        "PARANG_END", 0.)
                                    self.m_image_out_port_4.append_attribute_data(
                                        "PARANG_START", 0.)
                                    self.m_image_out_port_4.append_attribute_data(
                                        "PARANG_END", 0.)

                                elif fitskey == "ESO ADA PUPILPOS":
                                    self.m_image_out_port_1.append_attribute_data(
                                        item, 0.)
                                    self.m_image_out_port_2.append_attribute_data(
                                        item, 0.)
                                    self.m_image_out_port_3.append_attribute_data(
                                        item, 0.)
                                    self.m_image_out_port_4.append_attribute_data(
                                        item, 0.)

                            else:
                                warnings.warn("Non-static attribute %s (=%s) not found in the "
                                              "FITS header." % (item, fitskey))

                                self.m_image_out_port_1.append_attribute_data(item, -1)
                                self.m_image_out_port_2.append_attribute_data(item, -1)
                                self.m_image_out_port_3.append_attribute_data(item, -1)
                                self.m_image_out_port_4.append_attribute_data(item, -1)

        return None

    def _extra_attributes(self, fits_file, location, shape, nod):
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
            if nod == 'A':
                self.m_image_out_port_1.append_attribute_data("INDEX", item)
                self.m_image_out_port_2.append_attribute_data("INDEX", item)
            elif nod == 'B':
                self.m_image_out_port_3.append_attribute_data("INDEX", item)
                self.m_image_out_port_4.append_attribute_data("INDEX", item)

        if nod == 'A':
            self.m_image_out_port_1.append_attribute_data("FILES", location+fits_file)
            self.m_image_out_port_2.append_attribute_data("FILES", location+fits_file)
            self.m_image_out_port_1.add_attribute("PIXSCALE", pixscale, static=True)
            self.m_image_out_port_2.add_attribute("PIXSCALE", pixscale, static=True)
        elif nod == 'B':
            self.m_image_out_port_3.append_attribute_data("FILES", location+fits_file)
            self.m_image_out_port_4.append_attribute_data("FILES", location+fits_file)
            self.m_image_out_port_3.add_attribute("PIXSCALE", pixscale, static=True)
            self.m_image_out_port_4.add_attribute("PIXSCALE", pixscale, static=True)
        else:
            warnings.warn("Attribute -nod- in function _extra_attribtutes is not A or B.")

        self.m_count += nimages

        return None

    def _uncompress_multi(self, filename):
        """
        Subfuction of -uncompress- used for threading.
        It uncompresses the file -filename-

        return None
        """

        command = "uncompress " + filename
        subprocess.check_call(command.split())

        return None

    def uncompress(self):
        """
        This function checks the input directory if it contains any compressed files ending with
        '.fits.Z'. If this is the case, it will uncompress these using multithreading. This is much
        faster than uncompressing when having multiple files

        return None
        """

        cpu = self._m_config_port.get_attribute("CPU")

        location = os.path.join(self.m_im_dir, '')
        files = os.listdir(location)
        files_compressed = []

        for f in files:
            if f.endswith('.fits.Z'):
                files_compressed.append(location + f)

        if len(files_compressed) > cpu:
            # Split the threads into smaller chunks
            # Not implemented yet
            pass

        if len(files_compressed) == 0:
            pass

        else:
            sys.stdout.write("\rRunning VISIRInitializationModule... Uncompressing files ...")
            sys.stdout.flush()

            # First check if the number of files is not larger than cpu
            amount = len(files_compressed)
            if amount > cpu:
                for i in range(math.ceil(amount/cpu)):
                    files_compressed_chunk = files_compressed[cpu*i:min(cpu*(i+1), amount)]

                    jobs = []
                    for i, filename in enumerate(files_compressed_chunk):
                        thread = threading.Thread(target=self._uncompress_multi, args=(filename,))
                        jobs.append(thread)

                    for j in jobs:
                        j.start()

                    for j in jobs:
                        j.join()

            else:
                jobs = []
                for i, filename in enumerate(files_compressed):
                    thread = threading.Thread(target=self._uncompress_multi, args=(filename,))
                    jobs.append(thread)

                for j in jobs:
                    j.start()

                for j in jobs:
                    j.join()

        return None

    def chop_splitting(self, ndit, images, chopa, chopb, i):
        """
        Function that splits the images-tag into 2 different tags, chop A and chop B. The splitting
        is done by the parameter ndit, the number of frames taken each chop. Any NDITSKIP (not from
        overhead, but for some other reason) is not taken into account.
        It is only called in the Burst mode

        return None
        """

        # a: The first 0:ndit will contain chopa, the ndit:2*ndit contains chopb
        # b & c: Calculates at which chop-cycle we are
        a = i % (2*ndit)
        b = math.floor(i / (2*ndit))
        c = int(b*ndit)

        if a < ndit:
            chopa[c+a, :, :] = images[i, :, :]
        elif a >= ndit and a < 2*ndit:
            chopb[c+a, :, :] = images[i, :, :]

        return None

    def open_fit(self, location, image_file):
        """
        Function that opens the fit file at --location + image_file--. It returns the input image
        file into chop A and chop B, including the header data.

        return chopa, chopb, nod, head, head_small, images.shape
        """
        hdulist = fits.open(location + image_file)
        image = hdulist[1].data.byteswap().newbyteorder()

        nimages = len(hdulist) - 2
        head = hdulist[0].header
        head_small = hdulist[1].header
        nod = head['ESO SEQ NODPOS']

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            head.remove("NAXIS")
            head_small.remove("NAXIS")
            header = head.copy()
            header.update(head_small)
            header.append(("NAXIS3", nimages))

        # Put them in different fit/chop files
        chopa = np.zeros((int(nimages/2 + 1), image.shape[0], image.shape[1]))
        chopb = np.zeros((int(nimages/2 + 1), image.shape[0], image.shape[1]))

        images = np.zeros((nimages, image.shape[0], image.shape[1]))
        for i in range(1, nimages+1):
            images[i-1, :, :] = hdulist[i].data.byteswap().newbyteorder()

        count_im_1, count_im_2 = 0, 0

        # start_time = timeit.default_timer()

        for i in range(0, nimages):
            cycle = hdulist[i+1].header['HIERARCH ESO DET FRAM TYPE']

            if cycle == 'HCYCLE1':
                chopa[count_im_1, :, :] = images[i, :, :]
                count_im_1 += 1

            elif cycle == 'HCYCLE2':
                chopb[count_im_2, :, :] = images[i, :, :]
                count_im_2 += 1

            else:
                warnings.warn("The chop position(=HIERARCH ESO DET FRAM TYPE) could not be found"
                              "from the header(small). Iteration: {}".format(i))

        # elapsed = timeit.default_timer() - start_time
        # sys.stdout.write(
        #     "\r\t\t\t\t\t\tTime single Fit ---" + str(np.round(elapsed, 2)) + " seconds")
        # sys.stdout.flush()

        chopa = chopa[chopa[:, 0, 0] != 0, :, :]
        chopb = chopb[chopb[:, 0, 0] != 0, :, :]

        fits_header = []
        for key in header:
            fits_header.append(str(key)+" = "+str(header[key]))

        hdulist.close()

        header_out_port = self.add_output_port('fits_header/'+image_file)
        header_out_port.set_all(fits_header)

        return chopa, chopb, nod, header, images.shape

    def open_fit_burst(self, location, image_file):
        """
        Function that opens the fit file at --location + image_file--. It returns the input image
        file into chop A and chop B, including the header data.

        return chopa, chopb, nod, head, head_small, images.shape
        """
        hdulist = fits.open(location + image_file)

        head = hdulist[0].header
        head_small = hdulist[1].header

        nimages = int(head_small['NAXIS3'])
        ndit = int(head['ESO DET NDIT'])
        nod = head['ESO SEQ NODPOS']

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            head.remove("NAXIS")
            header = head.copy()
            header.update(head_small)

        images = hdulist[1].data.byteswap().newbyteorder()

        # Put them in different fit/chop files
        chopa = np.zeros((int(images.shape[0]/2 + ndit), images.shape[1], images.shape[2]))
        chopb = np.zeros((int(images.shape[0]/2 + ndit), images.shape[1], images.shape[2]))
        # shareda = sharedmem.empty(chopa.shape)
        # sharedb = sharedmem.empty(chopb.shape)

        for i in range(nimages):
            # self.chop_splitting(ndit, images, shareda, sharedb, i)
            self.chop_splitting(ndit, images, chopa, chopb, i)

        # chopa[:, :, :] = shareda[:, :, :]
        # chopb[:, :, :] = sharedb[:, :, :]
        chopa = chopa[chopa[:, 0, 0] != 0, :, :]
        chopb = chopb[chopb[:, 0, 0] != 0, :, :]

        fits_header = []
        for key in header:
            fits_header.append(str(key)+" = "+str(header[key]))

        hdulist.close()

        header_out_port = self.add_output_port('fits_header/'+image_file)
        header_out_port.set_all(fits_header)

        return chopa, chopb, nod, header, images.shape

    def run(self):
        """
        Run the module. The module first checks the tags for uniquenes. The fit files from the
        input-dir are collected, each ran with the  - self.open_fit() - function. This outputs the
        data into 2 parts, chop location A and B. The nod-tag will tell from the header from which
        nod location this chop A&B comes from. This is appended to the output tags. The output tags
        correspond to nod A -> chop A & B, nod B -> chop A & B - respectively.
        Lastly, from the header, the cards are inported to the general config port of PynPoint.

        return None
        """

        self._initialize()

        # Check if the files are compressed, if so; uncompress
        self.uncompress()

        sys.stdout.write("\rRunning VISIRInitializationModule...")
        sys.stdout.flush()

        countera, counterb = 0, 0

        # Open each fit file
        location = os.path.join(self.m_im_dir, '')

        files = []
        for filename in os.listdir(location):
            if filename.endswith('.fits'):
                files.append(filename)

        files.sort()

        assert(files), "No FITS files found in {}".format(self.m_im_dir)

        for i, im in enumerate(files):
            progress(i, len(files), "\rRunning VISIRInitializationModule...")

            # start_time = timeit.default_timer()

            if self.m_burst is True:
                chopa, chopb, nod, header, shape = self.open_fit_burst(location, im)
            elif self.m_burst is False:
                chopa, chopb, nod, header, shape = self.open_fit(location, im)

            if nod == "A":
                if countera == 0:
                    chopa_noda = chopa
                    chopb_noda = chopb
                    countera = 1
                else:
                    chopa_noda = np.append(chopa_noda, chopa, axis=0)
                    chopb_noda = np.append(chopb_noda, chopb, axis=0)

                self.m_image_out_port_1.append(chopa_noda, data_dim=3)
                self.m_image_out_port_2.append(chopb_noda, data_dim=3)

            if nod == "B":
                if counterb == 0:
                    chopa_nodb = chopa
                    chopb_nodb = chopb
                    counterb = 1
                else:
                    chopa_nodb = np.append(chopa_nodb, chopa, axis=0)
                    chopb_nodb = np.append(chopb_nodb, chopb, axis=0)

                self.m_image_out_port_3.append(chopa_nodb, data_dim=3)
                self.m_image_out_port_4.append(chopb_nodb, data_dim=3)

            # Collect header data
            self._static_attributes(files[i], header, i, len(files)-1)
            self._non_static_attributes(header)
            self._extra_attributes(files[i], location, shape, nod)

            self.m_image_out_port_1.flush()
            self.m_image_out_port_2.flush()
            self.m_image_out_port_3.flush()
            self.m_image_out_port_4.flush()

            # elapsed = timeit.default_timer() - start_time
            # sys.stdout.write(
            #     "\r\t\t\t\t\t\tTime single Fit ---" + str(np.round(elapsed, 2)) + " seconds")
            # sys.stdout.flush()

        # print("Shape of chopa_noda: ", chopa_noda.shape)
        # print("Shape of chopb_noda: ", chopb_noda.shape)
        # print("Shape of chopa_nodb: ", chopa_nodb.shape)
        # print("Shape of chopb_nodb: ", chopb_nodb.shape)

        sys.stdout.write("\rRunning VISIRInitializationModule...[DONE]\n")
        sys.stdout.flush()

        self.m_image_out_port_1.add_history_information("VisirBurstModule", "Nod A, Chop A")
        self.m_image_out_port_2.add_history_information("VisirBurstModule", "Nod A, Chop B")
        self.m_image_out_port_3.add_history_information("VisirBurstModule", "Nod B, Chop A")
        self.m_image_out_port_4.add_history_information("VisirBurstModule", "Nod B, Chop B")
        self.m_image_out_port_1.close_port()
        self.m_image_out_port_2.close_port()
        self.m_image_out_port_3.close_port()
        self.m_image_out_port_4.close_port()
