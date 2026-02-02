import axios from 'axios';
import type { DashboardData, UserProfile, UserEvent } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Fetch current default user from backend config
export const fetchDefaultUser = async (): Promise<string | null> => {
  try {
    const response = await apiClient.get<{ defaultUser: string }>('/config');
    return response.data.defaultUser;
  } catch (error) {
    console.error('Failed to fetch default user from backend:', error);
    return null;
  }
};

export const fetchDashboardData = async (userId: string): Promise<DashboardData> => {
  const response = await apiClient.get<DashboardData>(`/dashboard/${userId}`);
  return response.data;
};

export const fetchUserMemories = async (userId: string): Promise<{ profiles: UserProfile[]; events: UserEvent[] }> => {
  const response = await apiClient.get<{ profiles: UserProfile[]; events: UserEvent[] }>(`/memories/${userId}`);
  return response.data;
};

export const deleteProfile = async (userId: string, profileId: string): Promise<void> => {
  await apiClient.delete(`/profile/${profileId}?user_id=${userId}`);
};

export const deleteEvent = async (userId: string, eventId: string): Promise<void> => {
  await apiClient.delete(`/event/${eventId}?user_id=${userId}`);
};

export interface StreamingCallbacks {
  onFullUpdate?: (data: DashboardData) => void;
  onStreamingChunk?: (chunk: string, isFinal: boolean) => void;
  onUserInput?: (text: string, timestamp: string) => void;
  onStatusUpdate?: (status: string) => void;
  onAudioChunk?: (chunk: string, sampleRate: number, isFinal: boolean) => void;
}

export const subscribeToUpdates = (
  userId: string,
  onUpdate: (data: DashboardData) => void,
  callbacks?: StreamingCallbacks
) => {
  const sseBase = API_BASE_URL;
  const sseUrl = `${sseBase}/stream/${encodeURIComponent(userId)}`;

  console.log('[SSE] Connecting to:', sseUrl);
  const eventSource = new EventSource(sseUrl);

  // Handle user input (transcription complete)
  eventSource.addEventListener('user_input', (event) => {
    const data = JSON.parse(event.data);
    console.log('[SSE] Received user input:', data.text);
    if (callbacks?.onUserInput) {
      callbacks.onUserInput(data.text, data.timestamp);
    }
  });

  // Handle full dashboard updates
  eventSource.addEventListener('full_update', (event) => {
    console.log('[SSE] Received full update:', event.data.substring(0, 100) + '...');
    const data = JSON.parse(event.data);
    if (callbacks?.onFullUpdate) {
      callbacks.onFullUpdate(data);
    } else {
      onUpdate(data);
    }
  });

  // Handle streaming text chunks
  eventSource.addEventListener('streaming_chunk', (event) => {
    const data = JSON.parse(event.data);
    console.log('[SSE] Received streaming chunk:', data.chunk);
    if (callbacks?.onStreamingChunk) {
      callbacks.onStreamingChunk(data.chunk, data.is_final);
    }
  });

  // Handle streaming completion
  eventSource.addEventListener('streaming_complete', (event) => {
    const data = JSON.parse(event.data);
    console.log('[SSE] Streaming complete');
    if (callbacks?.onStreamingChunk) {
      callbacks.onStreamingChunk(data.chunk, true);
    }
  });

  // Handle streaming audio chunks
  eventSource.addEventListener('audio_chunk', (event) => {
    const data = JSON.parse(event.data);
    // DEBUG: Log received audio chunk from SSE
    console.log(
      `[SSE DEBUG] audio_chunk received: chunk_length=${data.chunk?.length || 0}, sample_rate=${data.sample_rate}, is_final=${data.is_final}, text_hash=${data.text_hash || ''}, text_preview=${(data.text_preview || '').slice(0, 60)}`
    );
    if (callbacks?.onAudioChunk) {
      callbacks.onAudioChunk(data.chunk, data.sample_rate, data.is_final);
    }
  });

  // Handle status updates
  eventSource.addEventListener('status_update', (event) => {
    const data = JSON.parse(event.data);
    console.log('[SSE] Received status update:', data.status);
    if (callbacks?.onStatusUpdate) {
      callbacks.onStatusUpdate(data.status);
    }
  });

  // Fallback for non-typed messages (backward compatibility)
  eventSource.onmessage = (event) => {
    console.log('[SSE] Received message (fallback):', event.data.substring(0, 100) + '...');
    const data = JSON.parse(event.data);
    onUpdate(data);
  };

  eventSource.onerror = (error) => {
    console.error('[SSE] Connection error:', error);
    // Keep EventSource open to allow automatic reconnection.
  };

  eventSource.onopen = () => {
    console.log('[SSE] Connection established');
  };

  return () => {
    console.log('[SSE] Closing connection');
    eventSource.close();
  };
};

export default apiClient;
