'''
Module that 'subtracts' (it actually adds) the different Nod positions
from each other. Before the 'subtraction', the module derotates the images
according to their POSANG angle.

This Module should run *after* the chop subtraction and after
VisirInverterModule. VisirInverter inverts the images such that here they are
actually added, not subtracted.

It assumes that the number of frames taken in every Nod position is the same
and that the star is centered.

@Jasper Jonker
'''

import warnings
import sys
import numpy as np
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

        #print '\n', "self.m_posang_start = ", self.m_posang_start
        #print '\n', "self.m_posang_end = ", self.m_posang_end

        for i in range(len(self.m_image_in_port1.get_attribute("NFRAMES"))):
            if self.m_cubesize != \
                    self.m_image_in_port1.get_attribute("NFRAMES")[i]:
                warnings.warn("There is a mismatch in the number of NFRAMES "
                              "in each cube. They should all be equal in "
                              "size.")

        def posangrot(signal_in):
            '''
            This function interpolates the Posang angle for all images.
            It takes NODB and derotates it to get the same rotation as
            NODA has.
            '''

            if signal_in.shape[0]/self.m_cubesize % 2 == 1:
                warnings.warn("The number of Nod positions is not even, "
                              "try removing a single Nod position (one "
                              " fits file)")

            data_out = np.zeros(signal_in.shape)
            im_rot = np.zeros((self.m_cubesize,
                               signal_in.shape[1],
                               signal_in.shape[2]))
            self.m_posang = np.zeros((self.m_cubesize*self.m_no_cube/2))

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
                    posang[ii] = posang1[ii] - posang2[ii]
                    cube1 = signal_in[ii + (i+1)*self.m_cubesize, :, :]

                    im_rot[ii, :, :] = rotate(input=cube1,
                                              angle=posang[ii],
                                              reshape=False)

                    data_out[ii + i*self.m_cubesize, :, :] = \
                        signal_in[ii, :, :]
                    data_out[ii + (i+1)*self.m_cubesize, :, :] = \
                        im_rot[ii, :, :]

                    self.m_posang[ii + i/2*self.m_cubesize] = posang1[ii] \
                            + self.m_posang_start[i]
            '''
            print '\n', 'Shape of self.m_cubesize : ', self.m_cubesize
            print '\n', 'Shape of data_out: ', data_out.shape
            '''
            #print '\n', 'self.m_posang: ', self.m_posang
            #print '\n', 'self.signal.shape: ', signal.shape
            #print '\n', 'shape of self.m_posang: ', self.m_posang.shape

            return data_out

        def sepcube(signal_in):
            '''
            This function finds the number of images taken every Nod position
            and adds the different Nod positions.
            Since the different Chop positions are already subtracted, we are
            left with half of all the images for every Nod position.

            Subtraction of the Nod positions is done in the following way:
            PynPoint saves each Nod position in one big 3D array. The first
            index represents the image number. This index goes from 0 to
            number_of_nod_rotations*images_every_nod_position. This function
            therefore subtracts images by moving the first index by the amount
            of images taken every Nod position.

            :return: data_output
            '''

            data_output = np.zeros((self.m_cubesize*self.m_no_cube/2,
                                    self.shape_d[1], self.shape_d[2]),
                                   dtype=np.float32)

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
            
        im_shape = self.m_image_in_port1.get_shape()
        #index_new = int(im_shape[0]/2)
        #print index_new    
        nframes = self.m_image_in_port1.get_attribute("NFRAMES")
        nframes_new = nframes[:len(nframes)]
        #print nframes_new
            
        self.m_image_out_port1.add_attribute("NFRAMES", nframes_new, static=False)    
        #self.m_image_out_port1.add_attribute("INDEX", index_new, static=False)            
            
            
        self.m_image_out_port1.add_history_information(
            "VisirNodSubtractionModule", "Subtracted Nod")
        self.m_image_out_port1.add_attribute("PARANG", self.m_posang,
                                             static=False)

        self.m_image_out_port1.close_port()

        sys.stdout.write("\rRunning VISIRNodSubtractionModule... [DONE]\n")
        sys.stdout.flush()
