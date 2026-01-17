import React from 'react';
import { Terminal } from 'lucide-react';

interface DebugPanelProps {
    data: any;
}

export const DebugPanel: React.FC<DebugPanelProps> = ({ data }) => {
    if (!data) return (
        <div className="h-full flex flex-col items-center justify-center text-slate-400 p-8 text-center">
            <Terminal size={48} className="mb-4 opacity-20" />
            <p>No triage data available yet.</p>
            <p className="text-sm">Send a message to see the agent's analysis.</p>
        </div>
    );

    return (
        <div className="h-full overflow-y-auto bg-slate-900 text-slate-50 p-4 font-mono text-xs">
            <div className="flex items-center gap-2 mb-4 pb-2 border-b border-slate-700">
                <Terminal size={16} />
                <span className="font-semibold">Agent Internal State</span>
            </div>

            <div className="space-y-4">
                <Section title="Analysis" content={data.analysis} color="text-blue-400" />
                <Section title="Triage Decision" content={data.triage_decision} color="text-yellow-400" />
                <Section title="Generated Draft" content={data.answer_draft} color="text-emerald-400" />
            </div>
        </div>
    );
};

const Section: React.FC<{ title: string; content: any; color: string }> = ({ title, content, color }) => (
    <div>
        <h3 className={`font-bold mb-2 ${color}`}>{title}</h3>
        <pre className="bg-slate-800 p-2 rounded overflow-x-auto">
            {JSON.stringify(content, null, 2)}
        </pre>
    </div>
);
