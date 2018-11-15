'''
Module that subtracts the different Nod positions from each other.
This Module should run *after* the chop subtraction.

It assumes that the number of frames taken in every Nod position is the same.

@Jasper Jonker
'''

import numpy as np
import sys
from PynPoint.Core.Processing import ProcessingModule


class VisirInverterModule(ProcessingModule):
    def __init__(self,
                 name_in="Inverter",
                 image_in_tag="image_in",
                 image_out_tag="image_out",
                 nod_type='ABBA'):
        '''
        Constructor of the VisirNodSubtractionModule
        :param name_in: Unique name of the instance
        :type name-in: str
        :param image_in_tag: Entry of the database used as input of the module
        :type image_in_tag: str
        :param image_out_tag: Entry written as output
        :type image_out_tag: str
        :param subtract: Number of images skipped for each cube (by e.g. using
        removing the first frame of every nod position, then set subtract to 1)
        :param subtract: int
        :param nod_type: Type of nodding pattern used. Or ABAB or ABBA
        :type nod_type: str, or ABBA or ABAB

        :return: None
        '''

        super(VisirInverterModule, self).__init__(name_in)

        self.m_nod_type = nod_type

        # Ports
        self.m_image_in_port1 = self.add_input_port(image_in_tag)
        self.m_image_out_port1 = self.add_output_port(image_out_tag)

    def run(self):
        sys.stdout.write("Running VISIRInverterModule...")
        sys.stdout.flush()

        self.m_cubesize = self.m_image_in_port1.get_attribute("NFRAMES")[0]

        # Check that all NFRAMES are the same

        def inverter(signal_in):
            '''
            This function finds the number of images taken every Nod position
            and inverts the second nod position by multiplying it with (-1).

            :return: data_output
            '''

            self.m_no_cube = int(len(signal_in[:, 0, 0]) / self.m_cubesize)

            data_output = np.zeros(signal_in.shape, np.float32)

            if self.m_nod_type == 'ABAB':
                for i in range(self.m_no_cube):
                    if i % 2 == 0:
                        for ii in range(self.m_cubesize):
                            data_output[ii + i*self.m_cubesize, :, :] = \
                                signal_in[ii + i*self.m_cubesize, :, :]
                    else:
                        for ii in range(self.m_cubesize):
                            data_output[ii + i*self.m_cubesize, :, :] = \
                               (-1)*signal_in[ii + i*self.m_cubesize, :, :]

            elif self.m_nod_type == 'ABBA':
                for i in range(self.m_no_cube):
                    if i % 4 == 0 or i % 4 == 3:
                        for ii in range(self.m_cubesize):
                            data_output[ii + i*self.m_cubesize, :, :] = \
                                signal_in[ii + i*self.m_cubesize, :, :]
                    elif i % 4 == 1 or i % 4 == 2:
                        for ii in range(self.m_cubesize):
                            data_output[ii + i*self.m_cubesize, :, :] = \
                               (-1)*signal_in[ii + i*self.m_cubesize, :, :]

            else:
                raise TypeError("Parameter nod_type should be 'ABAB' or"
                                "'ABBA'")

            return data_output

        data_output = inverter(signal_in=self.m_image_in_port1.get_all())

        self.m_image_out_port1.set_all(data_output)

        self.m_image_out_port1.copy_attributes_from_input_port(
            self.m_image_in_port1)
        self.m_image_out_port1.add_history_information(
            "VisirInverterModule", "Inverted the second Nod position")

        self.m_image_out_port1.close_port()

        sys.stdout.write("\rRunning VISIRInverterModule... [DONE]\n")
        sys.stdout.flush()
