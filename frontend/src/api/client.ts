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
export const fetchDefaultUser = async (): Promise<string> => {
  try {
    const response = await apiClient.get<{ defaultUser: string }>('/config');
    return response.data.defaultUser;
  } catch (error) {
    console.error('Failed to fetch default user from backend, falling back to "test1":', error);
    return 'test1'; // Fallback
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
}

export const subscribeToUpdates = (
  userId: string,
  onUpdate: (data: DashboardData) => void,
  callbacks?: StreamingCallbacks
) => {
  const sseUrl = API_BASE_URL.startsWith('http')
    ? `${API_BASE_URL}/stream/${userId}`
    : `http://localhost:5000/api/stream/${userId}`;

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

  // Fallback for non-typed messages (backward compatibility)
  eventSource.onmessage = (event) => {
    console.log('[SSE] Received message (fallback):', event.data.substring(0, 100) + '...');
    const data = JSON.parse(event.data);
    onUpdate(data);
  };

  eventSource.onerror = (error) => {
    console.error('[SSE] Connection error:', error);
    eventSource.close();
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
