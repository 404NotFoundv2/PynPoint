# This tool combines the burst data made every Chop
# @Jasper Jonker

import numpy as np
from pynpoint.core.processing import ProcessingModule
from pynpoint.util.module import progress, memory_frames, \
                             number_images_port
from pynpoint import FalsePositiveModule


class VisirSensitivityModule(ProcessingModule):
    def __init__(self,
                 name_in="burst",
                 image_in_tag="im_in",
                 image_out_tag="im_out",
                 model_flux=100.):
        '''
        Constructor of the VisirBurtModule
        :param name_in: Unique name of the instance
        :type name_in: str
        :param image_in_tag: Entry of the database used as input of the module
        :type image_in_tag: str
        :param image_out_tag: Entry written as output
        :type image_out_tag: str
        :param model_flux: Flux given in Jansky of the star
        :type method: float

        return None
        '''

        super(VisirSensitivityModule, self).__init__(name_in)

        # Port
        self.m_image_in_port = self.add_input_port(image_in_tag)
        self.image_out_port = self.add_output_port(image_out_tag)

        # Parameters
        self.m_model_flux = model_flux

    def _initialize(self):
        if self.m_image_out_port is not None:
            if self.m_image_in_port.tag == self.m_image_out_port.tag:
                raise ValueError("Input and output ports should have a "
                                 "different tag.")

        if not isinstance(self.m_model_flux, float):
            raise ValueError("The parameter model_flux should be a float")

        if self.m_image_out_port is not None:
            self.m_image_out_port.del_all_data()
            self.m_image_out_port.del_all_attributes()

        return None

    def sensitivity(self, images):
        """"
        Compute the sensitivity of the image for every frame
        """
        im_shape = self.m_image_in_port.get_shape()

        sys.stdout = os.devnull
        sys.stderr = os.devnull

        FalsePositiveModule(position,
                            aperture,
                            ignore,
                            name_in="snr",
                            image_in_tag="images",
                            snr_out_tag)
        pipeline.run_module("snr")

        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        return sensitivity

    def run(self):
        self._initialize()

        memory = self._m_config_port.get_attribute("MEMORY")
        nimages = number_images_port(self.m_image_in_port)
        frames = memory_frames(memory, nimages)

        # Move trough the seperate frames blocks
        for i, f in enumerate(frames[:-1]):
            progress(i, (len(frames)-1),
                     "Running VisirBurstModule...")

            frame_start = np.array(frames[i])
            frame_end = np.array(frames[i+1])

            images = self.m_image_in_port[frame_start:frame_end, ]

            sensitivity = self.sensitivity()

            self.m_image_out_port.append(images_combined)

        self.m_image_out_port.copy_attributes_from_input_port(
            self.m_image_in_port)
        self.m_image_out_port.add_history_information(
            "VisirSensitivityModule", "Sensitivity")
        self.m_image_out_port.close_port()
