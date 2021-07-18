import cv2
import imutils

class DogFaceResize():

    def final_resize(self, img):
        return cv2.resize(img, (224, 224), interpolation = cv2.INTER_CUBIC)

    def input_resize(self, img, max_size = 800):
        (h, w) = img.shape[:2]
        if max(h, w) <= max_size:
            return img
        if h > w:
            return imutils.resize(img, height = max_size, inter = cv2.INTER_CUBIC)
        else:
            return imutils.resize(img, width = max_size, inter = cv2.INTER_CUBIC)
