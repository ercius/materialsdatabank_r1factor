# -*- coding: utf-8 -*-
"""
Created on Fri Aug  3 02:55:49 2018

@author: Yongsoo Yang, UCLA Physics & Astronomy
         yongsoo.ysyang@gmail.com
"""

import numpy as np
from scipy.optimize import minimize

# main function for calculating R1 factor using individual atomic scattering factor
def calc_R1_function_indivFA_python(atomPos,atomType,Projections,Angles,Resolution,Axis_array,AtomicNumbers, zDir):    
    
    # rename variables    
    currPos = atomPos
    currAtom = atomType
    currProjs = Projections
    currAngles =Angles    
    volsize = [int(np.max(np.shape(currProjs)) + 20)]
    # BF arary
    # print('starting to get B and H')
    BF_Array = 5*np.ones(len(AtomicNumbers))
    # HT array
    HTFact_Array = np.ones(len(AtomicNumbers))
    [BF_Array,HTFact_Array] = get_handbfac(atomPos,currAtom,currProjs,currAngles,AtomicNumbers,Resolution,Axis_array)
    print('finished H and B optimization')
    print('Bfactors:',BF_Array,'Hfactors:',HTFact_Array)
    CropHalfWidth = int(np.round(np.sqrt(np.average(BF_Array)/8)/np.pi/Resolution*3))
    if CropHalfWidth%2 is 0:
        CropHalfWidth += 1

    # initialize array
    calcProjs = np.zeros(np.shape(currProjs))
        
    # loop over all projections
    for j in range(0,currAngles.shape[0]): 
        
        # calculate rotation matrix based on current input angles and axis convention
        currMAT1 = MatrixQuaternionRot_python(np.array(Axis_array[0]),currAngles[j,0])
        currMAT2 = MatrixQuaternionRot_python(np.array(Axis_array[1]),currAngles[j,1])
        currMAT3 = MatrixQuaternionRot_python(np.array(Axis_array[2]),currAngles[j,2])
      
        MAT = currMAT1*currMAT2*currMAT3;
    
        # apply rotation matrix to the input atomic coordinates
        Model = (np.transpose(MAT) * np.matrix(currPos)).A
        
        # calculate projection based on the atomic model
        cProj = My_create_volProj_from_model_indivFA_python(Model, currAtom, HTFact_Array, BF_Array, AtomicNumbers, volsize, Resolution, CropHalfWidth, zDir)
        
        # determine shift value and crop indices for cropping the calculated projections
        SizeDiff0 = cProj.shape[0] - currProjs.shape[0]
        if SizeDiff0%2 == 0:
            AddShift0 = SizeDiff0 / 2
        else:
            AddShift0 = (SizeDiff0-1) / 2            
      
        SizeDiff1 = cProj.shape[1] - currProjs.shape[1]
        if SizeDiff1%2 == 0:
            AddShift1 = SizeDiff1 / 2
        else:
            AddShift1 = (SizeDiff1-1) / 2            
 
        CropInd0 = np.arange(currProjs.shape[0])
        CropInd0 = list(CropInd0 + int(AddShift0) - 1)
        
        CropInd1 = np.arange(currProjs.shape[1])
        CropInd1 = list(CropInd1 + int(AddShift1) - 1) 
    
        # crop the calculated projection
        calcProjs[:,:,j] = cProj[np.ix_(CropInd0,CropInd1)]

    # calculate R factor
    Rfac = calcR_norm_YY_python(currProjs,calcProjs)
    Rfac = np.round(100*Rfac,decimals=1)
    return [calcProjs,Rfac]


def My_create_volProj_from_model_indivFA_python(model, atomtype, Heights, Bfactors, AtomicNumbers, volsize, Res, CropHalfWidth, zDir):
    
    # rescale model based on pixel resolution
    model = model / Res
    
    # rescale peak heights and B factors
    FHeights = Heights
    FWidths = Bfactors / np.pi**2 / Res**2
    
    # initialize xyz array for the volume
    if len(volsize) == 3:
        x = np.arange(volsize[0]) - np.round((volsize[0]+1)/2.) + 1
        y = np.arange(volsize[1]) - np.round((volsize[1]+1)/2.) + 1
        z = np.arange(volsize[2]) - np.round((volsize[2]+1)/2.) + 1
    elif len(volsize) == 1:
        x = np.arange(volsize[0]) - np.round((volsize[0]+1)/2.) + 1
        y = x
        z = x
    else:
        print('volsize should be either length 3 or length 1!')

    # a variable for the projection size
    sizeX = [len(x), len(y)]
    
    # check if there's any atom outside the projection size
    inInd = np.logical_and(np.logical_and(np.logical_and(np.logical_and (np.logical_and(model[0,:] >= np.min(x) , model[0,:] <= np.max(x)) ,
                 model[1,:] >= np.min(y)), model[1,:] <= np.max(y) ),
                 model[2,:] >= np.min(z)), model[2,:] <= np.max(z))
    

    # take only the atoms inside the projection
    calcModel = model[:,inInd]
    calcAtomtype = atomtype[:,inInd]
    
    
    # initialize projection array
    finalProj_padded = np.zeros( (len(x) + (CropHalfWidth+1)*2, len(y) + (CropHalfWidth+1)*2, len(Heights)))
    
    # proection center position
    cenPos = np.round((np.array(finalProj_padded.shape)+1)/2.)
    
    # local cropping indices for every atom
    cropIndRef = np.arange(-CropHalfWidth,CropHalfWidth+1)
    
    # meshgrid indices for local cropping
    [cropX,cropY] = np.meshgrid(cropIndRef,cropIndRef)
    cropX = cropX.T
    cropY = cropY.T
    
    #loop over all atoms in the model
    for i in range(calcModel.shape[1]):
        
        # obtain local cropping indices for current atom
        if zDir == 2:
            currPos1 = calcModel[0:2,i] + cenPos[0:2]
            currRndPos = np.round(currPos1)
        elif zDir == 1:
            currPos1 = calcModel[[2, 0],i] + cenPos[0:2]
            currRndPos = np.round(currPos1)
            
        
        cropInd1 = cropIndRef + currRndPos[0] -1
        cropInd2 = cropIndRef + currRndPos[1] -1
        
        # crop the local region for current atom
        CropProj = finalProj_padded[np.ix_(list(cropInd1.astype(int)),list(cropInd2.astype(int)),list([calcAtomtype[0,i].astype(int)]))] 

        # sub-pixel position difference for current atom from the center pixel
        diffPos = currPos1-currRndPos;
        
        if zDir == 2:
            diffPosZ = calcModel[2,i] - np.round(calcModel[2,i])
        elif zDir == 1:
            diffPosZ = calcModel[1,i] - np.round(calcModel[1,i])
        
        # calculate Gaussian profile based on the H and B factor
        gaussCalc = (FHeights[calcAtomtype[0,i]]*np.exp( -1.*( (cropX-diffPos[0])**2 + (cropY-diffPos[1])**2 ) / FWidths[calcAtomtype[0,i]] )).reshape(CropProj.shape)
        
        gaussZcalc = (np.exp(-1.*(cropIndRef - diffPosZ)**2 / FWidths[calcAtomtype[0,i]] ))
        
  
        # update the local region in the projection
        finalProj_padded[np.ix_(list(cropInd1.astype(int)),list(cropInd2.astype(int)),list([calcAtomtype[0,i].astype(int)]))] = CropProj + gaussCalc*np.sum(gaussZcalc)

    
    # initialize final projection array
    finalProj_summed = np.zeros( (len(x), len(y)) )
    
    # initialize Fourier indices
    kx = np.arange(1,finalProj_summed.shape[0]+1)
    ky = np.arange(1,finalProj_summed.shape[1]+1)
    
    # apply Fourier resolution
    MultF_X = 1./(len(kx)*Res)
    MultF_Y = 1./(len(ky)*Res)
    
    # initialize q vectors
    CentPos = np.round((np.array(finalProj_summed.shape)+1)/2.)
    [KX, KY] = np.meshgrid((kx-CentPos[0])*MultF_X,(ky-CentPos[1])*MultF_Y)
    KX = KX.T
    KY = KY.T
    q2 = KX**2 + KY**2    
 
    # loop over different type of atoms
    for j in range(len(Heights)):
        # crop to the original size image for current atom type
        CVol = finalProj_padded[(CropHalfWidth+1):(-1-CropHalfWidth),(CropHalfWidth+1):(-1-CropHalfWidth),j]
        
        # FFT
        FVol = np.fft.fftshift(np.fft.fftn(np.fft.ifftshift(CVol)))
        
        # obtain the tabulated electron scattering form factor based on the atomic number        
        currFA = fatom_vector_python( np.sqrt(q2),AtomicNumbers[j] )
        
        # apply the electron scattering factor
        FVol = FVol * currFA.reshape(sizeX)
        
        finalProj_summed =finalProj_summed+FVol
        
    # obtain final projection by IFFT    
    Vol = np.real(np.fft.fftshift(np.fft.ifftn(np.fft.ifftshift(finalProj_summed)))) 

    return Vol

def fparameters_python(Z):
    fparams = np.zeros((104,13))

    fparams[1,0+1] =  4.20298324e-003 
    fparams[1,1+1] =  2.25350888e-001 
    fparams[1,2+1] =  6.27762505e-002 
    fparams[1,3+1] =  2.25366950e-001 
    fparams[1,4+1] =  3.00907347e-002 
    fparams[1,5+1] =  2.25331756e-001 
    fparams[1,6+1] =  6.77756695e-002 
    fparams[1,7+1] =  4.38854001e+000 
    fparams[1,8+1] =  3.56609237e-003 
    fparams[1,9+1] =  4.03884823e-001 
    fparams[1,10+1] =  2.76135815e-002 
    fparams[1,11+1] =  1.44490166e+000 
    fparams[2,0+1] =  1.87543704e-005 
    fparams[2,1+1] =  2.12427997e-001 
    fparams[2,2+1] =  4.10595800e-004 
    fparams[2,3+1] =  3.32212279e-001 
    fparams[2,4+1] =  1.96300059e-001 
    fparams[2,5+1] =  5.17325152e-001 
    fparams[2,6+1] =  8.36015738e-003 
    fparams[2,7+1] =  3.66668239e-001 
    fparams[2,8+1] =  2.95102022e-002 
    fparams[2,9+1] =  1.37171827e+000 
    fparams[2,10+1] =  4.65928982e-007 
    fparams[2,11+1] =  3.75768025e+004 
    fparams[3,0+1] =  7.45843816e-002 
    fparams[3,1+1] =  8.81151424e-001 
    fparams[3,2+1] =  7.15382250e-002 
    fparams[3,3+1] =  4.59142904e-002 
    fparams[3,4+1] =  1.45315229e-001 
    fparams[3,5+1] =  8.81301714e-001 
    fparams[3,6+1] =  1.12125769e+000 
    fparams[3,7+1] =  1.88483665e+001 
    fparams[3,8+1] =  2.51736525e-003 
    fparams[3,9+1] =  1.59189995e-001 
    fparams[3,10+1] =  3.58434971e-001 
    fparams[3,11+1] =  6.12371000e+000 
    fparams[4,0+1] =  6.11642897e-002 
    fparams[4,1+1] =  9.90182132e-002 
    fparams[4,2+1] =  1.25755034e-001 
    fparams[4,3+1] =  9.90272412e-002 
    fparams[4,4+1] =  2.00831548e-001 
    fparams[4,5+1] =  1.87392509e+000 
    fparams[4,6+1] =  7.87242876e-001 
    fparams[4,7+1] =  9.32794929e+000 
    fparams[4,8+1] =  1.58847850e-003 
    fparams[4,9+1] =  8.91900236e-002 
    fparams[4,10+1] =  2.73962031e-001 
    fparams[4,11+1] =  3.20687658e+000 
    fparams[5,0+1] =  1.25716066e-001 
    fparams[5,1+1] =  1.48258830e-001 
    fparams[5,2+1] =  1.73314452e-001 
    fparams[5,3+1] =  1.48257216e-001 
    fparams[5,4+1] =  1.84774811e-001 
    fparams[5,5+1] =  3.34227311e+000 
    fparams[5,6+1] =  1.95250221e-001 
    fparams[5,7+1] =  1.97339463e+000 
    fparams[5,8+1] =  5.29642075e-001 
    fparams[5,9+1] =  5.70035553e+000 
    fparams[5,10+1] =  1.08230500e-003 
    fparams[5,11+1] =  5.64857237e-002 
    fparams[6,0+1] =  2.12080767e-001 
    fparams[6,1+1] =  2.08605417e-001 
    fparams[6,2+1] =  1.99811865e-001 
    fparams[6,3+1] =  2.08610186e-001 
    fparams[6,4+1] =  1.68254385e-001 
    fparams[6,5+1] =  5.57870773e+000 
    fparams[6,6+1] =  1.42048360e-001 
    fparams[6,7+1] =  1.33311887e+000 
    fparams[6,8+1] =  3.63830672e-001 
    fparams[6,9+1] =  3.80800263e+000 
    fparams[6,10+1] =  8.35012044e-004 
    fparams[6,11+1] =  4.03982620e-002 
    fparams[7,0+1] =  5.33015554e-001 
    fparams[7,1+1] =  2.90952515e-001 
    fparams[7,2+1] =  5.29008883e-002 
    fparams[7,3+1] =  1.03547896e+001 
    fparams[7,4+1] =  9.24159648e-002 
    fparams[7,5+1] =  1.03540028e+001 
    fparams[7,6+1] =  2.61799101e-001 
    fparams[7,7+1] =  2.76252723e+000 
    fparams[7,8+1] =  8.80262108e-004 
    fparams[7,9+1] =  3.47681236e-002 
    fparams[7,10+1] =  1.10166555e-001 
    fparams[7,11+1] =  9.93421736e-001 
    fparams[8,0+1] =  3.39969204e-001 
    fparams[8,1+1] =  3.81570280e-001 
    fparams[8,2+1] =  3.07570172e-001 
    fparams[8,3+1] =  3.81571436e-001 
    fparams[8,4+1] =  1.30369072e-001 
    fparams[8,5+1] =  1.91919745e+001 
    fparams[8,6+1] =  8.83326058e-002 
    fparams[8,7+1] =  7.60635525e-001 
    fparams[8,8+1] =  1.96586700e-001 
    fparams[8,9+1] =  2.07401094e+000 
    fparams[8,10+1] =  9.96220028e-004 
    fparams[8,11+1] =  3.03266869e-002 
    fparams[9,0+1] =  2.30560593e-001 
    fparams[9,1+1] =  4.80754213e-001 
    fparams[9,2+1] =  5.26889648e-001 
    fparams[9,3+1] =  4.80763895e-001 
    fparams[9,4+1] =  1.24346755e-001 
    fparams[9,5+1] =  3.95306720e+001 
    fparams[9,6+1] =  1.24616894e-003 
    fparams[9,7+1] =  2.62181803e-002 
    fparams[9,8+1] =  7.20452555e-002 
    fparams[9,9+1] =  5.92495593e-001 
    fparams[9,10+1] =  1.53075777e-001 
    fparams[9,11+1] =  1.59127671e+000 
    fparams[10,0+1] =  4.08371771e-001 
    fparams[10,1+1] =  5.88228627e-001 
    fparams[10,2+1] =  4.54418858e-001 
    fparams[10,3+1] =  5.88288655e-001 
    fparams[10,4+1] =  1.44564923e-001 
    fparams[10,5+1] =  1.21246013e+002 
    fparams[10,6+1] =  5.91531395e-002 
    fparams[10,7+1] =  4.63963540e-001 
    fparams[10,8+1] =  1.24003718e-001 
    fparams[10,9+1] =  1.23413025e+000 
    fparams[10,10+1] =  1.64986037e-003 
    fparams[10,11+1] =  2.05869217e-002 
    fparams[11,0+1] =  1.36471662e-001 
    fparams[11,1+1] =  4.99965301e-002 
    fparams[11,2+1] =  7.70677865e-001 
    fparams[11,3+1] =  8.81899664e-001 
    fparams[11,4+1] =  1.56862014e-001 
    fparams[11,5+1] =  1.61768579e+001 
    fparams[11,6+1] =  9.96821513e-001 
    fparams[11,7+1] =  2.00132610e+001 
    fparams[11,8+1] =  3.80304670e-002 
    fparams[11,9+1] =  2.60516254e-001 
    fparams[11,10+1] =  1.27685089e-001 
    fparams[11,11+1] =  6.99559329e-001 
    fparams[12,0+1] =  3.04384121e-001 
    fparams[12,1+1] =  8.42014377e-002 
    fparams[12,2+1] =  7.56270563e-001 
    fparams[12,3+1] =  1.64065598e+000 
    fparams[12,4+1] =  1.01164809e-001 
    fparams[12,5+1] =  2.97142975e+001 
    fparams[12,6+1] =  3.45203403e-002 
    fparams[12,7+1] =  2.16596094e-001 
    fparams[12,8+1] =  9.71751327e-001 
    fparams[12,9+1] =  1.21236852e+001 
    fparams[12,10+1] =  1.20593012e-001 
    fparams[12,11+1] =  5.60865838e-001 
    fparams[13,0+1] =  7.77419424e-001 
    fparams[13,1+1] =  2.71058227e+000 
    fparams[13,2+1] =  5.78312036e-002 
    fparams[13,3+1] =  7.17532098e+001 
    fparams[13,4+1] =  4.26386499e-001 
    fparams[13,5+1] =  9.13331555e-002 
    fparams[13,6+1] =  1.13407220e-001 
    fparams[13,7+1] =  4.48867451e-001 
    fparams[13,8+1] =  7.90114035e-001 
    fparams[13,9+1] =  8.66366718e+000 
    fparams[13,10+1] =  3.23293496e-002 
    fparams[13,11+1] =  1.78503463e-001 
    fparams[14,0+1] =  1.06543892e+000 
    fparams[14,1+1] =  1.04118455e+000 
    fparams[14,2+1] =  1.20143691e-001 
    fparams[14,3+1] =  6.87113368e+001 
    fparams[14,4+1] =  1.80915263e-001 
    fparams[14,5+1] =  8.87533926e-002 
    fparams[14,6+1] =  1.12065620e+000 
    fparams[14,7+1] =  3.70062619e+000 
    fparams[14,8+1] =  3.05452816e-002 
    fparams[14,9+1] =  2.14097897e-001 
    fparams[14,10+1] =  1.59963502e+000 
    fparams[14,11+1] =  9.99096638e+000 
    fparams[15,0+1] =  1.05284447e+000 
    fparams[15,1+1] =  1.31962590e+000 
    fparams[15,2+1] =  2.99440284e-001 
    fparams[15,3+1] =  1.28460520e-001 
    fparams[15,4+1] =  1.17460748e-001 
    fparams[15,5+1] =  1.02190163e+002 
    fparams[15,6+1] =  9.60643452e-001 
    fparams[15,7+1] =  2.87477555e+000 
    fparams[15,8+1] =  2.63555748e-002 
    fparams[15,9+1] =  1.82076844e-001 
    fparams[15,10+1] =  1.38059330e+000 
    fparams[15,11+1] =  7.49165526e+000 
    fparams[16,0+1] =  1.01646916e+000 
    fparams[16,1+1] =  1.69181965e+000 
    fparams[16,2+1] =  4.41766748e-001 
    fparams[16,3+1] =  1.74180288e-001 
    fparams[16,4+1] =  1.21503863e-001 
    fparams[16,5+1] =  1.67011091e+002 
    fparams[16,6+1] =  8.27966670e-001 
    fparams[16,7+1] =  2.30342810e+000 
    fparams[16,8+1] =  2.33022533e-002 
    fparams[16,9+1] =  1.56954150e-001 
    fparams[16,10+1] =  1.18302846e+000 
    fparams[16,11+1] =  5.85782891e+000 
    fparams[17,0+1] =  9.44221116e-001 
    fparams[17,1+1] =  2.40052374e-001 
    fparams[17,2+1] =  4.37322049e-001 
    fparams[17,3+1] =  9.30510439e+000 
    fparams[17,4+1] =  2.54547926e-001 
    fparams[17,5+1] =  9.30486346e+000 
    fparams[17,6+1] =  5.47763323e-002 
    fparams[17,7+1] =  1.68655688e-001 
    fparams[17,8+1] =  8.00087488e-001 
    fparams[17,9+1] =  2.97849774e+000 
    fparams[17,10+1] =  1.07488641e-002 
    fparams[17,11+1] =  6.84240646e-002 
    fparams[18,0+1] =  1.06983288e+000 
    fparams[18,1+1] =  2.87791022e-001 
    fparams[18,2+1] =  4.24631786e-001 
    fparams[18,3+1] =  1.24156957e+001 
    fparams[18,4+1] =  2.43897949e-001 
    fparams[18,5+1] =  1.24158868e+001 
    fparams[18,6+1] =  4.79446296e-002 
    fparams[18,7+1] =  1.36979796e-001 
    fparams[18,8+1] =  7.64958952e-001 
    fparams[18,9+1] =  2.43940729e+000 
    fparams[18,10+1] =  8.23128431e-003 
    fparams[18,11+1] =  5.27258749e-002 
    fparams[19,0+1] =  6.92717865e-001 
    fparams[19,1+1] =  7.10849990e+000 
    fparams[19,2+1] =  9.65161085e-001 
    fparams[19,3+1] =  3.57532901e-001 
    fparams[19,4+1] =  1.48466588e-001 
    fparams[19,5+1] =  3.93763275e-002 
    fparams[19,6+1] =  2.64645027e-002 
    fparams[19,7+1] =  1.03591321e-001 
    fparams[19,8+1] =  1.80883768e+000 
    fparams[19,9+1] =  3.22845199e+001 
    fparams[19,10+1] =  5.43900018e-001 
    fparams[19,11+1] =  1.67791374e+000 
    fparams[20,0+1] =  3.66902871e-001 
    fparams[20,1+1] =  6.14274129e-002 
    fparams[20,2+1] =  8.66378999e-001 
    fparams[20,3+1] =  5.70881727e-001 
    fparams[20,4+1] =  6.67203300e-001 
    fparams[20,5+1] =  7.82965639e+000 
    fparams[20,6+1] =  4.87743636e-001 
    fparams[20,7+1] =  1.32531318e+000 
    fparams[20,8+1] =  1.82406314e+000 
    fparams[20,9+1] =  2.10056032e+001 
    fparams[20,10+1] =  2.20248453e-002 
    fparams[20,11+1] =  9.11853450e-002 
    fparams[21,0+1] =  3.78871777e-001 
    fparams[21,1+1] =  6.98910162e-002 
    fparams[21,2+1] =  9.00022505e-001 
    fparams[21,3+1] =  5.21061541e-001 
    fparams[21,4+1] =  7.15288914e-001 
    fparams[21,5+1] =  7.87707920e+000 
    fparams[21,6+1] =  1.88640973e-002 
    fparams[21,7+1] =  8.17512708e-002 
    fparams[21,8+1] =  4.07945949e-001 
    fparams[21,9+1] =  1.11141388e+000 
    fparams[21,10+1] =  1.61786540e+000 
    fparams[21,11+1] =  1.80840759e+001 
    fparams[22,0+1] =  3.62383267e-001 
    fparams[22,1+1] =  7.54707114e-002 
    fparams[22,2+1] =  9.84232966e-001 
    fparams[22,3+1] =  4.97757309e-001 
    fparams[22,4+1] =  7.41715642e-001 
    fparams[22,5+1] =  8.17659391e+000 
    fparams[22,6+1] =  3.62555269e-001 
    fparams[22,7+1] =  9.55524906e-001 
    fparams[22,8+1] =  1.49159390e+000 
    fparams[22,9+1] =  1.62221677e+001 
    fparams[22,10+1] =  1.61659509e-002 
    fparams[22,11+1] =  7.33140839e-002 
    fparams[23,0+1] =  3.52961378e-001 
    fparams[23,1+1] =  8.19204103e-002 
    fparams[23,2+1] =  7.46791014e-001 
    fparams[23,3+1] =  8.81189511e+000 
    fparams[23,4+1] =  1.08364068e+000 
    fparams[23,5+1] =  5.10646075e-001 
    fparams[23,6+1] =  1.39013610e+000 
    fparams[23,7+1] =  1.48901841e+001 
    fparams[23,8+1] =  3.31273356e-001 
    fparams[23,9+1] =  8.38543079e-001 
    fparams[23,10+1] =  1.40422612e-002 
    fparams[23,11+1] =  6.57432678e-002 
    fparams[24,0+1] =  1.34348379e+000 
    fparams[24,1+1] =  1.25814353e+000 
    fparams[24,2+1] =  5.07040328e-001 
    fparams[24,3+1] =  1.15042811e+001 
    fparams[24,4+1] =  4.26358955e-001 
    fparams[24,5+1] =  8.53660389e-002 
    fparams[24,6+1] =  1.17241826e-002 
    fparams[24,7+1] =  6.00177061e-002 
    fparams[24,8+1] =  5.11966516e-001 
    fparams[24,9+1] =  1.53772451e+000 
    fparams[24,10+1] =  3.38285828e-001 
    fparams[24,11+1] =  6.62418319e-001 
    fparams[25,0+1] =  3.26697613e-001 
    fparams[25,1+1] =  8.88813083e-002 
    fparams[25,2+1] =  7.17297000e-001 
    fparams[25,3+1] =  1.11300198e+001 
    fparams[25,4+1] =  1.33212464e+000 
    fparams[25,5+1] =  5.82141104e-001 
    fparams[25,6+1] =  2.80801702e-001 
    fparams[25,7+1] =  6.71583145e-001 
    fparams[25,8+1] =  1.15499241e+000 
    fparams[25,9+1] =  1.26825395e+001 
    fparams[25,10+1] =  1.11984488e-002 
    fparams[25,11+1] =  5.32334467e-002 
    fparams[26,0+1] =  3.13454847e-001 
    fparams[26,1+1] =  8.99325756e-002 
    fparams[26,2+1] =  6.89290016e-001 
    fparams[26,3+1] =  1.30366038e+001 
    fparams[26,4+1] =  1.47141531e+000 
    fparams[26,5+1] =  6.33345291e-001 
    fparams[26,6+1] =  1.03298688e+000 
    fparams[26,7+1] =  1.16783425e+001 
    fparams[26,8+1] =  2.58280285e-001 
    fparams[26,9+1] =  6.09116446e-001 
    fparams[26,10+1] =  1.03460690e-002 
    fparams[26,11+1] =  4.81610627e-002 
    fparams[27,0+1] =  3.15878278e-001 
    fparams[27,1+1] =  9.46683246e-002 
    fparams[27,2+1] =  1.60139005e+000 
    fparams[27,3+1] =  6.99436449e-001 
    fparams[27,4+1] =  6.56394338e-001 
    fparams[27,5+1] =  1.56954403e+001 
    fparams[27,6+1] =  9.36746624e-001 
    fparams[27,7+1] =  1.09392410e+001 
    fparams[27,8+1] =  9.77562646e-003 
    fparams[27,9+1] =  4.37446816e-002 
    fparams[27,10+1] =  2.38378578e-001 
    fparams[27,11+1] =  5.56286483e-001 
    fparams[28,0+1] =  1.72254630e+000 
    fparams[28,1+1] =  7.76606908e-001 
    fparams[28,2+1] =  3.29543044e-001 
    fparams[28,3+1] =  1.02262360e-001 
    fparams[28,4+1] =  6.23007200e-001 
    fparams[28,5+1] =  1.94156207e+001 
    fparams[28,6+1] =  9.43496513e-003 
    fparams[28,7+1] =  3.98684596e-002 
    fparams[28,8+1] =  8.54063515e-001 
    fparams[28,9+1] =  1.04078166e+001 
    fparams[28,10+1] =  2.21073515e-001 
    fparams[28,11+1] =  5.10869330e-001 
    fparams[29,0+1] =  3.58774531e-001 
    fparams[29,1+1] =  1.06153463e-001 
    fparams[29,2+1] =  1.76181348e+000 
    fparams[29,3+1] =  1.01640995e+000 
    fparams[29,4+1] =  6.36905053e-001 
    fparams[29,5+1] =  1.53659093e+001 
    fparams[29,6+1] =  7.44930667e-003 
    fparams[29,7+1] =  3.85345989e-002 
    fparams[29,8+1] =  1.89002347e-001 
    fparams[29,9+1] =  3.98427790e-001 
    fparams[29,10+1] =  2.29619589e-001 
    fparams[29,11+1] =  9.01419843e-001 
    fparams[30,0+1] =  5.70893973e-001 
    fparams[30,1+1] =  1.26534614e-001 
    fparams[30,2+1] =  1.98908856e+000 
    fparams[30,3+1] =  2.17781965e+000 
    fparams[30,4+1] =  3.06060585e-001 
    fparams[30,5+1] =  3.78619003e+001 
    fparams[30,6+1] =  2.35600223e-001 
    fparams[30,7+1] =  3.67019041e-001 
    fparams[30,8+1] =  3.97061102e-001 
    fparams[30,9+1] =  8.66419596e-001 
    fparams[30,10+1] =  6.85657228e-003 
    fparams[30,11+1] =  3.35778823e-002 
    fparams[31,0+1] =  6.25528464e-001 
    fparams[31,1+1] =  1.10005650e-001 
    fparams[31,2+1] =  2.05302901e+000 
    fparams[31,3+1] =  2.41095786e+000 
    fparams[31,4+1] =  2.89608120e-001 
    fparams[31,5+1] =  4.78685736e+001 
    fparams[31,6+1] =  2.07910594e-001 
    fparams[31,7+1] =  3.27807224e-001 
    fparams[31,8+1] =  3.45079617e-001 
    fparams[31,9+1] =  7.43139061e-001 
    fparams[31,10+1] =  6.55634298e-003 
    fparams[31,11+1] =  3.09411369e-002 
    fparams[32,0+1] =  5.90952690e-001 
    fparams[32,1+1] =  1.18375976e-001 
    fparams[32,2+1] =  5.39980660e-001 
    fparams[32,3+1] =  7.18937433e+001 
    fparams[32,4+1] =  2.00626188e+000 
    fparams[32,5+1] =  1.39304889e+000 
    fparams[32,6+1] =  7.49705041e-001 
    fparams[32,7+1] =  6.89943350e+000 
    fparams[32,8+1] =  1.83581347e-001 
    fparams[32,9+1] =  3.64667232e-001 
    fparams[32,10+1] =  9.52190743e-003 
    fparams[32,11+1] =  2.69888650e-002 
    fparams[33,0+1] =  7.77875218e-001 
    fparams[33,1+1] =  1.50733157e-001 
    fparams[33,2+1] =  5.93848150e-001 
    fparams[33,3+1] =  1.42882209e+002 
    fparams[33,4+1] =  1.95918751e+000 
    fparams[33,5+1] =  1.74750339e+000 
    fparams[33,6+1] =  1.79880226e-001 
    fparams[33,7+1] =  3.31800852e-001 
    fparams[33,8+1] =  8.63267222e-001 
    fparams[33,9+1] =  5.85490274e+000 
    fparams[33,10+1] =  9.59053427e-003 
    fparams[33,11+1] =  2.33777569e-002 
    fparams[34,0+1] =  9.58390681e-001 
    fparams[34,1+1] =  1.83775557e-001 
    fparams[34,2+1] =  6.03851342e-001 
    fparams[34,3+1] =  1.96819224e+002 
    fparams[34,4+1] =  1.90828931e+000 
    fparams[34,5+1] =  2.15082053e+000 
    fparams[34,6+1] =  1.73885956e-001 
    fparams[34,7+1] =  3.00006024e-001 
    fparams[34,8+1] =  9.35265145e-001 
    fparams[34,9+1] =  4.92471215e+000 
    fparams[34,10+1] =  8.62254658e-003 
    fparams[34,11+1] =  2.12308108e-002 
    fparams[35,0+1] =  1.14136170e+000 
    fparams[35,1+1] =  2.18708710e-001 
    fparams[35,2+1] =  5.18118737e-001 
    fparams[35,3+1] =  1.93916682e+002 
    fparams[35,4+1] =  1.85731975e+000 
    fparams[35,5+1] =  2.65755396e+000 
    fparams[35,6+1] =  1.68217399e-001 
    fparams[35,7+1] =  2.71719918e-001 
    fparams[35,8+1] =  9.75705606e-001 
    fparams[35,9+1] =  4.19482500e+000 
    fparams[35,10+1] =  7.24187871e-003 
    fparams[35,11+1] =  1.99325718e-002 
    fparams[36,0+1] =  3.24386970e-001 
    fparams[36,1+1] =  6.31317973e+001 
    fparams[36,2+1] =  1.31732163e+000 
    fparams[36,3+1] =  2.54706036e-001 
    fparams[36,4+1] =  1.79912614e+000 
    fparams[36,5+1] =  3.23668394e+000 
    fparams[36,6+1] =  4.29961425e-003 
    fparams[36,7+1] =  1.98965610e-002 
    fparams[36,8+1] =  1.00429433e+000 
    fparams[36,9+1] =  3.61094513e+000 
    fparams[36,10+1] =  1.62188197e-001 
    fparams[36,11+1] =  2.45583672e-001 
    fparams[37,0+1] =  2.90445351e-001 
    fparams[37,1+1] =  3.68420227e-002 
    fparams[37,2+1] =  2.44201329e+000 
    fparams[37,3+1] =  1.16013332e+000 
    fparams[37,4+1] =  7.69435449e-001 
    fparams[37,5+1] =  1.69591472e+001 
    fparams[37,6+1] =  1.58687000e+000 
    fparams[37,7+1] =  2.53082574e+000 
    fparams[37,8+1] =  2.81617593e-003 
    fparams[37,9+1] =  1.88577417e-002 
    fparams[37,10+1] =  1.28663830e-001 
    fparams[37,11+1] =  2.10753969e-001 
    fparams[38,0+1] =  1.37373086e-002 
    fparams[38,1+1] =  1.87469061e-002 
    fparams[38,2+1] =  1.97548672e+000 
    fparams[38,3+1] =  6.36079230e+000 
    fparams[38,4+1] =  1.59261029e+000 
    fparams[38,5+1] =  2.21992482e-001 
    fparams[38,6+1] =  1.73263882e-001 
    fparams[38,7+1] =  2.01624958e-001 
    fparams[38,8+1] =  4.66280378e+000 
    fparams[38,9+1] =  2.53027803e+001 
    fparams[38,10+1] =  1.61265063e-003 
    fparams[38,11+1] =  1.53610568e-002 
    fparams[39,0+1] =  6.75302747e-001 
    fparams[39,1+1] =  6.54331847e-002 
    fparams[39,2+1] =  4.70286720e-001 
    fparams[39,3+1] =  1.06108709e+002 
    fparams[39,4+1] =  2.63497677e+000 
    fparams[39,5+1] =  2.06643540e+000 
    fparams[39,6+1] =  1.09621746e-001 
    fparams[39,7+1] =  1.93131925e-001 
    fparams[39,8+1] =  9.60348773e-001 
    fparams[39,9+1] =  1.63310938e+000 
    fparams[39,10+1] =  5.28921555e-003 
    fparams[39,11+1] =  1.66083821e-002 
    fparams[40,0+1] =  2.64365505e+000 
    fparams[40,1+1] =  2.20202699e+000 
    fparams[40,2+1] =  5.54225147e-001 
    fparams[40,3+1] =  1.78260107e+002 
    fparams[40,4+1] =  7.61376625e-001 
    fparams[40,5+1] =  7.67218745e-002 
    fparams[40,6+1] =  6.02946891e-003 
    fparams[40,7+1] =  1.55143296e-002 
    fparams[40,8+1] =  9.91630530e-002 
    fparams[40,9+1] =  1.76175995e-001 
    fparams[40,10+1] =  9.56782020e-001 
    fparams[40,11+1] =  1.54330682e+000 
    fparams[41,0+1] =  6.59532875e-001 
    fparams[41,1+1] =  8.66145490e-002 
    fparams[41,2+1] =  1.84545854e+000 
    fparams[41,3+1] =  5.94774398e+000 
    fparams[41,4+1] =  1.25584405e+000 
    fparams[41,5+1] =  6.40851475e-001 
    fparams[41,6+1] =  1.22253422e-001 
    fparams[41,7+1] =  1.66646050e-001 
    fparams[41,8+1] =  7.06638328e-001 
    fparams[41,9+1] =  1.62853268e+000 
    fparams[41,10+1] =  2.62381591e-003 
    fparams[41,11+1] =  8.26257859e-003 
    fparams[42,0+1] =  6.10160120e-001 
    fparams[42,1+1] =  9.11628054e-002 
    fparams[42,2+1] =  1.26544000e+000 
    fparams[42,3+1] =  5.06776025e-001 
    fparams[42,4+1] =  1.97428762e+000 
    fparams[42,5+1] =  5.89590381e+000 
    fparams[42,6+1] =  6.48028962e-001 
    fparams[42,7+1] =  1.46634108e+000 
    fparams[42,8+1] =  2.60380817e-003 
    fparams[42,9+1] =  7.84336311e-003 
    fparams[42,10+1] =  1.13887493e-001 
    fparams[42,11+1] =  1.55114340e-001 
    fparams[43,0+1] =  8.55189183e-001 
    fparams[43,1+1] =  1.02962151e-001 
    fparams[43,2+1] =  1.66219641e+000 
    fparams[43,3+1] =  7.64907000e+000 
    fparams[43,4+1] =  1.45575475e+000 
    fparams[43,5+1] =  1.01639987e+000 
    fparams[43,6+1] =  1.05445664e-001 
    fparams[43,7+1] =  1.42303338e-001 
    fparams[43,8+1] =  7.71657112e-001 
    fparams[43,9+1] =  1.34659349e+000 
    fparams[43,10+1] =  2.20992635e-003 
    fparams[43,11+1] =  7.90358976e-003 
    fparams[44,0+1] =  4.70847093e-001 
    fparams[44,1+1] =  9.33029874e-002 
    fparams[44,2+1] =  1.58180781e+000 
    fparams[44,3+1] =  4.52831347e-001 
    fparams[44,4+1] =  2.02419818e+000 
    fparams[44,5+1] =  7.11489023e+000 
    fparams[44,6+1] =  1.97036257e-003 
    fparams[44,7+1] =  7.56181595e-003 
    fparams[44,8+1] =  6.26912639e-001 
    fparams[44,9+1] =  1.25399858e+000 
    fparams[44,10+1] =  1.02641320e-001 
    fparams[44,11+1] =  1.33786087e-001 
    fparams[45,0+1] =  4.20051553e-001 
    fparams[45,1+1] =  9.38882628e-002 
    fparams[45,2+1] =  1.76266507e+000 
    fparams[45,3+1] =  4.64441687e-001 
    fparams[45,4+1] =  2.02735641e+000 
    fparams[45,5+1] =  8.19346046e+000 
    fparams[45,6+1] =  1.45487176e-003 
    fparams[45,7+1] =  7.82704517e-003 
    fparams[45,8+1] =  6.22809600e-001 
    fparams[45,9+1] =  1.17194153e+000 
    fparams[45,10+1] =  9.91529915e-002 
    fparams[45,11+1] =  1.24532839e-001 
    fparams[46,0+1] =  2.10475155e+000 
    fparams[46,1+1] =  8.68606470e+000 
    fparams[46,2+1] =  2.03884487e+000 
    fparams[46,3+1] =  3.78924449e-001 
    fparams[46,4+1] =  1.82067264e-001 
    fparams[46,5+1] =  1.42921634e-001 
    fparams[46,6+1] =  9.52040948e-002 
    fparams[46,7+1] =  1.17125900e-001 
    fparams[46,8+1] =  5.91445248e-001 
    fparams[46,9+1] =  1.07843808e+000 
    fparams[46,10+1] =  1.13328676e-003 
    fparams[46,11+1] =  7.80252092e-003 
    fparams[47,0+1] =  2.07981390e+000 
    fparams[47,1+1] =  9.92540297e+000 
    fparams[47,2+1] =  4.43170726e-001 
    fparams[47,3+1] =  1.04920104e-001 
    fparams[47,4+1] =  1.96515215e+000 
    fparams[47,5+1] =  6.40103839e-001 
    fparams[47,6+1] =  5.96130591e-001 
    fparams[47,7+1] =  8.89594790e-001 
    fparams[47,8+1] =  4.78016333e-001 
    fparams[47,9+1] =  1.98509407e+000 
    fparams[47,10+1] =  9.46458470e-002 
    fparams[47,11+1] =  1.12744464e-001 
    fparams[48,0+1] =  1.63657549e+000 
    fparams[48,1+1] =  1.24540381e+001 
    fparams[48,2+1] =  2.17927989e+000 
    fparams[48,3+1] =  1.45134660e+000 
    fparams[48,4+1] =  7.71300690e-001 
    fparams[48,5+1] =  1.26695757e-001 
    fparams[48,6+1] =  6.64193880e-001 
    fparams[48,7+1] =  7.77659202e-001 
    fparams[48,8+1] =  7.64563285e-001 
    fparams[48,9+1] =  1.66075210e+000 
    fparams[48,10+1] =  8.61126689e-002 
    fparams[48,11+1] =  1.05728357e-001 
    fparams[49,0+1] =  2.24820632e+000 
    fparams[49,1+1] =  1.51913507e+000 
    fparams[49,2+1] =  1.64706864e+000 
    fparams[49,3+1] =  1.30113424e+001 
    fparams[49,4+1] =  7.88679265e-001 
    fparams[49,5+1] =  1.06128184e-001 
    fparams[49,6+1] =  8.12579069e-002 
    fparams[49,7+1] =  9.94045620e-002 
    fparams[49,8+1] =  6.68280346e-001 
    fparams[49,9+1] =  1.49742063e+000 
    fparams[49,10+1] =  6.38467475e-001 
    fparams[49,11+1] =  7.18422635e-001 
    fparams[50,0+1] =  2.16644620e+000 
    fparams[50,1+1] =  1.13174909e+001 
    fparams[50,2+1] =  6.88691021e-001 
    fparams[50,3+1] =  1.10131285e-001 
    fparams[50,4+1] =  1.92431751e+000 
    fparams[50,5+1] =  6.74464853e-001 
    fparams[50,6+1] =  5.65359888e-001 
    fparams[50,7+1] =  7.33564610e-001 
    fparams[50,8+1] =  9.18683861e-001 
    fparams[50,9+1] =  1.02310312e+001 
    fparams[50,10+1] =  7.80542213e-002 
    fparams[50,11+1] =  9.31104308e-002 
    fparams[51,0+1] =  1.73662114e+000 
    fparams[51,1+1] =  8.84334719e-001 
    fparams[51,2+1] =  9.99871380e-001 
    fparams[51,3+1] =  1.38462121e-001 
    fparams[51,4+1] =  2.13972409e+000 
    fparams[51,5+1] =  1.19666432e+001 
    fparams[51,6+1] =  5.60566526e-001 
    fparams[51,7+1] =  6.72672880e-001 
    fparams[51,8+1] =  9.93772747e-001 
    fparams[51,9+1] =  8.72330411e+000 
    fparams[51,10+1] =  7.37374982e-002 
    fparams[51,11+1] =  8.78577715e-002 
    fparams[52,0+1] =  2.09383882e+000 
    fparams[52,1+1] =  1.26856869e+001 
    fparams[52,2+1] =  1.56940519e+000 
    fparams[52,3+1] =  1.21236537e+000 
    fparams[52,4+1] =  1.30941993e+000 
    fparams[52,5+1] =  1.66633292e-001 
    fparams[52,6+1] =  6.98067804e-002 
    fparams[52,7+1] =  8.30817576e-002 
    fparams[52,8+1] =  1.04969537e+000 
    fparams[52,9+1] =  7.43147857e+000 
    fparams[52,10+1] =  5.55594354e-001 
    fparams[52,11+1] =  6.17487676e-001 
    fparams[53,0+1] =  1.60186925e+000 
    fparams[53,1+1] =  1.95031538e-001 
    fparams[53,2+1] =  1.98510264e+000 
    fparams[53,3+1] =  1.36976183e+001 
    fparams[53,4+1] =  1.48226200e+000 
    fparams[53,5+1] =  1.80304795e+000 
    fparams[53,6+1] =  5.53807199e-001 
    fparams[53,7+1] =  5.67912340e-001 
    fparams[53,8+1] =  1.11728722e+000 
    fparams[53,9+1] =  6.40879878e+000 
    fparams[53,10+1] =  6.60720847e-002 
    fparams[53,11+1] =  7.86615429e-002 
    fparams[54,0+1] =  1.60015487e+000 
    fparams[54,1+1] =  2.92913354e+000 
    fparams[54,2+1] =  1.71644581e+000 
    fparams[54,3+1] =  1.55882990e+001 
    fparams[54,4+1] =  1.84968351e+000 
    fparams[54,5+1] =  2.22525983e-001 
    fparams[54,6+1] =  6.23813648e-002 
    fparams[54,7+1] =  7.45581223e-002 
    fparams[54,8+1] =  1.21387555e+000 
    fparams[54,9+1] =  5.56013271e+000 
    fparams[54,10+1] =  5.54051946e-001 
    fparams[54,11+1] =  5.21994521e-001 
    fparams[55,0+1] =  2.95236854e+000 
    fparams[55,1+1] =  6.01461952e+000 
    fparams[55,2+1] =  4.28105721e-001 
    fparams[55,3+1] =  4.64151246e+001 
    fparams[55,4+1] =  1.89599233e+000 
    fparams[55,5+1] =  1.80109756e-001 
    fparams[55,6+1] =  5.48012938e-002 
    fparams[55,7+1] =  7.12799633e-002 
    fparams[55,8+1] =  4.70838600e+000 
    fparams[55,9+1] =  4.56702799e+001 
    fparams[55,10+1] =  5.90356719e-001 
    fparams[55,11+1] =  4.70236310e-001 
    fparams[56,0+1] =  3.19434243e+000 
    fparams[56,1+1] =  9.27352241e+000 
    fparams[56,2+1] =  1.98289586e+000 
    fparams[56,3+1] =  2.28741632e-001 
    fparams[56,4+1] =  1.55121052e-001 
    fparams[56,5+1] =  3.82000231e-002 
    fparams[56,6+1] =  6.73222354e-002 
    fparams[56,7+1] =  7.30961745e-002 
    fparams[56,8+1] =  4.48474211e+000 
    fparams[56,9+1] =  2.95703565e+001 
    fparams[56,10+1] =  5.42674414e-001 
    fparams[56,11+1] =  4.08647015e-001 
    fparams[57,0+1] =  2.05036425e+000 
    fparams[57,1+1] =  2.20348417e-001 
    fparams[57,2+1] =  1.42114311e-001 
    fparams[57,3+1] =  3.96438056e-002 
    fparams[57,4+1] =  3.23538151e+000 
    fparams[57,5+1] =  9.56979169e+000 
    fparams[57,6+1] =  6.34683429e-002 
    fparams[57,7+1] =  6.92443091e-002 
    fparams[57,8+1] =  3.97960586e+000 
    fparams[57,9+1] =  2.53178406e+001 
    fparams[57,10+1] =  5.20116711e-001 
    fparams[57,11+1] =  3.83614098e-001 
    fparams[58,0+1] =  3.22990759e+000 
    fparams[58,1+1] =  9.94660135e+000 
    fparams[58,2+1] =  1.57618307e-001 
    fparams[58,3+1] =  4.15378676e-002 
    fparams[58,4+1] =  2.13477838e+000 
    fparams[58,5+1] =  2.40480572e-001 
    fparams[58,6+1] =  5.01907609e-001 
    fparams[58,7+1] =  3.66252019e-001 
    fparams[58,8+1] =  3.80889010e+000 
    fparams[58,9+1] =  2.43275968e+001 
    fparams[58,10+1] =  5.96625028e-002 
    fparams[58,11+1] =  6.59653503e-002 
    fparams[59,0+1] =  1.58189324e-001 
    fparams[59,1+1] =  3.91309056e-002 
    fparams[59,2+1] =  3.18141995e+000 
    fparams[59,3+1] =  1.04139545e+001 
    fparams[59,4+1] =  2.27622140e+000 
    fparams[59,5+1] =  2.81671757e-001 
    fparams[59,6+1] =  3.97705472e+000 
    fparams[59,7+1] =  2.61872978e+001 
    fparams[59,8+1] =  5.58448277e-002 
    fparams[59,9+1] =  6.30921695e-002 
    fparams[59,10+1] =  4.85207954e-001 
    fparams[59,11+1] =  3.54234369e-001 
    fparams[60,0+1] =  1.81379417e-001 
    fparams[60,1+1] =  4.37324793e-002 
    fparams[60,2+1] =  3.17616396e+000 
    fparams[60,3+1] =  1.07842572e+001 
    fparams[60,4+1] =  2.35221519e+000 
    fparams[60,5+1] =  3.05571833e-001 
    fparams[60,6+1] =  3.83125763e+000 
    fparams[60,7+1] =  2.54745408e+001 
    fparams[60,8+1] =  5.25889976e-002 
    fparams[60,9+1] =  6.02676073e-002 
    fparams[60,10+1] =  4.70090742e-001 
    fparams[60,11+1] =  3.39017003e-001 
    fparams[61,0+1] =  1.92986811e-001 
    fparams[61,1+1] =  4.37785970e-002 
    fparams[61,2+1] =  2.43756023e+000 
    fparams[61,3+1] =  3.29336996e-001 
    fparams[61,4+1] =  3.17248504e+000 
    fparams[61,5+1] =  1.11259996e+001 
    fparams[61,6+1] =  3.58105414e+000 
    fparams[61,7+1] =  2.46709586e+001 
    fparams[61,8+1] =  4.56529394e-001 
    fparams[61,9+1] =  3.24990282e-001 
    fparams[61,10+1] =  4.94812177e-002 
    fparams[61,11+1] =  5.76553100e-002 
    fparams[62,0+1] =  2.12002595e-001 
    fparams[62,1+1] =  4.57703608e-002 
    fparams[62,2+1] =  3.16891754e+000 
    fparams[62,3+1] =  1.14536599e+001 
    fparams[62,4+1] =  2.51503494e+000 
    fparams[62,5+1] =  3.55561054e-001 
    fparams[62,6+1] =  4.44080845e-001 
    fparams[62,7+1] =  3.11953363e-001 
    fparams[62,8+1] =  3.36742101e+000 
    fparams[62,9+1] =  2.40291435e+001 
    fparams[62,10+1] =  4.65652543e-002 
    fparams[62,11+1] =  5.52266819e-002 
    fparams[63,0+1] =  2.59355002e+000 
    fparams[63,1+1] =  3.82452612e-001 
    fparams[63,2+1] =  3.16557522e+000 
    fparams[63,3+1] =  1.17675155e+001 
    fparams[63,4+1] =  2.29402652e-001 
    fparams[63,5+1] =  4.76642249e-002 
    fparams[63,6+1] =  4.32257780e-001 
    fparams[63,7+1] =  2.99719833e-001 
    fparams[63,8+1] =  3.17261920e+000 
    fparams[63,9+1] =  2.34462738e+001 
    fparams[63,10+1] =  4.37958317e-002 
    fparams[63,11+1] =  5.29440680e-002 
    fparams[64,0+1] =  3.19144939e+000 
    fparams[64,1+1] =  1.20224655e+001 
    fparams[64,2+1] =  2.55766431e+000 
    fparams[64,3+1] =  4.08338876e-001 
    fparams[64,4+1] =  3.32681934e-001 
    fparams[64,5+1] =  5.85819814e-002 
    fparams[64,6+1] =  4.14243130e-002 
    fparams[64,7+1] =  5.06771477e-002 
    fparams[64,8+1] =  2.61036728e+000 
    fparams[64,9+1] =  1.99344244e+001 
    fparams[64,10+1] =  4.20526863e-001 
    fparams[64,11+1] =  2.85686240e-001 
    fparams[65,0+1] =  2.59407462e-001 
    fparams[65,1+1] =  5.04689354e-002 
    fparams[65,2+1] =  3.16177855e+000 
    fparams[65,3+1] =  1.23140183e+001 
    fparams[65,4+1] =  2.75095751e+000 
    fparams[65,5+1] =  4.38337626e-001 
    fparams[65,6+1] =  2.79247686e+000 
    fparams[65,7+1] =  2.23797309e+001 
    fparams[65,8+1] =  3.85931001e-002 
    fparams[65,9+1] =  4.87920992e-002 
    fparams[65,10+1] =  4.10881708e-001 
    fparams[65,11+1] =  2.77622892e-001 
    fparams[66,0+1] =  3.16055396e+000 
    fparams[66,1+1] =  1.25470414e+001 
    fparams[66,2+1] =  2.82751709e+000 
    fparams[66,3+1] =  4.67899094e-001 
    fparams[66,4+1] =  2.75140255e-001 
    fparams[66,5+1] =  5.23226982e-002 
    fparams[66,6+1] =  4.00967160e-001 
    fparams[66,7+1] =  2.67614884e-001 
    fparams[66,8+1] =  2.63110834e+000 
    fparams[66,9+1] =  2.19498166e+001 
    fparams[66,10+1] =  3.61333817e-002 
    fparams[66,11+1] =  4.68871497e-002 
    fparams[67,0+1] =  2.88642467e-001 
    fparams[67,1+1] =  5.40507687e-002 
    fparams[67,2+1] =  2.90567296e+000 
    fparams[67,3+1] =  4.97581077e-001 
    fparams[67,4+1] =  3.15960159e+000 
    fparams[67,5+1] =  1.27599505e+001 
    fparams[67,6+1] =  3.91280259e-001 
    fparams[67,7+1] =  2.58151831e-001 
    fparams[67,8+1] =  2.48596038e+000 
    fparams[67,9+1] =  2.15400972e+001 
    fparams[67,10+1] =  3.37664478e-002 
    fparams[67,11+1] =  4.50664323e-002 
    fparams[68,0+1] =  3.15573213e+000 
    fparams[68,1+1] =  1.29729009e+001 
    fparams[68,2+1] =  3.11519560e-001 
    fparams[68,3+1] =  5.81399387e-002 
    fparams[68,4+1] =  2.97722406e+000 
    fparams[68,5+1] =  5.31213394e-001 
    fparams[68,6+1] =  3.81563854e-001 
    fparams[68,7+1] =  2.49195776e-001 
    fparams[68,8+1] =  2.40247532e+000 
    fparams[68,9+1] =  2.13627616e+001 
    fparams[68,10+1] =  3.15224214e-002 
    fparams[68,11+1] =  4.33253257e-002 
    fparams[69,0+1] =  3.15591970e+000 
    fparams[69,1+1] =  1.31232407e+001 
    fparams[69,2+1] =  3.22544710e-001 
    fparams[69,3+1] =  5.97223323e-002 
    fparams[69,4+1] =  3.05569053e+000 
    fparams[69,5+1] =  5.61876773e-001 
    fparams[69,6+1] =  2.92845100e-002 
    fparams[69,7+1] =  4.16534255e-002 
    fparams[69,8+1] =  3.72487205e-001 
    fparams[69,9+1] =  2.40821967e-001 
    fparams[69,10+1] =  2.27833695e+000 
    fparams[69,11+1] =  2.10034185e+001 
    fparams[70,0+1] =  3.10794704e+000 
    fparams[70,1+1] =  6.06347847e-001 
    fparams[70,2+1] =  3.14091221e+000 
    fparams[70,3+1] =  1.33705269e+001 
    fparams[70,4+1] =  3.75660454e-001 
    fparams[70,5+1] =  7.29814740e-002 
    fparams[70,6+1] =  3.61901097e-001 
    fparams[70,7+1] =  2.32652051e-001 
    fparams[70,8+1] =  2.45409082e+000 
    fparams[70,9+1] =  2.12695209e+001 
    fparams[70,10+1] =  2.72383990e-002 
    fparams[70,11+1] =  3.99969597e-002 
    fparams[71,0+1] =  3.11446863e+000 
    fparams[71,1+1] =  1.38968881e+001 
    fparams[71,2+1] =  5.39634353e-001 
    fparams[71,3+1] =  8.91708508e-002 
    fparams[71,4+1] =  3.06460915e+000 
    fparams[71,5+1] =  6.79919563e-001 
    fparams[71,6+1] =  2.58563745e-002 
    fparams[71,7+1] =  3.82808522e-002 
    fparams[71,8+1] =  2.13983556e+000 
    fparams[71,9+1] =  1.80078788e+001 
    fparams[71,10+1] =  3.47788231e-001 
    fparams[71,11+1] =  2.22706591e-001 
    fparams[72,0+1] =  3.01166899e+000 
    fparams[72,1+1] =  7.10401889e-001 
    fparams[72,2+1] =  3.16284788e+000 
    fparams[72,3+1] =  1.38262192e+001 
    fparams[72,4+1] =  6.33421771e-001 
    fparams[72,5+1] =  9.48486572e-002 
    fparams[72,6+1] =  3.41417198e-001 
    fparams[72,7+1] =  2.14129678e-001 
    fparams[72,8+1] =  1.53566013e+000 
    fparams[72,9+1] =  1.55298698e+001 
    fparams[72,10+1] =  2.40723773e-002 
    fparams[72,11+1] =  3.67833690e-002 
    fparams[73,0+1] =  3.20236821e+000 
    fparams[73,1+1] =  1.38446369e+001 
    fparams[73,2+1] =  8.30098413e-001 
    fparams[73,3+1] =  1.18381581e-001 
    fparams[73,4+1] =  2.86552297e+000 
    fparams[73,5+1] =  7.66369118e-001 
    fparams[73,6+1] =  2.24813887e-002 
    fparams[73,7+1] =  3.52934622e-002 
    fparams[73,8+1] =  1.40165263e+000 
    fparams[73,9+1] =  1.46148877e+001 
    fparams[73,10+1] =  3.33740596e-001 
    fparams[73,11+1] =  2.05704486e-001 
    fparams[74,0+1] =  9.24906855e-001 
    fparams[74,1+1] =  1.28663377e-001 
    fparams[74,2+1] =  2.75554557e+000 
    fparams[74,3+1] =  7.65826479e-001 
    fparams[74,4+1] =  3.30440060e+000 
    fparams[74,5+1] =  1.34471170e+001 
    fparams[74,6+1] =  3.29973862e-001 
    fparams[74,7+1] =  1.98218895e-001 
    fparams[74,8+1] =  1.09916444e+000 
    fparams[74,9+1] =  1.35087534e+001 
    fparams[74,10+1] =  2.06498883e-002 
    fparams[74,11+1] =  3.38918459e-002 
    fparams[75,0+1] =  1.96952105e+000 
    fparams[75,1+1] =  4.98830620e+001 
    fparams[75,2+1] =  1.21726619e+000 
    fparams[75,3+1] =  1.33243809e-001 
    fparams[75,4+1] =  4.10391685e+000 
    fparams[75,5+1] =  1.84396916e+000 
    fparams[75,6+1] =  2.90791978e-002 
    fparams[75,7+1] =  2.84192813e-002 
    fparams[75,8+1] =  2.30696669e-001 
    fparams[75,9+1] =  1.90968784e-001 
    fparams[75,10+1] =  6.08840299e-001 
    fparams[75,11+1] =  1.37090356e+000 
    fparams[76,0+1] =  2.06385867e+000 
    fparams[76,1+1] =  4.05671697e+001 
    fparams[76,2+1] =  1.29603406e+000 
    fparams[76,3+1] =  1.46559047e-001 
    fparams[76,4+1] =  3.96920673e+000 
    fparams[76,5+1] =  1.82561596e+000 
    fparams[76,6+1] =  2.69835487e-002 
    fparams[76,7+1] =  2.84172045e-002 
    fparams[76,8+1] =  2.31083999e-001 
    fparams[76,9+1] =  1.79765184e-001 
    fparams[76,10+1] =  6.30466774e-001 
    fparams[76,11+1] =  1.38911543e+000 
    fparams[77,0+1] =  2.21522726e+000 
    fparams[77,1+1] =  3.24464090e+001 
    fparams[77,2+1] =  1.37573155e+000 
    fparams[77,3+1] =  1.60920048e-001 
    fparams[77,4+1] =  3.78244405e+000 
    fparams[77,5+1] =  1.78756553e+000 
    fparams[77,6+1] =  2.44643240e-002 
    fparams[77,7+1] =  2.82909938e-002 
    fparams[77,8+1] =  2.36932016e-001 
    fparams[77,9+1] =  1.70692368e-001 
    fparams[77,10+1] =  6.48471412e-001 
    fparams[77,11+1] =  1.37928390e+000 
    fparams[78,0+1] =  9.84697940e-001 
    fparams[78,1+1] =  1.60910839e-001 
    fparams[78,2+1] =  2.73987079e+000 
    fparams[78,3+1] =  7.18971667e-001 
    fparams[78,4+1] =  3.61696715e+000 
    fparams[78,5+1] =  1.29281016e+001 
    fparams[78,6+1] =  3.02885602e-001 
    fparams[78,7+1] =  1.70134854e-001 
    fparams[78,8+1] =  2.78370726e-001 
    fparams[78,9+1] =  1.49862703e+000 
    fparams[78,10+1] =  1.52124129e-002 
    fparams[78,11+1] =  2.83510822e-002 
    fparams[79,0+1] =  9.61263398e-001 
    fparams[79,1+1] =  1.70932277e-001 
    fparams[79,2+1] =  3.69581030e+000 
    fparams[79,3+1] =  1.29335319e+001 
    fparams[79,4+1] =  2.77567491e+000 
    fparams[79,5+1] =  6.89997070e-001 
    fparams[79,6+1] =  2.95414176e-001 
    fparams[79,7+1] =  1.63525510e-001 
    fparams[79,8+1] =  3.11475743e-001 
    fparams[79,9+1] =  1.39200901e+000 
    fparams[79,10+1] =  1.43237267e-002 
    fparams[79,11+1] =  2.71265337e-002 
    fparams[80,0+1] =  1.29200491e+000 
    fparams[80,1+1] =  1.83432865e-001 
    fparams[80,2+1] =  2.75161478e+000 
    fparams[80,3+1] =  9.42368371e-001 
    fparams[80,4+1] =  3.49387949e+000 
    fparams[80,5+1] =  1.46235654e+001 
    fparams[80,6+1] =  2.77304636e-001 
    fparams[80,7+1] =  1.55110144e-001 
    fparams[80,8+1] =  4.30232810e-001 
    fparams[80,9+1] =  1.28871670e+000 
    fparams[80,10+1] =  1.48294351e-002 
    fparams[80,11+1] =  2.61903834e-002 
    fparams[81,0+1] =  3.75964730e+000 
    fparams[81,1+1] =  1.35041513e+001 
    fparams[81,2+1] =  3.21195904e+000 
    fparams[81,3+1] =  6.66330993e-001 
    fparams[81,4+1] =  6.47767825e-001 
    fparams[81,5+1] =  9.22518234e-002 
    fparams[81,6+1] =  2.76123274e-001 
    fparams[81,7+1] =  1.50312897e-001 
    fparams[81,8+1] =  3.18838810e-001 
    fparams[81,9+1] =  1.12565588e+000 
    fparams[81,10+1] =  1.31668419e-002 
    fparams[81,11+1] =  2.48879842e-002 
    fparams[82,0+1] =  1.00795975e+000 
    fparams[82,1+1] =  1.17268427e-001 
    fparams[82,2+1] =  3.09796153e+000 
    fparams[82,3+1] =  8.80453235e-001 
    fparams[82,4+1] =  3.61296864e+000 
    fparams[82,5+1] =  1.47325812e+001 
    fparams[82,6+1] =  2.62401476e-001 
    fparams[82,7+1] =  1.43491014e-001 
    fparams[82,8+1] =  4.05621995e-001 
    fparams[82,9+1] =  1.04103506e+000 
    fparams[82,10+1] =  1.31812509e-002 
    fparams[82,11+1] =  2.39575415e-002 
    fparams[83,0+1] =  1.59826875e+000 
    fparams[83,1+1] =  1.56897471e-001 
    fparams[83,2+1] =  4.38233925e+000 
    fparams[83,3+1] =  2.47094692e+000 
    fparams[83,4+1] =  2.06074719e+000 
    fparams[83,5+1] =  5.72438972e+001 
    fparams[83,6+1] =  1.94426023e-001 
    fparams[83,7+1] =  1.32979109e-001 
    fparams[83,8+1] =  8.22704978e-001 
    fparams[83,9+1] =  9.56532528e-001 
    fparams[83,10+1] =  2.33226953e-002 
    fparams[83,11+1] =  2.23038435e-002 
    fparams[84,0+1] =  1.71463223e+000 
    fparams[84,1+1] =  9.79262841e+001 
    fparams[84,2+1] =  2.14115960e+000 
    fparams[84,3+1] =  2.10193717e-001 
    fparams[84,4+1] =  4.37512413e+000 
    fparams[84,5+1] =  3.66948812e+000 
    fparams[84,6+1] =  2.16216680e-002 
    fparams[84,7+1] =  1.98456144e-002 
    fparams[84,8+1] =  1.97843837e-001 
    fparams[84,9+1] =  1.33758807e-001 
    fparams[84,10+1] =  6.52047920e-001 
    fparams[84,11+1] =  7.80432104e-001 
    fparams[85,0+1] =  1.48047794e+000 
    fparams[85,1+1] =  1.25943919e+002 
    fparams[85,2+1] =  2.09174630e+000 
    fparams[85,3+1] =  1.83803008e-001 
    fparams[85,4+1] =  4.75246033e+000 
    fparams[85,5+1] =  4.19890596e+000 
    fparams[85,6+1] =  1.85643958e-002 
    fparams[85,7+1] =  1.81383503e-002 
    fparams[85,8+1] =  2.05859375e-001 
    fparams[85,9+1] =  1.33035404e-001 
    fparams[85,10+1] =  7.13540948e-001 
    fparams[85,11+1] =  7.03031938e-001 
    fparams[86,0+1] =  6.30022295e-001 
    fparams[86,1+1] =  1.40909762e-001 
    fparams[86,2+1] =  3.80962881e+000 
    fparams[86,3+1] =  3.08515540e+001 
    fparams[86,4+1] =  3.89756067e+000 
    fparams[86,5+1] =  6.51559763e-001 
    fparams[86,6+1] =  2.40755100e-001 
    fparams[86,7+1] =  1.08899672e-001 
    fparams[86,8+1] =  2.62868577e+000 
    fparams[86,9+1] =  6.42383261e+000 
    fparams[86,10+1] =  3.14285931e-002 
    fparams[86,11+1] =  2.42346699e-002 
    fparams[87,0+1] =  5.23288135e+000 
    fparams[87,1+1] =  8.60599536e+000 
    fparams[87,2+1] =  2.48604205e+000 
    fparams[87,3+1] =  3.04543982e-001 
    fparams[87,4+1] =  3.23431354e-001 
    fparams[87,5+1] =  3.87759096e-002 
    fparams[87,6+1] =  2.55403596e-001 
    fparams[87,7+1] =  1.28717724e-001 
    fparams[87,8+1] =  5.53607228e-001 
    fparams[87,9+1] =  5.36977452e-001 
    fparams[87,10+1] =  5.75278889e-003 
    fparams[87,11+1] =  1.29417790e-002 
    fparams[88,0+1] =  1.44192685e+000 
    fparams[88,1+1] =  1.18740873e-001 
    fparams[88,2+1] =  3.55291725e+000 
    fparams[88,3+1] =  1.01739750e+000 
    fparams[88,4+1] =  3.91259586e+000 
    fparams[88,5+1] =  6.31814783e+001 
    fparams[88,6+1] =  2.16173519e-001 
    fparams[88,7+1] =  9.55806441e-002 
    fparams[88,8+1] =  3.94191605e+000 
    fparams[88,9+1] =  3.50602732e+001 
    fparams[88,10+1] =  4.60422605e-002 
    fparams[88,11+1] =  2.20850385e-002 
    fparams[89,0+1] =  1.45864127e+000 
    fparams[89,1+1] =  1.07760494e-001 
    fparams[89,2+1] =  4.18945405e+000 
    fparams[89,3+1] =  8.89090649e+001 
    fparams[89,4+1] =  3.65866182e+000 
    fparams[89,5+1] =  1.05088931e+000 
    fparams[89,6+1] =  2.08479229e-001 
    fparams[89,7+1] =  9.09335557e-002 
    fparams[89,8+1] =  3.16528117e+000 
    fparams[89,9+1] =  3.13297788e+001 
    fparams[89,10+1] =  5.23892556e-002 
    fparams[89,11+1] =  2.08807697e-002 
    fparams[90,0+1] =  1.19014064e+000 
    fparams[90,1+1] =  7.73468729e-002 
    fparams[90,2+1] =  2.55380607e+000 
    fparams[90,3+1] =  6.59693681e-001 
    fparams[90,4+1] =  4.68110181e+000 
    fparams[90,5+1] =  1.28013896e+001 
    fparams[90,6+1] =  2.26121303e-001 
    fparams[90,7+1] =  1.08632194e-001 
    fparams[90,8+1] =  3.58250545e-001 
    fparams[90,9+1] =  4.56765664e-001 
    fparams[90,10+1] =  7.82263950e-003 
    fparams[90,11+1] =  1.62623474e-002 
    fparams[91,0+1] =  4.68537504e+000 
    fparams[91,1+1] =  1.44503632e+001 
    fparams[91,2+1] =  2.98413708e+000 
    fparams[91,3+1] =  5.56438592e-001 
    fparams[91,4+1] =  8.91988061e-001 
    fparams[91,5+1] =  6.69512914e-002 
    fparams[91,6+1] =  2.24825384e-001 
    fparams[91,7+1] =  1.03235396e-001 
    fparams[91,8+1] =  3.04444846e-001 
    fparams[91,9+1] =  4.27255647e-001 
    fparams[91,10+1] =  9.48162708e-003 
    fparams[91,11+1] =  1.77730611e-002 
    fparams[92,0+1] =  4.63343606e+000 
    fparams[92,1+1] =  1.63377267e+001 
    fparams[92,2+1] =  3.18157056e+000 
    fparams[92,3+1] =  5.69517868e-001 
    fparams[92,4+1] =  8.76455075e-001 
    fparams[92,5+1] =  6.88860012e-002 
    fparams[92,6+1] =  2.21685477e-001 
    fparams[92,7+1] =  9.84254550e-002 
    fparams[92,8+1] =  2.72917100e-001 
    fparams[92,9+1] =  4.09470917e-001 
    fparams[92,10+1] =  1.11737298e-002 
    fparams[92,11+1] =  1.86215410e-002 
    fparams[93,0+1] =  4.56773888e+000 
    fparams[93,1+1] =  1.90992795e+001 
    fparams[93,2+1] =  3.40325179e+000 
    fparams[93,3+1] =  5.90099634e-001 
    fparams[93,4+1] =  8.61841923e-001 
    fparams[93,5+1] =  7.03204851e-002 
    fparams[93,6+1] =  2.19728870e-001 
    fparams[93,7+1] =  9.36334280e-002 
    fparams[93,8+1] =  2.38176903e-001 
    fparams[93,9+1] =  3.93554882e-001 
    fparams[93,10+1] =  1.38306499e-002 
    fparams[93,11+1] =  1.94437286e-002 
    fparams[94,0+1] =  5.45671123e+000 
    fparams[94,1+1] =  1.01892720e+001 
    fparams[94,2+1] =  1.11687906e-001 
    fparams[94,3+1] =  3.98131313e-002 
    fparams[94,4+1] =  3.30260343e+000 
    fparams[94,5+1] =  3.14622212e-001 
    fparams[94,6+1] =  1.84568319e-001 
    fparams[94,7+1] =  1.04220860e-001 
    fparams[94,8+1] =  4.93644263e-001 
    fparams[94,9+1] =  4.63080540e-001 
    fparams[94,10+1] =  3.57484743e+000 
    fparams[94,11+1] =  2.19369542e+001 
    fparams[95,0+1] =  5.38321999e+000 
    fparams[95,1+1] =  1.07289857e+001 
    fparams[95,2+1] =  1.23343236e-001 
    fparams[95,3+1] =  4.15137806e-002 
    fparams[95,4+1] =  3.46469090e+000 
    fparams[95,5+1] =  3.39326208e-001 
    fparams[95,6+1] =  1.75437132e-001 
    fparams[95,7+1] =  9.98932346e-002 
    fparams[95,8+1] =  3.39800073e+000 
    fparams[95,9+1] =  2.11601535e+001 
    fparams[95,10+1] =  4.69459519e-001 
    fparams[95,11+1] =  4.51996970e-001 
    fparams[96,0+1] =  5.38402377e+000 
    fparams[96,1+1] =  1.11211419e+001 
    fparams[96,2+1] =  3.49861264e+000 
    fparams[96,3+1] =  3.56750210e-001 
    fparams[96,4+1] =  1.88039547e-001 
    fparams[96,5+1] =  5.39853583e-002 
    fparams[96,6+1] =  1.69143137e-001 
    fparams[96,7+1] =  9.60082633e-002 
    fparams[96,8+1] =  3.19595016e+000 
    fparams[96,9+1] =  1.80694389e+001 
    fparams[96,10+1] =  4.64393059e-001 
    fparams[96,11+1] =  4.36318197e-001 
    fparams[97,0+1] =  3.66090688e+000 
    fparams[97,1+1] =  3.84420906e-001 
    fparams[97,2+1] =  2.03054678e-001 
    fparams[97,3+1] =  5.48547131e-002 
    fparams[97,4+1] =  5.30697515e+000 
    fparams[97,5+1] =  1.17150262e+001 
    fparams[97,6+1] =  1.60934046e-001 
    fparams[97,7+1] =  9.21020329e-002 
    fparams[97,8+1] =  3.04808401e+000 
    fparams[97,9+1] =  1.73525367e+001 
    fparams[97,10+1] =  4.43610295e-001 
    fparams[97,11+1] =  4.27132359e-001 
    fparams[98,0+1] =  3.94150390e+000 
    fparams[98,1+1] =  4.18246722e-001 
    fparams[98,2+1] =  5.16915345e+000 
    fparams[98,3+1] =  1.25201788e+001 
    fparams[98,4+1] =  1.61941074e-001 
    fparams[98,5+1] =  4.81540117e-002 
    fparams[98,6+1] =  4.15299561e-001 
    fparams[98,7+1] =  4.24913856e-001 
    fparams[98,8+1] =  2.91761325e+000 
    fparams[98,9+1] =  1.90899693e+001 
    fparams[98,10+1] =  1.51474927e-001 
    fparams[98,11+1] =  8.81568925e-002 
    fparams[99,0+1] =  4.09780623e+000 
    fparams[99,1+1] =  4.46021145e-001 
    fparams[99,2+1] =  5.10079393e+000 
    fparams[99,3+1] =  1.31768613e+001 
    fparams[99,4+1] =  1.74617289e-001 
    fparams[99,5+1] =  5.02742829e-002 
    fparams[99,6+1] =  2.76774658e+000 
    fparams[99,7+1] =  1.84815393e+001 
    fparams[99,8+1] =  1.44496639e-001 
    fparams[99,9+1] =  8.46232592e-002 
    fparams[99,10+1] =  4.02772109e-001 
    fparams[99,11+1] =  4.17640100e-001 
    fparams[100,0+1] =  4.24934820e+000 
    fparams[100,1+1] =  4.75263933e-001 
    fparams[100,2+1] =  5.03556594e+000 
    fparams[100,3+1] =  1.38570834e+001 
    fparams[100,4+1] =  1.88920613e-001 
    fparams[100,5+1] =  5.26975158e-002 
    fparams[100,6+1] =  3.94356058e-001 
    fparams[100,7+1] =  4.11193751e-001 
    fparams[100,8+1] =  2.61213100e+000 
    fparams[100,9+1] =  1.78537905e+001 
    fparams[100,10+1] =  1.38001927e-001 
    fparams[100,11+1] =  8.12774434e-002 
    fparams[101,0+1] =  2.00942931e-001 
    fparams[101,1+1] =  5.48366518e-002 
    fparams[101,2+1] =  4.40119869e+000 
    fparams[101,3+1] =  5.04248434e-001 
    fparams[101,4+1] =  4.97250102e+000 
    fparams[101,5+1] =  1.45721366e+001 
    fparams[101,6+1] =  2.47530599e+000 
    fparams[101,7+1] =  1.72978308e+001 
    fparams[101,8+1] =  3.86883197e-001 
    fparams[101,9+1] =  4.05043898e-001 
    fparams[101,10+1] =  1.31936095e-001 
    fparams[101,11+1] =  7.80821071e-002 
    fparams[102,0+1] =  2.16052899e-001 
    fparams[102,1+1] =  5.83584058e-002 
    fparams[102,2+1] =  4.91106799e+000 
    fparams[102,3+1] =  1.53264212e+001 
    fparams[102,4+1] =  4.54862870e+000 
    fparams[102,5+1] =  5.34434760e-001 
    fparams[102,6+1] =  2.36114249e+000 
    fparams[102,7+1] =  1.68164803e+001 
    fparams[102,8+1] =  1.26277292e-001 
    fparams[102,9+1] =  7.50304633e-002 
    fparams[102,10+1] =  3.81364501e-001 
    fparams[102,11+1] =  3.99305852e-001 
    fparams[103,0+1] =  4.86738014e+000 
    fparams[103,1+1] =  1.60320520e+001 
    fparams[103,2+1] =  3.19974401e-001 
    fparams[103,3+1] =  6.70871138e-002 
    fparams[103,4+1] =  4.58872425e+000 
    fparams[103,5+1] =  5.77039373e-001 
    fparams[103,6+1] =  1.21482448e-001 
    fparams[103,7+1] =  7.22275899e-002 
    fparams[103,8+1] =  2.31639872e+000 
    fparams[103,9+1] =  1.41279737e+001 
    fparams[103,10+1] =  3.79258137e-001 
    fparams[103,11+1] =  3.89973484e-001 
    
    dd = fparams[Z,:]

    return dd


def fatom_vector_python(q0, Z0):
    """ Calculate the electron scattering factor based on the tabulated value
    
    Parameters
    ----------
        q0 : 
        
        Z0 : 
        
    Returns
    -------
        : ndarray
            The electron scattering factors
    
    """
    # get tabulated value based on atomic number
    fpara = fparameters_python(Z0)
    
    # prepare the calculation variable based on the tabulated value
    a0 = np.array([fpara[1], fpara[3], fpara[5]])
    b0 = np.array([fpara[2], fpara[4], fpara[6]])
    c0 = np.array([fpara[7], fpara[9], fpara[11]])
    d0 = np.array([fpara[8], fpara[10], fpara[12]])

    num = q0.size 
    v0 = np.zeros((num))
    
    q0 = q0.reshape(num)
    
    # calculate the electron scattering factors
    for ii in range(3):
        lor = a0[ii] / (q0**2 + b0[ii])
        gau = c0[ii] * np.exp(-d0[ii] * q0**2)
        
        v0 += lor + gau
        
    return v0

# function for calculating R factor with least sqare normalization
def calcR_norm_YY_python(data1,data2):

    # reshape array
    data1 = data1.reshape((data1.size))
    data2 = data2.reshape((data2.size))
    
    if len(data1)!=len(data2):
        print('data length does not match!\n')
        R = -1
    else:
        # scale factor for least square noamlization
        lscale = np.dot(data1,data2)/np.linalg.norm(data2)**2
    
        # normalize
        data2 = data2 * lscale
    
        # calculate R factor
        R = np.sum(np.abs(np.abs(data1)-np.abs(data2)))/np.sum(np.abs(data1))
    
    return R


# function for obatining rotation matrix based on quaternion algorithm
def MatrixQuaternionRot_python(vector,theta):

    theta = theta*np.pi/180;
    vector = vector / np.linalg.norm(vector);
    w = np.cos(theta/2.)
    x = -np.sin(theta/2.)*vector[0]
    y = -np.sin(theta/2)*vector[1]
    z = -np.sin(theta/2)*vector[2]
    
    RotM = [[1-2*y**2-2*z**2 , 2*x*y+2*w*z, 2*x*z-2*w*y],
      [2*x*y-2*w*z, 1-2*x**2-2*z**2, 2*y*z+2*w*x],
      [2*x*z+2*w*y, 2*y*z-2*w*x, 1-2*x**2-2*y**2]]

    dd = np.matrix(np.array(RotM))
    return dd



def get_handbfac(currPos,currAtom,currProjs,currAngles,AtomicNumbers,Resolution,Axis_array):
    from scipy.optimize import minimize, Bounds
    Bfactors = 5*np.ones(len(AtomicNumbers))
    # HT array
    Heights = np.ones(len(AtomicNumbers))

    if np.shape(currAngles)[1] is not 3:
        currAngles = np.transpose(currAngles)

    normang = np.sum(currAngles ** 2,axis=1)
    getnorms = np.argsort(normang)

    pick = getnorms[0:int(np.round(np.shape(currAngles)[0]/5))]

    projs = currProjs
    if np.shape(projs)[0]%2 is 0:
        projs = projs[1:,1:,pick]
    else:
        projs = projs[:,:,pick]

    currAngles = currAngles[pick,:]
    N = np.shape(projs)[0]
    Hf = round(N/2)-1 
    M = np.shape(currAngles)[0]
    sc = 1.0; res = Resolution*sc
    delta_r = res
    delta_k = 1/(N*delta_r)
    pos = currPos.copy()
    #
    rotmats = np.zeros((3,3,currAngles.shape[0]))
    for j in range(0,currAngles.shape[0]): 
        # calculate rotation matrix based on current input angles and axis convention
        currMAT1 = MatrixQuaternionRot_python(np.array(Axis_array[0]),currAngles[j,0])
        currMAT2 = MatrixQuaternionRot_python(np.array(Axis_array[1]),currAngles[j,1])
        currMAT3 = MatrixQuaternionRot_python(np.array(Axis_array[2]),currAngles[j,2])
        #
        MAT = currMAT1*currMAT2*currMAT3
        rotmats[:,:,j] = MAT

    Fobs = np.array(np.zeros(M*N*N),dtype=complex)
    Fcalc = np.array(np.zeros(M*N*N),dtype=complex)
    kx = np.zeros(M*N*N)
    ky = np.zeros(M*N*N)
    kz = np.zeros(M*N*N)

    for nj in range(0,M):
        [kx0, kz0] = np.meshgrid(np.arange(-Hf,Hf+1),np.arange(-Hf,Hf+1))
        ky0 = 0*kx0
        ky0[:] = 0
        k_plane0 = np.array([kx0.flatten(), ky0.flatten(), kz0.flatten()])
        k_plane0 = k_plane0*delta_k
        k_plane = np.matmul(rotmats[:,:,nj],(k_plane0))  
        kx[(nj)*N*N:(nj+1)*N*N] = k_plane[0,:]
        ky[(nj)*N*N:(nj+1)*N*N] = k_plane[1,:]
        kz[(nj)*N*N:(nj+1)*N*N] = k_plane[2,:]
        proj = projs[:,:,nj]
        Fobs_t = np.fft.fftshift(np.fft.fftn(np.fft.ifftshift(proj)))
        Fobs[(nj)*N*N:(nj+1)*N*N] = np.reshape(Fobs_t,N*N)


    L = len(kx)

    q2 = kx**2 + ky**2 + kz**2
    fa = np.zeros(L)
    for j in range(0,len(AtomicNumbers)):
        fa += fatom_vector_python( np.sqrt(q2),AtomicNumbers[j] )

    fa = np.divide(fa,len(AtomicNumbers))

    rx = pos[0,:].copy() 
    ry = pos[1,:].copy() 
    rz = pos[2,:].copy()

    x0 = np.hstack([Bfactors,Heights])
    costfun = lambda x: parameterfun(x,pos,rx,ry,rz,fa,kx,ky,kz,L,Fobs,Fcalc,currAtom)

    lb_b = 0.001
    lb_h = 0.001 
    ub_b = 50.00
    ub_h = 100.00
    bnds = np.zeros((2*len(AtomicNumbers),2))
    bnds[0:len(AtomicNumbers),0] = lb_b
    bnds[0:len(AtomicNumbers),1] = ub_b
    bnds[len(AtomicNumbers):,0] = lb_h
    bnds[len(AtomicNumbers):,1] = ub_h
    bounds = Bounds(bnds[:,0], bnds[:,1])

    print('start the optimization...')
    res = minimize(costfun,x0,method='TNC', jac=True, bounds=bounds,tol=1e-10, options={'maxiter': 10, 'disp': True})
    # # res = minimize(costfun,x0,method='Powell', tol=1e-20, options={'maxiter': 10, 'disp': True})
    # print(res.x)
    print(res)
    Bfactors = res.x[0:len(AtomicNumbers)]
    Heights = res.x[len(AtomicNumbers):]
    return [Bfactors,Heights]


def kfactor(Fobs,Fcalc):
    k = np.sum( Fobs*(np.conj(Fcalc))+(np.conj(Fobs))*Fcalc )/np.sum( 2*(np.conj(Fcalc))*Fcalc )
    dd = np.real(k)
    return dd

def parameterfun(x,pos,rx,ry,rz,fa,kx,ky,kz,L,Fobs,Fcalc,atoms):
    from joblib import Parallel, delayed
    import multiprocessing as mp

    dd2 = x.copy()
    bf = pos[0,:].copy()
    ht = pos[0,:].copy()
    for tt in range(0,int(len(x)/2)):
        I = atoms == tt
        bf[I[0]] = x[tt]
        ht[I[0]] = x[tt+int(len(x)/2)]
    M = len(rx)
    dbf = np.zeros(M)
    dht = np.zeros(M)
    s2 = kx**2 + ky**2 + kz**2
    # print('first thing...')
    
    Fcalc = np.zeros_like(kx, dtype='complex')
    for bf0, ht0, rx0, ry0, rz0 in zip(bf, ht, rx, ry, rz):
        Fcalc += fa * ht0 * np.exp(-2*np.pi*1j*(kx*rx0+ky*ry0+kz*rz0)-bf0*s2)

    k = kfactor(Fobs,Fcalc)
    Fcalc = np.array(Fcalc,dtype=complex) * k
    dd1 = np.sum(np.abs(np.subtract(Fobs,Fcalc)**2))
    # print(dd1)
    # print('grad thing...')                                       
    Fsub = np.subtract(Fcalc,Fobs)
    
    # TODO: Need to vectorize funrun2 similar to funrun1
    #Fsub_conj = np.conj(Fsub)
    #for bf0, ht0, rx0, ry0, rz0 in zip(bf, ht, rx, ry, rz):
    #    dbf += (-ht0 * s2 * fa) * np.exp(-2*np.pi*1j*(kx*rx0+ky*ry0+kz*rz0)-bf0*s2)
    
    def funrun2(hh,fa,bf,ht,rx,ry,rz,kx,ky,kz,s2,Fsub):
        temp = np.multiply(-np.multiply(ht[hh]*s2,fa),np.multiply(np.exp( -2*np.pi*1j*(kx*rx[hh]+ky*ry[hh]+kz*rz[hh])-bf[hh]*s2 ),np.conj(Fsub)))
        return 2*np.real(np.sum(temp)) 
    
    inputs = np.arange(0,M)
    dbf = Parallel(n_jobs=num_cores)(delayed(funrun2)(M,fa,bf,ht,rx,ry,rz,kx,ky,kz,s2,Fsub) for M in inputs) 
    dbf = np.array(dbf)
    for tt in range(0,int(len(x)/2)):
        I = atoms == tt
        dd2[tt] = np.sum(dbf[I[0]])

    # TODO: Need to vectorize funrun3 similar to funrun1
    def funrun3(hh,fa,bf,ht,rx,ry,rz,kx,ky,kz,s2,Fsub):
        temp = fa * np.multiply(np.exp( -2*np.pi*1j*(kx*rx[hh]+ky*ry[hh]+kz*rz[hh])-bf[hh]*s2 ),np.conj(Fsub))
        return 2*np.real(np.sum(temp)) 

    dht = Parallel(n_jobs=num_cores)(delayed(funrun3)(M,fa,bf,ht,rx,ry,rz,kx,ky,kz,s2,Fsub) for M in inputs)
    dht = np.array(dht)
    for tt in range(0,int(len(x)/2)):
        I = atoms == tt
        dd2[tt+int(len(x)/2)] = np.sum(dht[I[0]])
    
    return [dd1,dd2]
    # return dd1


