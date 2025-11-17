import React, { useState, useEffect } from 'react';
import RadarChart from './RadarChart';
import DualRadarChart from './DualRadarChart';
import TranscriptionDisplay from './TranscriptionDisplay';
import MemoryViewer from './MemoryViewer';
import { fetchDashboardData, subscribeToUpdates } from '../api/client';
import type { DashboardData } from '../types';

const DEFAULT_USER_ID = 'test1';

const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      const dashboardData = await fetchDashboardData(DEFAULT_USER_ID);
      setData(dashboardData);
      setError(null);
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error('Error loading dashboard:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();

    const unsubscribe = subscribeToUpdates(DEFAULT_USER_ID, (updatedData) => {
      setData(updatedData);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-white mx-auto mb-4"></div>
          <p className="text-white text-xl">Loading Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glassmorphism card max-w-md p-8 text-center">
          <h2 className="text-2xl font-bold text-white mb-4">Error</h2>
          <p className="text-white text-opacity-90">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 px-6 py-2 bg-white text-purple-600 rounded-lg font-medium hover:bg-opacity-90 transition-all"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Voice Chatbot Dashboard</h1>
          <p className="text-white text-opacity-80">Real-time Emotion & Personality Analysis</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
          {/* Left: Memory Viewer */}
          <div className="lg:col-span-1 glassmorphism rounded-xl p-6 overflow-hidden flex flex-col">
            <MemoryViewer
              userId={DEFAULT_USER_ID}
              profiles={data?.profiles || []}
              events={data?.events || []}
              isLoading={false}
              onRefresh={loadDashboardData}
            />
          </div>

          {/* Right: Conversation and Charts */}
          <div className="lg:col-span-2 flex flex-col gap-6 overflow-y-auto">
            {/* Conversation Display (Top) - Always visible */}
            <TranscriptionDisplay
              text={data?.currentTranscription?.text || ''}
              response={data?.currentTranscription?.response || ''}
              timestamp={data?.currentTranscription?.timestamp || ''}
            />

            {/* Radar Charts (Bottom) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <DualRadarChart
                title="Emotion"
                data1={data?.speechEmotion || {}}
                data2={data?.textEmotion || {}}
                label1="Speech"
                label2="Text"
                color1="#3b82f6"
                color2="#ef4444"
              />

              <RadarChart
                title="Big5 Personality"
                data={data?.big5 || {}}
                color="#10b981"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
