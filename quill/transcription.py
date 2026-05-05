import logging
import riva.client

logger = logging.getLogger("quill.transcription")

SERVER = "grpc.nvcf.nvidia.com:443"
FUNCTION_ID = "71203149-d3b7-4460-8231-1be2543a1fca"

CHUNK_DURATION_MS = 160
SAMPLE_RATE = 16000


class NvidiaTranscriptionService:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._auth = riva.client.Auth(
            uri=SERVER,
            use_ssl=True,
            metadata_args=[
                ("function-id", FUNCTION_ID),
                ("authorization", f"Bearer {api_key}"),
            ],
        )
        self._asr = riva.client.ASRService(self._auth)

    def transcribe(self, wav_path: str) -> str:
        logger.info("Sending %s to NVIDIA NIM ASR…", wav_path)
        config = riva.client.StreamingRecognitionConfig(
            config=riva.client.RecognitionConfig(
                encoding=riva.client.AudioEncoding.LINEAR_PCM,
                sample_rate_hertz=SAMPLE_RATE,
                language_code="en-US",
                max_alternatives=1,
                enable_automatic_punctuation=True,
            ),
            interim_results=False,
        )

        chunk_n_frames = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)
        audio_chunks = riva.client.AudioChunkFileIterator(
            wav_path, chunk_n_frames
        )
        responses = self._asr.streaming_response_generator(
            audio_chunks=audio_chunks,
            streaming_config=config,
        )

        transcripts = []
        for response in responses:
            for result in response.results:
                if result.is_final and result.alternatives:
                    transcripts.append(result.alternatives[0].transcript)

        text = " ".join(transcripts).strip()
        logger.info("Transcription complete: %r", text)
        return text


class GroqTranscriptionService:
    def __init__(self, api_key: str, model: str = "whisper-large-v3"):
        self._api_key = api_key
        self._model = model

    def transcribe(self, wav_path: str) -> str:
        from groq import Groq

        logger.info("Sending %s to Groq ASR (%s)…", wav_path, self._model)
        client = Groq(api_key=self._api_key)

        with open(wav_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(wav_path, audio_file.read()),
                model=self._model,
                temperature=0,
                response_format="verbose_json",
            )

        text = transcription.text
        logger.info("Transcription complete: %r", text)
        return text
