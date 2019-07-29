#!/usr/bin/env python3
#-*- coding: utf-8

import importlib
import os

import numpy as np
import tensorflow as tf

#Network
from keras.models import Sequential,Model
from keras.layers import Input,Activation
from keras.layers import Dense, Dropout, Flatten
from keras.layers import ZeroPadding2D,Convolution2D, MaxPooling2D
from keras import backend, optimizers
from keras.utils import multi_gpu_model
from keras.applications import vgg16
from keras import regularizers
from keras_contrib.layers import GroupNormalization
from keras import backend as K

#Locals
from Utils import CacheManager
from Models.GenericModel import GenericModel

class KNet(GenericModel):
    """
    Implements abstract methods from GenericModel.
    Model is the same as in: https://keras.io/examples/mnist_cnn/
    """
    def __init__(self,config,ds,name=None):
        super().__init__(config,ds,name=name)
        if name is None:
            self.name = "KerasNet"
        self._modelCache = "{0}-model.h5".format(self.name)
        self._weightsCache = "{0}-weights.h5".format(self.name)
        
        self.cache_m = CacheManager()
        self.cache_m.registerFile(os.path.join(config.model_path,self._modelCache),self._modelCache)
        self.cache_m.registerFile(os.path.join(config.weights_path,self._weightsCache),self._weightsCache)
        self.cache_m.registerFile(os.path.join(config.weights_path,self._mgpu_weightsCache),self._mgpu_weightsCache)
        
    def get_model_cache(self):
        """
        Returns path to model cache
        """
        return self.cache_m.fileLocation(self._modelCache)
    
    def get_weights_cache(self):
        """
        Returns path to model cache
        """
        return self.cache_m.fileLocation(self._weightsCache)

    def get_mgpu_weights_cache(self):
        """
        Returns path to model cache
        """
        return self.cache_m.fileLocation(self._mgpu_weightsCache)
    
    def build(self,pre_trained=False):
        """
        Returns a VGG 16 model instance, final fully-connected layers are substituted by Conv2Ds
        
        @param pre_trained <boolean>: returned model should be pre-trained or not
        """
        width,height,channels = self._check_input_shape()
        
        if backend.image_data_format() == 'channels_first':
            input_shape = (channels, height, width)
        else:
            input_shape = (height, width, channels)

            
        self.cache_m = CacheManager()
        
        model = self._build_architecture(input_shape)
        
        #Check if previous training and LR is saved, if so, use it
        lr_cache = "{0}_learning_rate.txt".format(self.name)
        self.cache_m.registerFile(os.path.join(self._config.cache,lr_cache),lr_cache)
        l_rate = 0.0005
        if os.path.isfile(self.cache_m.fileLocation(lr_cache)) and not self._config.new_net:
            l_rate = float(self.cache_m.read(lr_cache))
            if self._config.info:
                print("Found previous learning rate: {0}".format(l_rate))
        
        sgd = optimizers.SGD(lr=l_rate, decay=1.5e-4, momentum=0.9, nesterov=True)
        #adam = optimizers.Adam(lr = l_rate)
        
        #Return parallel model if multiple GPUs are available
        parallel_model = None
        
        if self._config.gpu_count > 1:
            with tf.device('/cpu:0'):
                model.compile(loss='categorical_crossentropy',
                    optimizer=sgd,
                    metrics=['accuracy'])

            parallel_model = multi_gpu_model(model,gpus=self._config.gpu_count)
            parallel_model.compile(loss='categorical_crossentropy',
                                       optimizer=sgd,
                                       metrics=['accuracy'],
                                       #options=p_opt, 
                                       #run_metadata=p_mtd
                                       )
        else:
            model.compile(loss='categorical_crossentropy',
                optimizer=sgd,
                metrics=['accuracy'],
                #options=p_opt, 
                #run_metadata=p_mtd
                )

        return (model,parallel_model)

    def _build_architecture(self,input_shape):
        model = Sequential()
        model.add(Convolution2D(32, kernel_size=(3, 3),
                    activation='relu',
                    input_shape=input_shape))
        model.add(Convolution2D(64, (3, 3), activation='relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))
        model.add(Dropout(0.25))
        model.add(Flatten())
        model.add(Dense(128, activation='relu'))
        model.add(Dropout(0.5))
        model.add(Dense(self._ds.nclasses, activation='softmax'))

        return model

class BayesKNet(KNet):
    """
    Bayesian model for the KNet
    """
    def __init__(self,config,ds):
        super(BayesKNet,self).__init__(config=config,ds=ds,name = "BayesKNet")

    def _build_architecture(self,input_shape):
        inp = Input(shape=input_shape)

        x = Convolution2D(32, (3, 3),input_shape=input_shape,
                        strides=1,
                        padding='valid',
                        name='block1_conv1')(inp)
        x = Activation('relu')(x)

        x = Convolution2D(64, (3, 3),
                        strides=1,
                        padding='valid',
                    name='block1_conv2')(x)
        x = Activation('relu')(x)
        x = MaxPooling2D(pool_size=(2, 2),strides=1)(x)
        x = Dropout(0.25)(x,training=True)
        x = Flatten()(x)
        x = Dense(128)(x)
        x = Dropout(0.5)(x,training=True)
        x = Dense(self._ds.nclasses)(x)
        output = Activation('softmax')(x)
        
        return Model(inp,output)
