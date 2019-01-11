# This tool combines the burst data made every Chop
# @Jasper Jonker

import numpy as np
from astropy.io import fits
import glob
import math
from pynpoint.core.processing import ProcessingModule
from pynpoint.util.module import progress, memory_frames, \
                             number_images_port


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

        return chopa, chopb

    def open_fit(self, image_file):
        hdulist = fits.open(image_file)

        head = hdulist[0].header
        head_small = hdulist[1].header

        nimages = int(head_small['NAXIS3'])
        ndit = int(head['ESO DET NDIT'])
        images = hdulist[1].data

        # Put them in different fit/chop files
        chopa = np.zeros((int(images.shape[0]/2 + ndit), images.shape[1], images.shape[2]))
        chopb = np.zeros((int(images.shape[0]/2 + ndit), images.shape[1], images.shape[2]))
        for i in range(nimages):
            chopa, chopb = self.chop_splitting(ndit, images, chopa, chopb, i)
        chopa = chopa[chopa[:,0,0] != 0, :, :]
        chopb = chopb[chopb[:,0,0] != 0, :, :]
        print(chopa.shape)
        print(chopb.shape)

        hdulist.close()

        return None

    def _none(self, images):

        return images_comb

    def _mean(self, images):

        return images_comb

    def _median(self, images):

        return images_comb

    def run(self):
        # Check if inpu tags are correct
        self._initialize()

        # Open each fit file
        image_in = glob.glob(self.m_im_dir + '*.fits')
        for im in image_in:
            self.open_fit(im)

        '''
        frames = memory_frames(memory, nimages)

        # Move trough the seperate frames blocks
        for i, f in enumerate(frames[:-1]):
            progress(i, (len(frames)-1),
                     "Running VisirBurstModule...")

            frame_start = np.array(frames[i])
            frame_end = np.array(frames[i+1])

            images = self.m_image_in_port[frame_start:frame_end, ]

            if self.m_method == "mean":
                images_combined = self._mean(images)

            elif self.m_method == "median":
                images_combined = self._median(images)

            if self.m_method == None:
                images_combined = self._none(images)

            self.m_image_out_port.append(images_combined)
        '''
        #self.m_image_out_port.add_history_information(
        #    "VisirBurstModule", self.m_method)
        #self.m_image_out_port.close_port()
