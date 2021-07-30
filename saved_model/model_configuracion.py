import os
import tensorflow as tf
#os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow.keras.backend as K
from src.config import MODELO_ENTRENADO
import numpy as np

class ModelConfig():

    def __init__(self):
        pass

    def cargar_modelo(self):

        alpha = 0.3
        def triplet(y_true,y_pred):
            
            a = y_pred[0::3]
            p = y_pred[1::3]
            n = y_pred[2::3]
            
            ap = K.sum(K.square(a-p),-1)
            an = K.sum(K.square(a-n),-1)

            return K.sum(tf.nn.relu(ap - an + alpha))

        def triplet_acc(y_true,y_pred):
            a = y_pred[0::3]
            p = y_pred[1::3]
            n = y_pred[2::3]
            
            ap = K.sum(K.square(a-p),-1)
            an = K.sum(K.square(a-n),-1)
            
            return K.less(ap+alpha,an)

        print('Loading model {}'.format(MODELO_ENTRENADO))
        try:
            model = tf.keras.models.load_model(
                MODELO_ENTRENADO,
                custom_objects={'tf': tf, 'triplet':triplet, 'triplet_acc':triplet_acc},compile=False)

            print('Done.')
            print(model)
            return model
        except Exception as e:
            print(f'Error al cargar el modelo: {e}')