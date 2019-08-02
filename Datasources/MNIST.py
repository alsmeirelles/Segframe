#!/usr/bin/env python3
#-*- coding: utf-8

import numpy as np
import os
import random

#Keras MNIST
from keras.datasets import mnist
import keras.backend as K

#Local modules
from Datasources import GenericDatasource as gd
from Preprocessing import NPImage
from Utils import CacheManager

class MNIST(gd.GenericDS):
    """
    Class that parses label.txt text files and loads all images into memory
    """

    def __init__(self,data_path,keepImg=False,config=None):
        """
        @param data_path <str>: path to directory where image patches are stored
        @param config <argparse>: configuration object
        @param keepImg <boolean>: keep image data in memory
        """
        if data_path == '':
            data_path = os.path.join(os.path.expanduser('~'), '.keras','datasets')
            
        super().__init__(data_path,keepImg,config,name='MNIST')
        self.nclasses = 10

        #MNIST is loaded from a single cache file
        self.multi_dir = False
        
    def _load_metadata_from_dir(self,d):
        """
        Create NPImages from KERAS MNIST
        """
        class_set = set()
        t_x,t_y = ([],[])

        (x_train, y_train), (x_test, y_test) = mnist.load_data()
        
        # input image dimensions
        img_rows, img_cols = 28, 28
        
        if K.image_data_format() == 'channels_first':
            x_train = x_train.reshape(x_train.shape[0], 1, img_rows, img_cols)
            x_test = x_test.reshape(x_test.shape[0], 1, img_rows, img_cols)
        else:
            x_train = x_train.reshape(x_train.shape[0], img_rows, img_cols, 1)
            x_test = x_test.reshape(x_test.shape[0], img_rows, img_cols, 1)

        #Normalize
        x_train = x_train.astype('float32')
        x_test = x_test.astype('float32')
        x_train /= 255
        x_test /= 255       
        tr_size = x_train.shape[0]
        test_size = x_test.shape[0]

        f_path = os.path.join(self.path,'mnist.npz')
        for s in range(tr_size):
            t_x.append(NPImage(f_path,x_train[s],True,'x_train',s,self._verbose))
            t_y.append(y_train[s])
            class_set.add(y_train[s])

        for i in range(test_size):
            t_x.append(NPImage(f_path,x_test[i],True,'x_test',i,self._verbose))
            t_y.append(y_test[i])
            class_set.add(y_test[i])

        return t_x,t_y
            