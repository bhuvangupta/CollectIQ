from datetime import datetime
from celery import shared_task
from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.tasks.campaign_tasks import get_sync_session
from app.core.config import settings


@celery_app.task(name="app.tasks.transcription_tasks.process_pending_transcriptions")
def process_pending_transcriptions():
    """Process pending call transcriptions."""
    session = get_sync_session()

    try:
        from app.models.communication import CallRecording

        # Find pending transcriptions
        pending = session.execute(
            select(CallRecording).where(
                CallRecording.transcription_status == "pending"
            ).limit(10)
        ).scalars().all()

        queued = 0
        for recording in pending:
            transcribe_recording.delay(str(recording.id))
            recording.transcription_status = "processing"
            queued += 1

        session.commit()

        return {"status": "success", "queued": queued}

    finally:
        session.close()


@celery_app.task(name="app.tasks.transcription_tasks.transcribe_recording")
def transcribe_recording(recording_id: str):
    """Transcribe a single recording."""
    session = get_sync_session()

    try:
        from app.models.communication import CallRecording, Communication
        import httpx

        recording = session.execute(
            select(CallRecording).where(CallRecording.id == recording_id)
        ).scalar_one_or_none()

        if not recording:
            return {"status": "error", "reason": "Recording not found"}

        # Get recording URL
        recording_url = recording.file_path

        try:
            # Call AI engine for transcription
            response = httpx.post(
                f"{settings.ai_engine_url}/stt/transcribe",
                json={
                    "audio_url": recording_url,
                    "language": "hi"  # Default to Hindi
                },
                timeout=120.0
            )
            response.raise_for_status()
            result = response.json()

            # Update recording with transcription
            recording.transcription_status = "completed"
            recording.transcription_text = result.get("text", "")
            recording.transcription_segments = result.get("segments", [])
            recording.transcription_language = result.get("language", "hi")
            recording.transcription_confidence = result.get("confidence", 0)

            # Trigger summarization
            summarize_transcription.delay(str(recording_id))

        except Exception as e:
            recording.transcription_status = "failed"
            session.commit()
            raise

        session.commit()

        return {"status": "success", "recording_id": recording_id}

    finally:
        session.close()


@celery_app.task(name="app.tasks.transcription_tasks.summarize_transcription")
def summarize_transcription(recording_id: str):
    """Generate AI summary of transcription."""
    session = get_sync_session()

    try:
        from app.models.communication import CallRecording, Communication
        import httpx

        recording = session.execute(
            select(CallRecording).where(CallRecording.id == recording_id)
        ).scalar_one_or_none()

        if not recording or not recording.transcription_text:
            return {"status": "skipped"}

        try:
            # Call AI engine for summarization
            response = httpx.post(
                f"{settings.ai_engine_url}/analyze/summarize",
                json={
                    "transcript": recording.transcription_text,
                    "language": "en"
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()

            # Update recording
            recording.ai_summary = result.get("summary", "")
            recording.key_points = result.get("key_points", [])
            recording.action_items = result.get("action_items", [])
            recording.entities_mentioned = result.get("entities", {})

            # Check for compliance issues
            compliance_response = httpx.post(
                f"{settings.ai_engine_url}/analyze/compliance",
                json={"transcript": recording.transcription_text},
                timeout=30.0
            )
            if compliance_response.status_code == 200:
                compliance_result = compliance_response.json()
                recording.compliance_flags = compliance_result.get("flags", [])

            # Update communication summary
            communication = session.execute(
                select(Communication).where(
                    Communication.id == recording.communication_id
                )
            ).scalar_one_or_none()

            if communication:
                communication.summary = recording.ai_summary

        except Exception as e:
            # Don't fail the whole task, just log
            print(f"Summarization failed: {e}")

        session.commit()

        return {"status": "success"}

    finally:
        session.close()


@celery_app.task(name="app.tasks.transcription_tasks.analyze_sentiment")
def analyze_sentiment(communication_id: str):
    """Analyze sentiment of a call."""
    session = get_sync_session()

    try:
        from app.models.communication import Communication, CallRecording
        import httpx

        communication = session.execute(
            select(Communication).where(Communication.id == communication_id)
        ).scalar_one_or_none()

        if not communication:
            return {"status": "error", "reason": "Communication not found"}

        # Get transcription
        recording = session.execute(
            select(CallRecording).where(
                CallRecording.communication_id == communication_id
            )
        ).scalar_one_or_none()

        if not recording or not recording.transcription_text:
            return {"status": "skipped", "reason": "No transcription"}

        try:
            response = httpx.post(
                f"{settings.ai_engine_url}/analyze/sentiment",
                json={"text": recording.transcription_text},
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

            communication.sentiment = result.get("sentiment", "neutral")
            communication.sentiment_score = result.get("score", 0)

            session.commit()

        except Exception as e:
            print(f"Sentiment analysis failed: {e}")

        return {"status": "success"}

    finally:
        session.close()
