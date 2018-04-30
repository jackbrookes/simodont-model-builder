# -*- coding: utf-8 -*-
"""
Created on Mon Feb 20 19:42:00 2017

@author: JackPC
"""

import tkinter as tk
from tkinter import colorchooser
import numpy as np
GENERATOR_NAME = "Solid"
GENERATOR_DESCRIPTION = "Generates a single value for each mode across the model"


if __name__ == "__main__":
    app = tk.Tk()

class MainFrame(tk.Frame):

    denvar = tk.IntVar()
    denvar.set(0)
    segvar = tk.IntVar()
    segvar.set(1)

    def __init__(self, parent, shape=(47,50,50), **kwargs):
        self.shape = shape
        tk.Frame.__init__(self, parent, **kwargs)
        tk.Button(self, text="Pick colour", command=self.get_colour).grid(row=1, column=0, sticky="EW")
        self.clrlbl = tk.Label(self)
        self.clrlbl.grid(row=1, column=1, sticky="EW")
        self.set_colour(((255,255,255),"#FFFFFF"))

        tk.Label(self, text="Density/ISO (0-255)").grid(row=2,column=0, sticky="W")
        tk.Entry(self, textvariable=self.denvar).grid(row=2, column=1)

        tk.Label(self, text="Segment assignment (1-32)").grid(row=3,column=0, sticky="W")
        tk.Entry(self, textvariable=self.segvar).grid(row=3, column=1)

    def get_colour(self):
        colour = colorchooser.askcolor()
        self.set_colour(colour)

    def set_colour(self, colourtuple):
        self.colour = colourtuple[0]
        self.clrlbl.config(bg=colourtuple[1])


    def get_data(self):
        data = {}
        data['color'] = np.full(self.shape['color'], self.colour, dtype=np.uint8)

        try:
            denval = capnbit(self.denvar.get(), 8)
        except tk.TclError:
            print("density error")
            denval = 0

        data['density'] = np.full(self.shape['density'], denval, dtype=np.uint8)
        data['iso'] = np.full(self.shape['iso'], denval, dtype=np.uint8)

        try:
            segval = capnbit(self.segvar.get(), 4)
        except tk.TclError:
            print("segment error")
            segval = 1

        data['segment'] = np.full(self.shape['segment'], segval, dtype=np.uint8)
        #print(data['segment'])
        return data

def capnbit(val, bit):
    ival = int(val)
    return  max(0,min(2**bit-1,ival))

def get_frame(master, shape):
    return MainFrame(master, shape)


if __name__ == "__main__":
    mf = MainFrame(app)
    tk.Button(app, text="Print data", command=lambda:mf.get_data()).pack()
    mf.pack()

    app.mainloop()
