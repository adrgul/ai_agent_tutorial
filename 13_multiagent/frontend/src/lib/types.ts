export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface TraceEvent {
  type: 'node_start' | 'node_end' | 'tool_call' | 'tool_result' | 'send_fanout' | 'handoff' | 'cache_hit' | 'cache_miss';
  timestamp: string;
  node_name?: string;
  tool_name?: string;
  from_agent?: string;
  to_agent?: string;
  reason?: string;
  data?: Record<string, any>;
}

export interface TicketTriage {
  category: string;
  priority: string;
  sentiment?: string;
  routing_team: string;
  assignee_group?: string;
  tags: string[];
  confidence: number;
}

export interface AgentAssist {
  draft_reply: string;
  case_summary: string[];
  next_actions: string[];
}

export interface StateSnapshot {
  selected_pattern: string;
  active_agent?: string;
  recursion_depth: number;
  sources_count: number;
  messages_count: number;
}

export interface FinalResult {
  text: string;
  pattern: string;
  ticket?: TicketTriage;
  agent_assist?: AgentAssist;
  sources?: string[];
  active_agent?: string;
  stats?: {
    latency_ms: number;
    cache_stats: Record<string, any>;
    recursion_depth: number;
    trace_events: number;
  };
  state_snapshot?: StateSnapshot;
}

export interface Pattern {
  id: string;
  name: string;
  description: string;
  concepts: string[];
}
