import { TraceEvent } from '../lib/types';

interface TracePanelProps {
  events: TraceEvent[];
}

const EVENT_COLORS: Record<string, string> = {
  node_start: 'bg-blue-100 text-blue-800',
  node_end: 'bg-green-100 text-green-800',
  tool_call: 'bg-purple-100 text-purple-800',
  tool_result: 'bg-purple-100 text-purple-800',
  send_fanout: 'bg-orange-100 text-orange-800',
  handoff: 'bg-red-100 text-red-800',
  cache_hit: 'bg-emerald-100 text-emerald-800',
  cache_miss: 'bg-gray-100 text-gray-800',
};

const EVENT_ICONS: Record<string, string> = {
  node_start: '▶',
  node_end: '■',
  tool_call: '🔧',
  tool_result: '✓',
  send_fanout: '⚡',
  handoff: '🔄',
  cache_hit: '💾',
  cache_miss: '🔍',
};

export default function TracePanel({ events }: TracePanelProps) {
  return (
    <div className="bg-white rounded-lg shadow-md p-4 h-[300px] flex flex-col">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">Trace / Events</h2>
      <div className="flex-1 overflow-y-auto space-y-2">
        {events.length === 0 && (
          <p className="text-sm text-gray-500 text-center mt-4">
            No trace events yet
          </p>
        )}
        {events.map((event, index) => (
          <div key={index} className="text-xs border-l-2 border-gray-300 pl-3 py-1">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded font-medium ${EVENT_COLORS[event.type] || 'bg-gray-100'}`}>
                {EVENT_ICONS[event.type]} {event.type}
              </span>
              <span className="text-gray-500">
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
            </div>
            {event.node_name && (
              <div className="mt-1 text-gray-700">
                Node: <span className="font-medium">{event.node_name}</span>
              </div>
            )}
            {event.tool_name && (
              <div className="mt-1 text-gray-700">
                Tool: <span className="font-medium">{event.tool_name}</span>
              </div>
            )}
            {event.from_agent && event.to_agent && (
              <div className="mt-1 text-gray-700">
                Handoff: <span className="font-medium">{event.from_agent}</span> → <span className="font-medium">{event.to_agent}</span>
                {event.reason && <span className="text-gray-600"> ({event.reason})</span>}
              </div>
            )}
            {event.data && Object.keys(event.data).length > 0 && (
              <div className="mt-1 text-gray-600">
                {JSON.stringify(event.data, null, 0).substring(0, 100)}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
