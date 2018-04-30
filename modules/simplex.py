   
import random
random.seed()
#octaves = random.random()
import noise
import numpy as np
from PIL import Image

w = 512
h = 1000
        
octaves = 5
freq = 64 * octaves

def func(x,y):
    n = int(noise.snoise2(x/freq, y/freq, octaves) * 127.0 + 128.0)
    #n = x * y
    return n
vfunc = np.vectorize(func)



#a = np.zeros((h,w), dtype=np.uint8)

a = np.fromfunction(vfunc, (h,w)).astype(np.uint8)


#for y in range(h):
#	for x in range(w):
#         a[y,x] = int(noise.snoise2(x / freq, y / freq, octaves) * 127.0 + 128.0)
         
        


img = Image.fromarray(a, "L")
img.save("img.png")





