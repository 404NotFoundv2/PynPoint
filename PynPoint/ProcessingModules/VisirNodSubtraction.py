'''
Module that 'subtracts' the different Nod positions from each other.
Before the 'subtraction', the module derotates the images according to their
POSANG angle.

This Module should run *after* the chop subtraction and after
VisirInverterModule. VisirInverter inverts the images such that here they are
actually added, not subtracted.

It assumes that the number of frames taken in every Nod position is the same.

@Jasper Jonker
'''

import numpy as np
import sys
from PynPoint.Core.Processing import ProcessingModule
from scipy.ndimage import rotate


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
        self.m_posang_start = \
            self.m_image_in_port1.get_attribute("PARANG_START")
        self.m_posang_end = self.m_image_in_port1.get_attribute("PARANG_END")
        # Check that all NFRAMES are the same

        # data = self.m_image_in_port1.get_all()
        # self.shape_d = data.shape
        # self.m_no_cube = int(len(data[:, 0, 0]) / self.m_cubesize)

        def posangrot(signal_in):
            '''
            This function interpolates the Posang angle for all images.
            '''

            '''
            print '\n', 'Posang start: ', self.m_posang_start, '\n'
            print '\n', 'Posang end: ', self.m_posang_end, '\n'
            print '\n', 'Number of cubes: ', self.m_no_cube, '\n'
            '''

            # self.m_posang_start[0]

            data_out = np.zeros(signal_in.shape)

            for i in range(0, self.m_no_cube, 2):
                posang1 = np.linspace(start=0,
                                      stop=(self.m_posang_end[i] -
                                            self.m_posang_start[i]),
                                      num=self.m_cubesize)

                posang2 = np.linspace(start=0,
                                      stop=(self.m_posang_end[i+1] -
                                            self.m_posang_start[i+1]),
                                      num=self.m_cubesize)
                posang = np.zeros(posang1.shape)

                for ii in range(self.m_cubesize):
                    posang[ii] = 50  # posang2[ii] - posang1[ii]
                    cube1 = signal_in[ii + (i+1)*self.m_cubesize, :, :]
                    im_rot = rotate(input=cube1,
                                    angle=posang[ii],
                                    reshape=False)

                data_out[0:self.m_cubesize + i*self.m_cubesize, :, :] = \
                    signal_in[0:self.m_cubesize, :, :]
                data_out[0:self.m_cubesize + (i+1)*self.m_cubesize, :, :] = \
                    im_rot[:, :, :]

            return data_out

            # Change the attribute Posangangle

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

            # self.shape_d = signal_in.shape
            # self.m_no_cube = int(len(signal_in[:, 0, 0]) / self.m_cubesize)

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

        signal = self.m_image_in_port1.get_all()
        self.shape_d = signal.shape
        self.m_no_cube = int(len(signal[:, 0, 0]) / self.m_cubesize)

        data_rotate = posangrot(signal_in=signal)
        data_output = sepcube(signal_in=data_rotate)

        self.m_image_out_port1.set_all(data_output)

        self.m_image_out_port1.copy_attributes_from_input_port(
            self.m_image_in_port1)
        self.m_image_out_port1.add_history_information(
            "VisirNodSubtractionModule", "Subtracted Nod positions")

        self.m_image_out_port1.close_port()

        sys.stdout.write("\rRunning VISIRNodSubtractionModule... [DONE]\n")
        sys.stdout.flush()
