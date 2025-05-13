import json
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from pydub import AudioSegment
from PIL import Image
import io
import numpy as np
from deepface import DeepFace
import ffmpeg
import librosa


def decode_audio_with_ffmpeg(audio_bytes):
    try:
        out, _ = (
            ffmpeg
            .input('pipe:0', format='webm')  # ✅ explicitly tell FFmpeg it's WebM
            .output('pipe:1', format='wav', acodec='pcm_s16le', ac=1, ar='16000')
            .run(input=audio_bytes, capture_stdout=True, capture_stderr=True)
        )
        return out
    except ffmpeg.Error as e:
        print("FFmpeg error:", e.stderr.decode())
        return None

def classify_depression(depression_score: float) -> str:
    if depression_score <= 0.2:
        return "No Depression: No significant depression detected."
    elif depression_score <= 0.5:
        return "Mild Depression: Mild depression detected."
    elif depression_score <= 0.8:
        return "Moderate Depression: Moderate depression detected."
    else:
        return "Severe Depression: Severe depression detected."

def classify_anxiety(anxiety_score: float) -> str:
    if anxiety_score <= 0.2:
        return "Low Anxiety: No significant anxiety detected."
    elif anxiety_score <= 0.5:
        return "Moderate Anxiety: Moderate anxiety level detected."
    else:
        return "High Anxiety: High anxiety level detected."


# Dummy ML model for now
def analyze_video_audio(video_frame=None, audio_chunk=None):
    result = {}

    # Facial expression analysis (video frame)
    if video_frame is not None:
        try:
            analysis = DeepFace.analyze(video_frame, actions=['emotion'], enforce_detection=False)
            result["emotion"] = analysis[0]["dominant_emotion"]
        except Exception as e:
            result["error"] = f"Error: {str(e)}"

    # Audio emotion analysis (audio chunk)
    if audio_chunk is not None:
        print("audio chunk received")
        result["depression_status"] = 0.0
        result['anxiety_score'] = 0.0
        decoded_wav = decode_audio_with_ffmpeg(audio_chunk)
        if not decoded_wav:
            result["anxiety_score"] = "Failed to decode audio"
            return result

        y, sr = librosa.load(io.BytesIO(decoded_wav), sr=None)

        # Calculate RMS energy
        rms = np.mean(librosa.feature.rms(y=y))
        print(f"RMS: {rms}")

        # Pitch detection
        pitch, voiced_flag, voiced_probs = librosa.pyin(y, fmin=50, fmax=300)
        avg_pitch = np.nanmean(pitch)
        print(f"Avg Pitch: {avg_pitch}")

        # Depression score
        if avg_pitch is not None and avg_pitch < 150:
            result["depression_score"] = min(max(1 - avg_pitch / 150, 0), 1)

        # Anxiety score
        if rms > 0.01:
            result["anxiety_score"] = min(max(rms * 10, 0), 1)

    return result

def fix_base64_padding(base64_str):
    """Ensure the base64 string has correct padding."""
    return base64_str + '=' * (4 - len(base64_str) % 4) if len(base64_str) % 4 != 0 else base64_str


class VideoAudioConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.latest_image = None  # Store the most recent video frame
        await self.accept()
        await self.send(text_data=json.dumps({'message': 'WebSocket connection established'}))

    async def disconnect(self, close_code):
        print("WebSocket closed")

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
                data = json.loads(text_data)
                image_array = None
                audio_data = None

                # Decode image if present
                if 'image' in data:
                    try:
                        image_data = data['image'].split(',')[1]  # Remove base64 prefix
                        decoded_image = base64.b64decode(image_data)
                        img = Image.open(io.BytesIO(decoded_image)).convert("RGB")
                        image_array = np.array(img)
                        self.latest_image = image_array  # Optionally store for fallback
                    except Exception as e:
                        print("Image decoding error:", e)

                # Decode audio if present
                if 'audio_chunk' in data:
                    try:
                        b64_audio = fix_base64_padding(data['audio_chunk'])
                        audio_data = base64.b64decode(b64_audio)
                    except Exception as e:
                        print("Audio decoding error:", e)

                # Perform combined analysis
                result = analyze_video_audio(video_frame=image_array, audio_chunk=audio_data)
                if result.get("depression_score", None) and isinstance(result.get("anxiety_score"), float):
                    if result.get("depression_score") >= 0:
                        result['depression_status'] = classify_depression(result.get("depression_score"))
                if result.get("anxiety_score", None) and isinstance(result.get("anxiety_score"), float):
                    if result.get("anxiety_score") >= 0:
                        result['anxiety_status'] = classify_anxiety(result.get("anxiety_score"))
                await self.send(text_data=json.dumps({"analysis": result}))
