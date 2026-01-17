/**
 * Type definitions for the AI Agent application.
 */

export interface Message {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface ChatRequest {
  user_id: string;
  message: string;
  session_id?: string;
}

export interface ToolUsed {
  name: string;
  arguments: Record<string, any>;
  success: boolean;
}

export interface MemorySnapshot {
  preferences: {
    language: string;
    default_city: string;
    [key: string]: any;
  };
  workflow_state: {
    flow: string | null;
    step: number;
    total_steps: number;
    data: Record<string, any>;
  };
  message_count: number;
}

/**
 * RAG-related types
 */
export interface RAGChunk {
  chunk_id: string;
  text: string;
  source_label: string;
  score: number;
}

export interface RAGContext {
  rewritten_query: string | null;
  citations: string[];
  chunk_count: number;
  used_in_response: boolean;
  chunks: RAGChunk[];
}

export interface RAGMetrics {
  query_rewrite_latency_ms: number;
  retrieval_latency_ms: number;
  total_pipeline_latency_ms: number;
  chunk_count: number;
  max_similarity_score: number;
}

export interface ChatResponse {
  final_answer: string;
  tools_used: ToolUsed[];
  memory_snapshot: MemorySnapshot;
  logs?: string[];
  rag_context?: RAGContext;
  rag_metrics?: RAGMetrics;
  debug_logs?: string[];  // MCP debug steps
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  toolsUsed?: ToolUsed[];
}

/**
 * RAG API response types
 */
export interface DocumentUploadResponse {
  success: boolean;
  document_id: string;
  filename: string;
  chunk_count: number;
  size_chars: number;
}

export interface RAGStats {
  user_id: string;
  document_count: number;
  chunk_count: number;
  collection_name: string;
  persist_directory: string;
}

export interface DocumentInfo {
  doc_id: string;
  filename: string;
  chunk_count: number;
  ingested_at: string;
  size_chars: number;
}

export interface DocumentListResponse {
  user_id: string;
  documents: DocumentInfo[];
  count: number;
}

export interface DocumentDeleteResponse {
  success: boolean;
  doc_id: string;
  deleted_chunks: number;
}
