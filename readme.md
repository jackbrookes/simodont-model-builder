# Simodont Model Builder [Unofficial]

A user friendly Python 3 application for developing models for use in the Simodont VR dental simulator.

![Simodont model builder banner](/media/smb-banner.png)

## Install & Run

Tested on Windows 10 with Python 3.6. 

1. [Install Python 3.6+](https://www.python.org/downloads/).

2. In a command prompt, clone this repository (or download as a `.zip`)

```
> git clone https://github.com/jackbrookes/simodont-model-builder
```

3. Go to new directory

```
> cd simodont-model-builder
```

4. Install requirements

```
> pip install requirements.txt
```

5. Run the GUI

```
> python smb.py
```

![Simodont model builder screenshot](/media/Capture.PNG)

## How to use

Information available in a PDF [/media/information.pdf](/media/information.pdf).

## Extending the Simodont Model Builder

Users can create their own Python + Tkinter programs - "generators" - which are called upon by the Simodont Model Builder to generate data. Several are pre-installed in the generators folder and can be used as a basis for custom generators. 

Users can use their own bitmaps, image sequences, etc, with the built in generators. 

### Contact me

[http://jbrookes.com/](http://jbrookes.com/)