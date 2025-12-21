import React, { useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';

interface Message {
    role: 'user' | 'assistant' | 'system';
    content: string;
}

interface ChatWindowProps {
    messages: Message[];
    isLoading: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ messages, isLoading }) => {
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages, isLoading]);

    return (
        <div className="flex-1 overflow-y-auto p-4 bg-slate-50">
            {messages.map((msg, idx) => (
                <MessageBubble key={idx} role={msg.role} content={msg.content} />
            ))}
            {isLoading && (
                <div className="flex w-full mb-4 justify-start">
                    <div className="flex flex-row gap-3">
                        <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center shrink-0 animate-pulse">
                        </div>
                        <div className="p-4 bg-white border border-slate-200 rounded-2xl rounded-tl-none text-slate-500 text-sm">
                            Thinking...
                        </div>
                    </div>
                </div>
            )}
            <div ref={messagesEndRef} />
        </div>
    );
};
