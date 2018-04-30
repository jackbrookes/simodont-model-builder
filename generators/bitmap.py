# -*- coding: utf-8 -*-
"""
Created on Mon Feb 20 19:42:00 2017

@author: JackPC
"""

import tkinter as tk
from tkinter import filedialog
import numpy as np
from PIL import Image, ImageTk
GENERATOR_NAME = "Bitmap"
GENERATOR_DESCRIPTION = "Generates data from a single image file and repeats it along another axis"
import os
import PIL.ImageOps

CURRDIR = os.path.normpath(os.path.dirname(__file__))
INITIALDIR = os.path.abspath(os.path.join(CURRDIR, os.pardir, 'bitmaps'))
#print(INITIALDIR)

if __name__ == "__main__":
    app = tk.Tk()


class MainFrame(tk.Frame):

    scalemodes = {"Nearest neighbor": Image.NEAREST,
                  "Bilinear": Image.BILINEAR,
                  "Bicubic": Image.BICUBIC,
                  "Hamming": Image.HAMMING,
                  "Lanczos": Image.LANCZOS,
                  "Box": Image.BOX}


    planes = (0,1,2)

    scalemode = tk.StringVar()
    scalemode.set("Nearest neighbor")
    plane = tk.IntVar()
    plane.set(0)
    segvar = tk.StringVar()
    segvar.set(1)


    def __init__(self, parent, shape, **kwargs):
        self.shape = shape
        tk.Frame.__init__(self, parent, **kwargs)

        tk.Label(self, text="Resizing method (if bitmap size is not equal to the plane shape)",
                 wraplength=200, justify=tk.LEFT).grid(row=1,column=0, sticky="NW")
        tk.OptionMenu(self, self.scalemode, *self.scalemodes.keys()).grid(row=1, column=1, sticky="EW")

        tk.Label(self, text="Plane to apply to",
                 wraplength=200).grid(row=2,column=0, sticky="NW")
        tk.OptionMenu(self, self.plane, *self.planes).grid(row=2, column=1, sticky="EW")

        tk.Label(self, text="Segment to assign white to (1-16)").grid(row=3,column=0, sticky="W")
        tk.Entry(self, textvariable=self.segvar).grid(row=3, column=1)

        tk.Button(self, text="Pick image", command=self.get_image).grid(row=4, column=0, sticky="NEW")
        tk.Button(self, text="Invert image", command=self.invert).grid(row=5, column=0, sticky="NEW")
        self.grid_rowconfigure(5, weight=1)

        self.image = Image.new("RGB", (150, 150), "white")
        photo = ImageTk.PhotoImage(self.image)
        self.imglbl = tk.Label(self, image=photo)
        self.imglbl.image = photo
        self.imglbl.grid(row=4, column=1, rowspan=2, sticky="EW")

    def invert(self):
        self.image = PIL.ImageOps.invert(self.image)
        self.set_image()

    def get_image(self):
        file = filedialog.askopenfilename(initialdir=INITIALDIR)
        if file:
            self.image = Image.open(file).convert(mode="RGB")
            self.set_image()

    def set_image(self):
        thumb = self.image.resize((150, 150), Image.BILINEAR)
        photo = ImageTk.PhotoImage(thumb)
        self.imglbl.config(image = photo)
        self.imglbl.image = photo


    def get_data(self):
        data = {}
        sm = self.scalemodes[self.scalemode.get()]
        ax = self.plane.get()
        planeshape = list(self.shape['iso'])
        othersize = planeshape[ax]
        del planeshape[ax]
        planeshape.reverse()
        resizedimg = self.image.resize(planeshape, sm)

        rgb = np.asarray(resizedimg, dtype=np.uint8)#.transpose((1,0,2))
        bw = np.asarray(resizedimg.convert(mode="L"), dtype=np.uint8)#.transpose((1,0))
        if ax == 0:
            rgb_t = rgb[np.newaxis, :, :]
            bw_t = bw[np.newaxis, :, :]
        elif ax == 1:
            rgb_t = rgb[:, np.newaxis, :]
            bw_t = bw[:, np.newaxis, :]
        else:
            rgb_t = rgb[:, :, np.newaxis]
            bw_t = bw[:, :, np.newaxis]
        seg = int(self.segvar.get())
        seg_t = ((bw_t>127) * seg).astype(np.uint8)
        #print(rgb_t.shape)

        data['color'] = np.repeat(rgb_t, othersize, ax)
        data['density'] = np.repeat(bw_t[:,:,:,np.newaxis], othersize, ax)
        data['iso'] = np.repeat(bw_t, othersize, ax)
        data['segment'] = np.repeat(seg_t[:,:,:,np.newaxis], othersize, ax)

        return data

def capnbit(val, bit):
    ival = int(val)
    return  max(0,min(2**bit-1,ival))

if __name__ == "__main__":
    mf = MainFrame(app)
    tk.Button(app, text="Print data", command=lambda:print(mf.get_data())).pack()
    mf.pack()

    app.mainloop()
