"""
Speech Emotion Recognizer — Real Backend
=========================================
Uses a pre-trained Hugging Face model (wav2vec2) fine-tuned on emotion data.
Model: ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition
Emotions: angry, calm, disgust, fearful, happy, neutral, sad, surprised

Install:
    pip install -r requirements.txt

Run:
    python app.py

API:
    POST http://localhost:5000/analyze
    Form field: 'audio' (.wav file)
"""

import os
import uuid
import traceback

import numpy as np
import torch
import librosa
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------------------------------------------------------
# Load model once at startup (downloads ~1.2 GB on first run, cached after)
# ---------------------------------------------------------------------------
MODEL_NAME = "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"

print("Loading emotion recognition model... (first run downloads ~1.2 GB)")
feature_extractor = AutoFeatureExtractor.from_pretrained(MODEL_NAME)
model = AutoModelForAudioClassification.from_pretrained(MODEL_NAME)
model.eval()
print("Model loaded successfully!")

# Emotion labels from this model
EMOTION_EMOJIS = {
    "angry":     "😠",
    "calm":      "😌",
    "disgust":   "🤢",
    "fearful":   "😨",
    "happy":     "😊",
    "neutral":   "😐",
    "sad":       "😢",
    "surprised": "😲",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "wav"


def predict_emotion(file_path: str) -> dict:
    """
    Load a WAV file, run it through the wav2vec2 model, and return
    the top emotion with confidence scores for all classes.
    """
    # Load audio at 16kHz (required by wav2vec2)
    audio, sr = librosa.load(file_path, sr=16000, mono=True)

    # Limit to 10 seconds to avoid memory issues
    max_samples = 16000 * 10
    if len(audio) > max_samples:
        audio = audio[:max_samples]

    # Prepare inputs
    inputs = feature_extractor(
        audio,
        sampling_rate=16000,
        return_tensors="pt",
        padding=True
    )

    # Run inference
    with torch.no_grad():
        logits = model(**inputs).logits

    # Convert logits to probabilities
    probs = torch.softmax(logits, dim=-1).squeeze().numpy()

    # Map to label names
    id2label = model.config.id2label
    all_scores = {
        id2label[i]: round(float(probs[i]) * 100, 1)
        for i in range(len(probs))
    }

    # Top prediction
    best_idx = int(np.argmax(probs))
    top_emotion = id2label[best_idx]
    confidence = round(float(probs[best_idx]) * 100, 1)

    return {
        "emotion":    top_emotion,
        "confidence": confidence,
        "emoji":      EMOTION_EMOJIS.get(top_emotion, "🎙️"),
        "all_scores": all_scores,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status":  "ok",
        "message": "Speech Emotion Recognizer API is running.",
        "model":   MODEL_NAME,
        "emotions": list(EMOTION_EMOJIS.keys()),
    })


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    POST /analyze
    Form data: audio = <.wav file>

    Response:
    {
        "emotion":    "happy",
        "confidence": 91.3,
        "emoji":      "😊",
        "all_scores": {
            "angry": 1.2, "calm": 2.1, "disgust": 0.5,
            "fearful": 0.8, "happy": 91.3, "neutral": 3.1,
            "sad": 0.6, "surprised": 0.4
        }
    }
    """
    if "audio" not in request.files:
        return jsonify({"error": "No audio file found. Use field name 'audio'."}), 400

    file = request.files["audio"]

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only .wav files are supported."}), 415

    temp_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.wav")

    try:
        file.save(temp_path)
        result = predict_emotion(temp_path)
        return jsonify(result), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\nServer starting at http://localhost:5000\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
