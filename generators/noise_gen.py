# -*- coding: utf-8 -*-
"""
Created on Mon Feb 20 19:42:00 2017

@author: JackPC
"""

import tkinter as tk
import numpy as np
import noise
GENERATOR_NAME = "Noise"
GENERATOR_DESCRIPTION = "Generates data using perlin noise"


if __name__ == "__main__":
    app = tk.Tk()


class MainFrame(tk.Frame):

    a0var = tk.StringVar()
    a0var.set(8)
    a1var = tk.StringVar()
    a1var.set(8)
    a2var = tk.StringVar()
    a2var.set(8)
    ocvar = tk.StringVar()
    ocvar.set(2)
    seedvar = tk.StringVar()
    seedvar.set(0)
    minvar = tk.StringVar()
    minvar.set(0)
    maxvar = tk.StringVar()
    maxvar.set(255)
    contvar = tk.StringVar()
    contvar.set(0.5)


    def __init__(self, parent, shape=(47,50,55), **kwargs):
        self.shape = shape
        tk.Frame.__init__(self, parent, **kwargs)

        tk.Label(self, text="Axis 0 scale").grid(row=1,column=0, sticky="W")
        tk.Entry(self, textvariable=self.a0var).grid(row=1, column=1)

        tk.Label(self, text="Axis 1 scale").grid(row=2,column=0, sticky="W")
        tk.Entry(self, textvariable=self.a1var).grid(row=2, column=1)

        tk.Label(self, text="Axis 2 scale").grid(row=3,column=0, sticky="W")
        tk.Entry(self, textvariable=self.a2var).grid(row=3, column=1)

        tk.Label(self, text="Octaves (int 1-5ish)").grid(row=4,column=0, sticky="W")
        tk.Entry(self, textvariable=self.ocvar).grid(row=4, column=1)

        tk.Label(self, text="Seed (any number)").grid(row=5,column=0, sticky="W")
        tk.Entry(self, textvariable=self.seedvar).grid(row=5, column=1)

        tk.Label(self, text="Noise min").grid(row=6,column=0, sticky="W")
        tk.Entry(self, textvariable=self.minvar).grid(row=6, column=1)

        tk.Label(self, text="Noise max").grid(row=7,column=0, sticky="W")
        tk.Entry(self, textvariable=self.maxvar).grid(row=7, column=1)

        tk.Label(self, text="Contrast change (-1 to 1)").grid(row=8,column=0, sticky="W")
        tk.Entry(self, textvariable=self.contvar).grid(row=8, column=1)

    def get_data(self):
        freq0 =  float(self.a0var.get())
        freq1 =  float(self.a1var.get())
        freq2 =  float(self.a2var.get())
        octaves =  int(float(self.ocvar.get()))
        seed =  float(self.seedvar.get())
        minv = capnbit(self.minvar.get(), 8)
        maxv = capnbit(self.maxvar.get(), 8)
        k = min(0.999, max(-0.999, float(self.contvar.get())))
        diff = maxv-minv

        def noise_gen(x,y,z):
            n = noise.pnoise3(seed + x/freq0, seed + y/freq1, seed + z/freq2, octaves) * 0.5 + 0.5

            # apply contrast
            if n < 0.5:
                n = ((k*(2*n)-(2*n))/(2*k*(2*n)-k-1))*0.5;
            else:
                n = 0.5*((-k*(2*(n-0.5))-(2*(n-0.5)))/(2*-n*(2*(n-0.5))-(-n)-1))+0.5;

            # return scaled to min/max
            return int(n*diff+minv)

        v_noise_gen = np.vectorize(noise_gen)

        data3d = np.fromfunction(v_noise_gen, self.shape['iso']).astype(np.uint8)

        data = {}
        data['color'] = np.repeat(data3d[:,:,:,np.newaxis], 3, 3)
        data['density'] = data3d[:,:,:,np.newaxis]
        data['iso'] = data3d
        data['segment'] = None


        return data


def capnbit(val, bit):
    ival = int(val)
    return  max(0,min(2**bit-1,ival))

def pr(data):
    for k in data.keys():
        print(data[k].shape, k)

def get_frame(master, shape):
    return MainFrame(master, shape)


if __name__ == "__main__":
    mf = MainFrame(app)
    tk.Button(app, text="Print data", command=lambda:pr(mf.get_data())).pack()
    mf.pack()
    app.mainloop()
