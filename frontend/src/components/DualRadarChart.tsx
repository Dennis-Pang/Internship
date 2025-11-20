import React from 'react';
import { Radar, RadarChart as RechartsRadar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface DualRadarChartProps {
  title: string;
  data1: Record<string, number>;
  data2: Record<string, number>;
  label1: string;
  label2: string;
  color1?: string;
  color2?: string;
}

const DualRadarChart: React.FC<DualRadarChartProps> = ({
  title,
  data1,
  data2,
  label1,
  label2,
  color1 = '#667EEA', // Purple-blue for speech
  color2 = '#4ECDC4', // Mint green for text
}) => {
  // Default emotion values
  const getDefaultEmotion = () => {
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
  };

  // Use provided data or default values
  const displayData1 = (data1 && Object.keys(data1).length > 0) ? data1 : getDefaultEmotion();
  const displayData2 = (data2 && Object.keys(data2).length > 0) ? data2 : getDefaultEmotion();

  // Merge both datasets
  const chartData = Object.keys(displayData1).map((key) => ({
    subject: key.charAt(0).toUpperCase() + key.slice(1),
    [label1]: displayData1[key],
    [label2]: displayData2[key],
    fullMark: 1,
  }));

  // Custom tooltip component for dual data
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white rounded-xl p-3 shadow-2xl border" style={{ borderColor: 'rgba(139, 126, 200, 0.2)' }}>
          <p className="font-semibold text-sm mb-2" style={{ color: 'var(--color-text-primary)' }}>
            {payload[0].payload.subject}
          </p>
          <div className="space-y-1">
            {payload.map((entry: any, index: number) => (
              <div key={index} className="flex items-center justify-between gap-3">
                <span className="text-xs" style={{ color: entry.color }}>
                  {entry.name}:
                </span>
                <span className="font-bold text-sm" style={{ color: entry.color }}>
                  {(entry.value * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
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
              <linearGradient id={`gradient-${label1}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color1} stopOpacity={0.5} />
                <stop offset="100%" stopColor={color1} stopOpacity={0.15} />
              </linearGradient>
              <linearGradient id={`gradient-${label2}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color2} stopOpacity={0.5} />
                <stop offset="100%" stopColor={color2} stopOpacity={0.15} />
              </linearGradient>
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
              name={label1}
              dataKey={label1}
              stroke={color1}
              strokeWidth={2.5}
              fill={`url(#gradient-${label1})`}
              fillOpacity={0.8}
              dot={{ fill: color1, r: 2, strokeWidth: 2, stroke: '#fff' }}
              activeDot={{ r: 3, strokeWidth: 2 }}
            />
            <Radar
              name={label2}
              dataKey={label2}
              stroke={color2}
              strokeWidth={2.5}
              fill={`url(#gradient-${label2})`}
              fillOpacity={0.8}
              dot={{ fill: color2, r: 2, strokeWidth: 2, stroke: '#fff' }}
              activeDot={{ r: 3, strokeWidth: 2 }}
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

export default DualRadarChart;
