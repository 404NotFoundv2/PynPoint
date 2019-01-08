# This tool combines the burst data made every Chop
# @Jasper Jonker

import numpy as np
from pynpoint.core.processing import ProcessingModule
from pynpoint.util.module import progress, memory_frames, \
                             number_images_port


class VisirBurstModule(ProcessingModule):
    def __init__(self,
                 name_in="burst",
                 image_in_tag="im_in",
                 image_out_tag="im_out",
                 method="median"):
        '''
        Constructor of the VisirBurtModule
        :param name_in: Unique name of the instance
        :type name_in: str
        :param image_in_tag: Entry of the database used as input of the module
        :type image_in_tag: str
        :param image_out_tag: Entry written as output
        :type image_out_tag: str
        :param method: Method used for combining the frames, median of mean
        :type method: str

        return None
        '''

        super(VisirBurstModule, self).__init__(name_in)

        # Port
        self.m_image_in_port = self.add_input_port(image_in_tag)
        self.image_out_port = self.add_output_port(image_out_tag)

        # Parameters
        self.m_method = method

    def _initialize(self):
        if self.m_image_out_port is not None:
            if self.m_image_in_port.tag == self.m_image_out_port.tag:
                raise ValueError("Input and output ports should have a "
                                 "different tag.")

        if self.m_method != "median" and self.m_method != "mean":
            raise ValueError("The parameter method should be set to "
                             "'median' or 'mean'")

        if self.m_image_out_port is not None:
            self.m_image_out_port.del_all_data()
            self.m_image_out_port.del_all_attributes()

        return None

    def _mean(self, images):

        return images_comb

    def _median(self, images):

        return images_comb

    def run(self):
        self._initialize()

        memory = self._m_config_port.get_attribute("MEMORY")

        im_shape = self.m_image_in_port.get_shape()
        nimages = number_images_port(self.m_image_in_port)
        nditchop = self.m_image_in_port.get_attribute("NDITSKIP")

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

            self.m_image_out_port.append(images_combined)

        self.m_image_out_port.copy_attributes_from_input_port(
            self.m_image_in_port)
        self.m_image_out_port.add_history_information(
            "VisirBurstModule", self.m_method)
        self.m_image_out_port.close_port()
