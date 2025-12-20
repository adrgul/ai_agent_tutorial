import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ChatResponse {
    response: string;
    conversation_id: string;
    generated_ticket?: {
        analysis: any;
        triage_decision: any;
        answer_draft: any;
    };
}

export const api = {
    chat: async (message: string, conversation_id?: string): Promise<ChatResponse> => {
        const response = await axios.post(`${API_URL}/chat`, {
            message,
            conversation_id,
        });
        return response.data;
    },

    clearHistory: async (conversation_id: string) => {
        await axios.post(`${API_URL}/reset/${conversation_id}`);
    },

    seedKB: async () => {
        await axios.post(`${API_URL}/seed_kb`);
    }
};
