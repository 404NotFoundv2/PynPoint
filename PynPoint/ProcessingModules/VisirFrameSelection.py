# This is a tool that checks the surroundings of the star on high background
# flux and will remove these corresponding frames

import numpy as np
import sys
from PynPoint.Core.Processing import ProcessingModule
from PynPoint.Util.ModuleTools import progress, memory_frames, \
                             number_images_port, locate_star
import time
import math


class VisirFrameSelectionModule(ProcessingModule):
    def __init__(self,
                 name_in="frame_selection",
                 image_in_tag="image_in",
                 image_out_tag="image_out",
                 aperture="0.3",
                 fwhm="0.3",
                 num_ref=100,
                 sigma=5.,
                 num_patch=100):
        '''
        Constructor of the VisirFrameSelectionModule
        :param name_in: Unique name of the instance
        :type name_in: str
        :param image_in_tag: Engry of the database used as input of the module
        :type image_in_tag: str
        :param image_out_tag: Entry written as output
        :type image_out_tag: str

        :return: None
        '''

        super(VisirFrameSelectionModule, self).__init__(name_in)

        # Port
        self.m_image_in_port = self.add_input_port(image_in_tag)
        self.m_image_out_port = self.add_output_port(image_out_tag)

        # Parameters
        self.m_aperture = aperture
        self.m_fwhm = fwhm
        self.m_num_ref = num_ref
        self.m_sigma = sigma
        self.m_num_patch = num_patch

    def _initialize(self):
        if self.m_image_out_port is not None:
            if self.m_image_in_port.tag == self.m_image_out_port.tag:
                raise ValueError("Input and output ports should have a "
                                 "different tag.")

        if not isinstance(self.m_aperture, float):
            raise ValueError("The parameter aperture should be a float")

        if not isinstance(self.m_sigma, float):
            raise ValueError("The parameter sigma should be a float")

        if not isinstance(self.m_num_ref, int):
            raise ValueError("The parameter num_ref should be an integer")

        if not isinstance(self.m_num_patch, int):
            raise ValueError("The parameter num_ref should be an integer")

        if self.m_image_out_port is not None:
            self.m_image_out_port.del_all_data()
            self.m_image_out_port.del_all_attributes()

    def patch(self):
        '''
        Do the sigma check every patch
        '''

    def frame(self):
        '''
        Check the frame for high fluctuations of the background
        - Idea what to do, check for the whole frame wether this is close to
           zero (mean?)
        - Look trough all pixels in the frame and whenever there is a that is
            higher than 5-sigma, remove the frame (check we do not remove to
            many tho)

        Implementation now: Take num_ref frames, divide the frames into patches
        (discrete disks, numer set by num_patch) and check wether they are
        outliers. The central PSF is masked with the size of the parameter
        aperture
        '''

        memory = self._m_config_port.get_attribute("MEMORY")
        nimages = number_images_port(self.m_image_in_port)
        nframes = self.m_image_in_port.get_attribute("NFRAMES")
        index = self.m_image_in_port.get_attribute("INDEX")

        if self.m_num_ref > nimages or self.m_num_ref == 0:
            self.m_num_ref = nimages

        frames = memory_frames(self.m_num_ref, nimages)

        print "Memory is: ", memory
        print "nimages is: ", nimages
        print "frames is: ", frames  # frames[:-1]
        print "nframes is:", nframes
        # print "index :", index

        for i, f in enumerate(frames[:-1]):
            progress(i, (len(frames)-1), "Running VisirFrameSelectionModule...")

            time.sleep(1)
            print '\n', "i is: ", i, '\t', "f is: ", f

            frame_start = np.array(frames[i])
            frame_end = np.array(frames[i+1])

            # Check outside aperature for flatness
            images = self.m_image_in_port[frame_start:frame_end, ]
            print "frame_start: ", frame_start
            print "frame_end: ", frame_end
            print images.shape

            starpos = np.zeros((nimages, 2), dtype=np.int64)

            for ii in range(images.shape[0]):
                l_image = images[ii, :, :]

                starpos[ii, :] = locate_star(image=l_image,
                                             center=None,
                                             width=None,
                                             fwhm=int(math.ceil(float(self.m_fwhm)/(float(self.m_pixscale)))))
            print "Starpos is: ", starpos[1, :]
            self.m_image_out_port.append(images)

        sys.stdout.write("Running VisirFrameSelectionModule... [DONE]\n")
        sys.stdout.flush()

        return None

    def run(self):
        '''
        Run the method of the module
        '''

        self.m_pixscale = self.m_image_in_port.get_attribute("PIXSCALE")
        self.m_aperture = self.m_aperture/self.m_pixscale

        self._initialize()
        self.frame()

        self.m_image_out_port.copy_attributes_from_input_port(self.m_image_in_port)

        # self.m_image_out_port.add_attribute()
        self.m_image_out_port.add_history_information("FrameSelectionModule",
                                                      "")
        self.m_image_out_port.close_port()
