/**
 * API client for backend communication.
 */
import axios from 'axios';
import {
  ChatRequest,
  ChatResponse,
  DocumentUploadResponse,
  RAGStats,
  DocumentListResponse,
  DocumentDeleteResponse
} from './types';

const API_BASE_URL = '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 180000, // 180 seconds for complex multi-tool agent requests
});

export const api = {
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await apiClient.post<ChatResponse>('/chat', request);
    return response.data;
  },

  async getSession(sessionId: string) {
    const response = await apiClient.get(`/session/${sessionId}`);
    return response.data;
  },

  async getProfile(userId: string) {
    const response = await apiClient.get(`/profile/${userId}`);
    return response.data;
  },

  async updateProfile(userId: string, updates: any) {
    const response = await apiClient.put(`/profile/${userId}`, updates);
    return response.data;
  },

  async searchHistory(query: string) {
    const response = await apiClient.get('/history/search', {
      params: { q: query },
    });
    return response.data;
  },

  /**
   * RAG API methods
   */
  async uploadDocument(file: File, userId: string): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);

    const response = await apiClient.post<DocumentUploadResponse>(
      '/rag/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  async getRagStats(userId: string): Promise<RAGStats> {
    const response = await apiClient.get<RAGStats>(`/rag/stats/${userId}`);
    return response.data;
  },

  async listDocuments(userId: string): Promise<DocumentListResponse> {
    const response = await apiClient.get<DocumentListResponse>(`/rag/documents/${userId}`);
    return response.data;
  },

  async deleteDocument(docId: string, userId: string): Promise<DocumentDeleteResponse> {
    const response = await apiClient.delete<DocumentDeleteResponse>(
      `/rag/documents/${docId}`,
      {
        params: { user_id: userId },
      }
    );
    return response.data;
  },
};
