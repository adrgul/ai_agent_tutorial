import { AgentAssist } from '../lib/types';

interface AgentAssistPanelProps {
  agentAssist: AgentAssist | null;
}

export default function AgentAssistPanel({ agentAssist }: AgentAssistPanelProps) {
  if (!agentAssist) {
    return (
      <div className="bg-white rounded-lg shadow-md p-4">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Agent Assist</h2>
        <p className="text-sm text-gray-500">No agent assist data yet</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-4">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">Agent Assist</h2>
      
      <div className="space-y-4">
        {/* Draft Reply */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Suggested Reply Draft</h3>
          <div className="bg-gray-50 border border-gray-200 rounded p-3 text-sm text-gray-700">
            {agentAssist.draft_reply}
          </div>
        </div>

        {/* Case Summary */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Case Summary</h3>
          <ul className="space-y-1">
            {agentAssist.case_summary.map((item, idx) => (
              <li key={idx} className="text-sm text-gray-700 flex items-start">
                <span className="text-blue-600 mr-2">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Next Actions */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Next Best Actions</h3>
          <ul className="space-y-1">
            {agentAssist.next_actions.map((action, idx) => (
              <li key={idx} className="text-sm text-gray-700 flex items-start">
                <input 
                  type="checkbox" 
                  className="mt-0.5 mr-2 text-blue-600" 
                  id={`action-${idx}`}
                />
                <label htmlFor={`action-${idx}`} className="cursor-pointer">
                  {action}
                </label>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
