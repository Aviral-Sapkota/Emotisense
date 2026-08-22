import os
import base64
import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# The 7 emotion labels — ORDER MUST MATCH THE MODEL 

EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

# Emoji for display (used in push notifications)
EMOTION_EMOJI = {
    "angry":    "😠",
    "disgust":  "🤢",
    "fear":     "😨",
    "happy":    "😄",
    "sad":      "😢",
    "surprise": "😮",
    "neutral":  "😐",
}


class FERModel:
    """
    Wraps Keras .h5 model + OpenCV face detector.
    Loaded once at startup and reused for every request (efficient).
    """

    def __init__(self):
        self._model = None           # Keras model (loaded lazily on first use)
        self._face_cascade = None    # OpenCV Haar Cascade for face detection
        self._model_path = os.environ.get("MODEL_PATH", "model/emotion_model.h5")

    def _load(self):
        """Load the model and face detector the first time they're needed."""
        if self._model is not None:
            return  # already loaded

        # Load your Keras CNN 
        import tensorflow as tf   # imported here so startup is faster if GPU not available

        if not os.path.exists(self._model_path):
            raise FileNotFoundError(
                f"Model file not found at '{self._model_path}'.\n"
                f"Put your .h5 file in the project folder and set MODEL_PATH in .env"
            )

        logger.info("Loading Keras model from %s ...", self._model_path)
        self._model = tf.keras.models.load_model(self._model_path)
        logger.info("✅ Model loaded. Input shape: %s", self._model.input_shape)

        #  Load OpenCV Haar Cascade 
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._face_cascade = cv2.CascadeClassifier(cascade_path)
        logger.info("✅ Face detector loaded.")

    def predict(self, image_b64: str) -> dict:
        """
        Run face detection + emotion prediction on a base64 JPEG image.

        Args:
            image_b64: Base64-encoded JPEG string (no data-URL prefix)

        Returns:
            {
                "primary":        "happy",
                "confidence":     87.3,
                "scores":         {"happy": 87.3, "sad": 5.1, ...},
                "faces_detected": 1,
                "message":        None   (or "No face detected" etc.)
            }
        """
        self._load()  # no-op if already loaded

        #  1. Decode base64 → NumPy image array 
        try:
            img_bytes = base64.b64decode(image_b64)
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            frame     = cv2.imdecode(img_array, cv2.IMREAD_COLOR)  # BGR colour image
        except Exception as exc:
            logger.error("Failed to decode image: %s", exc)
            return self._no_face_result("Could not decode image.")

        if frame is None:
            return self._no_face_result("Could not decode image.")

        # 2. Convert to grayscale for face detection 
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 3. Detect faces using Haar Cascade 
        
        faces = self._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )

        if len(faces) == 0:
            return self._no_face_result("No face detected. Please face the camera directly.")

        # 4. Pick the largest face (most prominent in frame)
        # faces is an array of (x, y, w, h) rectangles
        largest_face = max(faces, key=lambda f: f[2] * f[3])  # w * h = area
        x, y, w, h   = largest_face

        #  5. Crop + preprocess for your CNN 
        face_roi = gray[y : y + h, x : x + w]           # crop face region

        face_48  = cv2.resize(face_roi, (48, 48))        # resize to 48×48

        face_norm = face_48.astype("float32") / 255.0    # normalise 0-255 → 0.0-1.0

        # Keras expects shape (batch_size, height, width, channels)
        # Our model: (1, 48, 48, 1) — 1 image, 48×48, 1 channel (grayscale)
        face_input = face_norm.reshape(1, 48, 48, 1)

        # 6. Run  CNN 
        raw_scores = self._model.predict(face_input, verbose=0)[0]
        
        
        scores_prob = raw_scores

        # Convert to percentages (sum to 100)
        scores_pct  = (scores_prob * 100).tolist()

        #  7. Build result dict 
        scores_dict = {
            label: round(score, 2)
            for label, score in zip(EMOTION_LABELS, scores_pct)
        }

        primary_idx  = int(np.argmax(scores_prob))
        primary      = EMOTION_LABELS[primary_idx]
        confidence   = round(scores_pct[primary_idx], 2)

        logger.info(
            "Prediction → primary=%s confidence=%.1f%% faces=%d",
            primary, confidence, len(faces)
        )

        return {
            "primary":        primary,
            "confidence":     confidence,
            "scores": scores_dict,
            "faces_detected": len(faces),
            "message": None
            
        }

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        """Numerically stable softmax."""
        e = np.exp(x - np.max(x))
        return e / e.sum()

    @staticmethod
    def _no_face_result(message: str) -> dict:
        """Return a safe default when no face is found."""
        return {
            "primary":        "neutral",
            "confidence":     0.0,
            "scores":         {label: 0.0 for label in EMOTION_LABELS},
            "faces_detected": 0,
            "message":        message,
        }



# Loading the model takes a few seconds. We do it once at startup, then reuse.
fer_model = FERModel()
