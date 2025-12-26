// API service for communicating with the FastAPI backend

import { jwtDecode } from 'jwt-decode';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'; // Update this to match your FastAPI server port

export interface PromptInput {
  prompt: string;
  model: string;
}

export interface ApiResponse {
  model: string;
  response: string;
}

export interface ChainRequest {
  prompt: string;
  models: string[];
}

export interface ChainResponse {
  responses: Array<{
    model: string;
    response: string;
  }>;
}

export interface ChatMessageRequest {
  prompt: string;
  response: string;
}

export interface ChatMessageResponse {
  id: number;
  prompt: string;
  response: string;
  timestamp: string;
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  // Single model request
  async askModel(prompt: string, model: string, session_id?: string): Promise<ApiResponse> {
    try {
      const token = getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const response = await fetch(`${this.baseUrl}/ask`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          prompt,
          model,
          session_id,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request failed: ${response.status} - ${errorText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error calling API:', error);
      throw error;
    }
  }
  
  // Health check to verify backend connectivity
  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
      });
      return response.ok;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }
}

// Export singleton instance
export const apiService = new ApiService();

// Export the class for testing or custom instances
export { ApiService };

export async function chainModelsAPI(prompt: string, models: string[]) {
  const response = await fetch(`${API_BASE_URL}/chain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, models }),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
// Add this function to your api.ts
export async function analyzeDataAPI(prompt: string, sessionId: string) {
  const token = getToken();
  const response = await fetch(`${API_BASE_URL}/analyze-data`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      prompt,
      model: 'data-analysis',
      session_id: sessionId,
    }),
  });
  
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

// Enhanced streaming single model request with search
export async function* askModelStreamWithSearch(
  prompt: string, 
  model: string, 
  session_id?: string, 
  token?: string, 
  signal?: AbortSignal
) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  // Create an AbortController with a 10-minute timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minutes
  
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/ask`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ prompt, model, session_id }),
      signal: signal || controller.signal,
    });

    if (!response.ok || !response.body) {
      throw new Error(`API request failed: ${response.status}`);
    }
    
    // Clear the timeout if the request completes successfully
    clearTimeout(timeoutId);
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('Request timed out after 10 minutes');
    }
    throw error;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    let lines = buffer.split('\n');
    buffer = lines.pop()!;

    for (const line of lines) {
      if (line.trim()) {
        try {
          const parsed = JSON.parse(line);
          yield parsed;
        } catch (e) {
          console.error('Failed to parse streaming response:', e);
        }
      }
    }
  }

  if (buffer.trim()) {
    try {
      yield JSON.parse(buffer);
    } catch (e) {
      console.error('Failed to parse final buffer:', e);
    }
  }
}

export async function uploadFilesAPI(files: File[], sessionId: string) {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}/upload?session_id=${encodeURIComponent(sessionId)}`, {
    method: 'POST',
    body: formData,
    headers, // Add Authorization header
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

// Tavily-powered search endpoints
export async function searchYouTubeAPI(query: string, maxResults: number = 5) {
  const response = await fetch(`${API_BASE_URL}/search/youtube?query=${encodeURIComponent(query)}&max_results=${maxResults}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function searchRedditAPI(query: string, maxResults: number = 5) {
  const response = await fetch(`${API_BASE_URL}/search/reddit?query=${encodeURIComponent(query)}&max_results=${maxResults}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function searchAcademicAPI(query: string, maxResults: number = 5) {
  const response = await fetch(`${API_BASE_URL}/search/academic?query=${encodeURIComponent(query)}&max_results=${maxResults}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function searchCryptoAPI(query: string, maxResults: number = 5) {
  const response = await fetch(`${API_BASE_URL}/search/crypto?query=${encodeURIComponent(query)}&max_results=${maxResults}`);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export async function getChatHistoryAPI(session_id: string) {
  const token = getToken();
  if (!token) throw new Error('Not authenticated');
  const response = await fetch(`${API_BASE_URL}/history?session_id=${encodeURIComponent(session_id)}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<ChatMessageResponse[]>;
}

export async function saveChatMessageAPI(session_id: string, prompt: string, responseText: string) {
  const token = getToken();
  if (!token) throw new Error('Not authenticated');
  const response = await fetch(`${API_BASE_URL}/history`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ session_id, prompt, response: responseText }),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<ChatMessageResponse>;
}

export function getToken() {
  return localStorage.getItem('token');
}

export function setToken(token: string) {
  localStorage.setItem('token', token);
}

export function removeToken() {
  localStorage.removeItem('token');
}

export function getUserInfo() {
  const token = getToken();
  if (!token) return null;
  try {
    return jwtDecode(token) as { sub: string; role: string };
  } catch {
    return null;
  }
}

export function isAuthenticated() {
  return !!getToken();
}

// Streaming single model request
export async function* askModelStream(prompt: string, model: string, session_id?: string, token?: string, signal?: AbortSignal) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ prompt, model, session_id }),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`API request failed: ${response.status}`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let lines = buffer.split('\n');
    buffer = lines.pop()!;
    for (const line of lines) {
      if (line.trim()) yield JSON.parse(line);
    }
  }
  if (buffer.trim()) yield JSON.parse(buffer);
}

// Streaming chain model request
export async function* chainModelsStream(prompt: string, models: string[], token?: string, signal?: AbortSignal) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}/chain`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ prompt, models }),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`API request failed: ${response.status}`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let lines = buffer.split('\n');
    buffer = lines.pop()!;
    for (const line of lines) {
      if (line.trim()) yield JSON.parse(line);
    }
  }
  if (buffer.trim()) yield JSON.parse(buffer);
} 
