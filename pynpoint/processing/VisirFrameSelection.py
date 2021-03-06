# This is a tool that checks the surroundings of the star on high background
# flux and will remove these corresponding frames

import numpy as np
import sys
from pynpoint.core.processing import ProcessingModule
from pynpoint.util.module import progress, memory_frames, \
                             locate_star
import math
import warnings


class VisirFrameSelectionModule(ProcessingModule):
    """
    This is a tool that checks the surroundings of the star on high background
    flux and will remove these corresponding frames
    """

    def __init__(self,
                 name_in="frame_selection",
                 image_in_tag="image_in",
                 image_out_tag="image_out",
                 image_removed="image_rem",
                 std_out="std_out_text",
                 method="median",
                 aperture="3.",
                 fwhm="0.3",
                 num_ref=100,
                 sigma=5.):
        '''
        Constructor of the VisirFrameSelectionModule
        :param name_in: Unique name of the instance
        :type name_in: str
        :param image_in_tag: Engry of the database used as input of the module
        :type image_in_tag: str
        :param image_out_tag: Entry written as output
        :type image_out_tag: str
        :param image_removed: Entry of the removed images written as output
        :type image_removed: str
        :param std_out: Tag that writes the mean/median (depending on the
        method) and in the second column the standard deviation for every frame.
        :type std_out: str
        :param method: Set to "median" or "mean" that is used as reference to
            the sigma clipping
        :type method: str
        :param aperture: Diameter in arcsec used to mask the star, usually
            taken to be a few times the fwhm of the psf
        :type aperture: float
        :param fwhm: fwhm of the star
        :type fwhm: float
        :param num_ref: Number of references used in calculating the mean of
            the background. If this is set to None, all images are used (up to
            where the memory in the configuration file allows)
        :type num_ref: int
        :param sigma: The standard deviation setting the limit which images are
            kept
        :type sigma: float

        :return: None
        '''

        super(VisirFrameSelectionModule, self).__init__(name_in)

        # Port
        self.m_image_in_port = self.add_input_port(image_in_tag)
        self.m_image_out_port = self.add_output_port(image_out_tag)
        self.m_image_out_port_2 = self.add_output_port(image_removed)
        self.m_image_out_port_3 = self.add_output_port(std_out)

        # Parameters
        self.m_method = method
        self.m_aperture = aperture
        self.m_fwhm = fwhm
        self.m_num_ref = num_ref
        self.m_sigma = sigma

    def _initialize(self):
        if self.m_image_out_port is not None:
            if self.m_image_in_port.tag == self.m_image_out_port.tag:
                raise ValueError("Input and output ports should have a "
                                 "different tag.")

        if self.m_image_out_port_2 is not None:
            if self.m_image_in_port.tag == self.m_image_out_port_2.tag:
                raise ValueError("Input and output ports should have a "
                                 "different tag.")

        if self.m_image_out_port_3 is not None:
            if self.m_image_in_port.tag == self.m_image_out_port_3.tag:
                raise ValueError("Input and output ports should have a "
                                 "different tag.")

        if self.m_method != "median" and self.m_method != "mean":
            raise ValueError("The parameter method should be set to "
                             "'median' or 'mean'")

        if not isinstance(self.m_aperture, float):
            raise ValueError("The parameter aperture should be a float")

        if not isinstance(self.m_fwhm, float):
            raise ValueError("The parameter fwhm should be a float")

        if not isinstance(self.m_num_ref, int) and self.m_num_ref is not None:
            raise ValueError("The parameter num_ref should be an integer")

        if not isinstance(self.m_sigma, float):
            raise ValueError("The parameter sigma should be a float")

        if self.m_image_out_port is not None:
            self.m_image_out_port.del_all_data()
            self.m_image_out_port.del_all_attributes()

        if self.m_image_out_port_2 is not None:
            self.m_image_out_port_2.del_all_data()
            self.m_image_out_port_2.del_all_attributes()

        if self.m_image_out_port_3 is not None:
            self.m_image_out_port_3.del_all_data()
            self.m_image_out_port_3.del_all_attributes()

    def _median(self, science_in):
        '''
        This function calculates the median of every image and returns it,
        '''

        med = np.zeros(science_in.shape[0])
        sig = np.zeros(science_in.shape[0])

        for i in range(science_in.shape[0]):
            science_frame = science_in[i, :, :]

            med[i] = np.median(science_frame)
            sig[i] = np.std(science_frame)
        print(med[3])

        return med, sig

    def _mean(self, science_in):
        '''
        This function calculates the mean of every image and returns it,
        including the index which image has which mean
        '''

        mean = np.zeros(science_in.shape[0], dtype=np.float64)
        sig = np.zeros(science_in.shape[0], dtype=np.float64)

        for i in range(science_in.shape[0]):
            science_frame = science_in[i, :, :]

            mean[i] = np.mean(science_frame)
            sig[i] = np.std(science_frame)

        return mean, sig

    def remove_frame(self, science_in, mean, sig):
        '''
        This function removes the frames that have large sigma of the
        mean/median
        '''

        sigma_mean = np.zeros(mean.shape, dtype=np.float64)
        sigma_mean = np.std(mean)

        if self.m_method == "mean":
            tot_mean = np.mean(mean)
        elif self.m_method == "median":
            tot_mean = np.median(mean)
        else:
            raise ValueError("Method input is not properly defined")

        science_out = science_in
        index = np.array([], dtype=np.int64)

        '''
        for i in range(mean.shape[0]):
            check = abs(tot_mean + mean[i])

            if check >= self.m_sigma*sigma_mean:
                    index = np.append(index, i)
        '''

        for i in range(mean.shape[0]):
            if mean[i] <= (tot_mean - self.m_sigma*sigma_mean) or \
                    mean[i] >= (tot_mean + self.m_sigma*sigma_mean):
                index = np.append(index, i)

        index_rev = index[::-1]

        for i in index_rev:
                # print "science_out.shape = ", science_out.shape
                # print "Frame % : ", '{:.0f}'.format((index_rev[0]-i)/index_rev[0]*100.) ,  "    limit- ", '{:.2f}'.format(tot_mean-self.m_sigma*sigma_mean), "    mean: ", '{:.2f}'.format(mean[i]), "    limit+ ", '{:.2f}'.format(tot_mean+self.m_sigma*sigma_mean)
                science_out = np.delete(science_out, i, 0)

        im_rem = np.zeros((len(index), science_in.shape[1],
                           science_in.shape[2]))
        b = 0

        for i in index:
            im_rem[b, :, :] = science_in[i, :, :]
            b += 1

        return science_out, index, im_rem, sigma_mean

    def patch_frame(self, science_frame):
        '''
        Masking of single frame
        '''

        pixscale = self.m_image_in_port.get_attribute("PIXSCALE")

        starpos = np.zeros((2), dtype=np.int64)
        fwhm_starps = int(math.ceil(float(self.m_fwhm) /
                                    (pixscale)))

        starpos[:] = locate_star(image=science_frame,
                                 center=None,
                                 width=None,
                                 fwhm=fwhm_starps)

        radius = int(round(self.m_aperture/2.))

        # Inside every frame mask the pixels around the starpos
        for j in range(radius):
            for jj in range(radius):
                if int(round(math.sqrt((j**2 + jj**2)))) <= radius:
                        science_frame[starpos[0] + j,
                                      starpos[1] + jj] = 0
                        science_frame[starpos[0] - j,
                                      starpos[1] - jj] = 0
                        science_frame[starpos[0] - j,
                                      starpos[1] + jj] = 0
                        science_frame[starpos[0] + j,
                                      starpos[1] - jj] = 0

        return science_frame

    def patch(self, science_in):
        '''
        For the patch of images, pass a single frame trough the function
        patch_frame, and collect the output and return it.
        '''

        science_out = np.zeros(science_in.shape)
        science = science_in.copy()

        for ii in range(science_in.shape[0]):
            science_out[ii, :, :] = \
                self.patch_frame(science_frame=science[ii, :, :])

        return science_out

    def frame(self):
        '''
        This function separates the frames into bunches called patches. The
        mean or median and standard deviation is calculated when a mask of
        size 'aperture' is covered over the star. Then sigma clipping is
        applied onto these and it outputs the selected and removed frames.

        return the removed frames
        '''

        memory = self._m_config_port.get_attribute("MEMORY")
        nimages = number_images_port(self.m_image_in_port)
        # pixscale = self._m_config_port.get_attribute("PIXSCALE")

        if self.m_num_ref is None or self.m_num_ref > nimages or self.m_num_ref == 0:
            self.m_num_ref = nimages

        # if self.m_num_ref > memory:
        #     # self.m_num_ref = memory
        #     warnings.warn("The number of references set is larger than "
        #                   "the memory allowed. Change this in the "
        #                   "configuration file. Memory={}, "
        #                   " num_ref={}".format(memory, self.m_num_ref))

        frames = memory_frames(self.m_num_ref, nimages)

        frames_removed_idx = np.array([], dtype=int)

        # Move trough the seperate frames blocks
        for i, f in enumerate(frames[:-1]):
            progress(i, (len(frames)-1),
                     "Running VisirFrameSelectionModule...")

            frame_start = np.array(frames[i])
            frame_end = np.array(frames[i+1])

            images = self.m_image_in_port[frame_start:frame_end, ]

            # Create mask around PSF
            masked = self.patch(science_in=images)

            # Do the statistics here
            if self.m_method == "mean":
                mean, sig = self._mean(masked)
            elif self.m_method == "median":
                mean, sig = self._median(masked)
            else:
                raise ValueError("Method input is not properly defined")

            good_science, idx, image_rem, sig_tot = \
                self.remove_frame(science_in=images,
                                  mean=mean,
                                  sig=sig)

            idx = idx + f
            frames_removed_idx = np.append(frames_removed_idx, idx)

            result = np.column_stack((mean, sig))

            if i == 0:
                print("Mean/Median = ", np.mean(mean))
                print("Sigma = ", sig_tot)

            self.m_image_out_port.append(good_science)
            self.m_image_out_port_2.append(image_rem)
            self.m_image_out_port_3.append(result)

        sys.stdout.write("Running VisirFrameSelectionModule... [DONE]\n")
        sys.stdout.flush()
        print("Frames removed: \n", frames_removed_idx)

        return frames_removed_idx

    def run(self):
        '''
        Run the method of the module
        '''
        nframes = self.m_image_in_port.get_attribute("NFRAMES")
        # print nframes
        indexx = self.m_image_in_port.get_attribute("INDEX")
        # print indexx
        parang = self.m_image_in_port.get_attribute("PARANG") #PARANG_START?
        # print parang

        im_shape = self.m_image_in_port.get_shape()
        nimages = im_shape[0]
        # print nimages

        self._initialize()
        frames_removed = self.frame()

        frames_removed_new = frames_removed[::-1]
        for i, f in enumerate(frames_removed_new):
            parang = np.delete(parang, f)
        print("length parang now: ", len(parang))
        print("length frames: ", (nimages-len(frames_removed)))

        # print "length parang: ", len(parang)
        # Check this: should be here
            # frames_removed_new = frames_removed[::-1]
            # for i, f in enumerate(frames_removed_new):
            #     parang = np.delete(parang, f)
        # print "length parang now: ", len(parang)
        # print "length frames: ", (nimages-len(frames_removed))

        history = "Number of frames removed ="+str(len(frames_removed))

        self.m_image_out_port.copy_attributes_from_input_port(self.m_image_in_port)
        self.m_image_out_port_2.copy_attributes_from_input_port(self.m_image_in_port)

        self.m_image_out_port.add_attribute("INDEX", np.arange(0, (nimages-len(frames_removed)), 1),
                static=False)
        self.m_image_out_port.add_attribute("PARANG", parang, static=False)
        print("Number frames removed: ", len(frames_removed))
        non_static = self.m_image_in_port.get_all_non_static_attributes()

        # if "NFRAMES" in non_static:
        #     self.m_image_out_port.del_attribute("NFRAMES")

        self.m_image_out_port.add_attribute("Frames_Removed", frames_removed,
                                            static=False)
        self.m_image_out_port.add_history_information("FrameSelectionModule", history)
        self.m_image_out_port.close_port()
        self.m_image_out_port_2.close_port()
        self.m_image_out_port_3.close_port()
