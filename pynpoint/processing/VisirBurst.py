# This tool combines the burst data made every Chop
# @Jasper Jonker

import numpy as np
import sys
from pynpoint.core.processing import ProcessingModule

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

        super(VisirBurtModule, self).__init__(name_in)

        # Port
        self.m_image_in_port = self.add_input_port(image_in_tag)
        self.image_out_port = self.add_output_port(image_out_tag)

        # Parameters
        self.m_method = method

    def _initialize(self):

        return None

    def run(self):
        self._initialize()

        nskip = self.m_image_in_port.get_attribute("NDITSKIP")

        if method == "mean":
            ...
        elif method == "median":
            ...
