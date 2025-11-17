export interface EmotionData {
  anger: number;
  disgust: number;
  fear: number;
  happy: number;
  neutral: number;
  sad: number;
  surprise: number;
}

export interface Big5Data {
  Extroversion: number;
  Neuroticism: number;
  Agreeableness: number;
  Conscientiousness: number;
  Openness: number;
}

export interface UserProfile {
  id: string;
  topic: string;
  sub_topic: string;
  content: string;
  created_at: string;
  updated_at?: string;
}

export interface UserEvent {
  id: string;
  created_at: string;
  event_data?: {
    event_tip?: string;
    event_tags?: { tag: string; value: string }[];
    profile_delta?: Array<{
      content: string;
      attributes?: {
        topic: string;
        sub_topic: string;
      };
    }>;
  };
}

export interface TranscriptionData {
  text: string;
  response: string;
  timestamp: string;
  speechEmotion: EmotionData;
  textEmotion: EmotionData;
  big5: Big5Data;
}

export interface DashboardData {
  userId: string;
  userName?: string;
  currentTranscription: TranscriptionData | null;
  speechEmotion: EmotionData | null;
  textEmotion: EmotionData | null;
  big5: Big5Data | null;
  profiles: UserProfile[];
  events: UserEvent[];
}
