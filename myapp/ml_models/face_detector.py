import mediapipe as mp

class FaceDetector:
    def __init__(self):
        print("Loading face detection model...")
        self.face_detection = mp.solutions.face_detection.FaceDetection(
            model_selection=1,
            min_detection_confidence=0.5
        )

    def detect(self, image_rgb):
        return self.face_detection.process(image_rgb)

# Singleton instance
face_detector_instance = FaceDetector()
