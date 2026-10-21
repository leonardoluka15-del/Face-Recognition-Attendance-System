"""CPU-only baseline recognition using OpenCV Haar + LBPH.
Distances are not probabilities. This baseline has no spoof protection.
"""
import cv2
import numpy as np

class FaceEngine:
    def __init__(self):
        self.detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    def extract(self, data):
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None: raise ValueError('Cannot decode image.')
        if max(image.shape[:2]) > 1600:
            image = cv2.resize(image, None, fx=1600/max(image.shape[:2]), fy=1600/max(image.shape[:2]))
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(80,80))
        if len(faces) != 1: raise ValueError('Exactly one visible face is required. Move closer and use good lighting.')
        x,y,w,h = faces[0]
        face = cv2.resize(gray[y:y+h,x:x+w], (160,160))
        if cv2.Laplacian(face, cv2.CV_64F).var() < 35:
            raise ValueError('Face is too blurry. Hold still and try again.')
        return cv2.equalizeHist(face)
    @staticmethod
    def encode(face):
        ok, buf = cv2.imencode('.png', face)
        if not ok: raise ValueError('Could not save face sample.')
        return buf.tobytes()
    @staticmethod
    def recognize(face, samples, threshold=55, margin=8):
        if not samples: raise ValueError('Enrol someone first.')
        # Score each identity separately so ambiguous matches can be rejected.
        scores = []
        for person_id in sorted({s[0] for s in samples}):
            images = [cv2.imdecode(np.frombuffer(b, np.uint8), 0) for pid,b in samples if pid == person_id]
            model = cv2.face.LBPHFaceRecognizer_create()
            model.train(images, np.full(len(images), person_id, dtype=np.int32))
            _, distance = model.predict(face)
            scores.append((float(distance), person_id))
        scores.sort()
        distance, person_id = scores[0]
        if distance > threshold or (len(scores)>1 and scores[1][0]-distance < margin):
            return None, distance
        return person_id, distance
