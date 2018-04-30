# -*- coding: utf-8 -*-
"""
Created on Mon Feb 20 19:42:00 2017

@author: JackPC
"""

import tkinter as tk
from tkinter import filedialog
import numpy as np
from PIL import Image, ImageTk
GENERATOR_NAME = "Image sequence"
GENERATOR_DESCRIPTION = "Generates data from a set of image files (in alphabatical order)"
import os
import PIL.ImageOps
from itertools import cycle
from smb import TaskModel
from scipy.ndimage.interpolation import zoom as scipyzoom


CURRDIR = os.path.normpath(os.path.dirname(__file__))
INITIALDIR = os.path.abspath(os.path.join(CURRDIR, os.pardir, 'sequences'))

if __name__ == "__main__":
    app = tk.Tk()


class MainFrame(tk.Frame):


    planes = (0,1,2)
    plane = tk.IntVar()
    plane.set(0)
    int_orders = (0,1,2)
    int_order = tk.IntVar()
    int_order.set(0)
    segvar = tk.StringVar()
    segvar.set(1)


    def __init__(self, parent, shape, **kwargs):
        self.shape = shape
        tk.Frame.__init__(self, parent, **kwargs)

        tk.Label(self, text="Plane to apply to",
                 wraplength=200).grid(row=2,column=0, sticky="NW")
        tk.OptionMenu(self, self.plane, *self.planes).grid(row=2, column=1, sticky="EW")

        tk.Label(self, text="Segment to assign white to (1-16)").grid(row=3,column=0, sticky="W")
        tk.Entry(self, textvariable=self.segvar).grid(row=3, column=1)

        tk.Label(self, text="Interpolation order (NN, linear, 2nd order)",
                 wraplength=300).grid(row=4,column=0, sticky="NW")
        tk.OptionMenu(self, self.int_order, *self.int_orders).grid(row=4, column=1, sticky="EW")

        tk.Button(self, text="Pick image folder", command=self.get_images).grid(row=5, column=0, columnspan=2, sticky="NEW")
        self.grid_rowconfigure(5, weight=1)


        self.images = [Image.new("RGB", (250, 250), "white")]

        self.imglbl = tk.Label(self)
        self.imglbl.grid(row=6, column=0, columnspan=2, sticky="EW")

        tk.Button(self, text="Preview next image >", command=self.skip_image).grid(row=7, column=0, columnspan=2, sticky="NEW")

        self.skip_image(reset = True)

    def get_images(self):
        folder_path = filedialog.askdirectory(initialdir=INITIALDIR, title="Select folder containing the sequence of images")
        if not folder_path: return
        files_in_folder = sorted(os.listdir(folder_path))
        self.images = []
        for file_name in files_in_folder:
            try:
                file_path = os.path.join(folder_path, file_name)
                img = Image.open(file_path).convert(mode="RGB")
                self.images.append(img)
            except OSError:
                print("Skipping file \"{}\", doesnt seem to be an image".format(file_name))
        self.skip_image(reset = True)

    def skip_image(self, reset=False):
        self.i = 0 if reset else self.i + 1
        try:
            img = self.images[self.i % len(self.images)]
            thumb = img.resize((250, 250), Image.BILINEAR)
            photo = ImageTk.PhotoImage(thumb)
            self.imglbl.config(image = photo)
            self.imglbl.image = photo
        except ZeroDivisionError:
            pass

    def get_data(self):
        data = {}
        ax = self.plane.get()
        int_order = self.int_order.get()

        rgb_raw = np.stack(
                           [np.asarray(img,
                                       dtype=np.uint8) for img in self.images])
        bw_raw = np.stack(
                          [np.asarray(img.convert(mode="L"),
                                      dtype=np.uint8) for img in self.images])

        if ax == 0:
            rgb_t = rgb_raw.transpose((0, 1, 2, 3))
            bw_t = bw_raw.transpose((0, 1, 2))
        elif ax == 1:
            rgb_t = rgb_raw.transpose((2, 0, 1, 3))
            bw_t = bw_raw.transpose((2, 0, 1))
        else:
            rgb_t = rgb_raw.transpose((1, 2, 0, 3))
            bw_t = bw_raw.transpose((1, 2, 0))

        seg = int(self.segvar.get())
        seg_t = ((bw_t>127) * seg).astype(np.uint8)

        data['color'] = rgb_t
        data['density'] = bw_t[:,:,:,np.newaxis]
        data['iso'] = bw_t
        data['segment'] = seg_t[:,:,:,np.newaxis]

        for mode in TaskModel.modes:
            if data[mode] is not None:
                order = 0 if mode == "segment" else int_order
                zoom = np.divide(self.shape[mode], data[mode].shape)
                newdata = (scipyzoom(data[mode],
                                     zoom,
                                     order=order)).astype(np.uint8)
                data[mode] = newdata

        return data

def capnbit(val, bit):
    ival = int(val)
    return  max(0,min(2**bit-1,ival))

def get_frame(master, shape):
    return MainFrame(master, shape)


if __name__ == "__main__":
    mf = MainFrame(app)
    tk.Button(app, text="Print data", command=lambda:print(mf.get_data())).pack()
    mf.pack()

    app.mainloop()
