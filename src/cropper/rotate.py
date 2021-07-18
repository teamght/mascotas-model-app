from ..util import get_detection_and_shape
import math
import imutils


class DogFaceRotate():

    def __init__(self, detector, predictor):
        self.detector = detector
        self.predictor = predictor

    def get_eyes(self, img):
        _, _, shape = get_detection_and_shape(self.detector, self.predictor, img)
        left_eye = shape[5]
        right_eye = shape[2]
        return left_eye, right_eye

    def rotate_finding_eyes(self, img):
        left_eye, right_eye = self.get_eyes(img)
        lx, ly = left_eye
        rx, ry = right_eye
        
        vect_x, vect_y = rx - lx, ry - ly
        angle = (-1) * math.degrees(math.atan2(vect_y, vect_x))
        img_rotated = imutils.rotate_bound(img, angle)
        
        return angle, img_rotated

    def find_final_angle(self, img, threshold, max_times):
        angles = []
        for i in range(max_times):
            angle, img = self.rotate_finding_eyes(img)
            angles.append(angle)
            if abs(angle) < threshold:
                break
        return sum(angles)

    def rotate(self, img):
        angle = self.find_final_angle(img, 2, 2)
        #print(angle)
        return imutils.rotate_bound(img, angle), angle
