
import numpy as np
import scipy.io as sio

# load data
stringList = ''
currPos = sio.loadmat('./model.mat'.format(stringList)) 
currAtom = sio.loadmat('./atoms.mat'.format(stringList))
currProjs = sio.loadmat('./projs.mat'.format(stringList))
currAngles =sio.loadmat('./angles.mat'.format(stringList))

currPos = currPos['currModel']
currAtom = currAtom['currAtom'] - 1
currProjs = currProjs['currProjection']
currAngles =currAngles['currAngle']     


np.save('./model.npy',currPos)
np.save('./atoms.npy',currAtom)
np.save('./projs.npy',currProjs)
np.save('./angles.npy',currAngles)