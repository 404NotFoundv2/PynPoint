'''
Module that subtracts the different Nod positions from each other.
This Module should run *after* the chop subtraction.

It assumes that the number of frames taken in every Nod position is the same.

@Jasper Jonker
'''

import numpy as np
import sys
import warnings
from pynpoint.core.processing import ProcessingModule


class VisirBurstNodInverterModule(ProcessingModule):
    def __init__(self,
                 name_in="Inverter",
                 image_in_tag_1="image_in_1",
                 image_in_tag_2="image_in_2",
                 image_out_tag="image_out",
                 nod_type='ABBA'):
        '''
        Constructor of the VisirBurstNodInverterModule
        :param name_in: Unique name of the instance
        :type name_in: str
        :param image_in_tag_1: Entry of the database used as input of the module, considerd Nod A
        :type image_in_tag: str
        :param image_in_tag_2: Entry of the database used as input of the module, considerd Nod B
        :type image_in_tag: str
        :param image_out_tag: Entry written as output
        :type image_out_tag: str
        :param subtract: Number of images skipped for each cube (by e.g. using removing the first
            frame of every nod position, then set subtract to 1)
        :param subtract: int
        :param nod_type: Type of nodding pattern used. Or ABAB or ABBA
        :type nod_type: str, or ABBA or ABAB

        :return: None
        '''

        super(VisirBurstNodInverterModule, self).__init__(name_in)

        # Parameters
        self.m_nod_type = nod_type

        # Ports
        self.m_image_in_port1 = self.add_input_port(image_in_tag_1)
        self.m_image_in_port2 = self.add_input_port(image_in_tag_2)
        self.m_image_out_port1 = self.add_output_port(image_out_tag)

    def _initialize(self):
        """
        Function that clears the __init__ tags if they are not
        empty given incorrect input
        """

        if self.m_nod_type != "ABBA" and self.m_nod_type != "ABAB":
            raise ValueError("Check port should be set to 'True' or 'False'")

        if self.m_image_in_port1.tag == self.m_image_out_port1.tag or \
                self.m_image_in_port2.tag == self.m_image_out_port1.tag:
            raise ValueError("Input and output tags should be different")

        if self.m_image_out_port1 is not None:
            self.m_image_out_port1.del_all_data()
            self.m_image_out_port1.del_all_attributes()

    def run(self):
        sys.stdout.write("Running VISIRBurstNodInverterModule...")
        sys.stdout.flush()

        self._initialize()

        shape_1 = self.m_image_in_port1.get_shape()
        shape_2 = self.m_image_in_port2.get_shape()
        if shape_1 != shape_2:
            warnings.warn("Input image size should be the same. Image shape 1 {}, "
                          "is not equal to Image size 2 {}".format(shape_1, shape_2))

        data_output = np.zeros(shape_1, np.float32)

        data_1 = self.m_image_in_port1.get_all()
        data_2 = self.m_image_in_port2.get_all()
        data_output[:, :, :] = data_1[:, :, :] + data_2[:, :, :]

        self.m_image_out_port1.set_all(data_output)

        #self.m_image_out_port1.copy_attributes_from_input_port(self.m_image_in_port1)
        #self.m_image_out_port1.add_history_information("VisirBurstNodInverterModule",
        #                                               "Combined Nod BurstMode")

        sys.stdout.write("\rRunning VISIRBurstNodInverterModule... [DONE]\n")
        sys.stdout.flush()

        self.m_image_out_port1.close_port()
