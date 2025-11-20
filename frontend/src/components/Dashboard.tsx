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
  const [activeChart, setActiveChart] = useState<'emotion' | 'personality'>('emotion');

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
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-purple-500 mx-auto mb-4" style={{ borderTopColor: '#8B7EC8' }}></div>
          <p className="text-lg font-medium" style={{ color: 'var(--color-text-primary)' }}>Loading MemoBot Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glassmorphism card max-w-md p-8 text-center">
          <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text-primary)' }}>Error</h2>
          <p style={{ color: 'var(--color-text-secondary)' }}>{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 px-6 py-2.5 text-white rounded-xl font-medium transition-all shadow-md hover:shadow-lg"
            style={{ background: 'var(--gradient-primary)' }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <div className="flex-shrink-0 px-6 pt-6 pb-4">
        <div className="max-w-7xl mx-auto">
          <header>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-2xl flex items-center justify-center" style={{ background: 'var(--gradient-primary)' }}>
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h1 className="text-3xl font-bold tracking-tight" style={{
                background: 'var(--gradient-primary)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}>
                MemoBot
              </h1>
            </div>
            <p className="text-base" style={{ color: 'var(--color-text-secondary)' }}>
              AI-Powered Emotion & Personality Analysis Dashboard
            </p>
          </header>
        </div>
      </div>

      <div className="flex-1 px-6 pb-6 overflow-hidden">
        <div className="max-w-7xl mx-auto h-full">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full">
            {/* Left: Memory Viewer (narrower) */}
            <div className="lg:col-span-3 glassmorphism rounded-xl p-6 overflow-hidden flex flex-col">
              <MemoryViewer
                userId={DEFAULT_USER_ID}
                profiles={data?.profiles || []}
                events={data?.events || []}
                isLoading={false}
                onRefresh={loadDashboardData}
              />
            </div>

            {/* Middle: Conversation */}
            <div className="lg:col-span-4 flex flex-col h-full overflow-hidden">
              <TranscriptionDisplay
                text={data?.currentTranscription?.text || ''}
                response={data?.currentTranscription?.response || ''}
                timestamp={data?.currentTranscription?.timestamp || ''}
              />
            </div>

            {/* Right: Radar Charts with Tab Switcher */}
            <div className="lg:col-span-5 flex flex-col h-full overflow-hidden gap-4">
              {/* Tab Switcher */}
              <div className="flex gap-2 flex-shrink-0">
                <button
                  onClick={() => setActiveChart('emotion')}
                  className={`flex-1 px-4 py-3 rounded-xl font-medium transition-all ${activeChart === 'emotion' ? 'text-white shadow-md' : 'hover:shadow-sm'}`}
                  style={activeChart === 'emotion'
                    ? { background: 'var(--gradient-primary)' }
                    : { background: 'rgba(139, 126, 200, 0.1)', color: 'var(--color-text-secondary)' }
                  }
                >
                  <div className="flex items-center justify-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Emotion Analysis
                  </div>
                </button>
                <button
                  onClick={() => setActiveChart('personality')}
                  className={`flex-1 px-4 py-3 rounded-xl font-medium transition-all ${activeChart === 'personality' ? 'text-white shadow-md' : 'hover:shadow-sm'}`}
                  style={activeChart === 'personality'
                    ? { background: 'var(--gradient-accent)' }
                    : { background: 'rgba(240, 147, 251, 0.1)', color: 'var(--color-text-secondary)' }
                  }
                >
                  <div className="flex items-center justify-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    Big5 Personality
                  </div>
                </button>
              </div>

              {/* Chart Display Area */}
              <div className="flex-1 min-h-0">
                {activeChart === 'emotion' ? (
                  <DualRadarChart
                    title="Emotion Analysis"
                    data1={(data?.speechEmotion || {}) as Record<string, number>}
                    data2={(data?.textEmotion || {}) as Record<string, number>}
                    label1="Speech"
                    label2="Text"
                    color1="#667EEA"
                    color2="#4ECDC4"
                  />
                ) : (
                  <RadarChart
                    title="Big5 Personality"
                    data={(data?.big5 || {}) as Record<string, number>}
                    color="#F093FB"
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
