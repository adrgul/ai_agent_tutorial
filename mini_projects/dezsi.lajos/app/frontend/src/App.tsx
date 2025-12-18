import { useState, useEffect } from 'react';
import { MessageSquare, RefreshCw, Database } from 'lucide-react';
import { ChatWindow } from './components/ChatWindow';
import { ChatInput } from './components/ChatInput';
import { DebugPanel } from './components/DebugPanel';
import { api } from './api';

interface Message {
    role: 'user' | 'assistant' | 'system';
    content: string;
}

function App() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [conversationId, setConversationId] = useState<string>('');
    const [debugData, setDebugData] = useState<any>(null);

    useEffect(() => {
        if (!conversationId) {
            setConversationId(crypto.randomUUID());
        }
    }, []);

    const handleSend = async (text: string) => {
        const userMsg: Message = { role: 'user', content: text };
        setMessages(prev => [...prev, userMsg]);
        setIsLoading(true);

        try {
            const response = await api.chat(text, conversationId);

            if (response.conversation_id) {
                setConversationId(response.conversation_id);
            }

            const botMsg: Message = { role: 'assistant', content: response.response };
            setMessages(prev => [...prev, botMsg]);

            if (response.generated_ticket) {
                setDebugData(response.generated_ticket);
            }

        } catch (error) {
            console.error(error);
            setMessages(prev => [...prev, { role: 'system', content: 'Detailed Error: Check console. Error connecting to backend.' }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleReset = async () => {
        if (conversationId) {
            await api.clearHistory(conversationId);
            setMessages([]);
            setDebugData(null);
        }
    };

    const handleSeed = async () => {
        try {
            await api.seedKB();
            alert('Knowledge base seeded with sample policies!');
        } catch (e) {
            alert('Failed to seed KB');
        }
    };

    return (
        <div className="flex h-screen bg-slate-100 font-sans">
            <div className="flex-1 flex flex-col h-full border-r border-slate-200">
                <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
                    <div className="flex items-center gap-3">
                        <div className="bg-blue-600 p-2 rounded-lg text-white">
                            <MessageSquare size={20} />
                        </div>
                        <h1 className="font-bold text-slate-800">MedicalSupport AI</h1>
                    </div>
                    <div className="flex gap-2">
                        <button onClick={handleSeed} className="p-2 hover:bg-slate-100 rounded-full text-slate-600" title="Seed Knowledge Base">
                            <Database size={20} />
                        </button>
                        <button onClick={handleReset} className="p-2 hover:bg-slate-100 rounded-full text-slate-600" title="Reset Chat">
                            <RefreshCw size={20} />
                        </button>
                    </div>
                </header>

                <ChatWindow messages={messages} isLoading={isLoading} />
                <ChatInput onSend={handleSend} disabled={isLoading} />
            </div>

            <div className="w-[400px] h-full hidden lg:block bg-slate-900 border-l border-slate-800">
                <DebugPanel data={debugData} />
            </div>
        </div>
    );
}

export default App;
