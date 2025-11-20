import React, { useState } from 'react';
import type { UserProfile, UserEvent } from '../types';
import { deleteProfile, deleteEvent } from '../api/client';

interface MemoryViewerProps {
  userId: string;
  profiles: UserProfile[];
  events: UserEvent[];
  isLoading?: boolean;
  onRefresh?: () => void;
}

const MemoryViewer: React.FC<MemoryViewerProps> = ({ userId, profiles, events, isLoading = false, onRefresh }) => {
  const [activeTab, setActiveTab] = useState<'profiles' | 'events'>('profiles');
  const [expandedTopics, setExpandedTopics] = useState<Set<string>>(new Set());
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const groupedProfiles = profiles.reduce((acc, profile) => {
    if (!acc[profile.topic]) {
      acc[profile.topic] = [];
    }
    acc[profile.topic].push(profile);
    return acc;
  }, {} as Record<string, UserProfile[]>);

  const toggleTopic = (topic: string) => {
    setExpandedTopics(prev => {
      const newSet = new Set(prev);
      if (newSet.has(topic)) {
        newSet.delete(topic);
      } else {
        newSet.add(topic);
      }
      return newSet;
    });
  };

  const handleDeleteProfile = async (profileId: string) => {
    try {
      setDeletingId(profileId);
      await deleteProfile(userId, profileId);
      setConfirmDeleteId(null);
      if (onRefresh) {
        onRefresh();
      }
    } catch (error) {
      console.error('Failed to delete profile:', error);
      alert('Failed to delete profile. Please try again.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteEvent = async (eventId: string) => {
    try {
      setDeletingId(eventId);
      await deleteEvent(userId, eventId);
      setConfirmDeleteId(null);
      if (onRefresh) {
        onRefresh();
      }
    } catch (error) {
      console.error('Failed to delete event:', error);
      alert('Failed to delete event. Please try again.');
    } finally {
      setDeletingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2" style={{ borderTopColor: '#8B7EC8' }}></div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <h2 className="text-2xl font-bold mb-4" style={{ color: 'var(--color-text-primary)' }}>
        User Memory
      </h2>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('profiles')}
          className={`px-4 py-2 rounded-xl font-medium transition-all ${activeTab === 'profiles' ? 'text-white shadow-md' : 'hover:shadow-sm'}`}
          style={activeTab === 'profiles'
            ? { background: 'var(--gradient-primary)' }
            : { background: 'rgba(139, 126, 200, 0.1)', color: 'var(--color-text-secondary)' }
          }
        >
          Profiles ({profiles.length})
        </button>
        <button
          onClick={() => setActiveTab('events')}
          className={`px-4 py-2 rounded-xl font-medium transition-all ${activeTab === 'events' ? 'text-white shadow-md' : 'hover:shadow-sm'}`}
          style={activeTab === 'events'
            ? { background: 'var(--gradient-secondary)' }
            : { background: 'rgba(78, 205, 196, 0.1)', color: 'var(--color-text-secondary)' }
          }
        >
          Events ({events.length})
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === 'profiles' ? (
          <div className="space-y-3">
            {profiles.length === 0 ? (
              <div className="text-center py-8" style={{ color: 'var(--color-text-tertiary)' }}>
                No profiles found
              </div>
            ) : (
              Object.entries(groupedProfiles).map(([topic, topicProfiles]) => (
                <div key={topic} className="bg-white rounded-2xl overflow-hidden border shadow-sm" style={{ borderColor: 'rgba(139, 126, 200, 0.15)' }}>
                  <button
                    onClick={() => toggleTopic(topic)}
                    className="w-full px-4 py-3 flex items-center justify-between font-semibold transition-all hover:bg-opacity-50"
                    style={{
                      color: 'var(--color-text-primary)',
                      background: expandedTopics.has(topic) ? 'rgba(139, 126, 200, 0.05)' : 'transparent'
                    }}
                  >
                    <span>{topic}</span>
                    <span className="text-sm" style={{ color: 'var(--color-text-tertiary)' }}>
                      {expandedTopics.has(topic) ? '▼' : '▶'}
                    </span>
                  </button>

                  {expandedTopics.has(topic) && (
                    <div className="px-4 pb-3 space-y-2" style={{ background: 'rgba(139, 126, 200, 0.02)' }}>
                      {topicProfiles.map((profile) => (
                        <div
                          key={profile.id}
                          className="bg-white rounded-xl p-3 hover:shadow-md transition-all group relative border accent-border-primary"
                          style={{ borderColor: 'rgba(46, 94, 170, 0.1)' }}
                        >
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setConfirmDeleteId(profile.id);
                            }}
                            disabled={deletingId === profile.id}
                            className="absolute top-2 right-2 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                            style={{ background: 'rgba(232, 93, 117, 0.1)' }}
                            title="Delete profile"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" style={{ color: 'var(--color-error)' }} viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                          </button>
                          <div className="text-sm font-medium mb-1" style={{ color: 'var(--color-primary)' }}>
                            {profile.sub_topic}
                          </div>
                          <div className="text-sm leading-relaxed" style={{ color: 'var(--color-text-primary)' }}>
                            {profile.content}
                          </div>
                          <div className="text-xs mt-2" style={{ color: 'var(--color-text-tertiary)' }}>
                            {new Date(profile.created_at).toLocaleString()}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {events.length === 0 ? (
              <div className="text-center py-8" style={{ color: 'var(--color-text-tertiary)' }}>
                No events found
              </div>
            ) : (
              events.map((event) => (
                <div key={event.id} className="bg-white rounded-2xl p-4 group relative border shadow-sm hover:shadow-md transition-all accent-border-secondary" style={{ borderColor: 'rgba(139, 126, 200, 0.15)' }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmDeleteId(event.id);
                    }}
                    disabled={deletingId === event.id}
                    className="absolute top-3 right-3 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                    style={{ background: 'rgba(232, 93, 117, 0.1)' }}
                    title="Delete event"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" style={{ color: 'var(--color-error)' }} viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </button>
                  <div className="text-sm font-semibold mb-2" style={{ color: 'var(--color-accent)' }}>
                    {new Date(event.created_at).toLocaleString()}
                  </div>
                  {event.event_data?.event_tip && (
                    <div className="text-sm leading-relaxed mb-2" style={{ color: 'var(--color-text-primary)' }}>
                      {event.event_data.event_tip}
                    </div>
                  )}
                  {event.event_data?.event_tags && event.event_data.event_tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {event.event_data.event_tags.map((tag, idx) => (
                        <span
                          key={idx}
                          className="text-xs px-2.5 py-1 rounded-full border medical-badge"
                        >
                          {tag.tag}: {tag.value}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Confirmation Dialog */}
      {confirmDeleteId && (
        <div className="fixed inset-0 flex items-center justify-center z-50 backdrop-blur-sm" style={{ background: 'rgba(26, 54, 93, 0.4)' }} onClick={() => setConfirmDeleteId(null)}>
          <div className="bg-white rounded-3xl p-6 max-w-md mx-4 shadow-2xl border" style={{ borderColor: 'rgba(139, 126, 200, 0.2)' }} onClick={(e) => e.stopPropagation()}>
            <h3 className="text-xl font-bold mb-3" style={{ color: 'var(--color-text-primary)' }}>
              Confirm Delete
            </h3>
            <p className="mb-6" style={{ color: 'var(--color-text-secondary)' }}>
              Are you sure you want to delete this {activeTab === 'profiles' ? 'profile' : 'event'}? This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmDeleteId(null)}
                className="px-4 py-2 rounded-xl transition-all"
                style={{
                  background: 'rgba(139, 126, 200, 0.1)',
                  color: 'var(--color-text-secondary)'
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (activeTab === 'profiles') {
                    handleDeleteProfile(confirmDeleteId);
                  } else {
                    handleDeleteEvent(confirmDeleteId);
                  }
                }}
                disabled={deletingId === confirmDeleteId}
                className="px-4 py-2 rounded-xl text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: 'var(--color-error)' }}
              >
                {deletingId === confirmDeleteId ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MemoryViewer;
