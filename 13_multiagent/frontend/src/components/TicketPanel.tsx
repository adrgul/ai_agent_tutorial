import { TicketTriage } from '../lib/types';

interface TicketPanelProps {
  ticket: TicketTriage | null;
}

const PRIORITY_COLORS: Record<string, string> = {
  P0: 'bg-red-100 text-red-800',
  P1: 'bg-orange-100 text-orange-800',
  P2: 'bg-yellow-100 text-yellow-800',
  P3: 'bg-green-100 text-green-800',
};

const SENTIMENT_COLORS: Record<string, string> = {
  positive: 'text-green-600',
  neutral: 'text-gray-600',
  negative: 'text-red-600',
};

export default function TicketPanel({ ticket }: TicketPanelProps) {
  if (!ticket) {
    return (
      <div className="bg-white rounded-lg shadow-md p-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Ticket Triage</h2>
        <p className="text-sm text-gray-500">No ticket data yet</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">Ticket Triage</h2>
      <div className="space-y-3 text-sm">
        <div>
          <span className="text-gray-600 block mb-1">Category</span>
          <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 rounded font-medium">
            {ticket.category}
          </span>
        </div>
        
        <div>
          <span className="text-gray-600 block mb-1">Priority</span>
          <span className={`inline-block px-3 py-1 rounded font-medium ${PRIORITY_COLORS[ticket.priority] || 'bg-gray-100'}`}>
            {ticket.priority}
          </span>
        </div>

        {ticket.sentiment && (
          <div>
            <span className="text-gray-600 block mb-1">Sentiment</span>
            <span className={`font-medium ${SENTIMENT_COLORS[ticket.sentiment] || 'text-gray-600'}`}>
              {ticket.sentiment}
            </span>
          </div>
        )}

        <div>
          <span className="text-gray-600 block mb-1">Routing Team</span>
          <span className="font-medium">{ticket.routing_team}</span>
        </div>

        {ticket.tags.length > 0 && (
          <div>
            <span className="text-gray-600 block mb-1">Tags</span>
            <div className="flex flex-wrap gap-1">
              {ticket.tags.map((tag, idx) => (
                <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        <div>
          <span className="text-gray-600 block mb-1">Confidence</span>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${ticket.confidence * 100}%` }}
              />
            </div>
            <span className="text-xs font-medium">{(ticket.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}
