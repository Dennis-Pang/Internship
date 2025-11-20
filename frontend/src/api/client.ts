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

export const subscribeToUpdates = (userId: string, onUpdate: (data: DashboardData) => void) => {
  const eventSource = new EventSource(`${API_BASE_URL}/stream/${userId}`);

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onUpdate(data);
  };

  eventSource.onerror = () => {
    console.error('SSE connection error');
    eventSource.close();
  };

  return () => {
    eventSource.close();
  };
};

export default apiClient;
