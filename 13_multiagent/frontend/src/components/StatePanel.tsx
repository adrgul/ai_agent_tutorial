import { StateSnapshot } from '../lib/types';

interface StatePanelProps {
  state: StateSnapshot | null;
}

export default function StatePanel({ state }: StatePanelProps) {
  if (!state) {
    return (
      <div className="bg-white rounded-lg shadow-md p-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">State Snapshot</h2>
        <p className="text-sm text-gray-500">No state data yet</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">State Snapshot</h2>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Pattern:</span>
          <span className="font-medium">{state.selected_pattern}</span>
        </div>
        {state.active_agent && (
          <div className="flex justify-between">
            <span className="text-gray-600">Active Agent:</span>
            <span className="font-medium">{state.active_agent}</span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-gray-600">Recursion Depth:</span>
          <span className="font-medium">{state.recursion_depth}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Sources:</span>
          <span className="font-medium">{state.sources_count}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Messages:</span>
          <span className="font-medium">{state.messages_count}</span>
        </div>
      </div>
    </div>
  );
}
