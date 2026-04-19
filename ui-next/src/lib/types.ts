export type MethodId =
  | 'multi-perspective'
  | 'iterative'
  | 'debate'
  | 'scientific'
  | 'socratic'
  | 'research'
  | 'jury'
  | 'pre-mortem'
  | 'bayesian'
  | 'dialectical'
  | 'analogical'
  | 'delphi';

export interface TokenCount {
  input: number;
  output: number;
  total: number;
}

export interface PhaseEvent {
  type: 'start' | 'prompt_enhanced' | 'phase_start' | 'phase_complete' | 'phase_error' | 'error' | 'cancelled' | 'done' | 'agent_start' | 'agent_complete' | 'text_chunk';
  phase?: number;
  name?: string;
  data?: Record<string, unknown>;
  cached?: boolean;
  errors?: string[];
  total_tokens?: TokenCount;
  duration?: number;
  message?: string;
  original?: string;
  enhanced?: string;
  /** Populated on `type === 'start'` when the backend auto-selected a method. */
  auto_selected_method?: string;
  /** Agent activity tracking */
  agent?: string;
  role?: string;
  task?: string;
  model?: string;
  models?: string[];
  error?: string | null;
  /** Streaming text chunk */
  text?: string;
}

export interface ConversationTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface Conversation {
  id: string;
  conversation_id: string;
  turn_number: number;
  timestamp: string;
  problem: string;
  phases: Array<{ phase: number; name: string; data: unknown }>;
  errors: string[];
  preset: string;
  method: string;
  total_tokens: TokenCount | null;
  duration?: number;
}

export interface RunRequest {
  problem: string;
  preset: string;
  top_k: number;
  sequential: boolean;
  enhance_prompt: boolean;
}

export interface RunFollowupRequest {
  question: string;
  preset: string;
  top_k: number;
  sequential: boolean;
  enhance_prompt: boolean;
  conversation_id: string;
  history: ConversationTurn[];
  previous_synthesis: string;
  agent_model?: string | null;
}

export interface PresetMeta {
  available: boolean;
  missing_keys?: string[];
}

export interface PresetsResponse {
  presets: Record<string, PresetMeta>;
  models: Record<string, unknown>;
}

export interface MethodPreset {
  id: string;
  label: string;
}

export interface MethodPhase {
  id: number;
  name: string;
  short: string;
}

export interface MethodDef {
  id: MethodId;
  name: string;
  icon: string;
  cost: number;
  description: string;
}
