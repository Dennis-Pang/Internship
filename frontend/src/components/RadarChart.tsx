import React from 'react';
import { Radar, RadarChart as RechartsRadar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from 'recharts';

interface RadarChartProps {
  title: string;
  data: Record<string, number>;
  color?: string;
}

const RadarChart: React.FC<RadarChartProps> = ({ title, data, color = '#8b5cf6' }) => {
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

  return (
    <div className="glassmorphism card">
      <h3 className="text-xl font-bold text-white mb-4 text-center">{title}</h3>
      <ResponsiveContainer width="100%" height={400}>
        <RechartsRadar data={chartData} margin={{ top: 20, right: 60, bottom: 40, left: 60 }}>
          <PolarGrid stroke="rgba(255, 255, 255, 0.3)" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: 'white', fontSize: 13 }}
            tickLine={false}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 1]}
            tick={{ fill: 'white', fontSize: 10 }}
          />
          <Radar
            name={title}
            dataKey="value"
            stroke={color}
            fill={color}
            fillOpacity={0.6}
          />
          <Legend wrapperStyle={{ color: 'white' }} />
        </RechartsRadar>
      </ResponsiveContainer>
    </div>
  );
};

export default RadarChart;
