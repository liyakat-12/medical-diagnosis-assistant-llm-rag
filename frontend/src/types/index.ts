export type TriageLevel = "self_care" | "consult_doctor" | "emergency";

export interface User {
  id: string;
  name: string;
  email: string;
  created_at?: string | null;
  updated_at?: string | null;
  last_login?: string | null;
  is_active: boolean;
  medical_disclaimer_accepted: boolean;
}

export interface Chat {
  id: string;
  user_id: string;
  title: string;
  created_at?: string | null;
  updated_at?: string | null;
  last_message_at?: string | null;
  message_count: number;
  archived: boolean;
}

export interface Citation {
  title?: string;
  source?: string;
  url?: string;
  condition?: string;
  relevance_score?: number;
}

export interface Triage {
  level: TriageLevel;
  label: string;
  guidance: string;
  reason?: string;
}

export interface PossibleCondition {
  condition: string;
  title?: string;
  source?: string;
  url?: string;
  relevance_score?: number;
  match_percent?: number;
}

export interface Faithfulness {
  supported?: string[];
  uncited?: string[];
  not_retrieved?: string[];
  [key: string]: unknown;
}

export interface ChatMessage {
  id: string;
  chat_id: string;
  user_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string | null;
  updated_at?: string | null;
  model?: string | null;
  citations: Citation[];
  triage?: Triage | null;
  possible_conditions: PossibleCondition[];
  faithfulness?: Faithfulness | null;
  recommendations: string[];
  refused: boolean;
  disclaimer?: string | null;
  metadata?: Record<string, unknown>;
  streaming?: boolean;
}

export interface StreamEvent {
  type: "status" | "token" | "citation" | "triage" | "metadata" | "done";
  content?: string;
  citations?: Citation[];
  possible_conditions?: PossibleCondition[];
  level?: TriageLevel;
  label?: string;
  guidance?: string;
  recommendations?: string[];
  faithfulness?: Faithfulness | null;
  result?: Record<string, unknown>;
  message?: ChatMessage;
}

export interface ApiError {
  message: string;
  status: number;
}
