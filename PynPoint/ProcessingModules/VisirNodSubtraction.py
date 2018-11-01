'''
Module that subtracts the different Nod positions from each other.
This Module should run *after* the chop subtraction.

It assumes that the number of frames taken in every Nod position is the same.

@Jasper Jonker
'''

import numpy as np
import sys
from PynPoint.Core.Processing import ProcessingModule


class VisirNodSubtractionModule(ProcessingModule):
    def __init__(self,
                 name_in="Nod_sub",
                 image_in_tag="image_in",
                 image_out_tag="image_out"):
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

        :return: None
        '''

        super(VisirNodSubtractionModule, self).__init__(name_in)

        # Ports
        self.m_image_in_port1 = self.add_input_port(image_in_tag)
        self.m_image_out_port1 = self.add_output_port(image_out_tag)

    def run(self):
        sys.stdout.write("Running VISIRNodSubtractionModule...")
        sys.stdout.flush()

        self.m_cubesize = self.m_image_in_port1.get_attribute("NFRAMES")[0]
        # - self.m_subtract)

        # Check that all NFRAMES are the same

        data = self.m_image_in_port1.get_all()
        self.shape_d = data.shape

        self.m_no_cube = int(len(data[:, 0, 0]) / self.m_cubesize)

        def sepcube(signal_in):
            '''
            This function finds the number of images taken every Nod position.
            Since the different Chop positions are already subtracted, we are
            left with half of all the images for every Nod position.

            Subtraction of the Nod positions is done in the following way:
            PynPoint saves each Nod position in one big 3D array. The first
            index represents the image number. This index goes from 0 to
            number_of_nod_positions*images_every_nod_position. This function
            therefore subtracts images by moving the first index by the amount
            of images taken every Nod position.

            :return: data_output
            '''

            # print '\n', self.shape_d, '\n'
            # print '\n', self.m_cubesize, '\n'

            data_output = np.zeros((self.m_cubesize*self.m_no_cube/2,
                                    self.shape_d[1], self.shape_d[2]),
                                   np.float32)

            for i in range(self.m_no_cube/2):
                k = self.m_cubesize
                j = i*k

                for ii in range(self.m_cubesize):
                    data_output[ii + j, :, :] = signal_in[ii + 2*j, :, :] + \
                        signal_in[ii + k + 2*j, :, :]

            return data_output

        data_output = sepcube(signal_in=self.m_image_in_port1.get_all())

        self.m_image_out_port1.set_all(data_output)

        self.m_image_out_port1.copy_attributes_from_input_port(
            self.m_image_in_port1)
        self.m_image_out_port1.add_history_information(
            "VisirNodSubtractionModule", "Subtracted Nod positions")

        self.m_image_out_port1.close_port()

        sys.stdout.write("\rRunning VISIRNodSubtractionModule... [DONE]\n")
        sys.stdout.flush()
