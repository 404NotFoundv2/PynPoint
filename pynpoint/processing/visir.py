# @Jasper Jonker

import numpy as np
from astropy.io import fits
import os
import subprocess
import math
import timeit
import sys
import six
import warnings
from pynpoint.core.processing import ReadingModule, ProcessingModule
from pynpoint.util.module import progress, locate_star
from pynpoint.core.attributes import get_attributes
import threading
from scipy.ndimage import rotate


class VisirInitializationModule(ReadingModule):
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
                 overwrite=True,
                 multithread=False):
        """
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
        :param multithread: TESTING PHASE! Using multithreading for splitting the chop positions.
            This is --NOT-- able to keep the time ordering of frames inside a single Fit-file.
        :type multithread: bool

        return None
        """

        super(VisirInitializationModule, self).__init__(name_in)

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
        self.m_multithread = multithread

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

        if not isinstance(self.m_multithread, bool):
            raise ValueError("Multithread port should be set to 'True' or 'False'")

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
                                        "PARANG", 0.)
                                    self.m_image_out_port_1.append_attribute_data(
                                        "PARANG_END", 0.0001)
                                    self.m_image_out_port_2.append_attribute_data(
                                        "PARANG_START", 0.)
                                    self.m_image_out_port_2.append_attribute_data(
                                        "PARANG", 0.)
                                    self.m_image_out_port_2.append_attribute_data(
                                        "PARANG_END", 0.0001)
                                    self.m_image_out_port_3.append_attribute_data(
                                        "PARANG_START", 0.)
                                    self.m_image_out_port_3.append_attribute_data(
                                        "PARANG", 0.)
                                    self.m_image_out_port_3.append_attribute_data(
                                        "PARANG_END", 0.0001)
                                    self.m_image_out_port_4.append_attribute_data(
                                        "PARANG_START", 0.)
                                    self.m_image_out_port_4.append_attribute_data(
                                        "PARANG", 0.)
                                    self.m_image_out_port_4.append_attribute_data(
                                        "PARANG_END", 0.0001)

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

    def chop_splitting_multiprocessing(self, hdulist, chopa, chopb, images, i,):
        """
        REMOVE FUNCTION IF MULTIPROCESSING FOR CHOPA/CHOPB LIST DOESNT WORK
        Multiprocessing function for filling chopa and chopb

        return None
        """

        cycle = hdulist[i+1].header['HIERARCH ESO DET FRAM TYPE']

        if cycle == 'HCYCLE1':
            chopa = np.append(chopa, images[i, :, :], axis=0)

        elif cycle == 'HCYCLE2':
            chopa = np.append(chopa, images[i, :, :], axis=0)

        else:
            warnings.warn("The chop position(=HIERARCH ESO DET FRAM TYPE) could not be found"
                          "from the header(small). Iteration: {}".format(i))

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
        chopa = np.zeros((int(nimages/2 + 1), image.shape[0], image.shape[1]), dtype=np.float32)
        chopb = np.zeros((int(nimages/2 + 1), image.shape[0], image.shape[1]), dtype=np.float32)

        images = np.zeros((nimages, image.shape[0], image.shape[1]))
        for i in range(1, nimages+1):
            images[i-1, :, :] = hdulist[i].data.byteswap().newbyteorder()

        count_im_1, count_im_2 = 0, 0

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
        hdulist = fits.open(location + image_file)  # do_not_scale_image_data=True)

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

        if self.m_multithread is True:

            # Start Multiprocessing trail
            chopa = np.empty((0, images.shape[1], images.shape[2]))
            chopb = np.empty((0, images.shape[1], images.shape[2]))

            start_time = timeit.default_timer()

            cpu = self._m_config_port.get_attribute("CPU")

            # Create -cpu- number of threads every time
            for i in range(math.ceil(nimages/cpu)):
                noimages = range(0, nimages)
                images_chunk = noimages[cpu*i:min(cpu*(i+1), nimages)]

                jobs = []
                for i, fileno in enumerate(images_chunk):
                    thread = threading.Thread(target=self.chop_splitting_multiprocessing,
                                              args=(hdulist, chopa, chopb, images, fileno,))
                    jobs.append(thread)

                for j in jobs:
                    j.start()

                for j in jobs:
                    j.join()

            elapsed = timeit.default_timer() - start_time
            sys.stdout.write("\r\t\t\t\t\t\tTime ---" + str(np.round(elapsed, 2)) + " seconds")
            sys.stdout.flush()

            # End multiprocessing trail

        else:
            # Initialize chop A and B to allow quick slicing manipulations
            chopa = np.zeros((int(images.shape[0]/2 + ndit), images.shape[1], images.shape[2]),
                             dtype=np.float32)
            chopb = np.zeros((int(images.shape[0]/2 + ndit), images.shape[1], images.shape[2]),
                             dtype=np.float32)

            for i in range(nimages):
                self.chop_splitting(ndit, images, chopa, chopb, i)

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

            start_time = timeit.default_timer()

            if self.m_burst is True:
                chopa, chopb, nod, header, shape = self.open_fit_burst(location, im)
            elif self.m_burst is False:
                chopa, chopb, nod, header, shape = self.open_fit(location, im)

            if nod == "A":
                self.m_image_out_port_1.append(chopa, data_dim=3)
                self.m_image_out_port_2.append(chopb, data_dim=3)

            if nod == "B":
                self.m_image_out_port_3.append(chopa, data_dim=3)
                self.m_image_out_port_4.append(chopb, data_dim=3)

            # Collect header data
            self._static_attributes(files[i], header, i, len(files)-1)
            self._non_static_attributes(header)
            self._extra_attributes(files[i], location, shape, nod)

            self.m_image_out_port_1.flush()
            self.m_image_out_port_2.flush()
            self.m_image_out_port_3.flush()
            self.m_image_out_port_4.flush()

            elapsed = timeit.default_timer() - start_time
            sys.stdout.write(
                "\r\t\t\t\t\t\tTime single Fit ---" + str(np.round(elapsed, 2)) + " seconds")
            sys.stdout.flush()

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


class VisirAngleInterpolationModule(ProcessingModule):
    """
    Module for calculating the parallactic angle values by interpolating between the begin and end
    value of a data cube.
    In FieldStabilized mode, the datacubes are given a very small rotation, necessary to run the
    contrastcurve module

    """

    def __init__(self,
                 name_in="angle_interpolation",
                 data_tag="im_arr",
                 pupilstabilized=True):
        """
        Constructor of AngleInterpolationModule.

        :param name_in: Unique name of the module instance.
        :type name_in: str
        :param data_tag: Tag of the database entry for which the parallactic angles are written as
                         attributes.
        :type data_tag: str
        :param pupilstabilized: Pupilstabilized data (Yes) or FieldStabilized (No)
        :type pupilstabilized: bool

        :return: None
        """

        super(VisirAngleInterpolationModule, self).__init__(name_in)

        self.m_data_in_port = self.add_input_port(data_tag)
        self.m_data_out_port = self.add_output_port(data_tag)

        self.m_pupil = pupilstabilized

    def run(self):
        """
        Run method of the module. Calculates the parallactic angles of each frame by linearly
        interpolating between the start and end values of the data cubes. The values are written
        as attributes to *data_tag*. A correction of 360 deg is applied when the start and end
        values of the angles change sign at +/-180 deg.

        :return: None
        """

        sys.stdout.write("Running VisirAngleInterpolationModule...")
        sys.stdout.flush()

        if self.m_pupil is True:
            parang_start = self.m_data_in_port.get_attribute("PARANG_START")
            parang_end = self.m_data_in_port.get_attribute("PARANG_END")

            steps = self.m_data_in_port.get_attribute("NFRAMES")

            if sum(steps) != self.m_data_in_port.get_shape()[0]:
                cubes = len(steps)
                frames = self.m_data_in_port.get_shape()[0]

                steps = [int(frames/cubes)] * cubes

            new_angles = []

            for i, _ in enumerate(parang_start):

                if parang_start[i] < -170. and parang_end[i] > 170.:
                    parang_start[i] += 360.

                elif parang_end[i] < -170. and parang_start[i] > 170.:
                    parang_end[i] += 360.

                new_angles = np.append(new_angles,
                                       np.linspace(parang_start[i],
                                                   parang_end[i],
                                                   num=steps[i]))

        elif self.m_pupil is False:
            frames = self.m_data_in_port.get_shape()
            steps = frames[0]

            parang_start = [0.]
            parang_end = [1e-4]

            new_angles = []

            new_angles = np.append(new_angles,
                                   np.linspace(parang_start,
                                               parang_end,
                                               num=steps))

        sys.stdout.write("\rRunning VisirAngleInterpolationModule... [DONE]\n")
        sys.stdout.flush()

        self.m_data_out_port.copy_attributes_from_input_port(self.m_data_in_port)
        self.m_data_out_port.add_attribute("PARANG", new_angles, static=False)

        self.m_data_out_port.close_port()


class VisirNodAdditionModule(ProcessingModule):
    """
    Module that adds the two Nod postitions for Parallel nodding. The input expects an parallactic
    angle for each frame, requiring the FieldStabilizedAngleInterpolationModule or the
    AngleInterpolationModule to be ranned before.
    """

    def __init__(self,
                 name_in="NodAddition",
                 image_in_tag_1="image_in_1",
                 image_in_tag_2="image_in_2",
                 image_out_tag="image_out",
                 pupilstabilized=True):
        """
        Constructor of the VisirNodAdditionModule
        :param name_in: Unique name of the instance
        :type name_in: str
        :param image_in_tag_1: Entry of the database used as input of the module, considerd Nod A
        :type image_in_tag: str
        :param image_in_tag_2: Entry of the database used as input of the module, considerd Nod B
        :type image_in_tag: str
        :param image_out_tag: Entry written as output
        :type image_out_tag: str
        :param burst: True if data is taken in Burst, False if data is taken in normal mode.
        :type burst: bool

        :return: None
        """

        super(VisirNodAdditionModule, self).__init__(name_in)

        # Parameters
        self.m_pupil = pupilstabilized

        # Ports
        self.m_image_in_port1 = self.add_input_port(image_in_tag_1)
        self.m_image_in_port2 = self.add_input_port(image_in_tag_2)
        self.m_image_out_port = self.add_output_port(image_out_tag)

    def _initialize(self):
        """
        Function that clears the __init__ tags if they are not
        empty given incorrect input
        """

        if not isinstance(self.m_pupil, bool):
            raise ValueError("Parameter --pupilstabilized-- should be set to True or False")

        if self.m_image_in_port1.tag == self.m_image_out_port.tag or \
                self.m_image_in_port2.tag == self.m_image_out_port.tag:
            raise ValueError("Input and output tags should be different")

        if self.m_image_out_port is not None:
            self.m_image_out_port.del_all_data()
            self.m_image_out_port.del_all_attributes()

    def rotation(self, data):
        """
        Function that rotates the second block of images to the same angle as the first block (nod).

        Returns the dataset rotated given by the posangle in the central database
        """

        posang_1 = self.m_image_in_port1.get_attribute("PARANG")
        posang_2 = self.m_image_in_port2.get_attribute("PARANG")

        if posang_1 is None or posang_2 is None:
            raise ValueError("Attribute --PARANG-- not found in database. "
                             "\nDid you run AngleInterpolationModule before?")

        if len(posang_1) != len(data[:, 0, 0]):
            raise ValueError("The number of images: {} is not equal to the number of angles: {}"
                             "\nDid you run AngleInterpolation before?".format(len(data[:, 0, 0]),
                                                                               len(posang_1)))

        if len(posang_1) != len(posang_2):
            raise UserWarning("Attribute --PARANG-- in the central database has a different size "
                              "for the two input cubes. \nImage_in_tag_1 --PARANG-- size: {1}, "
                              "Image_in_tag_2 --PARANG-- size: {2}. Reducing to size {3}"
                              "".format(len(posang_1),
                                        len(posang_2),
                                        min(len(posang_1), len(posang_2))))

        data_out = np.zeros(data.shape)

        for i in range(len(posang_1)):
            data_out[i, :, :] = rotate(input=data[i, :, :],
                                       angle=posang_1[i]-posang_2[i],
                                       reshape=False)

        return data_out

    def run(self):
        sys.stdout.write("Running VISIRNodAdditionModule...")
        sys.stdout.flush()

        self._initialize()

        shape_1 = self.m_image_in_port1.get_shape()
        shape_2 = self.m_image_in_port2.get_shape()

        if shape_1 != shape_2:
            warnings.warn("Input image size should be the same. Image shape 1 {}, "
                          "is not equal to Image size 2 {}. Reducing to same "
                          "size".format(shape_1, shape_2))

        data_1 = self.m_image_in_port1.get_all()
        data_2 = self.m_image_in_port2.get_all()

        index = min(shape_1[0], shape_2[0])
        data_output = np.zeros((index, shape_1[1], shape_1[2]), dtype=np.float32)

        # Rotate second image set
        if self.m_pupil is True:
            data_2 = self.rotation(data_2)

        else:
            pass

        data_output[:, :, :] = data_1[:index, :, :] + data_2[:index, :, :]

        self.m_image_out_port.set_all(data_output)

        self.m_image_out_port.copy_attributes_from_input_port(self.m_image_in_port1)
        self.m_image_out_port.add_history_information("VisirNodAdditionModule", "Combined Nod")

        sys.stdout.write("\rRunning VISIRNodAdditionModule... [DONE]\n")
        sys.stdout.flush()

        self.m_image_out_port.close_port()


class VisirFrameSelectionModule(ProcessingModule):
    """
    This is a tool that checks the surroundings of the star on high background
    flux and will remove these corresponding frames
    """

    def __init__(self,
                 name_in="frame_selection",
                 image_in_tag="image_in",
                 image_out_tag="image_out",
                 image_removed="image_rem",
                 std_out="std_out_text",
                 method="median",
                 aperture="3.",
                 fwhm="0.3",
                 num_ref=100,
                 sigma=5.):
        """
        Constructor of the VisirFrameSelectionModule
        :param name_in: Unique name of the instance
        :type name_in: str
        :param image_in_tag: Engry of the database used as input of the module
        :type image_in_tag: str
        :param image_out_tag: Entry written as output
        :type image_out_tag: str
        :param image_removed: Entry of the removed images written as output
        :type image_removed: str
        :param std_out: Tag that writes the mean/median (depending on the
        method) and in the second column the standard deviation for every frame.
        :type std_out: str
        :param method: Set to "median" or "mean" that is used as reference to
            the sigma clipping
        :type method: str
        :param aperture: Diameter in arcsec used to mask the star, usually
            taken to be a few times the fwhm of the psf
        :type aperture: float
        :param fwhm: fwhm of the star
        :type fwhm: float
        :param num_ref: Number of references used in calculating the mean of
            the background. If this is set to None, all images are used (up to
            where the memory in the configuration file allows)
        :type num_ref: int
        :param sigma: The standard deviation setting the limit which images are
            kept
        :type sigma: float

        :return: None
        """

        super(VisirFrameSelectionModule, self).__init__(name_in)

        # Port
        self.m_image_in_port = self.add_input_port(image_in_tag)
        self.m_image_out_port = self.add_output_port(image_out_tag)
        self.m_image_out_port_rem = self.add_output_port(image_removed)
        self.m_image_out_port_std = self.add_output_port(std_out)

        # Parameters
        self.m_method = method
        self.m_aperture = aperture
        self.m_fwhm = fwhm
        self.m_num_ref = num_ref
        self.m_sigma = sigma

    def _initialize(self):
        if self.m_image_in_port.tag == self.m_image_out_port.tag or \
           self.m_image_in_port.tag == self.m_image_out_port_rem.tag or \
           self.m_image_in_port.tag == self.m_image_out_port_std.tag:
            raise ValueError("Input and output ports should have a different tag.")

        if self.m_method != "median" and self.m_method != "mean":
            raise ValueError("The parameter method should be set to "
                             "'median' or 'mean'")

        if not isinstance(self.m_aperture, float):
            raise ValueError("The parameter aperture should be a float")

        if not isinstance(self.m_fwhm, float):
            raise ValueError("The parameter fwhm should be a float")

        if not isinstance(self.m_num_ref, int) and self.m_num_ref is not None:
            raise ValueError("The parameter num_ref should be an integer")

        if not isinstance(self.m_sigma, float):
            raise ValueError("The parameter sigma should be a float")

        if self.m_image_out_port is not None:
            self.m_image_out_port.del_all_data()
            self.m_image_out_port.del_all_attributes()

        if self.m_image_out_port_rem is not None:
            self.m_image_out_port_rem.del_all_data()
            self.m_image_out_port_rem.del_all_attributes()

        if self.m_image_out_port_std is not None:
            self.m_image_out_port_std.del_all_data()
            self.m_image_out_port_std.del_all_attributes()

    def mask(self, i):
        """
        Mask the input images with a diameter of fwhm and return
        """

        image = self.m_image_in_port.__getitem__(i)

        pixscale = self.m_image_in_port.get_attribute("PIXSCALE")

        starpos = np.zeros((2), dtype=np.int64)
        fwhm_starps = int(math.ceil(float(self.m_fwhm) / pixscale))

        starpos[:] = locate_star(image=image,
                                 center=None,
                                 width=None,
                                 fwhm=fwhm_starps)

        radius = int(round(self.m_aperture/2.))
        image_masked = image.copy()

        # Inside every frame mask the pixels around the starpos
        for j in range(radius):
            for jj in range(radius):
                if int(round(math.sqrt((j**2 + jj**2)))) <= radius:
                        image_masked[starpos[0] + j,
                                     starpos[1] + jj] = 0
                        image_masked[starpos[0] - j,
                                     starpos[1] - jj] = 0
                        image_masked[starpos[0] - j,
                                     starpos[1] + jj] = 0
                        image_masked[starpos[0] + j,
                                     starpos[1] - jj] = 0

        return image_masked

    def run(self):
        """
        nframes = self.m_image_in_port.get_attribute("NFRAMES")
        indexx = self.m_image_in_port.get_attribute("INDEX")
        parang = self.m_image_in_port.get_attribute("PARANG_START") #PARANG_START?
        im_shape = self.m_image_in_port.get_shape()
        nimages = im_shape[0]
        """

        self._initialize()

        image_shape = self.m_image_in_port.get_shape()

        masked_image = np.zeros(image_shape, dtype=np.float32)

        # for i in range(images.shape[0]):
        #     t = threading.Tread(target=self.mask, args=(i,))

        masked_image[0, :, :] = self.mask(1)
        print(masked_image)

        history = "Number of frames removed ="+""

        self.m_image_out_port.copy_attributes_from_input_port(self.m_image_in_port)
        self.m_image_out_port_rem.copy_attributes_from_input_port(self.m_image_in_port)
        self.m_image_out_port_std.copy_attributes_from_input_port(self.m_image_in_port)

        self.m_image_out_port.add_history_information("FrameSelectionModule", history)

        self.m_image_out_port.close_port()
        self.m_image_out_port_rem.close_port()
        self.m_image_out_port_std.close_port()
