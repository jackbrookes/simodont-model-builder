# -*- coding: utf-8 -*-
"""
Simodont model builder
Script to create, export & import Simodont models
Uses tkinter for GUI
Layers can be created using "generators"
Generators can be dropped into the /generators folder and will auto loaded

Created on Thu Feb  2 10:38:30 2017
@author: Jack Brookes
"""

import os
import stat
import tempfile
import fileinput
import sys
import numpy as np
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox
import ctypes
from PIL import Image, ImageTk
import shutil
import imp
import copy
import zipfile
from scipy.ndimage.interpolation import zoom as scipyzoom
import traceback
import datetime

CURRDIR = os.path.dirname(__file__)
sys.path.append(os.path.join(CURRDIR, "modules"))

try:
    import hover
    import nrrd
    from SBF import VerticalScrolledFrame
except:
    raise

myappid = 'jackbrookes.simodontmodelbuilder.preproduction.1'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


def load_generators():
    """
    Checks for generators in /generators folder and imports them
    """
    gen_folder = os.path.join(CURRDIR, "generators")
    genfiles = []
    for f in os.listdir(gen_folder):
        fullfile = os.path.normpath(os.path.join(gen_folder, f))
        if os.path.isfile(fullfile):
            genfiles.append(fullfile)

    gens = []
    for g in genfiles:
        mod_name, file_ext = os.path.splitext(os.path.split(g)[-1])
        if file_ext.lower() == '.py':
            py_mod = imp.load_source(mod_name, g)
            ispy = True
        elif file_ext.lower() == '.pyc':
            py_mod = imp.load_compiled(mod_name, g)
            ispy = True
        else:
            ispy = False

        if ispy and hasattr(py_mod, "MainFrame"):
            gens.append(Generator(py_mod))

    return gens


class Generator():
    def __init__(self, module):
        self.name = module.GENERATOR_NAME
        self.description = module.GENERATOR_DESCRIPTION
        self.module = module

    def get_frame(self, master):
        shape = get_shapes_dict()
        self.frame = self.module.MainFrame(master, shape)
        return self.frame

    def get_data(self):
        return self.frame.get_data()


class App(tk.Tk):
    def __init__(self, title):
        tk.Tk.__init__(self)
        self.create_fonts()
        self.w, self.h = 1200, 710
        self.x, self.y = 300, 100  # needs to load from last pos on exit
        geo = (self.w, self.h, self.x, self.y)
        self.geometry("%dx%d+%d+%d" % geo)
        self.minsize(self.w, self.h)
        self.title(title)
        # ('winnative', 'clam', 'alt', 'default',
        # 'classic', 'vista', 'xpnative')
        self.set_theme('vista')
        self.load_palettes()
        menubar = self.Menubar(self)
        self.config(menu=menubar)
        self.create_main_panels()

    def create_fonts(self):
        global OVERLAY_FONT, TAB_FONT, SMALL_FONT, TINY_FONT, DARK_GREY
        global MEDIUM_GREY, LIGHT_GREY, CANVAS_BACKGROUND, CANVAS_DARK
        global AXIS_COLOUR_LIST
        global CANVAS_COLOUR_LIST
        OVERLAY_FONT = tkfont.Font(root=self, family="Helvetica",
                                   size=8, weight="bold",
                                   slant="italic")
        TAB_FONT = tkfont.Font(root=self, family="Helvetica",
                               size=8, weight="bold")
        SMALL_FONT = tkfont.Font(root=self, family="Arial",
                                 size=6)
        TINY_FONT = tkfont.Font(root=self, family="Arial",
                                size=6)
        DARK_GREY = "#444"
        MEDIUM_GREY = "#666"
        LIGHT_GREY = "#ddd"
        CANVAS_BACKGROUND = "#e0f0ff"
        CANVAS_DARK = "#363d44"
        r = "#d00000"
        b = "#004cff"
        g = "#0dc609"
        AXIS_COLOUR_LIST = [g, b, r]
        lr = "#e5c6c6"
        lb = "#c6d2ec"
        lg = "#c8e4c8"
        CANVAS_COLOUR_LIST = [lg, lb, lr]

    def load_palettes(self):
        global PALETTE, PALETTE_HEX_LIST

        path = os.path.join(CURRDIR, 'resources', 'palette.csv')
        rawdata = np.genfromtxt(path, delimiter=',').astype(np.uint8)
        PALETTE = rawdata.flatten().tolist()

        PALETTE_HEX_LIST = []
        for r in rawdata:
            hexcode = '#%02x%02x%02x' % tuple(r)
            PALETTE_HEX_LIST.append(hexcode)

    def set_theme(self, theme_name):
        style = ttk.Style()
        style.theme_use(theme_name)

    def create_main_panels(self):
        self.sidebar = self.MainPanel(self, text="Sidebar")
        self.sidebar.pack(fill=tk.BOTH, side=tk.RIGHT,
                          expand=tk.YES,
                          padx=(3, 6), pady=(5, 5))

        self.fill_sidebar()

        self.modelviewer = self.MainPanel(self, text="Model viewer",
                                          width=300)
        self.modelviewer.pack(expand=tk.NO, side=tk.TOP,
                              padx=(6, 3), pady=(5, 5))
        self.fill_modelviewer()

        self.info = self.MainPanel(self, text="Info",
                                   width=300)
        self.info.pack(expand=tk.YES, fill=tk.BOTH,
                       padx=(6, 3), pady=(0, 5))
        self.fill_infopanel()

    def fill_modelviewer(self):
        self.main_mvw = ModelViewerWidget(self.modelviewer,
                                          width=550, height=550)
        self.main_mvw.pack()

    def fill_infopanel(self):
        self.main_iw = InformationWidget(self.info, padx=5)
        self.main_iw.pack(expand=tk.YES, fill=tk.BOTH)

    def fill_sidebar(self):

        self.sidebar.grid_rowconfigure(1, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        genframe = tk.Frame(self.sidebar, padx=10, pady=15)
        genframe.grid(row=0, column=0, sticky="nsew")
        tk.Label(
                 genframe,
                 text="GENERATORS",
                 anchor="w",
                 pady=4,
                 font=OVERLAY_FONT).grid(row=0,
                                         column=0,
                                         columnspan=2,
                                         sticky="w")
        try:
            gens, i = load_generators(), 0
        except Exception as e:
            print(e)
            show_error(e)
        for g in gens:
            genbttn = ttk.Button(
                                 genframe,
                                 text=g.name,
                                 command=(lambda x=g: self.launch_gen(x)))
            genbttn.grid(row=1, column=i, sticky="W")
            hover.createToolTip(genbttn, g.description)
            i += 1

        self.layersystem = LayerSystem(self.sidebar)
        self.layersystem.grid(row=1, column=0, sticky="nsew")

    def launch_gen(self, gen):

        def center_window():
            window.update_idletasks()
            w = window.winfo_screenwidth()
            h = window.winfo_screenheight()
            sizelist = window.geometry().split('+')[0].split('x')
            size = tuple(int(_) for _ in sizelist)
            x = w/2 - size[0]/2
            y = h/2 - size[1]/2
            window.geometry("%dx%d+%d+%d" % (size + (x, y)))

        window = tk.Toplevel(APP)
        window.grab_set()
        window.wm_title("Generator window: {}".format(gen.name))
        tk.Label(window, text="New layer name").grid(row=0,
                                                     column=0,
                                                     sticky="e")

        layername = tk.Entry(window)

        def finish(*args):
            asmask = maskvar.get()
            ln = layername.get()
            if asmask:  # if checkbutton ticked
                ln = "New mask" if ln == "" else ln
            else:
                ln = "New layer" if ln == "" else ln
            # make new layer..
            data = gen.get_data()
            if data is not None:

                if asmask:
                    channel = ddvar.get()
                    self.layersystem.mask_from_data(
                                                    data[channel],
                                                    ln,
                                                    gen.name)
                else:
                    self.layersystem.layer_from_data(data, ln, gen.name)
                window.destroy()
            else:
                print("Generator did not return data")

        def set_dropdown():
            if maskvar.get():  # if checkbutton ticked
                dd.state(["!disabled"])
            else:
                dd.state(["disabled"])

        layername.bind('<Return>', finish)
        layername.grid(row=0, column=1, columnspan=2, sticky="nsew")

        maskvar = tk.IntVar()
        maskvar.set(0)
        masktt = "Data generated will be used as a mask for the layer below it"

        cbl = tk.Label(window, text="Use layer as mask")
        cbl.grid(
                 row=1,
                 column=0,
                 sticky="e")
        hover.createToolTip(cbl, masktt)
        cb = tk.Checkbutton(
                       window,
                       command=set_dropdown,
                       variable=maskvar)
        cb.grid(row=1, column=1, sticky="w")
        hover.createToolTip(cb, masktt)

        ddvar = tk.StringVar()
        dd = ttk.OptionMenu(
                            window,
                            ddvar,
                            "density",
                            "density",
                            "iso")
        dd.grid(row=1, column=2, sticky="w")
        set_dropdown()
        hover.createToolTip(dd, "Data channel to generate mask from")

        ttk.Button(window, text="Done", command=finish).grid(
                                                             row=0,
                                                             column=3,
                                                             rowspan=2,
                                                             sticky="nsew")

        window.grid_columnconfigure(2, weight=1)

        # separator
        tk.Frame(window,
                 height=3,
                 bg=CANVAS_DARK).grid(columnspan=4,
                                      row=2,
                                      sticky="nsew")


        genframe = gen.get_frame(window)
        genframe.grid(row=3, column=0, columnspan=4)
        center_window()

    class Menubar(tk.Menu):
        def __init__(self, parent):
            tk.Menu.__init__(self, parent)
            filemenu = tk.Menu(self, tearoff=0)

            filemenu.add_command(label="New model",
                                 command=new_model)

            filemenu.add_command(label="Load model folder",
                                 command=load_model_folder)

            filemenu.add_command(label="Load model .zip",
                                 command=load_model_zip)

            filemenu.add_separator()

            filemenu.add_command(label="Export model .zip folder",
                                 command=export_model_folder)

            filemenu.add_command(label="Export .nrrds",
                                 command=export_nrrds)

            saveimgmenu = tk.Menu(self, tearoff=0)
            saveimgmenu.add_command(label="1x",
                                    command=lambda: export_image(1))
            saveimgmenu.add_command(label="2x",
                                    command=lambda: export_image(2))
            saveimgmenu.add_command(label="4x",
                                    command=lambda: export_image(4))
            saveimgmenu.add_command(label="8x",
                                    command=lambda: export_image(8))

            filemenu.add_cascade(label="Render views as .pngs",
                                 menu=saveimgmenu)

            filemenu.add_separator()

            filemenu.add_command(label="Exit", command=parent.destroy)
            self.add_cascade(label="File", menu=filemenu)

            editmenu = tk.Menu(self, tearoff=0)
            editmenu.add_command(label="Undo", command=donothing)

            editmenu.add_separator()

#            editmenu.add_command(label="Cut", command=donothing)
#            editmenu.add_command(label="Copy", command=donothing)
#            editmenu.add_command(label="Paste", command=donothing)
#            editmenu.add_command(label="Delete", command=donothing)
#            editmenu.add_command(label="Select All", command=donothing)
#
#            self.add_cascade(label="Edit", menu=editmenu)

            helpmenu = tk.Menu(self, tearoff=0)
            helpmenu.add_command(label="Todo list", command=launch_todo)
            helpmenu.add_command(label="About", command=launch_about)
            self.add_cascade(label="Help", menu=helpmenu)

    class MainPanel(ttk.LabelFrame):
        def __init__(self, parent, **kwargs):
            ttk.LabelFrame.__init__(self, parent,
                                    **kwargs)
            # self.pack_propagate(0)


class LayerSystem(tk.Frame):
    def __init__(self, parent, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs,
                          relief=tk.GROOVE, bg=CANVAS_DARK, height=500)
        self.pack_propagate(0)

        headings = tk.Frame(self, bg=CANVAS_DARK)
        headings.pack(fill=tk.X, padx=(0, VerticalScrolledFrame.width))
        tk.Grid.grid_columnconfigure(headings, 1, weight=1)

        tk.Label(
                 headings,
                 text="LAYERS",
                 font=OVERLAY_FONT,
                 bg=CANVAS_DARK,
                 fg="white",
                 anchor=tk.W,
                 justify=tk.LEFT,
                 bd=3,
                 pady=3).grid(row=0, column=1, sticky="W")

        i = 2
        for m in TASKMODEL.modes:
            tk.Label(
                     headings,
                     text=m.upper(),
                     bg=CANVAS_DARK,
                     fg=LIGHT_GREY,
                     anchor="w",
                     padx=2,
                     width=self.Layer.max_comp_width+2).grid(row=0,
                                                             column=i,
                                                             sticky="w")
            i += 1

        self.layerframe = VerticalScrolledFrame(self)
        self.layerframe.canvas.config(bg=LIGHT_GREY)
        self.layerframe.pack(fill=tk.BOTH, expand=tk.YES)
        self.layers = []

    def export(self):
        TASKMODEL.export(self.data)

    def clear(self):
        for l in self.layers:
            l.destroy()
        self.layers = []
        self.render()

    def layer_from_data(self, data, name, gen="FILE"):
        self.layers.append(self.Layer(self, data, name, gen))
        self.update_layers()
        self.render()

    def mask_from_data(self, maskdata, name, gen):
        self.layers.append(self.Mask(self, maskdata, name, gen))
        self.update_layers()
        self.render()

    def swaplayer(self, chosenlayer, offset):
        idx = self.layers.index(chosenlayer)
        idx2 = (idx + offset) % len(self.layers)
        (self.layers[idx], self.layers[idx2]) = (self.layers[idx2],
                                                 self.layers[idx])
        self.update_layers()
        self.render()

    def update_layers(self):
        for s in self.layerframe.interior.pack_slaves():
            s.pack_forget()
        for l in reversed(self.layers):
            l.pack(fill=tk.X)

    def resize_all(self):
        target_shape = get_shapes_dict()
        for l in self.layers:
            if type(l) == self.Layer:
                for mode in TASKMODEL.modes:
                    if l.data[mode] is not None:
                        order = 0 if mode == "segment" else 1
                        zoom = np.divide(target_shape[mode], l.data[mode].shape)
                        newdata = (scipyzoom(l.data[mode],
                                             zoom,
                                             order=order)).astype(np.uint8)
                        l.data[mode] = newdata
            elif type(l) == self.Mask:
                zoom = np.divide(target_shape['iso'], l.maskdata.shape)
                newdata = (scipyzoom(l.maskdata,
                                     zoom,
                                     order=1)).astype(np.uint8)
                l.maskdata = newdata
    def render(self, *args):
        """Loops through all layers and renders them according to
        layer settings"""

        # blank background
        rendered = gen_blank_data()

        # loop through layers starting from layer 0
        i = 0
        for layer in self.layers:
            if layer.visible and type(layer) != self.Mask:
                mask = self.seek_masks(i)
                for mode in TASKMODEL.modes:
                    if type(mask) is not int:
                        shapedmask = data3d_to_mode(mode, mask)
                    else:
                        shapedmask = mask
                    olddata = np.copy(rendered[mode])
                    output = self.composite_layer(olddata,
                                                  layer,
                                                  shapedmask,
                                                  mode)
                    rendered[mode] = output
            i += 1

        # push data to screen
        APP.main_mvw.push(rendered)

    def seek_masks(self, idx):
        """gets masks directly above the layer at current index"""
        try:
            possible = self.layers[(idx+1):]
        except IndexError:
            possible = []
        mask = 1
        for p in possible:
            if type(p) != self.Mask:
                break
            elif p.visible:
                mask = np.multiply(mask, p.maskdata/255)
        return mask * 255

    def composite_layer(self, olddata, layer, mask, mode):
        comp = layer.composites[mode].get()
        if comp == "DISABLED":
            return olddata
        # multiply mask by opacity
        mask = mask * layer.opacities[mode].get() / 255
        # apply mask to layer data, in multiply case we invert
        if comp == "MULTIPLY":
            newdata = np.multiply(np.subtract(255, layer.data[mode]),
                                  mask).astype(np.uint8)
        else:
            newdata = np.multiply(layer.data[mode], mask).astype(np.uint8)

        if mode != "segment":
            if comp == "REPLACE":
                if newdata.ndim == 4 and mode == 'iso':
                    newdata = newdata.squeeze()
                # REPLACE data, old data shown where mask < 1
                output = (newdata +
                          np.multiply(olddata, (1-mask))).astype(np.uint8)

            elif comp == "ADD":
                # ADD layer data
                diff = 255 - newdata  # a temp uint8 array here
                np.putmask(olddata, diff < olddata, diff)
                output = np.add(
                                olddata,
                                newdata)
            elif comp == "MULTIPLY":

                # MULTIPLY layer data
                output = np.subtract(olddata, np.multiply(newdata/255,
                                     olddata)).astype(np.uint8)
            # if disabled, do nothing
        elif mode == "segment":
            # special settings for segment
            comp = layer.composites[mode].get()
            if comp == "REPLACE":
                output = newdata
            elif comp == "SMART":
                # where there is no new data, use previous data
                np.putmask(newdata, newdata == 0, olddata)
                output = newdata
        else:
            Exception("Unknown mode recieved")

        return output

    class LayerObject(tk.Frame):
        height = 60

        def create_icons(self, objectname):
            # icons
            iconcol = tk.Frame(self)
            iconcol.grid(row=0, column=0, rowspan=2)
            self.visible = True
            self.icons = {}

            def make_icon(name, image, tooltip, command, row, col):
                button = tk.Button(
                                   iconcol,
                                   text=image,
                                   font=SMALL_FONT,
                                   command=command,
                                   relief=tk.FLAT,
                                   overrelief=tk.RAISED,
                                   width=1,
                                   height=1,
                                   pady=0,
                                   bd=2)
                button.grid(column=col, row=row)
                hover.createToolTip(button, tooltip)
                self.icons[name] = button

            icons_args = [(
                           "visible",
                           u"\u2713",
                           "{} visible".format(objectname.capitalize()),
                           self.toggle_visible),

                          ("invert",
                           u"\u25D1",
                           "Invert {} data".format(objectname),
                           self.invert),

                          ("delete",
                           u"\u2613",
                           "Delete {}".format(objectname),
                           self.delete),

                          ("up",
                           u"\u25B2",
                           "Move {} up".format(objectname),
                           self.move_up),

                          ("down",
                           u"\u25BC",
                           "Move {} down".format(objectname),
                           self.move_down)]

            i, nr = 0, 3
            for args in icons_args:
                r = i % nr
                c = i // nr
                make_icon(*args, r, c)
                i += 1
                # skip idx 4
                i = i + 1 if i == 4 else i

        def toggle_visible(self):
            # change icon
            self.visible = not self.visible
            self.parent.render()
            txt = u"\u2713" if self.visible else "-"
            self.icons['visible'].config(text=txt)

        def invert(self):
            for mode in TASKMODEL.compmodes:
                self.data[mode] = 255 - self.data[mode]
            self.parent.render()

        def duplicate(self):
            self.parent.layer_from_data(
                                        copy.deepcopy(self.data),
                                        self.layer_name_var.get(),
                                        self.gen)

        def move_up(self):
            self.move(1)

        def move_down(self):
            self.move(-1)

        def move(self, direction):
            self.parent.swaplayer(self, direction)

        def delete(self):
            self.destroy()
            self.parent.layers.remove(self)
            self.parent.render()

    class Mask(LayerObject):
        def __init__(self, parent, maskdata, name, gen, **kwargs):
            self.parent = parent
            tk.Frame.__init__(
                              self,
                              parent.layerframe.interior,
                              **kwargs,
                              bd=1,
                              padx=2,
                              pady=3,
                              highlightthickness=1,
                              highlightbackground=LIGHT_GREY,
                              height=self.height)
            self.grid_columnconfigure(1, weight=1)
            self.grid_rowconfigure(1, weight=1)
            self.grid_propagate(0)
            self.create_icons("mask")
            self.maskdata = maskdata.squeeze() if maskdata is not None else 1
            self.layer_name_var = tk.StringVar()
            self.layer_name_var.set(name)
            # source
            src = tk.Label(
                     self,
                     anchor="w",
                     font=OVERLAY_FONT,
                     text="MASK: {}".format(gen.upper()))
            src.grid(row=0, column=1, sticky="SEW", padx=3)
            hover.createToolTip(src, "Mask source")

            # name
            ne = ttk.Entry(
                     self,
                     textvariable=self.layer_name_var,
                     width=15)
            ne.grid(row=1, column=1, sticky="EW", padx=3)
            hover.createToolTip(ne, "Mask name")

        def invert(self):

            self.maskdata = 255 - self.maskdata
            self.parent.render()

    class Layer(LayerObject):
        comp_functions = ("", "REPLACE", "ADD", "MULTIPLY", "DISABLED")
        segment_functions = ("", "REPLACE", "SMART", "DISABLED")
        joined_functions = comp_functions + segment_functions
        max_comp_width = max([len(c) for c in joined_functions]) + 3
        no_data_tooltip = "No data generated"

        def __init__(self, parent, data, name, gen, **kwargs):
            self.parent = parent
            tk.Frame.__init__(
                              self,
                              parent.layerframe.interior,
                              **kwargs,
                              bd=1,
                              padx=2,
                              pady=3,
                              highlightthickness=1,
                              highlightbackground=LIGHT_GREY,
                              height=self.height)

            self.gen = gen
            self.layer_name_var = tk.StringVar()
            self.layer_name_var.set(name)
            self.grid_columnconfigure(1, weight=1)
            self.grid_rowconfigure(1, weight=1)
            self.grid_propagate(0)
            self.create_icons("layer")

            # source
            src = tk.Label(
                     self,
                     anchor="w",
                     font=OVERLAY_FONT,
                     text=gen.upper())
            src.grid(row=0, column=1, sticky="SEW", padx=3)
            hover.createToolTip(src, "Layer source")

            # name
            ne = ttk.Entry(
                     self,
                     textvariable=self.layer_name_var,
                     width=15)
            ne.grid(row=1, column=1, sticky="EW", padx=3)
            hover.createToolTip(ne, "Layer name")

            # opacity scale and composite modes
            self.data = data
            self.composites, self.opacities = {}, {}
            i = 2
            for mode in TASKMODEL.compmodes:
                cvar = tk.StringVar()

                bx = ttk.OptionMenu(
                                    self,
                                    cvar,
                                    *self.comp_functions,
                                    command=parent.render)
                bx.grid(row=0, column=i, sticky="ew")
                bx.config(width=self.max_comp_width)
                if data[mode] is None:
                    cvar.set(self.comp_functions[-1])  # disabled
                    bx.state(["disabled"])
                    hover.createToolTip(bx, "No data generated")
                else:
                    cvar.set(self.comp_functions[1])
                    hover.createToolTip(bx, "Blend mode")
                optionmenu_patch(bx, cvar)
                self.composites[mode] = cvar

                scale = ttk.Scale(
                                self,
                                from_=0,
                                to=1,
                                command=parent.render)
                scale.grid(row=1, column=i, sticky="ew")
                scale.set(1)
                hover.createToolTip(scale, "Opacity")
                self.opacities[mode] = scale

                i += 1

            # special options for segment (+ -, diff modes)
            svar = tk.StringVar()
            bx = ttk.OptionMenu(
                                self,
                                svar,
                                *self.segment_functions,
                                command=parent.render)
            bx.grid(row=0, column=i, sticky="ew")
            bx.config(width=self.max_comp_width)
            if data['segment'] is None:
                svar.set(self.segment_functions[-1])  # disabled
                bx.state(["disabled"])
                hover.createToolTip(bx, self.no_data_tooltip)
            else:
                svar.set("SMART")
                hover.createToolTip(bx, "Blend mode")
            optionmenu_patch(bx, svar)
            self.composites['segment'] = svar
            dummyscale = ttk.Scale(self)
            dummyscale.set(1)
            self.opacities['segment'] = dummyscale

            plusminusframe = tk.Frame(self)
            plusminusframe.grid(row=1, column=i, sticky="nsew")
            plusminusframe.grid_columnconfigure((0, 1), weight=1)

            def make_segmod(name, tooltip, amount, col):
                btn = tk.Button(
                                 plusminusframe,
                                 text=name,
                                 relief=tk.FLAT,
                                 overrelief=tk.RAISED,
                                 command=lambda x=amount: self.seg_mod(x))
                btn.grid(row=0, column=col, sticky="nsew")
                if data['segment'] is None:
                    btn.config(state=tk.DISABLED)
                    hover.createToolTip(btn, self.no_data_tooltip)
                else:
                    hover.createToolTip(btn, tooltip)

            make_segmod("-", "Decrement segment", -1, 0)
            make_segmod("+", "Increment segment", 1, 1)

        def seg_mod(self, amount):
            tempdata = np.copy(self.data['segment'])
            if amount > 0:
                buff = 15-amount
                criteria = tempdata > buff
            else:
                buff = -amount
                criteria = tempdata < buff
            np.putmask(tempdata, criteria, buff)
            # modify the data only where data > 0
            np.putmask(tempdata, tempdata > 0,
                       (tempdata + amount).astype(np.uint8))
            self.data['segment'] = tempdata
            self.parent.render()


class ModelViewerWidget(tk.Frame):

    def __init__(self, parent, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)
        self.w = self.cget('width')
        self.h = self.cget('height')

        # general initial blank data
        self.data = {}

        self.zoomlvl = 1

        # widgets
        p, b = 5, 2  # padding and border
        # control frame
        self.controlframe = tk.Frame(self, padx = p, pady = p,
                                     width = self.w / 2 - 2 * (p + b),
                                     height = self.h / 2 - 2 * (p + b),
                                     relief = tk.GROOVE,
                                     bd = b)
        self.controlframe.grid(row = 0, column = 1, sticky = "NSEW")
        self.create_channel_selector()
        # views
        m, n = 2, 2
        self.topview = self.ModelViewerCanvas(self, 0, "Top view", m, n)
        self.topview.grid(row=0, column=0)
        self.frontview = self.ModelViewerCanvas(self, 1, "Front view", m, n)
        self.frontview.grid(row=1, column=0)
        self.sideview = self.ModelViewerCanvas(self, 2,
                                               "Right side view", m, n)
        self.sideview.grid(row=1, column=1)
        self.views = [self.topview, self.frontview, self.sideview]
        self.create_zoomslider(self.controlframe)

    def create_channel_selector(self):
        par = self.controlframe
        modes = TASKMODEL.modes
        self.tabrow = NiceTabRow(par, modes, self.update_data_channel)
        self.tabrow.pack(pady=(6, 12))

    def update_crosssections(self):
        for v in self.views:
            v.update_crosssection()

    def get_images(self):
        images, names = [], []
        for v in self.views:
            images.append(v.orig_img)
            names.append("axis{:d}".format(v.axis))
        return zip(images, names)

    def zoom_all(self):
        for v in self.views:
            v.zoom()

    def update_sliders(self):
        for v in self.views:
            v.update_slider()

    class ModelViewerCanvas(tk.Canvas):

        activecanvas = None

        def __init__(self, parent, axis, axisname, m, n, **kwargs):
            self.axis_colour = AXIS_COLOUR_LIST[axis]
            self.axis_light_colour = CANVAS_COLOUR_LIST[axis]
            self.mvw = parent
            self.hline, self.vline = None, None
            self.index = 0
            self.axisname = "{}. {}".format(axis, axisname)
            self.w = int(self.mvw.w/m)
            self.h = int(self.mvw.h/n)
            tk.Canvas.__init__(self, self.mvw, width=self.w, height=self.h,
                               background=self.axis_light_colour,
                               highlightthickness=0,
                               cursor='crosshair',
                               **kwargs)
            self.axis = axis
            self.other_axes = [0, 1, 2].pop(axis)
            self.create_slider(self.mvw.controlframe)
            self.setup_display()

        def setup_display(self):
            self.image_on_canvas = self.create_image(self.w/2, self.h/2,
                                                     anchor=tk.CENTER)
            self.bind(
                      "<Motion>",
                      self.display_hover)
            self.bind(
                      "<MouseWheel>",
                      self.mouse_wheel)
            self.update_slider()
            self.update_crosssection()

            textframe = tk.Frame(self, bg=self.axis_colour)

            self.canvastext = tk.Label(textframe,
                                       text=self.axisname.upper(),
                                       font=OVERLAY_FONT,
                                       fg="white",
                                       bg=CANVAS_DARK,
                                       padx=7)
            self.canvastext.pack(pady=(0, 3))
            textframe.place(anchor="se", relx=1, rely=1)

            self.hovertxt = self.hoverb = 0


        def slice_data(self):

            try:
                if self.axis == 0:
                    self.data = self.mvw.activedata[self.index, :, :]
                    return self.data
                elif self.axis == 1:
                    self.data = self.mvw.activedata[:, self.index, :]
                    return self.data
                elif self.axis == 2:
                    self.data = self.mvw.activedata[:, :, self.index]
                    return self.data
                else:
                    raise ValueError('Invalid axis supplied')
            except TypeError:
                return None

        def update_crosssection(self):
            dataslice = self.slice_data()
            self.img = self.smart_img_from_array(dataslice)
            self.set_orig_img()
            self.zoom()

        def smart_img_from_array(self, data):
            if data is not None:
                if data.ndim == 2:
                    imgmode = 'L'
                    # data = data.transpose((1,0))
                elif data.ndim == 3 and data.shape[2] == 1:
                    data = np.squeeze(data)
                    imgmode = 'L'
                    # data = data.transpose((1,0))
                elif data.ndim == 3 and data.shape[2] == 3:
                    imgmode = 'RGB'
                    # data = data.transpose((1,0,2))
                else:
                    raise RuntimeError("Cannot interpret array")

                mode = self.mvw.tabrow.tab
                if mode == "segment":
                    img = Image.fromarray(data, "P")
                    img.putpalette(PALETTE)
                else:
                    img = Image.fromarray(data, imgmode)

            else:
                img = Image.new("RGB", (10, 10), "white")
            return img

        def set_orig_img(self):
            """keeps a hold of unscaled image"""
            self.orig_img = self.img
            self.orig_imgw, self.orig_imgh = self.img.size

        def zoom(self):
            new_w = max(1, int(self.orig_imgw * self.mvw.zoomlvl))
            new_h = max(1, int(self.orig_imgh * self.mvw.zoomlvl))
            self.img = self.orig_img.resize((new_w, new_h), Image.NEAREST)
            self.pimg = ImageTk.PhotoImage(self.img)
            self.itemconfig(self.image_on_canvas, image=self.pimg)
            try:
                self.update_all_lines()
            except AttributeError:
                pass

        def update_all_lines(self):
            for v in self.mvw.views:
                self.draw_index_line(
                                     v.index,
                                     v.numlayers,
                                     v.axis)

        def update_slider(self):
            try:
                self.numlayers = self.mvw.activedata.shape[self.axis]
                self.slider.state(["!disabled"])
                self.slider.set_max(self.numlayers-1)
                self.index = min(self.numlayers-1, int(self.slider.value))
            except:
                self.slider.state(["disabled"])

        def create_slider(self, target_frame):
            """if in front view we'll invert the slider, as per orthographic
               projection standard"""
            width = target_frame.cget('width')
            isinverted = self.axis != 0
            self.slider = self.mvw.Slider(
                                          target_frame,
                                          self.axisname, '{0:.0f}',
                                          isinverted,
                                          to=1, length=width,
                                          command=self.slider_callback)

            self.slider.pack()

        def slider_callback(self, sliderval):
            self.index = int(sliderval)
            self.update_crosssection()
            self.mvw.draw_crosssection_lines(
                                             self.index,
                                             self.numlayers,
                                             self.axis)

        def draw_index_line(self, other_index, other_maxindex, other_axis):
            # top view:
            #   front = horizontal
            #   side = vertical
            # front view:
            #   top = horizontal
            #   side = vertical
            # side view:
            #   top = horizontal
            #   front = vertical

            if self.axis == 0:
                if other_axis == 0:
                    return
                elif other_axis == 1:
                    direction = 'horizontal'
                elif other_axis == 2:
                    direction = 'vertical'
            elif self.axis == 1:
                if other_axis == 0:
                    direction = 'horizontal'
                elif other_axis == 1:
                    return
                elif other_axis == 2:
                    direction = 'vertical'
            elif self.axis == 2:
                if other_axis == 0:
                    direction = 'horizontal'
                elif other_axis == 1:
                    direction = 'vertical'
                elif other_axis == 2:
                    return

            line_colour = AXIS_COLOUR_LIST[other_axis]
            other_relindex = other_index - other_maxindex/2
            z = self.mvw.zoomslider.value
            d = max(1, int(z*3))
            if direction == 'horizontal':
                x1 = 0
                x2 = self.w
                y1 = self.h/2 + other_relindex*z
                y2 = y1
                self.delete(self.hline)
                self.hline = self.create_line(x1, y1, x2, y2,
                                              width=2,
                                              fill=line_colour,
                                              dash=(d,))

            if direction == 'vertical':
                x1 = self.w/2 + other_relindex*z
                x2 = x1
                y1 = 0
                y2 = self.h
                self.delete(self.vline)
                self.vline = self.create_line(x1, y1, x2, y2,
                                              width=2,
                                              fill=line_colour,
                                              dash=(d,))

        def display_hover(self, event):
            self.activecanvas = self

            # get current voxel position under cursor
            img_x, img_y = tuple(self.coords(self.image_on_canvas))
            x = event.x - img_x
            y = event.y - img_y
            z = self.mvw.zoomlvl
            ix = int(x/z + self.orig_imgw/2)
            iy = int(y/z  + self.orig_imgh/2)

            strval = self.get_voxel_value(ix, iy)
            if strval:

                # get cursor quartile
                v = 'n' if event.y < self.h/2 else 's'
                h = 'w' if event.x < self.w/2 else 'e'
                xm = 1 if h == 'w' else -1
                ym = 1 if v == 'n' else -1
                xc, yc = 4, 2
                self.delete(self.hovertxt)
                self.hovertxt = self.create_text(
                                                 event.x + (6+xc)*xm,
                                                 event.y + (6+yc)*ym,
                                                 font = TAB_FONT,
                                                 text=strval,
                                                 anchor=v+h)

                textbbox = self.bbox(self.hovertxt)
                textbbox = (textbbox[0] - xc,
                            textbbox[1] - yc,
                            textbbox[2] + xc,
                            textbbox[3] + yc)
                self.delete(self.hoverb)
                self.hoverb = self.create_rectangle(
                                                    textbbox,
                                                    fill="white")
                self.tag_lower(self.hoverb, self.hovertxt)
            else:
                self.hide_hover()

            # hide from others
            for v in self.mvw.views:
                if v.activecanvas != self:
                    v.hide_hover()


        def hide_hover(self):
            self.delete(self.hovertxt)
            self.delete(self.hoverb)

        def mouse_wheel(self, event):
            self.display_hover(event)
            if event.delta == 120:
                self.mvw.forcezoom(0.25)
            elif event.delta == -120:
                self.mvw.forcezoom(-0.25)

        def get_voxel_value(self, x, y):
            try:
                if x < 0 or y < 0: raise IndexError()
                val = self.data[y, x]
                return str(val)
            except IndexError:
                return ""

    def draw_crosssection_lines(self, src_idx, src_maxindex, src_axis):
        a = 0
        for v in self.views:
            # draw lines on all but source view
            if a != src_axis:
                v.draw_index_line(src_idx, src_maxindex, src_axis)
            a += 1

    def push(self, data):
        self.data = data
        self.update_sliders()
        self.update_data_channel()

    def update_data_channel(self, *args):
        self.update_crosssections()

    @property
    def activedata(self):
        try:
            return self.data[self.tabrow.tab]
        except KeyError:
            return None

    def create_zoomslider(self, target_frame):
        width = target_frame.cget('width')
        self.zoomslider = self.Slider(target_frame, 'Zoom', "{0:.2f}x", False,
                                      from_=0.25, to=16.0,
                                      length=width,
                                      command=self.zoomslider_callback,
                                      value=1.0)
        self.zoomslider.pack()

    def zoomslider_callback(self, slider_float):
        self.zoomlvl = slider_float
        self.zoom_all()

    def forcezoom(self, dv):
        self.zoomslider.slide(dv)

    class Slider(ttk.Scale):
        def __init__(self, parent, text, frmtstr, isinverted, **kwargs):
            self.main = tk.Frame(parent)
            tk.Grid.grid_columnconfigure(self.main, 1, weight=1)
            self.label = ttk.Label(self.main, text=text+' -')
            self.label.grid(row=0, column=0)
            self.valuelabel = tk.Label(self.main, fg=MEDIUM_GREY)
            self.valuelabel.grid(row=0, column=1, sticky=tk.W)
            ttk.Scale.__init__(self, self.main, **kwargs)
            ttk.Scale.grid(self, row=1, column=0, columnspan=2)
            self.frmtstr = frmtstr
            self.max = 1
            self.inverted = isinverted
            try:
                self.cb_func = kwargs['command']
                ttk.Scale.config(self, command=self.callback)
            except ValueError:
                pass
            self.update_valuelabel()

        def update_valuelabel(self):
            valstr = self.get()
            valfloat = float(valstr)
            txt = self.frmtstr.format(valfloat)
            self.valuelabel.config(text=txt)

        @property
        def value(self):
            fval = float(self.get())
            if self.inverted:
                newval = self.max - fval
            else:
                newval = fval
            return newval

        def slide(self, dv):
            curr = self.get()
            new = max(curr + dv, 0)
            self.set(new)

        def callback(self, val):
            fval = float(val)
            self.update_valuelabel()
            # invert slider value before sending to function
            if self.inverted:
                newval = self.max - fval
            else:
                newval = fval
            self.cb_func(newval)

        def set_max(self, maxval):
            self.config(to=maxval)
            self.max = maxval
            curr = self.get()
            self.set(min(curr, self.max))

        def pack(self, **kwargs):
            self.main.pack(**kwargs, pady=(5, 0))

        def grid(self, **kwargs):
            self.main.grid(**kwargs)


class InformationWidget(tk.Frame):
    def __init__(self, parent, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)

        self.voxel_size = NiceEntry(self, "Voxel size (m)")
        self.voxel_size.grid(row=1, column=0)

        palframe = tk.Frame(self)
        palframe.grid(row=0, column=4, sticky="ns")
        tk.Label(palframe,
                 text="Segments").pack(fill=tk.BOTH)
        i = 0
        for c in PALETTE_HEX_LIST:
            tk.Label(palframe,
                     text=str(i),
                     bg=c,
                     font=TINY_FONT).pack(side=tk.LEFT)
            i += 1

        self.axis0 = NiceEntry(self, "Axis 0 length")
        self.axis0.grid(row=1, column=1)
        self.axis1 = NiceEntry(self, "Axis 1 length")
        self.axis1.grid(row=1, column=2)
        self.axis2 = NiceEntry(self, "Axis 2 length")
        self.axis2.grid(row=1, column=3)
        for a in [self.axis0, self.axis1, self.axis2]:
            a.enable()
            a.text = "1"
        self.updatebutton = ttk.Button(
                                       self,
                                       text="Resize",
                                       command=self.update)
        self.updatebutton.grid(row=1, column=4, sticky="nsew")
        self.columnconfigure(4, weight=1)

    def update(self):
        APP.layersystem.resize_all()
        APP.layersystem.render()

    def set_shape(self, shape):
        self.shape = shape
        self.axis0.text = str(self.shape[0])
        self.axis1.text = str(self.shape[1])
        self.axis2.text = str(self.shape[2])

    def get_shape(self, *args):
        a = self.axis0.int_val
        b = self.axis1.int_val
        c = self.axis2.int_val
        self.shape = (a, b, c)
        return self.shape


class TaskModel():

    # template
    template_name = "MAN002001"
    template_path = os.path.join(CURRDIR, "template", template_name)

    # should be configurable ?
    zeros = "00000000-0000-0000-0000-000000000000"
    zeroone = "000000000000000000000001"

    compmodes = [
        "color",
        "density",
        "iso"
    ]

    modes = compmodes + ["segment"]

    voxelsize = 0.0002

    mode_folder_names = {}
    for m in modes:
        mode_folder_names[m] = m + "_data"

    def __init__(self):
        self.name = None
        self.new = True
        self.options = {}
        self.mode_file_names = {}
        self.mode_file_paths = {}
        self.screenshot = Image.new("RGB", (10, 10), "white")

    def modelpath_to_datafolder(self, modelpath, name):
        return os.path.join(modelpath, self.zeros,
                            "models", self.zeroone,
                            name)

    def modelpath_to_screenshot(self, modelpath):
        return os.path.join(modelpath, self.zeros,
                            "models", self.zeroone,
                            "screenshot.png")

    def datafolder_to_modefolders(self, datafolder):
        modefolders = {}
        for m in self.modes:
            # construct folder name
            folder_name = os.path.join(datafolder,
                                       self.mode_folder_names[m])
            modefolders[m] = folder_name
        return modefolders

    def get_nrrd_files(self, modelpath):
        mode_file_names, mode_file_paths = {}, {}
        _, name = os.path.split(modelpath)
        datafolder = self.modelpath_to_datafolder(modelpath, name)
        # get mode folders (iso, color etc)
        modefolders = self.datafolder_to_modefolders(datafolder)
        # for each mode...
        for m in self.modes:
            # get files in folder
            files = os.listdir(modefolders[m])
            # check if nrrd file, then add to dictionary
            if len(files) == 1 and ".nrrd" in files[0]:
                path = os.path.join(modefolders[m],
                                    files[0])
                _, mode_file_names[m] = os.path.split(path)
                mode_file_paths[m] = path
            else:
                raise FileNotFoundError("""No .nrrd file found in
                                        {}""".format(modefolders[m]))

        return mode_file_names, mode_file_paths

    def load_model(self, modelpath):
        _, name = os.path.split(modelpath)
        _, mode_file_paths = self.get_nrrd_files(modelpath)
        data = self.load_data(mode_file_paths, name)
        APP.layersystem.clear()
        APP.layersystem.layer_from_data(data, name)

    def setup_template(self):
        (self.mode_file_names,
         self.mode_file_paths) = self.get_nrrd_files(self.template_path)
        self.load_data(self.mode_file_paths, self.template_name)

    def export_model(self, data, zip_path):
        # regenerate options
        name = os.path.splitext(os.path.basename(zip_path))[0]
        self.name = self.sanitise_name(name)
        self.update_options()
        # create zip file
        zip_file = zipfile.ZipFile(zip_path, "w")
        # temp dir
        with tempfile.TemporaryDirectory() as tempdir:
            # copy template to temp directory
            targetdir = os.path.join(tempdir, self.template_name)
            shutil.copytree(
                            self.template_path,
                            targetdir,
                            copy_function=shutil.copy)
            #  give write access
            self.give_write_access(targetdir)
            # get template modelpath
            modelpath = os.path.join(tempdir, self.template_name)
            # get datafolder
            datafolder = self.modelpath_to_datafolder(modelpath,
                                                     self.template_name)

            self.save_nrrds(data, datafolder)

            # rename and move to zip file
            self.move_rename_template(modelpath, zip_file, self.name)


    def save_nrrds(self, data, datafolder, in_subfolders = True):
        # segment data as 16bit
        temp = np.copy(data['segment']).astype(np.uint16)
        seg_16 = np.power(2, temp)
        data['segment'] = seg_16
        # target nrrd files
        for m in self.modes:
            # construct target nrrd file path
            if in_subfolders:
                targetpath = os.path.join(datafolder,
                                          self.mode_folder_names[m],
                                          self.mode_file_names[m])
            else:
                targetpath = os.path.join(datafolder,
                                          self.mode_file_names[m])
            # transpose back
            reshaped = self.reshape_data(data[m])
            # write
            nrrd.write(targetpath, reshaped, options = self.options[m])

    def load_data(self, mode_file_paths, name):
        data = {}
        for mode, path in mode_file_paths.items():
            data[mode], self.options[mode] = self.load_nrrd(path, mode)
        data['segment'] = np.log2(data['segment']).astype(np.uint8)
        APP.main_iw.set_shape(data['iso'].shape)
        self.voxelsize = float(self.options['iso']['spacings'][1])
        APP.main_iw.voxel_size.text = "{:.6f}".format(self.voxelsize)
        self.name = name
        return data

    def load_nrrd(self, file_path, mode):
        fixed_file_path = os.path.normpath(file_path)
        readdata, options = nrrd.read(fixed_file_path)
        data = self.reshape_data(readdata)

        return data.astype(np.uint8), options

    def reshape_data(self, data):
        """
        Checks data type and reshapes it into usable form
        """
        if data.ndim == 4:
            return np.transpose(data, (3, 2, 1, 0))
        elif data.ndim == 3:
            return np.transpose(data, (2, 1, 0))
        else:
            ValueError("Data is not 3 or 4 dimensional")

    def update_options(self):
        self.replace_screenshot()
        # update voxel
        self.voxelsize = float(APP.main_iw.voxel_size.text)
        # shape
        shapes = get_shapes_dict()
        for m in self.modes:
            # reverse shape, since it is transposed
            shape = list(shapes[m])
            shape.reverse()
            # spacings
            if m == 'iso':
                spacings = [str(self.voxelsize)] * 3
            else:
                spacings = ['NaN'] + [str(self.voxelsize)] * 3
            # data type
            if m == 'segment':
                type_ = 'unsigned short'
            else:
                type_ = 'unsigned char'

            self.options[m]['sizes'] = shape
            self.options[m]['spacings'] = spacings
            self.options[m]['type'] = type_
            self.options[m]['endian'] = 'little'

    def give_write_access(self, folder):
        """
        enable write access for folder
        """
        for root, dirs, files in os.walk(folder):
            for fname in files:
                full_path = os.path.join(root, fname)
                os.chmod(full_path, stat.S_IWRITE)
            for dname in dirs:
                full_path = os.path.join(root, dname)
                os.chmod(full_path, stat.S_IWRITE)

    def sanitise_name(self, value):
        """
        Deletes all non-valid filename characters from the string
        """
        return "".join(i for i in value if i not in r'\/:*?"<>|')

    def find_replace_tempname(self, filepath, newname):
        search = self.template_name
        replace = newname
        filepath = os.path.normpath(filepath)
        with fileinput.FileInput(filepath, inplace=True) as file:
            for line in file:
                print(line.replace(search, replace), end="")

        parent, oldfilename = os.path.split(filepath)
        newfilename = oldfilename.replace(self.template_name, newname)
        newpath = os.path.join(parent, newfilename)
        shutil.move(filepath, newpath)

    def move_rename_template(self, tempfolder, zip_file, newname):

        tn = self.template_name

        # temp data folder
        datafolder = self.modelpath_to_datafolder(
                                                 tempfolder,
                                                 tn)

        # modify various files
        lessonxml = os.path.join(datafolder, "{}.xml".format(tn))
        self.find_replace_tempname(lessonxml, newname)
        toothxml = os.path.join(datafolder, "teeth", "tooth_{}.xml".format(tn))
        self.find_replace_tempname(toothxml, newname)
        jawxml = os.path.join(datafolder, "jaws", "jaw_{}.xml".format(tn))
        self.find_replace_tempname(jawxml, newname)
        infojson = os.path.join(datafolder, "..", "info.json")
        self.find_replace_tempname(infojson, newname)

        # replace screenshot
        sspath = self.modelpath_to_screenshot(tempfolder)
        self.screenshot.save(sspath)

        # rename data folder
        pardir, _ = os.path.split(datafolder)
        target = os.path.join(pardir, newname)
        shutil.move(datafolder, target)

        # move all files to zip file
        for dirpath,dirs,files in os.walk(tempfolder):
            for f in files:
                fn = os.path.join(dirpath, f)
                relname = os.path.relpath(fn, tempfolder)
                zip_file.write(fn, relname)


        # target = os.path.join(newfolder, newname)
        # shutil.move(tempfolder, target)

    def replace_screenshot(self):
        images, names = zip(*APP.main_mvw.get_images())
        img = images[0]
        w, h = img.size
        new_w = w * 4
        new_h = h * 4
        self.screenshot = img.resize((new_w, new_h), Image.NEAREST)

    def gen_date_name(self):
        return datetime.datetime.now().strftime("model_%y%m%d_%H%M%S")



def get_shapes_dict():
    shapes = {k: None for k in TASKMODEL.modes}
    shape = APP.main_iw.get_shape()
    shapes['color'] = shape + (3,)
    shapes['density'] = shape + (1,)
    shapes['iso'] = shape
    shapes['segment'] = shape + (1,)
    return shapes


def gen_blank_data():
    blank = {k: None for k in TASKMODEL.modes}
    shapes = get_shapes_dict()
    blank['color'] = np.zeros(shapes['color'], dtype=np.uint8)
    blank['density'] = np.zeros(shapes['density'], dtype=np.uint8)
    blank['iso'] = np.zeros(shapes['iso'], dtype=np.uint8)
    blank['segment'] = np.zeros(shapes['segment'], dtype=np.uint8)

    return blank


def data3d_to_mode(mode, data):
    if mode == "color":
        return np.repeat(data[:, :, :, np.newaxis], 3, 3)
    elif mode == "density" or mode == "segment":
        return data[:, :, :, np.newaxis]
    elif mode == "iso":
        return data


def load_model_zip():
    initial = os.path.join(CURRDIR, "models")
    filetypes = [('Compressed zip folder', '*.zip')]
    raw_file_path = filedialog.askopenfilename(initialdir=initial,
                                               title = "Load model .zip",
                                               parent = APP,
                                               defaultextension = '.zip',
                                               filetypes = filetypes)
    file_path = os.path.normpath(raw_file_path)
    if file_path:
        # open zip file
        with zipfile.ZipFile(file_path, 'r') as model:
            zip_name, _ = os.path.splitext(os.path.basename(file_path))
            # extract zip to temp directory
            with tempfile.TemporaryDirectory() as tempdir:
                temp_model_dir = os.path.join(tempdir, zip_name)
                if not os.path.isdir(temp_model_dir):
                   os.makedirs(temp_model_dir)
                model.extractall(temp_model_dir)
                try:
                    TASKMODEL.load_model(temp_model_dir)
                except FileNotFoundError:
                    messagebox.showinfo("Error",
                                        "Invalid model. Check zip name")



def load_model_folder():
    initial = os.path.join(CURRDIR, "models")
    raw_file_path = filedialog.askdirectory(initialdir=initial,
                                            title = "Load model folder",
                                            parent = APP)
    file_path = os.path.normpath(raw_file_path)
    if file_path:
        try:
            TASKMODEL.load_model(file_path)
        except FileNotFoundError:
            messagebox.showinfo("Error", "Invalid folder")

def export_nrrds():
    indir = os.path.join(CURRDIR, "output")
    ttl = "Select folder to output to"
    raw_file_path = filedialog.askdirectory(title = ttl, parent = APP)
    if raw_file_path:
        file_path = os.path.normpath(raw_file_path)
        defaultname = TASKMODEL.gen_date_name()
        full_path = os.path.join(file_path, defaultname)
        if not os.path.exists(full_path):
            os.makedirs(full_path)
        data = copy.deepcopy(APP.main_mvw.data)
        TASKMODEL.save_nrrds(data, full_path, in_subfolders = False)

def export_model_folder():
    indir = os.path.join(CURRDIR, "output")
    defaultname = TASKMODEL.gen_date_name()
    filetypes = [('Compressed zip folder', '*.zip')]
    raw_file_path = filedialog.asksaveasfilename(
                                                 initialdir = indir,
                                                 defaultextension = '.zip',
                                                 filetypes = filetypes,
                                                 initialfile = defaultname,
                                                 parent = APP)
    if raw_file_path:
        file_path = os.path.normpath(raw_file_path)
        TASKMODEL.export_model(copy.deepcopy(APP.main_mvw.data), file_path)


def new_model():
    TASKMODEL.setup_template()
    APP.layersystem.clear()


class NiceEntry(tk.Frame):
    def __init__(self, parent, name, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs, padx = 5)
        self.textvar = tk.StringVar()
        self.label = ttk.Label(self, text = name)
        self.entry = ttk.Entry(self, textvariable = self.textvar, width = 10)
        # self.entry.state(["disabled"])

        self.label.grid(row = 0, pady = (6, 1), sticky = "W")
        self.entry.grid(row = 1, pady = (0, 3), sticky = "EW")

    @property
    def text(self):
        return self.textvar.get()

    @text.setter
    def text(self, val):
        self.textvar.set(val)

    @property
    def int_val(self):
        try:
            val = int(self.textvar.get())
        except ValueError:
            val = 1
            self.text = "1"
        return val

    def enable(self):
        self.entry.state(["!disabled"])

    def disable(self):
        self.entry.state(["disabled"])


class NiceTabRow(tk.Frame):
    def __init__(self, parent, tabnames, command, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)
        self.tabs = []
        self.tabnames = tabnames
        self.tabvar = tk.StringVar()
        self.tabvar.set(tabnames[0])
        self.command = command
        hover.createToolTip(self, "Currently displayed channel [Ctrl-Tab]")
        for t in tabnames:
            b = self.NiceTabButton(self, text=t.upper(),
                                   variable=self.tabvar,
                                   value=t,
                                   command=command)
            b.pack(side=tk.LEFT)
            self.tabs.append(b)

    @property
    def tab(self):
        return self.tabvar.get()

    @tab.setter
    def tab(self, val):
        self.tabvar.set(val)

    def tabconfig(self, **kwargs):
        for t in self.tabs:
            t.config(**kwargs)

    def cycle(self, event=None):
        idx = self.tabnames.index(self.tab)
        idx2 = (idx+1) % len(self.tabnames)
        self.tab = self.tabnames[idx2]
        self.command()
        # destroys event
        return "break"

    class NiceTabButton(tk.Radiobutton):
        def __init__(self, parent, **kwargs):
            tk.Radiobutton.__init__(self, parent, **kwargs,
                                    indicatoron=0,
                                    font=TAB_FONT,
                                    fg=DARK_GREY,
                                    padx=7)


def donothing():
    print("Not yet implemented")


def export_image(scale):
    ttl = "Select folder to save images in"
    raw_file_path = filedialog.askdirectory(title = ttl, parent = APP)
    file_path = os.path.normpath(raw_file_path)
    if file_path:
        for image, name in APP.main_mvw.get_images():
            w, h = image.size
            new_w = w * scale
            new_h = h * scale
            image = image.resize((new_w, new_h), Image.NEAREST)
            fname = "{}_{}.png".format(APP.main_mvw.tabrow.tab, name)
            image.save(os.path.join(file_path, fname))


def launch_about():
    message = [APP_NAME,
               "Jack Brookes",
               "University of Leeds",
               "ed11jb@leeds.ac.uk"]

    messagebox.showinfo("About", '\n'.join(message))


def launch_todo():
    message = ["Click to move slice lines",
               "More blend modes",
               "Tidy up existing generators",
               "Save/open as bespoke filetype containing layers"]

    messagebox.showinfo("Todo list", '\n'.join(message))


def optionmenu_patch(om, var):
    menu = om['menu']
    last = menu.index("end")
    for i in range(0, last + 1):
        menu.entryconfig(i, variable = var)

def show_error(e):
    messagebox.showinfo("Error", e)


def create_shortcuts():
    APP.bind('<Control-Tab>', APP.main_mvw.tabrow.cycle)


def main():
    global TASKMODEL, APP, APP_NAME
    APP_NAME = "Simodont model builder"
    TASKMODEL = TaskModel()
    APP = App(APP_NAME)
    create_shortcuts()
    new_model()
    APP.mainloop()


if __name__ == "__main__":
    main()
