import base64
import numpy as np
import cv2
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=True, lang="en")  # nên init 1 lần

def get_text_from_ocr(image_uri):
    # nếu là data URI dạng: data:image/png;base64,...
    if "," in image_uri:
        base64_img = image_uri.split(",")[1]
    else:
        base64_img = image_uri

    # decode base64
    img_bytes = base64.b64decode(base64_img)

    # convert thành numpy image
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # OCR
    result = ocr.predict(img)

    texts = []
    if result and result[0]:
        for line in result[0]:
            texts.append(line[1][0])

    return " ".join(texts)

img_uri = 