import numpy as np
from datetime import datetime
from ..util import get_detection_and_shape

def sum_v(v1, v2):
    return v1[0] + v2[0], v1[1] + v2[1]

def prod_v(v, k):
    return v[0] * k, v[1] * k

def prom_v(v1, v2):
    return prod_v(sum_v(v1, v2), 0.5)

class DogFaceCrop():

    def __init__(self, detector, predictor):
        self.detector = detector
        self.predictor = predictor

    def find_center_brain(self, img, left_eye, right_eye, nose):
        center_eyes = prom_v(left_eye, right_eye)
        nose_to_center_eyes = sum_v(center_eyes, prod_v(nose, -1))
        center_brain_x = sum_v(center_eyes, prod_v(nose_to_center_eyes, 0.75))[0]
        center_muzzle = prom_v(nose, center_eyes)
        center_brain_y = center_muzzle[1]
        center_brain = (center_brain_x, center_brain_y)
        return center_brain

    def crop_with_padding(self, img, x0, y0, x1, y1):
        original_shape = img.shape
        table_shape = (original_shape[0]*3, original_shape[1]*3, original_shape[2])
        table = np.zeros(table_shape, img.dtype)
        table_origin = original_shape[0], original_shape[1]
        table[original_shape[0]:original_shape[0]*2, original_shape[1]:original_shape[1]*2, :] = img[:, :, :]
        return table[y0+table_origin[0]:y1+table_origin[0], x0+table_origin[1]:x1+table_origin[1]]

    def crop(self, img):
        flag, detection, shape = get_detection_and_shape(self.detector, self.predictor, img)
        if flag:
            # find center of brain
            center_brain = self.find_center_brain(img, shape[5], shape[2], shape[3])
            # find size of head
            head_width = detection.rect.width()
            head_height = detection.rect.height()
            head_size = max(head_width, head_height)
            total_size = head_size * 1.75
            x0, y0 = round(center_brain[0] - total_size/2), round(center_brain[1] - total_size/2)
            x1, y1 = round(center_brain[0] + total_size/2), round(center_brain[1] + total_size/2)
            if False: # show cropping
                img_result = img.copy()
                cv2.rectangle(img_result, pt1=(x0, y0), pt2=(x1, y1), thickness=2, color=(255,0,0), lineType=cv2.LINE_AA)
            cropping_points = x0, y0, x1, y1
            return True, self.crop_with_padding(img, *cropping_points), cropping_points
        return False, None, None
