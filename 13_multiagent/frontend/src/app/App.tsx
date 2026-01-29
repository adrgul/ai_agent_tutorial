import { useState, useEffect } from 'react';
import { Message, TraceEvent, TicketTriage, AgentAssist, StateSnapshot, Pattern } from '../lib/types';
import { wsClient } from '../lib/ws';
import Chat from '../components/Chat';
import PatternSelector from '../components/PatternSelector';
import TracePanel from '../components/TracePanel';
import StatePanel from '../components/StatePanel';
import TicketPanel from '../components/TicketPanel';
import AgentAssistPanel from '../components/AgentAssistPanel';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

function App() {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [selectedPattern, setSelectedPattern] = useState<string>('router');
  const [messages, setMessages] = useState<Message[]>([]);
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([]);
  const [ticket, setTicket] = useState<TicketTriage | null>(null);
  const [agentAssist, setAgentAssist] = useState<AgentAssist | null>(null);
  const [stateSnapshot, setStateSnapshot] = useState<StateSnapshot | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Connect WebSocket on mount
  useEffect(() => {
    wsClient.connect()
      .then(() => setIsConnected(true))
      .catch(console.error);

    // Fetch available patterns
    fetch(`${API_URL}/patterns`)
      .then(res => res.json())
      .then(data => setPatterns(data.patterns))
      .catch(console.error);

    return () => {
      wsClient.disconnect();
    };
  }, []);

  // Handle WebSocket messages
  useEffect(() => {
    const handler = (message: any) => {
      if (message.type === 'trace') {
        setTraceEvents(prev => [...prev, message.event]);
      } else if (message.type === 'word') {
        setMessages(prev => {
          const newMessages = [...prev];
          if (newMessages.length > 0 && newMessages[newMessages.length - 1].role === 'assistant') {
            // Append to existing assistant message
            newMessages[newMessages.length - 1].content += message.content;
          } else {
            // Create new assistant message
            newMessages.push({ role: 'assistant', content: message.content });
          }
          return newMessages;
        });
      } else if (message.type === 'done') {
        setIsProcessing(false);
        const final = message.final;
        
        if (final.ticket) {
          setTicket(final.ticket);
        }
        if (final.agent_assist) {
          setAgentAssist(final.agent_assist);
        }
        if (final.state_snapshot) {
          setStateSnapshot(final.state_snapshot);
        }
      } else if (message.type === 'error') {
        setIsProcessing(false);
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Error: ${message.message}`
        }]);
      }
    };

    wsClient.onMessage(handler);

    return () => {
      wsClient.removeMessageHandler(handler);
    };
  }, []);

  const handleSendMessage = (content: string) => {
    // Add user message
    const userMessage: Message = { role: 'user', content };
    setMessages(prev => [...prev, userMessage]);

    // Clear previous results
    setTraceEvents([]);
    setTicket(null);
    setAgentAssist(null);
    setStateSnapshot(null);

    // Send to backend
    setIsProcessing(true);
    wsClient.send({
      pattern: selectedPattern,
      message: content,
      customer_id: 'CUST-001', // Demo customer
      channel: 'chat',
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">
            AI Customer Support Agent
          </h1>
          <p className="text-sm text-gray-600">
            Multi-agent patterns with LangGraph
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="mb-4">
          <PatternSelector
            patterns={patterns}
            selectedPattern={selectedPattern}
            onSelectPattern={setSelectedPattern}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left column - Chat */}
          <div className="space-y-6">
            <Chat
              messages={messages}
              onSendMessage={handleSendMessage}
              isProcessing={isProcessing}
              isConnected={isConnected}
            />
          </div>

          {/* Right column - Panels */}
          <div className="space-y-6">
            <StatePanel state={stateSnapshot} />
            <TracePanel events={traceEvents} />
            <TicketPanel ticket={ticket} />
            <AgentAssistPanel agentAssist={agentAssist} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
