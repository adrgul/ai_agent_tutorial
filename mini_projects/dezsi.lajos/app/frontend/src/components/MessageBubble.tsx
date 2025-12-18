import React from 'react';
import Markdown from 'react-markdown';
import { User, Bot } from 'lucide-react';
import { clsx } from 'clsx';

interface MessageBubbleProps {
    role: 'user' | 'assistant' | 'system';
    content: string;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ role, content }) => {
    const isUser = role === 'user';

    return (
        <div className={clsx("flex w-full mb-4", isUser ? "justify-end" : "justify-start")}>
            <div className={clsx("flex max-w-[80%] gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
                <div className={clsx(
                    "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                    isUser ? "bg-blue-600 text-white" : "bg-emerald-600 text-white"
                )}>
                    {isUser ? <User size={18} /> : <Bot size={18} />}
                </div>

                <div className={clsx(
                    "p-4 rounded-2xl text-sm shadow-sm",
                    isUser ? "bg-blue-600 text-white rounded-tr-none" : "bg-white border border-slate-200 text-slate-800 rounded-tl-none"
                )}>
                    <Markdown className="prose prose-sm max-w-none dark:prose-invert">
                        {content}
                    </Markdown>
                </div>
            </div>
        </div>
    );
};
