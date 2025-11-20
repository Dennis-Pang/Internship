import React from 'react';
import { Radar, RadarChart as RechartsRadar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface RadarChartProps {
  title: string;
  data: Record<string, number>;
  color?: string;
}

const RadarChart: React.FC<RadarChartProps> = ({ title, data, color = '#14b8a6' }) => {
  // Define default values based on chart type
  const getDefaultData = () => {
    if (title.includes('Big5') || title.includes('Personality')) {
      // Big5 personality: neutral values at 0.5
      return {
        'Extroversion': 0.5,
        'Neuroticism': 0.5,
        'Agreeableness': 0.5,
        'Conscientiousness': 0.5,
        'Openness': 0.5,
      };
    } else {
      // Emotion: uniform distribution (7 emotions)
      const uniformValue = 1.0 / 7;
      return {
        'anger': uniformValue,
        'disgust': uniformValue,
        'fear': uniformValue,
        'happy': uniformValue,
        'neutral': uniformValue,
        'sad': uniformValue,
        'surprise': uniformValue,
      };
    }
  };

  // Use provided data or default values
  const displayData = (data && Object.keys(data).length > 0) ? data : getDefaultData();

  const chartData = Object.entries(displayData).map(([key, value]) => ({
    subject: key.charAt(0).toUpperCase() + key.slice(1),
    value: value,
    fullMark: 1,
  }));

  // Custom tooltip component
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      return (
        <div className="bg-white rounded-xl p-3 shadow-2xl border" style={{ borderColor: 'rgba(139, 126, 200, 0.2)' }}>
          <p className="font-semibold text-sm mb-1" style={{ color: 'var(--color-text-primary)' }}>
            {data.payload.subject}
          </p>
          <p className="text-sm" style={{ color: 'var(--color-primary)' }}>
            <span className="font-bold">{(data.value * 100).toFixed(1)}%</span>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="glassmorphism card chart-3d h-full flex flex-col">
      <div className="chart-3d-inner flex-1 flex flex-col">
        <h3 className="text-xl font-bold mb-4 text-center tracking-tight flex-shrink-0" style={{ color: 'var(--color-text-primary)' }}>
          {title}
        </h3>
        <div className="flex-1 min-h-0">
          <ResponsiveContainer width="100%" height="100%">
          <RechartsRadar data={chartData} margin={{ top: 20, right: 60, bottom: 40, left: 60 }}>
            <defs>
              <linearGradient id={`gradient-${title}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.5} />
                <stop offset="100%" stopColor={color} stopOpacity={0.15} />
              </linearGradient>
              <filter id={`glow-${title}`}>
                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            <PolarGrid
              stroke="rgba(139, 126, 200, 0.15)"
              strokeWidth={1}
            />
            <PolarAngleAxis
              dataKey="subject"
              tick={{ fill: 'var(--color-text-primary)', fontSize: 13, fontWeight: 500 }}
              tickLine={false}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 1]}
              tick={{ fill: 'var(--color-text-tertiary)', fontSize: 10 }}
              tickCount={6}
            />
            <Radar
              name={title}
              dataKey="value"
              stroke={color}
              strokeWidth={2.5}
              fill={`url(#gradient-${title})`}
              fillOpacity={0.85}
              dot={{ fill: color, r: 2, strokeWidth: 2, stroke: '#fff' }}
              activeDot={{ r: 3, strokeWidth: 2, fill: color }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{
                color: 'var(--color-text-primary)',
                paddingTop: '20px',
                fontWeight: 500
              }}
            />
          </RechartsRadar>
        </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default RadarChart;
