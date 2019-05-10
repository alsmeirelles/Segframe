#!/usr/bin/env python3
#-*- coding: utf-8

import importlib
import os,sys
from tqdm import tqdm
import numpy as np

from Datasources.CellRep import CellRep
from Utils import SaveLRCallback
from Utils import Exitcodes,CacheManager,PrintConfusionMatrix

#Keras
from keras import backend as K
from keras.preprocessing.image import ImageDataGenerator
# Training callbacks
from keras.callbacks import ModelCheckpoint, ReduceLROnPlateau
from keras.utils import to_categorical
from keras.models import load_model

#Tensorflow
import tensorflow as tf

#Scikit learn
from sklearn import metrics

def run_prediction(config,locations=None):
    """
    Main training function, to work as a new process
    """
    if config.info:
        print("Starting prediction process....")

    if not locations is None:
        cache_m = CacheManager(locations=locations)
    if config.print_pred:
        print_previous_prediction(config)
    else:
        predictor = Predictor(config)
        predictor.run()

def print_previous_prediction(config):
    cache_m = CacheManager()

    if not os.path.isfile(cache_m.fileLocation('test_pred.pik')):
        return None
    
    #Load predictions
    (expected,Y_pred,nclasses) = cache_m.load('test_pred.pik')
    y_pred = np.argmax(Y_pred, axis=1)
    
    #Output metrics
    f1 = metrics.f1_score(expected,y_pred,pos_label=1)
    print("F1 score: {0:.2f}".format(f1))

    m_conf = PrintConfusionMatrix(y_pred,expected,nclasses,config,"TILs")

    #ROC AUC
    #Get positive scores
    scores = Y_pred.transpose()[1]
        
    fpr,tpr,thresholds = metrics.roc_curve(expected,scores,pos_label=1)
    print("False positive rates: {0}".format(fpr))
    print("True positive rates: {0}".format(tpr))
    print("Thresholds: {0}".format(thresholds))
    print("AUC: {0:f}".format(metrics.roc_auc_score(expected,scores)))
    
class Predictor(object):
    """
    Class responsible for running the predictions and outputing results
    """

    def __init__(self,config):
        """
        @param config <parsed configurations>: configurations
        """
        self._config = config
        self._verbose = config.verbose
        self._ds = None

    def run(self):
        """
        Checks configurations, loads correct module, loads data
        Trains!

        New networks should be inserted as individual modules. Networks should be imported
        by the Models module.
        """
        net_name = self._config.network
        if net_name is None or net_name == '':
            print("A network should be specified")
            return Exitcodes.RUNTIME_ERROR
                
        if self._config.data:
            dsm = importlib.import_module('Datasources',self._config.data)
            self._ds = getattr(dsm,self._config.data)(self._config.predst,self._config.keepimg,self._config)
        else:
            self._ds = CellRep(self._config.predst,self._config.keepimg,self._config)

        net_module = importlib.import_module('Models',net_name)
        net_model = getattr(net_module,net_name)(self._config,self._ds)

        self._ds.load_metadata()

        self.run_test(net_model)
        
    def run_test(self,model):
        """
        This should be executed after a model has been trained
        """

        cache_m = CacheManager()
        split = None
        if os.path.isfile(cache_m.fileLocation('split_ratio.pik')):
            split = cache_m.load('split_ratio.pik')
        else:
            print("[Predictor] A previously trained model and dataset should exist. No previously defined spliting found.")
            return Exitcodes.RUNTIME_ERROR
        
        _,_,(x_test,y_test) = self._ds.split_metadata(split)
        X,Y = self._ds.load_data(data=(x_test,y_test))
        if self._config.verbose > 1:
            print("Y original ({1}):\n{0}".format(Y,Y.shape))        
        Y = to_categorical(Y,self._ds.nclasses)
    
        #During test phase multi-gpu mode is not necessary, load full model (multi-gpu would need to load training weights)
        if os.path.isfile(model.get_model_cache()):
            pred_model = load_model(model.get_model_cache())
            if self._config.info:
                print("Model loaded from: {0}".format(model.get_model_cache()))
        else:
            if self._config.info:
                print("Model not found at: {0}".format(model.get_model_cache()))
            return None

        # session setup
        sess = K.get_session()
        ses_config = tf.ConfigProto(
            device_count={"CPU":self._config.cpu_count,"GPU":self._config.gpu_count},
            intra_op_parallelism_threads=self._config.cpu_count if self._config.gpu_count == 0 else self._config.gpu_count, 
            inter_op_parallelism_threads=self._config.cpu_count if self._config.gpu_count == 0 else self._config.gpu_count,
            log_device_placement=True if self._verbose > 1 else False
            )
        sess.config = ses_config
        K.set_session(sess)
        stp = len(X)

        image_generator = ImageDataGenerator(samplewise_center=False, samplewise_std_normalization=False)
        test_generator = image_generator.flow(x=X,
                                            y=Y,
                                            batch_size=1,
                                            shuffle=False)
        
        if self._config.progressbar:
            l = tqdm(desc="Making predictions...",total=stp)

        Y_pred = np.zeros((stp,self._ds.nclasses),dtype=np.float32)
        for i in range(stp):
            example = test_generator.next()
            Y_pred[i] = pred_model.predict_on_batch(example[0])
            if self._config.progressbar:
                l.update(1)
            elif self._config.info:
                print("Batch prediction ({0}/{1})".format(i,stp))
            if self._config.verbose > 0:
                if not np.array_equal(Y[i],example[1][0]):
                    print("Datasource label ({0}) and batch label ({1}) differ".format(Y[i],example[1][0]))

        del(X)
        del(test_generator)
        
        if self._config.progressbar:
            l.close()

        y_pred = np.argmax(Y_pred, axis=1)
        expected = np.argmax(Y, axis=1)

        if self._config.verbose > 0:
            np.set_printoptions(threshold=np.inf)
            print("Y ({1}):\n{0}".format(Y,Y.shape))
            print("expected ({1}):\n{0}".format(expected,expected.shape))
            print("Predicted probs ({1}):\n{0}".format(Y_pred,Y_pred.shape))
            print("Predicted ({1}):\n{0}".format(y_pred,y_pred.shape))
            
        #Save predictions
        cache_m.dump((expected,Y_pred,self._ds.nclasses),'test_pred.pik')

        #Output metrics
        print_previous_prediction(self._config)
