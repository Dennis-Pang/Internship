import React from 'react';

interface TranscriptionDisplayProps {
  text: string;
  response: string;
  timestamp: string;
}

const TranscriptionDisplay: React.FC<TranscriptionDisplayProps> = ({ text, response, timestamp }) => {
  const displayText = text || 'Waiting for user input...';
  const displayResponse = response || 'No response yet...';
  const displayTime = timestamp ? new Date(timestamp).toLocaleTimeString() : '--:--:--';

  return (
    <div className="glassmorphism card flex flex-col h-full">
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h3 className="text-xl font-semibold tracking-tight" style={{ color: 'var(--color-text-primary)' }}>
          Conversation
        </h3>
        <span className="text-sm font-medium" style={{ color: 'var(--color-text-tertiary)' }}>
          {displayTime}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        {/* User Input */}
        <div>
          <div className="text-sm font-medium mb-2 flex items-center gap-2" style={{ color: 'var(--color-primary)' }}>
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
            </svg>
            Patient
          </div>
          <div className="rounded-2xl p-4 border accent-border-primary" style={{
            background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(78, 205, 196, 0.08) 100%)',
            borderColor: 'rgba(46, 94, 170, 0.15)'
          }}>
            <p className="text-base leading-relaxed" style={{ color: 'var(--color-text-primary)' }}>
              {displayText}
            </p>
          </div>
        </div>

        {/* Bot Response */}
        <div>
          <div className="text-sm font-medium mb-2 flex items-center gap-2" style={{ color: 'var(--color-secondary)' }}>
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
              <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
            </svg>
            MemoBot Response
          </div>
          <div className="rounded-2xl p-4 border accent-border-secondary" style={{
            background: 'linear-gradient(135deg, rgba(139, 126, 200, 0.08) 0%, rgba(240, 147, 251, 0.08) 100%)',
            borderColor: 'rgba(139, 126, 200, 0.15)'
          }}>
            <p className="text-base leading-relaxed" style={{ color: 'var(--color-text-primary)' }}>
              {displayResponse}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TranscriptionDisplay;
