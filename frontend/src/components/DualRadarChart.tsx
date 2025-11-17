import React from 'react';
import { Radar, RadarChart as RechartsRadar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from 'recharts';

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
  color1 = '#3b82f6', // Blue for speech
  color2 = '#ef4444', // Red for text
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
            name={label1}
            dataKey={label1}
            stroke={color1}
            fill={color1}
            fillOpacity={0.5}
          />
          <Radar
            name={label2}
            dataKey={label2}
            stroke={color2}
            fill={color2}
            fillOpacity={0.5}
          />
          <Legend wrapperStyle={{ color: 'white' }} />
        </RechartsRadar>
      </ResponsiveContainer>
    </div>
  );
};

export default DualRadarChart;
