/**
 * DebugPanel component - Shows tools used, memory snapshot, and RAG context.
 */
import React from 'react';
import { MemorySnapshot, ToolUsed, RAGContext, RAGMetrics } from '../types';

interface DebugPanelProps {
  toolsUsed: ToolUsed[];
  memorySnapshot: MemorySnapshot | null;
  ragContext?: RAGContext | null;
  ragMetrics?: RAGMetrics | null;
  debugLogs?: string[];  // MCP debug steps
  isOpen: boolean;
  onToggle: () => void;
}

export const DebugPanel: React.FC<DebugPanelProps> = ({
  toolsUsed,
  memorySnapshot,
  ragContext,
  ragMetrics,
  debugLogs,
  isOpen,
  onToggle,
}) => {
  return (
    <>
      <button className="debug-toggle" onClick={onToggle}>
        {isOpen ? '✕ Close Debug' : '🔧 Debug Panel'}
      </button>
      
      {isOpen && (
        <div className="debug-panel">
          <h3>Debug Information</h3>
          
          {/* MCP Steps Section - Show at top for visibility */}
          {debugLogs && debugLogs.length > 0 && (
            <div className="debug-section">
              <h4>🔌 MCP Steps</h4>
              <div className="mcp-steps">
                {debugLogs.map((log, idx) => (
                  <div key={idx} className="mcp-step">
                    {log}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          <div className="debug-section">
            <h4>Last Tools Used ({toolsUsed.length})</h4>
            {toolsUsed.length === 0 ? (
              <div className="debug-empty">No tools used</div>
            ) : (
              <div className="tools-list">
                {toolsUsed.map((tool, idx) => (
                  <div key={idx} className="debug-tool">
                    <div className="debug-tool-name">
                      <span className={`status-icon ${tool.success ? 'success' : 'error'}`}>
                        {tool.success ? '✓' : '✗'}
                      </span>
                      {tool.name}
                    </div>
                    <pre className="debug-args">
                      {JSON.stringify(tool.arguments, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          <div className="debug-section">
            <h4>Memory Snapshot</h4>
            {memorySnapshot ? (
              <div>
                <div className="debug-subsection">
                  <strong>Preferences:</strong>
                  <pre>{JSON.stringify(memorySnapshot.preferences, null, 2)}</pre>
                </div>

                <div className="debug-subsection">
                  <strong>Workflow State:</strong>
                  <pre>{JSON.stringify(memorySnapshot.workflow_state, null, 2)}</pre>
                </div>

                <div className="debug-subsection">
                  <strong>Message Count:</strong> {memorySnapshot.message_count}
                </div>
              </div>
            ) : (
              <div className="debug-empty">No memory snapshot available</div>
            )}
          </div>

          {/* RAG Context Section */}
          {ragContext && (
            <div className="debug-section">
              <h4>🔍 RAG Context</h4>
              <div>
                {ragContext.rewritten_query && (
                  <div className="debug-subsection">
                    <strong>Rewritten Query:</strong>
                    <div className="debug-value">{ragContext.rewritten_query}</div>
                  </div>
                )}

                <div className="debug-subsection">
                  <strong>Citations:</strong>
                  {ragContext.citations.length > 0 ? (
                    <div className="citations-list">
                      {ragContext.citations.map((citation, idx) => (
                        <span key={idx} className="citation-badge">{citation}</span>
                      ))}
                    </div>
                  ) : (
                    <div className="debug-empty">No citations</div>
                  )}
                </div>

                <div className="debug-subsection">
                  <strong>Chunk Count:</strong> {ragContext.chunk_count}
                </div>

                <div className="debug-subsection">
                  <strong>Used in Response:</strong> {ragContext.used_in_response ? 'Yes' : 'No'}
                </div>

                {/* Chunk Previews */}
                {ragContext.chunks.length > 0 && (
                  <div className="debug-subsection">
                    <strong>Retrieved Chunks (preview):</strong>
                    <div className="chunks-list">
                      {ragContext.chunks.map((chunk, idx) => (
                        <div key={chunk.chunk_id} className="chunk-preview">
                          <div className="chunk-header">
                            <span className="chunk-citation">{ragContext.citations[idx]}</span>
                            <span className="chunk-source">{chunk.source_label}</span>
                            <span className="chunk-score">Score: {chunk.score.toFixed(3)}</span>
                          </div>
                          <div className="chunk-text">
                            {chunk.text}
                            {chunk.text.length >= 200 && '...'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* RAG Metrics Section */}
          {ragMetrics && (
            <div className="debug-section">
              <h4>📊 RAG Metrics</h4>
              <div>
                <div className="debug-subsection">
                  <strong>Query Rewrite Latency:</strong> {ragMetrics.query_rewrite_latency_ms.toFixed(2)}ms
                </div>

                <div className="debug-subsection">
                  <strong>Retrieval Latency:</strong> {ragMetrics.retrieval_latency_ms.toFixed(2)}ms
                </div>

                <div className="debug-subsection">
                  <strong>Total Pipeline Latency:</strong> {ragMetrics.total_pipeline_latency_ms.toFixed(2)}ms
                </div>

                <div className="debug-subsection">
                  <strong>Chunks Retrieved:</strong> {ragMetrics.chunk_count}
                </div>

                <div className="debug-subsection">
                  <strong>Max Similarity Score:</strong> {ragMetrics.max_similarity_score.toFixed(3)}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
};
