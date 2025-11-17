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
    <div className="glassmorphism card h-64 flex flex-col">
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <h3 className="text-xl font-semibold text-white">Conversation</h3>
        <span className="text-sm text-gray-300">{displayTime}</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        {/* User Input */}
        <div>
          <div className="text-sm font-medium text-blue-300 mb-2">User</div>
          <div className="bg-blue-500 bg-opacity-20 rounded-lg p-4 border border-blue-400 border-opacity-30">
            <p className="text-white text-base leading-relaxed">{displayText}</p>
          </div>
        </div>

        {/* Bot Response */}
        <div>
          <div className="text-sm font-medium text-green-300 mb-2">Assistant</div>
          <div className="bg-green-500 bg-opacity-20 rounded-lg p-4 border border-green-400 border-opacity-30">
            <p className="text-white text-base leading-relaxed">{displayResponse}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TranscriptionDisplay;
