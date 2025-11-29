"""Flask API backend for chatbot dashboard frontend."""
import json
import os
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import Flask, jsonify, Response, request
from flask_cors import CORS
from queue import Queue
from threading import Lock

from modules.config import (
    DB_PATH,
    MEMORY_CACHE_FILE,
    MEMOBASE_BASE_URL,
    MEMOBASE_API_KEY,
    DEFAULT_SPEAKER,
    logger,
)
from modules.memory import string_to_uuid, memobase_request, MemoBaseAPIError

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Global update notification system
_update_queues: Dict[str, List[Queue]] = {}
_queues_lock = Lock()


def get_big5_personality(user_name: str) -> Optional[Dict[str, float]]:
    """Get Big5 personality traits from database.

    Args:
        user_name: Name of the user

    Returns:
        Dict with Big5 traits or None if not found
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT extraversion, neuroticism, agreeableness, conscientiousness, openness
                FROM user WHERE name = ?
                """,
                (user_name,)
            )
            row = c.fetchone()

            if row:
                # Convert to frontend format (note: capitalization matches frontend types)
                return {
                    "Extroversion": float(row[0]) if row[0] is not None else 0.5,
                    "Neuroticism": float(row[1]) if row[1] is not None else 0.5,
                    "Agreeableness": float(row[2]) if row[2] is not None else 0.5,
                    "Conscientiousness": float(row[3]) if row[3] is not None else 0.5,
                    "Openness": float(row[4]) if row[4] is not None else 0.5,
                }
    except Exception as e:
        logger.error(f"Failed to fetch Big5 data: {e}")

    return None


def get_latest_emotions(user_uuid: str) -> tuple[Optional[Dict], Optional[Dict]]:
    """Get latest emotion data from memory cache.

    Args:
        user_uuid: UUID of the user

    Returns:
        Tuple of (speech_emotion, text_emotion) dicts
    """
    try:
        if not os.path.exists(MEMORY_CACHE_FILE):
            return None, None

        with open(MEMORY_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        if user_uuid not in cache_data:
            return None, None

        # Get latest conversation from most recent session
        sessions = cache_data[user_uuid].get("sessions", {})
        if not sessions:
            return None, None

        # Sort sessions by date to get most recent
        sorted_sessions = sorted(sessions.items(), reverse=True)

        for session_id, session_data in sorted_sessions:
            conversations = session_data.get("conversations", [])
            if conversations:
                # Get the last conversation
                latest = conversations[-1]

                speech_emotion = None
                text_emotion = None

                if "speech_emotion" in latest:
                    speech_emotion = json.loads(latest["speech_emotion"])

                if "text_emotion" in latest:
                    text_emotion = json.loads(latest["text_emotion"])

                return speech_emotion, text_emotion

    except Exception as e:
        logger.error(f"Failed to fetch emotion data: {e}")

    return None, None


def get_memobase_profiles(user_uuid: str) -> List[Dict]:
    """Get user profiles from MemoBase.

    Args:
        user_uuid: UUID of the user

    Returns:
        List of profile dicts
    """
    try:
        data = memobase_request("GET", f"/users/profile/{user_uuid}")
        if data and isinstance(data, dict):
            profile_list = data.get("profiles", [])
            # Transform to frontend format
            profiles = []
            for item in profile_list:
                attributes = item.get("attributes", {})
                profiles.append({
                    "id": item.get("id", ""),
                    "topic": attributes.get("topic", ""),
                    "sub_topic": attributes.get("sub_topic", ""),
                    "content": item.get("content", ""),
                    "created_at": item.get("created_at", ""),
                    "updated_at": item.get("updated_at", ""),
                })
            return profiles
    except (MemoBaseAPIError, Exception) as e:
        logger.error(f"Failed to fetch profiles from MemoBase: {e}")

    return []


def get_memobase_events(user_uuid: str, topk: int = 1000) -> List[Dict]:
    """Get user events from MemoBase.

    Args:
        user_uuid: UUID of the user
        topk: Number of events to retrieve (default: 1000)

    Returns:
        List of event dicts
    """
    try:
        # Add topk parameter to get more events (default is only 10)
        data = memobase_request("GET", f"/users/event/{user_uuid}", params={"topk": topk})
        if data and isinstance(data, dict):
            event_list = data.get("events", [])
            # Transform to frontend format
            events = []
            for item in event_list:
                events.append({
                    "id": item.get("id", ""),
                    "created_at": item.get("created_at", ""),
                    "event_data": item.get("event_data", {}),
                })
            return events
    except (MemoBaseAPIError, Exception) as e:
        logger.error(f"Failed to fetch events from MemoBase: {e}")

    return []


def get_latest_transcription(user_uuid: str) -> Optional[Dict]:
    """Get latest conversation transcription from cache.

    Args:
        user_uuid: UUID of the user

    Returns:
        Transcription dict or None
    """
    try:
        if not os.path.exists(MEMORY_CACHE_FILE):
            return None

        with open(MEMORY_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        if user_uuid not in cache_data:
            return None

        # Get latest conversation
        sessions = cache_data[user_uuid].get("sessions", {})
        if not sessions:
            return None

        sorted_sessions = sorted(sessions.items(), reverse=True)

        for session_id, session_data in sorted_sessions:
            conversations = session_data.get("conversations", [])
            if conversations:
                latest = conversations[-1]

                # Parse emotions
                speech_emotion = None
                text_emotion = None

                if "speech_emotion" in latest:
                    speech_emotion = json.loads(latest["speech_emotion"])

                if "text_emotion" in latest:
                    text_emotion = json.loads(latest["text_emotion"])

                return {
                    "text": latest.get("user_text", ""),
                    "response": latest.get("assistant_text", ""),
                    "timestamp": latest.get("timestamp", ""),
                    "speechEmotion": speech_emotion or {},
                    "textEmotion": text_emotion or {},
                    "big5": {},  # Will be filled from database
                }

    except Exception as e:
        logger.error(f"Failed to fetch transcription: {e}")

    return None


@app.route('/api/dashboard/<user_id>', methods=['GET'])
def get_dashboard_data(user_id: str):
    """Get complete dashboard data for a user.

    Args:
        user_id: User identifier (name)

    Returns:
        JSON response with dashboard data
    """
    try:
        # Convert user_id to UUID for MemoBase queries
        user_uuid = string_to_uuid(user_id)

        # Fetch data from various sources
        big5 = get_big5_personality(user_id)
        speech_emotion, text_emotion = get_latest_emotions(user_uuid)
        profiles = get_memobase_profiles(user_uuid)
        events = get_memobase_events(user_uuid)
        transcription = get_latest_transcription(user_uuid)

        # Add Big5 to transcription if available
        if transcription and big5:
            transcription["big5"] = big5

        # Build response
        response_data = {
            "userId": user_id,
            "userName": user_id,
            "currentTranscription": transcription,
            "speechEmotion": speech_emotion,
            "textEmotion": text_emotion,
            "big5": big5,
            "profiles": profiles,
            "events": events,
        }

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Dashboard API error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/memories/<user_id>', methods=['GET'])
def get_memories(user_id: str):
    """Get user memories (profiles and events).

    Args:
        user_id: User identifier

    Returns:
        JSON response with profiles and events
    """
    try:
        user_uuid = string_to_uuid(user_id)

        profiles = get_memobase_profiles(user_uuid)
        events = get_memobase_events(user_uuid)

        return jsonify({
            "profiles": profiles,
            "events": events,
        }), 200

    except Exception as e:
        logger.error(f"Memories API error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/stream/<user_id>', methods=['GET'])
def stream_updates(user_id: str):
    """Server-Sent Events stream for real-time updates.

    Args:
        user_id: User identifier

    Returns:
        SSE stream
    """
    def fetch_and_send_data():
        """Fetch current data and format for SSE."""
        user_uuid = string_to_uuid(user_id)
        big5 = get_big5_personality(user_id)
        speech_emotion, text_emotion = get_latest_emotions(user_uuid)
        profiles = get_memobase_profiles(user_uuid)
        events = get_memobase_events(user_uuid)
        transcription = get_latest_transcription(user_uuid)

        if transcription and big5:
            transcription["big5"] = big5

        data = {
            "userId": user_id,
            "userName": user_id,
            "currentTranscription": transcription,
            "speechEmotion": speech_emotion,
            "textEmotion": text_emotion,
            "big5": big5,
            "profiles": profiles,
            "events": events,
        }
        return f"event: full_update\ndata: {json.dumps(data)}\n\n"

    def generate():
        """Generate SSE events."""
        # Create a queue for this connection
        q = Queue(maxsize=100)  # Increased for streaming chunks

        with _queues_lock:
            if user_id not in _update_queues:
                _update_queues[user_id] = []
            _update_queues[user_id].append(q)

        try:
            # Send initial data immediately
            logger.info(f"SSE: New connection from user {user_id}")
            yield fetch_and_send_data()

            # Wait for push notifications
            while True:
                try:
                    # Block until notification received (with 30s timeout for keepalive)
                    msg = q.get(timeout=30)
                    if msg == "UPDATE":
                        logger.info(f"SSE: Sending push update to {user_id}")
                        yield fetch_and_send_data()
                    elif isinstance(msg, dict):
                        # Streaming chunk or other event
                        event_type = msg.get("event", "message")
                        event_data = msg.get("data", {})
                        yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
                except:
                    # Timeout - send keepalive comment
                    yield ": keepalive\n\n"

        finally:
            # Remove queue when connection closes
            with _queues_lock:
                if user_id in _update_queues:
                    _update_queues[user_id].remove(q)
                    if not _update_queues[user_id]:
                        del _update_queues[user_id]
            logger.info(f"SSE: Connection closed for user {user_id}")

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/profile/<profile_id>', methods=['DELETE'])
def delete_profile(profile_id: str):
    """Delete a profile by ID.

    Args:
        profile_id: Profile ID to delete

    Returns:
        JSON response with success/error message
    """
    try:
        # Get user_id from query params (required for MemoBase API)
        from flask import request
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "user_id parameter is required"}), 400

        user_uuid = string_to_uuid(user_id)

        # Call MemoBase API to delete profile
        memobase_request("DELETE", f"/users/profile/{user_uuid}/{profile_id}")

        return jsonify({"message": "Profile deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Delete profile API error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/event/<event_id>', methods=['DELETE'])
def delete_event(event_id: str):
    """Delete an event by ID.

    Args:
        event_id: Event ID to delete

    Returns:
        JSON response with success/error message
    """
    try:
        # Get user_id from query params (required for MemoBase API)
        from flask import request
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "user_id parameter is required"}), 400

        user_uuid = string_to_uuid(user_id)

        # Call MemoBase API to delete event
        memobase_request("DELETE", f"/users/event/{user_uuid}/{event_id}")

        return jsonify({"message": "Event deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Delete event API error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/notify/<user_id>', methods=['POST'])
def notify_update(user_id: str):
    """Webhook endpoint for chatbot to trigger real-time updates.

    Args:
        user_id: User identifier

    Returns:
        JSON response with notification status
    """
    try:
        with _queues_lock:
            if user_id in _update_queues:
                # Send notification to all connected clients for this user
                for q in _update_queues[user_id]:
                    try:
                        q.put_nowait("UPDATE")
                    except:
                        pass  # Queue full, skip this client
                logger.info(f"Notified {len(_update_queues[user_id])} SSE client(s) for user {user_id}")
                return jsonify({"status": "notified", "clients": len(_update_queues[user_id])}), 200
            else:
                logger.info(f"No SSE clients connected for user {user_id}")
                return jsonify({"status": "no_clients"}), 200

    except Exception as e:
        logger.error(f"Notify endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/user-input/<user_id>', methods=['POST'])
def push_user_input(user_id: str):
    """Webhook endpoint for chatbot to push user input text immediately after transcription.

    Args:
        user_id: User identifier

    Returns:
        JSON response with status
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        user_text = data.get("text", "")
        timestamp = data.get("timestamp", "")

        with _queues_lock:
            if user_id in _update_queues:
                event_data = {
                    "event": "user_input",
                    "data": {
                        "text": user_text,
                        "timestamp": timestamp,
                    }
                }

                # Push to all connected clients
                for q in _update_queues[user_id]:
                    try:
                        q.put_nowait(event_data)
                    except:
                        pass  # Queue full, skip this client

                logger.info(f"User input pushed to {len(_update_queues[user_id])} client(s)")
                return jsonify({"status": "pushed", "clients": len(_update_queues[user_id])}), 200
            else:
                return jsonify({"status": "no_clients"}), 200

    except Exception as e:
        logger.error(f"User input push error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/stream-chunk/<user_id>', methods=['POST'])
def stream_chunk(user_id: str):
    """Webhook endpoint for chatbot to push streaming text chunks.

    Args:
        user_id: User identifier

    Returns:
        JSON response with status
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        chunk_text = data.get("chunk", "")
        is_final = data.get("is_final", False)

        with _queues_lock:
            if user_id in _update_queues:
                event_data = {
                    "event": "streaming_complete" if is_final else "streaming_chunk",
                    "data": {
                        "chunk": chunk_text,
                        "is_final": is_final,
                    }
                }

                # Push to all connected clients
                for q in _update_queues[user_id]:
                    try:
                        q.put_nowait(event_data)
                    except:
                        pass  # Queue full, skip this client

                return jsonify({"status": "pushed", "clients": len(_update_queues[user_id])}), 200
            else:
                return jsonify({"status": "no_clients"}), 200

    except Exception as e:
        logger.error(f"Stream chunk endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/status/<user_id>', methods=['POST'])
def push_status(user_id: str):
    """Webhook endpoint for chatbot to push processing status updates.

    Args:
        user_id: User identifier

    Returns:
        JSON response with status
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        status = data.get("status", "")

        with _queues_lock:
            if user_id in _update_queues:
                event_data = {
                    "event": "status_update",
                    "data": {
                        "status": status,
                    }
                }

                # Push to all connected clients
                for q in _update_queues[user_id]:
                    try:
                        q.put_nowait(event_data)
                    except:
                        pass  # Queue full, skip this client

                logger.debug(f"Status '{status}' pushed to {len(_update_queues[user_id])} client(s)")
                return jsonify({"status": "pushed", "clients": len(_update_queues[user_id])}), 200
            else:
                return jsonify({"status": "no_clients"}), 200

    except Exception as e:
        logger.error(f"Status push endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration including default user."""
    return jsonify({
        "defaultUser": DEFAULT_SPEAKER,
        "memobaseUrl": MEMOBASE_BASE_URL,
    }), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    logger.info("Starting chatbot backend API server...")
    logger.info(f"MemoBase URL: {MEMOBASE_BASE_URL}")
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Memory cache: {MEMORY_CACHE_FILE}")

    # Run on port 5000 (frontend expects this)
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
