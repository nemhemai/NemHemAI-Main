import { useState, useRef, useEffect, useMemo } from 'react';
import { Send, Bot, User, Link2, Paperclip, Image, FileText, AlertCircle, Settings, Mic, Database, BarChart3, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ModelSelector } from '@/components/ModelSelector';
import { CopyButton } from '@/components/CopyButton';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { apiService, chainModelsAPI, uploadFilesAPI, searchYouTubeAPI, searchRedditAPI, searchAcademicAPI, searchCryptoAPI, getChatHistoryAPI, saveChatMessageAPI, askModelStream, chainModelsStream, askModelStreamWithSearch } from '@/lib/api';
import { removeToken, getUserInfo, getToken } from '@/lib/api';
import { saveMessage } from '@/lib/chatHistory';

import { models } from '@/components/ModelSelector';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { API_BASE_URL } from '@/lib/api';
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '@/components/ui/dropdown-menu';
import { Dialog, DialogTrigger, DialogContent, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { v4 as uuidv4 } from 'uuid';
import { toast } from 'sonner';

// Dual Chain Model Selector Component
interface DualChainModelSelectorProps {
  selectedModels: [string, string];
  onModelsChange: (models: [string, string]) => void;
}

const DualChainModelSelector = ({ selectedModels, onModelsChange }: DualChainModelSelectorProps) => {
  const [model1, model2] = selectedModels;

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-slate-400 font-medium">Model 1:</span>
      <Select value={model1} onValueChange={val => onModelsChange([val, model2 === val ? '' : model2])}>
        <SelectTrigger className="w-[220px] bg-slate-900 border-[#A259FF] text-white hover:bg-[#6C47FF]/10 transition-all duration-200 shadow-lg rounded-xl">
          <SelectValue />
        </SelectTrigger>
        <SelectContent className="bg-slate-900 border-[#A259FF] shadow-2xl rounded-xl">
            {models.map((model) => (
            <SelectItem
              key={model.id}
              value={model.id}
              disabled={model.id === model2}
              className="text-white hover:bg-[#6C47FF]/20 focus:bg-[#A259FF]/20 cursor-pointer rounded-xl"
            >
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-3">
                  <Badge
                    variant="outline"
                    className="text-xs bg-gradient-to-r from-[#6C47FF] to-[#A259FF] text-white border-0"
                  >
                    {model.category}
                  </Badge>
                  <span className="font-medium">{model.name}</span>
                </div>
                <span className="text-xs text-slate-400 ml-3">{model.description}</span>
              </div>
            </SelectItem>
            ))}
        </SelectContent>
      </Select>
      <span className="text-sm text-slate-400 font-medium">Model 2:</span>
      <Select value={model2} onValueChange={val => onModelsChange([model1 === val ? '' : model1, val])}>
        <SelectTrigger className="w-[220px] bg-slate-900 border-[#A259FF] text-white hover:bg-[#6C47FF]/10 transition-all duration-200 shadow-lg rounded-xl">
          <SelectValue />
        </SelectTrigger>
        <SelectContent className="bg-slate-900 border-[#A259FF] shadow-2xl rounded-xl">
            {models.map((model) => (
            <SelectItem
              key={model.id}
              value={model.id}
              disabled={model.id === model1}
              className="text-white hover:bg-[#6C47FF]/20 focus:bg-[#A259FF]/20 cursor-pointer rounded-xl"
            >
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-3">
                  <Badge
                    variant="outline"
                    className="text-xs bg-gradient-to-r from-[#6C47FF] to-[#A259FF] text-white border-0"
                  >
                    {model.category}
                  </Badge>
                  <span className="font-medium">{model.name}</span>
                </div>
                <span className="text-xs text-slate-400 ml-3">{model.description}</span>
              </div>
            </SelectItem>
            ))}
        </SelectContent>
      </Select>
    </div>
  );
};

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  model?: string;
  timestamp: Date;
  searchResults?: string;
  isChained?: boolean;
  chainResponses?: Array<{ model: string; response: string }>;
  isError?: boolean;
  uploadedFiles?: Array<{ name: string; type: string }>;
  // Data analysis specific fields
  isDataAnalysis?: boolean;
  analysisCode?: string;
  analysisOutput?: string;
  analysisChart?: string;
  analysisExplanation?: string;
}

interface ChatInterfaceProps {
  chatId: string;
  onLogout?: () => void;
}

// CSV file info interface
interface CSVInfo {
  has_csv: boolean;
  filename?: string;
  uploaded_at?: string;
  shape?: [number, number];
  columns?: string[];
  dtypes?: Record<string, string>;
  sample_data?: any[];
}

// Utility: Preprocess plain text to markdown for better formatting
function autoFormatMarkdown(text: string): string {
  // Convert 'Features:' or 'How to Use:' to headings
  let formatted = text.replace(/^(Features|How to Use|Conclusion|Future Trends|Applications of AI|Challenges and Ethical Considerations|Core AI Technologies|Key Types of AI):?/gim, (m) => `### ${m.replace(':','')}`);

  // Convert lines starting with dash, bullet, or similar to markdown bullets
  formatted = formatted.replace(/^(\s*[-•])\s?/gm, '- ');

  // Convert numbered steps to markdown ordered list
  formatted = formatted.replace(/^(\d+)\.\s+/gm, (m, n) => `${n}. `);

  // Add spacing before headings
  formatted = formatted.replace(/(\n)?(### )/g, '\n$2');

  // Remove duplicate blank lines
  formatted = formatted.replace(/\n{3,}/g, '\n\n');

  return formatted.trim();
}

// Utility: Convert plain URLs to clickable links (for web search results)
function linkify(text: string): string {
  // Regex to match URLs
  const urlRegex = /(https?:\/\/[\w\-._~:\/?#[\]@!$&'()*+,;=%]+)(?![^<]*>|[^\[]*\])/g;
  return text.replace(urlRegex, (url) => `<a href="${url}" target="_blank" rel="noopener noreferrer" style="color:#38bdf8;text-decoration:underline;">${url}</a>`);
}

const fileTypeIcon = (fileName: string) => {
  const ext = fileName.split('.').pop()?.toLowerCase();
  if (!ext) return <FileText className="h-4 w-4 text-emerald-400" />;
  if (["png", "jpg", "jpeg", "bmp", "tiff", "gif", "svg"].includes(ext)) return <Image className="h-4 w-4 text-emerald-400" />;
  if (["pdf"].includes(ext)) return <FileText className="h-4 w-4 text-red-400" />;
  if (["doc", "docx"].includes(ext)) return <FileText className="h-4 w-4 text-blue-400" />;
  if (["csv"].includes(ext)) return <Database className="h-4 w-4 text-green-400" />;
  return <FileText className="h-4 w-4 text-gray-400" />;
};

// Data Analysis API functions (add these to your api.ts file)
const uploadCSV = async (file: File, sessionId: string): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);
  
  console.log('Uploading file:', {
    name: file.name,
    size: file.size,
    type: file.type,
    sessionId
  });

  const token = getToken();
  if (!token) {
    throw new Error('No authentication token found. Please log in again.');
  }

  try {
    const response = await fetch(`${API_BASE_URL}/upload-csv?session_id=${sessionId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        // Don't set Content-Type header when using FormData
        // The browser will set it automatically with the correct boundary
      },
      body: formData,
    });

    const responseData = await response.text();
    console.log('Raw upload response:', responseData);
    
    let jsonResponse;
    try {
      jsonResponse = responseData ? JSON.parse(responseData) : {};
    } catch (e) {
      console.error('Failed to parse JSON response:', e);
      throw new Error(`Invalid server response: ${responseData.substring(0, 200)}...`);
    }

    console.log('Upload response:', {
      status: response.status,
      statusText: response.statusText,
      data: jsonResponse
    });

    if (!response.ok) {
      const error = new Error(`HTTP error! status: ${response.status} - ${response.statusText}`) as any;
      error.response = {
        status: response.status,
        statusText: response.statusText,
        data: jsonResponse.detail || responseData
      };
      throw error;
    }

    console.log('Upload successful:', jsonResponse);
    return jsonResponse;
    
  } catch (error: any) {
    console.error('Upload error:', {
      name: error.name,
      message: error.message,
      stack: error.stack,
      response: error.response
    });
    throw error;
  }
};

const getCSVInfo = async (sessionId: string): Promise<CSVInfo> => {
  const response = await fetch(`${API_BASE_URL}/csv-info?session_id=${sessionId}`, {
    headers: {
      'Authorization': `Bearer ${getToken()}`,
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
};

const dataAnalysisStream = async function* (
  prompt: string,
  sessionId: string,
  model: string = 'deepseek-coder-v2:latest'
) {
  const response = await fetch(`${API_BASE_URL}/data-analysis`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getToken()}`,
    },
    body: JSON.stringify({
      prompt,
      session_id: sessionId,
      model,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  if (!response.body) {
    throw new Error('No response body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter(line => line.trim());

      for (const line of lines) {
        try {
          const data = JSON.parse(line);
          yield data;
        } catch (e) {
          // Skip invalid JSON lines
          continue;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
};

export const ChatInterface = ({ chatId, onLogout }: ChatInterfaceProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sessionId] = useState(chatId || uuidv4());
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [uploadedFileInfos, setUploadedFileInfos] = useState<Array<{filename: string; uploaded_at: string}>>([]);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);
  const [chainMode, setChainMode] = useState(false);
  const [selectedModel, setSelectedModel] = useState('llama3.1:latest');
  const [selectedChainModels, setSelectedChainModels] = useState<[string, string]>(['llama3.1:latest', 'mistral:latest']);
  const [listening, setListening] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  
  // Data Analysis specific states
  const [dataAnalysisMode, setDataAnalysisMode] = useState(false);
  const [csvInfo, setCsvInfo] = useState<CSVInfo>({ has_csv: false });
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [selectedAnalysisModel, setSelectedAnalysisModel] = useState('deepseek-coder-v2:latest');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    setIsAtBottom(scrollHeight - scrollTop - clientHeight < 50); // 50px threshold
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isAtBottom) {
      scrollToBottom();
    }
  }, [messages, isAtBottom]);

  useEffect(() => {
    const checkUploadStatus = async () => {
      if (!sessionId) return;
      
      try {
        // Check CSV info for data analysis mode
        if (dataAnalysisMode) {
          try {
            const csvStatus = await getCSVInfo(sessionId);
            setCsvInfo(csvStatus);
          } catch (error) {
            console.log('No CSV info found, will be created on first upload');
          }
        }
      } catch (error) {
        console.error('Error checking upload status:', error);
      }
    };
    
    checkUploadStatus();
  }, [sessionId, dataAnalysisMode]);

  const callModelAPI = async (prompt: string, model: string): Promise<string> => {
    try {
      const result = await apiService.askModel(prompt, model, sessionId);
      return result?.response || '';
    } catch (error) {
      console.error(`Error calling model ${model}:`, error);
      throw error;
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) return;

    const newFiles = files.filter(file => 
      !uploadedFiles.some(f => f.name === file.name && f.size === file.size)
    );

    if (newFiles.length === 0) {
      toast.info('These files have already been added.');
      return;
    }

    setUploadedFiles(prev => [...prev, ...newFiles]);

    try {
      const uploadResult = await uploadFilesAPI(files, sessionId);
      
      // Update file list with server response
      setUploadedFileInfos(prev => [
        ...prev,
        ...(uploadResult.files || []).map((f: any) => ({
          filename: f.filename,
          uploaded_at: new Date().toISOString()
        }))
      ]);

      // Show success message
      const uploadMessage: Message = {
        id: Date.now().toString(),
        content: `📁 **Files Uploaded:**\n${uploadResult.files.map((f: any) => `• ${f.filename}`).join('\n')}`,
        isUser: false,
        timestamp: new Date(),
        uploadedFiles: uploadResult.files.map((f: any) => ({
          name: f.filename,
          type: f.filename.split('.').pop()?.toLowerCase() || 'file'
        }))
      };

      setMessages(prev => [...prev, uploadMessage]);
      
      // Save to chat history
      await saveChatMessageAPI(sessionId, `[Uploaded files: ${newFiles.map(f => f.name).join(', ')}]`, uploadMessage.content);
      
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Failed to upload files. Please try again.');
      // Remove the files from state if upload fails
      setUploadedFiles(prev => prev.filter(f => !newFiles.some(nf => nf.name === f.name)));
    }
  };

  // Handle CSV file upload for data analysis
  const handleCSVUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Reset file input
    if (csvInputRef.current) {
      csvInputRef.current.value = '';
    }

    // Basic validation
    if (!file.name || !file.name.toLowerCase().endsWith('.csv')) {
      toast.error('Please upload a valid CSV file');
      return;
    }

    // Check file size (e.g., 10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      toast.error('File is too large. Maximum size is 10MB');
      return;
    }

    setIsLoading(true);
    
    // Show uploading toast
    const toastId = toast.loading('Uploading CSV file...');
    
    try {
      const result = await uploadCSV(file, sessionId);
      
      // Validate response
      if (!result || !result.filename || !result.shape || !result.columns) {
        throw new Error('Invalid response from server');
      }

      const csvInfo = {
        has_csv: true,
        filename: result.filename,
        uploaded_at: new Date().toISOString(),
        shape: result.shape,
        columns: result.columns,
        dtypes: result.dtypes || {},
        sample_data: result.sample_data || []
      };

      setCsvInfo(csvInfo);

      // Show success message
      const uploadMessage: Message = {
        id: `csv-${Date.now()}`,
        content: `📊 **Dataset Uploaded:** ${result.filename}\n\n` +
                `**Shape:** ${result.shape[0]} rows × ${result.shape[1]} columns\n\n` +
                `**Columns:** ${result.columns.join(', ')}\n\n` +
                `✅ Ready for data analysis! Ask me anything about your dataset.`,
        isUser: false,
        timestamp: new Date(),
        isDataAnalysis: true
      };

      setMessages(prev => [...prev, uploadMessage]);
      
      // Update success toast
      toast.success('CSV uploaded successfully!', { id: toastId });
      
    } catch (error: any) {
      console.error('CSV upload error:', error);
      
      let errorMessage = 'Failed to upload CSV';
      if (error.response) {
        // Server responded with an error status code
        errorMessage = error.response.data?.detail || error.response.statusText || errorMessage;
      } else if (error.request) {
        // Request was made but no response received
        errorMessage = 'No response from server. Please check your connection.';
      } else if (error.message) {
        // Something happened in setting up the request
        errorMessage = error.message;
      }
      
      toast.error(`Upload failed: ${errorMessage}`, { id: toastId });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() && uploadedFiles.length === 0) return;

    if (backendConnected === false) {
      const errorMessage: Message = {
        id: Date.now().toString(),
        content: "❌ **Backend Not Connected**\n\nPlease ensure the AI backend server is running before sending messages. Check that the backend server is started and accessible.",
        isUser: false,
        model: 'error',
        timestamp: new Date(),
        isError: true,
        uploadedFiles: []
      };
      setMessages(prev => [...prev, errorMessage]);
      return;
    }

    let messageContent = input;

    // Handle data analysis mode
    if (dataAnalysisMode) {
      if (!csvInfo.has_csv) {
        toast.error('Please upload a CSV file first');
        return;
      }

      // Add user message
      const userMessage: Message = {
        id: Date.now().toString(),
        content: input,
        isUser: true,
        timestamp: new Date(),
        isDataAnalysis: true
      };
      setMessages(prev => [...prev, userMessage]);

      // Reset input and start loading
      setInput('');
      setIsLoading(true);

      try {
        // Create assistant message for data analysis
        const assistantMessage: Message = {
          id: `${Date.now()}-analysis`,
          content: '',
          isUser: false,
          model: selectedAnalysisModel,
          timestamp: new Date(),
          isDataAnalysis: true,
          analysisCode: '',
          analysisOutput: '',
          analysisChart: '',
          analysisExplanation: ''
        };

        setMessages(prev => [...prev, assistantMessage]);

        // Stream data analysis response
        for await (const chunk of dataAnalysisStream(messageContent, sessionId, selectedAnalysisModel)) {
          if (chunk.type === 'status') {
            // Update message with status
            setMessages(prev => 
              prev.map(msg => 
                msg.id === assistantMessage.id 
                  ? { ...msg, content: chunk.message }
                  : msg
              )
            );
          } else if (chunk.type === 'code') {
            // Show generated code
            setMessages(prev => 
              prev.map(msg => 
                msg.id === assistantMessage.id 
                  ? { ...msg, analysisCode: chunk.content }
                  : msg
              )
            );
          } else if (chunk.type === 'output') {
            // Show analysis output
            setMessages(prev => 
              prev.map(msg => 
                msg.id === assistantMessage.id 
                  ? { ...msg, analysisOutput: chunk.content }
                  : msg
              )
            );
          } else if (chunk.type === 'chart') {
            // Show generated chart
            setMessages(prev => 
              prev.map(msg => 
                msg.id === assistantMessage.id 
                  ? { ...msg, analysisChart: chunk.content }
                  : msg
              )
            );
          } else if (chunk.type === 'explanation') {
            // Show explanation
            setMessages(prev => 
              prev.map(msg => 
                msg.id === assistantMessage.id 
                  ? { ...msg, content: chunk.content, analysisExplanation: chunk.content }
                  : msg
              )
            );
          } else if (chunk.type === 'error') {
            // Show error
            setMessages(prev => 
              prev.map(msg => 
                msg.id === assistantMessage.id 
                  ? { ...msg, content: `❌ **Analysis Error:** ${chunk.content}`, isError: true }
                  : msg
              )
            );
          }
        }

        // Save to chat history
        await saveChatMessageAPI(sessionId, messageContent, assistantMessage.content || 'Data analysis completed');

      } catch (error) {
        console.error('Data analysis error:', error);
        const errorMessage: Message = {
          id: Date.now().toString(),
          content: `❌ **Data Analysis Error**\n\n${error instanceof Error ? error.message : "Failed to perform data analysis"}\n\nPlease try again or check your CSV file format.`,
          isUser: false,
          timestamp: new Date(),
          isError: true,
          isDataAnalysis: true
        };
        setMessages(prev => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // Handle file uploads (existing logic)
    if (uploadedFiles.length > 0) {
      setIsLoading(true);
      try {
        const uploadResult = await uploadFilesAPI(uploadedFiles, sessionId);
        
        // Update upload status if CSV was uploaded
        setUploadedFileInfos(prev => [
          ...prev,
          ...(uploadResult.files || []).map((f: any) => ({
            filename: f.filename,
            uploaded_at: new Date().toISOString()
          }))
        ]);

        // Show success message
        const uploadMessage: Message = {
          id: Date.now().toString(),
          content: `📁 **Files Uploaded:**\n${uploadResult.files.map((f: any) => `• ${f.filename}`).join('\n')}`,
          isUser: false,
          timestamp: new Date(),
          uploadedFiles: uploadResult.files.map((f: any) => ({
            name: f.filename,
            type: f.filename.split('.').pop()?.toLowerCase() || 'file'
          }))
        };

        setMessages(prev => [...prev, uploadMessage]);
        
        // Save to chat history
        await saveChatMessageAPI(sessionId, `[Uploaded files: ${uploadedFiles.map(f => f.name).join(', ')}]`, uploadMessage.content);
        
        // Reset UI states for new request
        setInput('');
        setUploadedFiles([]);
        setIsLoading(false);
      } catch (err) {
        const errorMessage: Message = {
          id: Date.now().toString(),
          content: `❌ **File Processing Error**\n\n${err instanceof Error ? err.message : String(err)}\n\nPlease try uploading the file again or check if the file format is supported.`,
          isUser: false,
          timestamp: new Date(),
          isError: true
        };
        setMessages(prev => [...prev, errorMessage]);
        setIsLoading(false);
        return;
      }
    }

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      isUser: true,
      timestamp: new Date(),
      uploadedFiles: uploadedFiles.map(f => ({ name: f.name, type: f.type })),
    };
    setMessages(prev => [...prev, userMessage]);

    // Save to IndexedDB for sidebar/session history
    if (getUserInfo()) {
      const userId = getUserInfo().sub + '_' + sessionId;
      await saveMessage(userId, { sessionId, content: input });
    }

    // Reset UI states for new request
    setInput('');
    setUploadedFiles([]);
    setIsLoading(true);

    try {
      // ----- CHAIN MODE -----
      if (chainMode && selectedChainModels[0] && selectedChainModels[1]) {
        let currentModel = '';
        let currentResponse = '';
        let gotFirstChunk = false;

        for await (const chunk of chainModelsStream(
          messageContent,
          selectedChainModels,
          getToken(),
          null
        )) {
          if (!gotFirstChunk && chunk.response) {
            gotFirstChunk = true;
          }

          if (chunk.model !== currentModel) {
            currentModel = chunk.model;
            currentResponse = '';
            setMessages(prev => [
              ...prev,
              { id: `${Date.now()}-chain-${currentModel}`, content: '', isUser: false, model: currentModel, timestamp: new Date(), isChained: true }
            ]);
          }

          if (chunk.response !== undefined) {
            currentResponse += chunk.response;
            setMessages(prev => {
              const last = prev[prev.length - 1];
              if (last && last.model === currentModel && last.isChained) {
                return [...prev.slice(0, -1), { ...last, content: currentResponse }];
              } else {
                return prev;
              }
            });
          }
        }

        const finalBotMsg = messages[messages.length - 1];
        if (finalBotMsg && finalBotMsg.content) {
          await saveChatMessageAPI(sessionId, messageContent, finalBotMsg.content);
        }

      } 
      // ----- SINGLE MODEL WITH SEARXNG -----
      else {
        let responseText = '';
        let gotFirstChunk = false;
        let searchResultsContent = '';

        // Create assistant message with search results field
        const assistantMessage: Message = {
          id: `${Date.now()}-single`,
          content: '',
          isUser: false,
          model: selectedModel,
          timestamp: new Date(),
          searchResults: '' // Initialize search results
        };

        setMessages(prev => [...prev, assistantMessage]);

        // Use the enhanced streaming function with search
        for await (const chunk of askModelStreamWithSearch(
          messageContent,
          selectedModel,
          sessionId,
          getToken(),
          null
        )) {
          if (chunk.type === 'search_results') {
            searchResultsContent = chunk.content;
            setMessages(prev => 
              prev.map(msg => 
                msg.id === assistantMessage.id 
                  ? { ...msg, searchResults: searchResultsContent }
                  : msg
              )
            );
          } else if (chunk.type === 'model_response') {
            if (!gotFirstChunk && chunk.response) {
              gotFirstChunk = true;
            }
             if (!chunk.done && chunk.response) {
              responseText += chunk.response;
              setMessages(prev => 
                prev.map(msg => 
                  msg.id === assistantMessage.id 
                    ? { ...msg, content: responseText }
                    : msg
                )
              );
            }
          } else if (chunk.type === 'error') {
            throw new Error(chunk.error);
          }
        }

        await saveChatMessageAPI(sessionId, messageContent, responseText);
      }
    } 
    catch (error) {
      console.error('Error generating response:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        content: `❌ **Error Generating Response**\n\n${error instanceof Error ? error.message : "Failed to generate response"}\n\nThis could be due to:\n• Backend server issues\n• API key problems\n• Network connectivity issues\n• Model availability\n\nPlease try again or check your backend connection.`,
        isUser: false,
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } 
    finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startListening = () => {
    if (!(window as any).webkitSpeechRecognition) {
      alert('Speech recognition is not supported in this browser.');
      return;
    }
    
    if (listening) {
      setListening(false);
      return;
    }
    
    const recognition = new (window as any).webkitSpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = true;

    recognition.onstart = () => {
      setListening(true);
    };
    recognition.onend = () => {
      setListening(false);
    };
    recognition.onerror = () => {
      setListening(false);
    };

    recognition.onresult = (event: any) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        transcript += event.results[i][0].transcript;
      }
      setInput(prev => prev + transcript);
    };

    recognition.start();
  };

  const handleLogout = () => {
    if (onLogout) {
      onLogout();
    } else {
      removeToken();
      window.location.reload();
    }
  };

  const components = {
    img: ({node, ...props}: any) => {
      // Convert relative URLs to absolute URLs
      const src = props.src?.startsWith('http') 
        ? props.src 
        : `${API_BASE_URL}${props.src}`;
      
      return <img {...props} src={src} alt={props.alt} style={{maxWidth: '100%', height: 'auto'}} />;
    },
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <div className="bg-white p-4 shadow-sm border-b border-gray-200">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 28,
              height: 28,
              borderRadius: 8,
              background: 'linear-gradient(90deg, #181C5A 0%, #B983FD 100%)',
            }}>
              <span className="text-primary-foreground font-bold text-base" style={{ color: 'white', fontWeight: 700, fontSize: 16 }}>N</span>
            </span>
            <h1 className="text-lg font-bold text-gray-900">NemHem AI</h1>
            {dataAnalysisMode && (
              <Badge className="bg-green-100 text-green-800 border-green-300">
                <Database className="h-3 w-3 mr-1" />
                Data Analysis
              </Badge>
            )}
          </span>
          <div className="flex items-center gap-4">
            {/* Data Analysis Toggle */}
            <Button
              onClick={() => {
                setDataAnalysisMode(!dataAnalysisMode);
                // Reset relevant states when switching modes
                if (dataAnalysisMode) {
                  setCsvInfo({ has_csv: false });
                } else {
                  // Reset any data analysis specific states when turning off
                  setMessages(prev => prev.filter(m => !m.isDataAnalysis));
                }
              }}
              variant={dataAnalysisMode ? "default" : "outline"}
              className={`flex items-center gap-1 rounded-xl ${dataAnalysisMode ? 'bg-gradient-to-r from-[#6C47FF] to-[#A259FF] text-white hover:from-[#5A3BD9] hover:to-[#8C4DFF]' : 'text-slate-200 hover:bg-slate-700/50 border-slate-600'}`}
            >
              <BarChart3 className="h-4 w-4 mr-1" />
              Data Analysis
            </Button>
            
            {/* Model Name Badge */}
            <Badge variant="outline" className="text-slate-400 border-slate-600 bg-slate-800/50">
              {dataAnalysisMode 
                ? selectedAnalysisModel
                : chainMode 
                  ? `${selectedChainModels[0] || ''}${selectedChainModels && selectedChainModels[1] ? '/' : ''}${selectedChainModels[1] || ''}` 
                  : selectedModel
              }
            </Badge>
            {/* Profile Dropdown */}
            <DropdownMenu open={dropdownOpen} onOpenChange={setDropdownOpen}>
              <DropdownMenuTrigger asChild>
                <Button
                  className="bg-gradient-to-r from-[#181C5A] to-[#B983FD] text-white font-bold rounded-[12px] px-3 h-8 text-sm shadow-md hover:brightness-110 transition-all duration-200 flex items-center ml-2"
                >
                  <User className="h-4 w-4" />
                  Profile
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-slate-900 border-slate-700 text-slate-200">
                <DropdownMenuItem onClick={() => alert(`Username: ${getUserInfo()?.sub}\nRole: ${getUserInfo()?.role}`)}>
                  View Profile
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleLogout()} className="text-red-400">
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 min-h-0 flex flex-col">
        <ScrollArea className="flex-1 min-h-0 px-4 py-2 overflow-y-auto" onScroll={handleScroll}>
          {messages.length === 0 ? (
            <div className="flex flex-1 items-center justify-center h-full">
              <div className="flex flex-col items-center text-center">
                <div className="mb-6 flex items-center justify-center">
                  {/* NemHem AI Bot Logo */}
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 48,
                    height: 48,
                    borderRadius: 12,
                    background: 'linear-gradient(90deg, #181C5A 0%, #B983FD 100%)',
                  }}>
                    <span className="text-primary-foreground font-bold text-2xl" style={{ color: 'white', fontWeight: 700, fontSize: 24 }}>N</span>
                  </span>
                </div>
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  Welcome to NemHem AI
                </h2>
                <p className="text-gray-500 mb-6">
                  {dataAnalysisMode 
                    ? "Upload a CSV file and start analyzing your data with AI-powered insights."
                    : "Start a conversation or enable chain mode to connect multiple AI models for enhanced responses."
                  }
                </p>
                {dataAnalysisMode && !csvInfo.has_csv && (
                  <Button
                    onClick={() => csvInputRef.current?.click()}
                    className="text-xs bg-slate-800/50 hover:bg-slate-700/70 text-slate-200 border-slate-600 rounded-xl"
                  >
                    <Upload className="h-4 w-4 mr-1" />
                    Upload CSV
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-8">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-4 ${message.isUser ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`flex max-w-2xl ${message.isUser ? 'justify-end' : 'justify-start'} items-start gap-2`}>
                    <div className={`relative rounded-xl px-4 py-2 pr-10 pb-4 shadow ${
                      message.isUser 
                        ? 'bg-[#A259FF] text-white'
                        : message.isError
                        ? 'bg-red-900/80 text-red-100 border border-red-700/50 backdrop-blur-sm'
                        : 'bg-[#F5F6FA] text-black border border-gray-200'
                    }`}>
                      
                      {/* Enhanced SearxNG Search Results Display */}
                      {!message.isUser && message.searchResults && (
                        <div className="mb-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg border border-blue-200 dark:border-blue-700/50 shadow-sm">
                          <div className="flex items-center gap-2 text-sm font-bold text-blue-800 dark:text-blue-200 mb-3">
                            <Link2 className="w-5 h-5" />
                            🔍 Search Sources
                          </div>
                          <div className="text-sm text-gray-700 dark:text-gray-200 whitespace-pre-wrap max-h-48 overflow-y-auto bg-white/50 dark:bg-black/20 p-3 rounded border border-blue-100 dark:border-blue-800/30">
                            {message.searchResults}
                          </div>
                        </div>
                      )}

                      {/* Data Analysis Code Display */}
                      {message.analysisCode && (
                        <div className="mb-4 p-4 bg-gray-900 rounded-lg border border-gray-600">
                          <div className="flex items-center gap-2 text-sm font-bold text-green-400 mb-3">
                            <FileText className="w-4 h-4" />
                            Generated Code
                          </div>
                          <pre className="text-green-300 text-sm overflow-x-auto">
                            <code>{message.analysisCode}</code>
                          </pre>
                          <CopyButton text={message.analysisCode} />
                        </div>
                      )}

                      {/* Data Analysis Output Display */}
                      {message.analysisOutput && (
                        <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                          <div className="flex items-center gap-2 text-sm font-bold text-blue-800 mb-3">
                            <BarChart3 className="w-4 h-4" />
                            Analysis Output
                          </div>
                          <pre className="text-blue-900 text-sm whitespace-pre-wrap">
                            {message.analysisOutput}
                          </pre>
                        </div>
                      )}

                      {/* Data Analysis Chart Display */}
                      {message.analysisChart && (
                        <div className="mb-4 p-4 bg-green-50 rounded-lg border border-green-200">
                          <div className="flex items-center gap-2 text-sm font-bold text-green-800 mb-3">
                            <BarChart3 className="w-4 h-4" />
                            Generated Visualization
                          </div>
                          <img 
                            src={`data:image/png;base64,${message.analysisChart}`} 
                            alt="Data Analysis Chart"
                            className="max-w-full h-auto rounded border"
                          />
                        </div>
                      )}

                      {/* Copy button for bot/assistant only */}
                      {!message.isUser && (
                        <div className="absolute bottom-2 right-2 z-10">
                          <CopyButton text={message.content} />
                        </div>
                      )}
                      
                      {/* Error badge */}
                      {message.isError && (
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="text-xs bg-red-700 text-red-100 border-red-600">
                              Error
                            </Badge>
                          </div>
                        </div>
                      )}

                      {/* Model badge */}
                      {!message.isUser && !message.isError && message.model && (
                        <div className="mb-2">
                          <Badge variant="secondary" className="text-xs">
                            {message.model}
                          </Badge>
                          {message.isDataAnalysis && (
                            <Badge variant="secondary" className="text-xs ml-2 bg-green-100 text-green-800">
                              Data Analysis
                            </Badge>
                          )}
                        </div>
                      )}

                      {/* Show uploaded file names */}
                      {message.uploadedFiles && message.uploadedFiles.length > 0 && (
                        <div className="mb-2 flex flex-wrap gap-1">
                          {message.uploadedFiles.map((file, index) => (
                            <Badge key={index} variant="outline" className="text-xs">
                              📄 {file.name}
                            </Badge>
                          ))}
                        </div>
                      )}
                      
                      {/* Enhanced Markdown Message Content */}
                      <div className={`prose max-w-none ${message.isError ? 'text-red-100' : (!message.isUser ? 'text-black' : 'text-slate-100')}`}>
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          rehypePlugins={[rehypeHighlight]}
                          components={{
                            img: ({node, ...props}: any) => {
                              const src = props.src?.startsWith('http') 
                                ? props.src 
                                : `${API_BASE_URL}${props.src}`;
                              
                              return <img {...props} src={src} alt={props.alt} style={{maxWidth: '100%', height: 'auto', borderRadius: '8px'}} />;
                            },
                            code({node, inline, className, children, ...props}: any) {
                              return !inline ? (
                                <div className="relative group my-2">
                                  <pre className={`rounded-lg ${message.isError ? 'bg-red-900/80 border border-red-700/60' : 'bg-slate-900/80 border border-slate-700/60'} p-4 overflow-x-auto text-sm font-mono ${className || ''}`}
                                    {...props}
                                  >
                                    <code>{children}</code>
                                  </pre>
                                  <CopyButton
                                    text={String(children)}
                                  />
                                </div>
                              ) : (
                                <code className={`${message.isError ? 'bg-red-800/70 text-red-200' : 'bg-slate-800/70 text-emerald-300'} px-1.5 py-0.5 rounded font-mono text-sm ${className || ''}`}>{children}</code>
                              );
                            },
                            a({node, ...props}: any) {
                              return (
                                <a 
                                  {...props} 
                                  target="_blank" 
                                  rel="noopener noreferrer" 
                                  className={
                                    (message.model === 'YouTube' || message.model === 'Reddit' || message.model === 'Academic' || message.model === 'Crypto') 
                                    ? 'text-blue-400 underline hover:text-blue-300 transition-colors cursor-pointer' 
                                    : 'text-blue-600 hover:text-blue-800 underline transition-colors cursor-pointer'
                                  } 
                                />
                              );
                            }
                          }}
                        >
                          {message.isUser ? message.content : message.content}
                        </ReactMarkdown>
                      </div>

                      {/* Chain responses */}
                      {message.chainResponses && (
                        <div className="mt-3 space-y-3">
                          {message.chainResponses.map((response, index) => (
                            <div key={index} className="border-l-2 border-gray-300 pl-3">
                              <Badge variant="outline" className="text-xs mb-1">
                                {response.model}
                              </Badge>
                              <div className="text-sm">
                                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                                  {response.response}
                                </ReactMarkdown>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Show if message is part of a chain */}
                      {message.isChained && (
                        <div className="mt-2">
                          <Badge variant="outline" className="text-xs">
                            Chain Response
                          </Badge>
                        </div>
                      )}
                      
                      {/* Timestamp */}
                      <div className="text-xs text-gray-500 mt-2">
                        {message.timestamp.toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Loading indicator */}
              {isLoading && (
                <div className="flex gap-4 justify-start">
                  <div className="flex gap-4 max-w-4xl">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center shadow-lg" style={{ background: '#A259FF' }}>
                      <Bot className="h-5 w-5 text-white" />
                    </div>
                    <div className="bg-[#44485A] rounded-2xl px-6 py-4 border border-gray-200 shadow-lg">
                      <div className="flex space-x-2">
                        <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#A259FF' }}></div>
                        <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#A259FF', animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: '#A259FF', animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </ScrollArea>
      </div>
      
      {/* Input Area */}
      <div className="bg-[#E5E7EB] p-6 shadow-[0_-2px_16px_0_rgba(24,28,90,0.04)] border-t border-gray-200 rounded-b-[20px]">
        <div className="max-w-4xl mx-auto space-y-4">
          
          {/* CSV Info Display for Data Analysis Mode */}
          {dataAnalysisMode && csvInfo.has_csv && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-medium text-green-800">
                    Dataset: {csvInfo.filename}
                  </span>
                </div>
                <div className="text-sm text-green-600">
                  {csvInfo.shape?.[0]} rows × {csvInfo.shape?.[1]} columns
                </div>
              </div>
              {csvInfo.columns && (
                <div className="mt-2 text-xs text-green-700">
                  <strong>Columns:</strong> {csvInfo.columns.join(', ')}
                </div>
              )}
            </div>
          )}

          {/* Enhanced File Upload Area */}
          {(uploadedFiles.length > 0 || uploadedFileInfos.length > 0) && !dataAnalysisMode && (
            <div className="flex flex-wrap gap-2">
              {/* Current upload queue */}
              {uploadedFiles.map((file, index) => (
                <div key={index} className="flex items-center gap-2 bg-slate-800/50 rounded-lg px-3 py-2 border border-slate-600">
                  {fileTypeIcon(file.name)}
                  <span className="text-sm text-slate-300 truncate max-w-32">{file.name}</span>
                  <button
                    onClick={() => setUploadedFiles(prev => prev.filter(f => f.name !== file.name))}
                    className="text-slate-400 hover:text-red-400 ml-1"
                  >
                    ×
                  </button>
                </div>
              ))}
              
              {/* Previously uploaded files */}
              {uploadedFileInfos.map((file, index) => (
                <div key={`uploaded-${index}`} className="flex items-center gap-2 bg-green-100 rounded-lg px-3 py-2 border border-green-300">
                  {fileTypeIcon(file.filename)}
                  <span className="text-sm text-green-700 truncate max-w-32">{file.filename}</span>
                  <span className="text-xs text-green-500 ml-auto">
                    {new Date(file.uploaded_at).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          )}
          
          {/* Controls */}
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-6">
              {!dataAnalysisMode && (
                <>
                  {/* Chain Mode Toggle */}
                  <div className="flex items-center gap-3">
                    <Switch
                      id="chain-mode"
                      checked={chainMode}
                      onCheckedChange={setChainMode}
                      className="data-[state=unchecked]:bg-gray-200 data-[state=checked]:bg-[#B983FD] data-[state=unchecked]:border-gray-300 data-[state=checked]:border-[#B983FD]"
                    />
                    <Label htmlFor="chain-mode" className="text-sm font-medium cursor-pointer" style={{ color: '#181C5A' }}>
                      Chain Mode
                    </Label>
                  </div>
                  
                  {/* Chain Mode Warning */}
                  {chainMode && (!selectedChainModels[0] || !selectedChainModels[1]) && (
                    <Alert className="bg-amber-900/20 border-amber-600/50 text-amber-300">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>
                        Please add at least one model to the chain.
                      </AlertDescription>
                    </Alert>
                  )}
                  
                  {/* Model Selector */}
                  {!chainMode ? (
                    <ModelSelector
                      selectedModel={selectedModel}
                      onModelChange={(model) => setSelectedModel(model)}
                    />
                  ) : (
                    <DualChainModelSelector selectedModels={selectedChainModels} onModelsChange={setSelectedChainModels} />
                  )}
                </>
              )}

              {/* Data Analysis Model Selector */}
              {dataAnalysisMode && (
                <div className="flex items-center gap-3">
                  <Label className="text-sm font-medium" style={{ color: '#181C5A' }}>
                    Analysis Model:
                  </Label>
                  <Select value={selectedAnalysisModel} onValueChange={setSelectedAnalysisModel}>
                    <SelectTrigger className="w-[250px] bg-white border-[#A259FF] text-black">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-white border-[#A259FF]">
                      <SelectItem value="deepseek-coder-v2:latest" className="text-black">
                        DeepSeek Coder V2 (Recommended)
                      </SelectItem>
                      <SelectItem value="llama3.1:latest" className="text-black">
                        Llama 3.1
                      </SelectItem>
                      <SelectItem value="mistral:latest" className="text-black">
                        Mistral
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
            
            <div className="flex items-center gap-3">
              {/* CSV Upload Button for Data Analysis Mode */}
              {dataAnalysisMode && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => csvInputRef.current?.click()}
                  className="text-xs bg-slate-800/50 hover:bg-slate-700/70 text-slate-200 border-slate-600 rounded-xl"
                >
                  <Upload className="h-4 w-4 mr-1" />
                  {csvInfo.has_csv ? 'Replace CSV' : 'Upload CSV'}
                </Button>
              )}
              
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={startListening}
                className={`h-8 w-8 p-0 text-slate-400 hover:text-[#B983FD] hover:bg-[#181C5A]/10 ${listening ? 'bg-[#B983FD]/20 text-[#181C5A]' : ''}`}
                aria-label={listening ? "Stop voice input" : "Start voice input"}
              >
                <Mic className="h-4 w-4" />
              </Button>
              <Button
                onClick={handleSend}
                disabled={
                  (!input.trim() && uploadedFiles.length === 0) || 
                  isLoading || 
                  (chainMode && (!selectedChainModels[0] || !selectedChainModels[1])) ||
                  (dataAnalysisMode && !csvInfo.has_csv)
                }
                className="bg-gradient-to-r from-[#181C5A] to-[#B983FD] text-white border-0 h-10 w-10 rounded-[12px] shadow-md hover:brightness-110 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center ml-2"
              >
                <Send className="h-5 w-5" />
              </Button>
            </div>
          </div>
          
          {/* Input */}
          <div className="flex gap-3 items-center">
            <div className="flex-1 relative flex items-center">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={dataAnalysisMode 
                  ? csvInfo.has_csv 
                    ? "Ask questions about your dataset..." 
                    : "Please upload a CSV file first"
                  : "Type your message..."
                }
                className="min-h-[48px] max-h-40 pr-12 resize-none text-base bg-white border border-gray-300 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#A259FF] focus-visible:outline-none rounded-2xl shadow-sm text-gray-900"
                disabled={isLoading || (dataAnalysisMode && !csvInfo.has_csv)}
                rows={1}
              />
              <div className="absolute right-2 flex items-center gap-1">
                {!dataAnalysisMode && (
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="p-1.5 rounded-full hover:bg-slate-200/50 text-slate-500 hover:text-slate-700 transition-colors"
                    disabled={isLoading}
                  >
                    <Paperclip className="h-5 w-5" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={startListening}
                  className="p-1.5 rounded-full hover:bg-slate-200/50 text-slate-500 hover:text-slate-700 transition-colors"
                  disabled={isLoading}
                >
                  <Mic className="h-5 w-5" />
                </button>
              </div>
            </div>
            
            <div className="flex-shrink-0">
              <Button 
                onClick={handleSend} 
                disabled={isLoading || (!input.trim() && uploadedFiles.length === 0) || (dataAnalysisMode && !csvInfo.has_csv)}
                className="bg-gradient-to-r from-[#6C47FF] to-[#A259FF] hover:from-[#5A3BD9] hover:to-[#8C4DFF] text-white font-medium py-2 px-6 rounded-2xl shadow-lg transition-all duration-200 transform hover:scale-105"
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>{dataAnalysisMode ? 'Analyzing...' : 'Generating...'}</span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Send className="h-4 w-4" />
                    <span>{dataAnalysisMode ? 'Analyze' : 'Send'}</span>
                  </div>
                )}
              </Button>
            </div>
          </div>
          
          {/* Hidden file inputs */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            className="hidden"
            multiple
            accept=".pdf,.doc,.docx,.txt,.md,.csv,.xls,.xlsx"
          />
          
          <input
            type="file"
            ref={csvInputRef}
            onChange={handleCSVUpload}
            className="hidden"
            accept=".csv"
          />
        </div>
      </div>
    </div>
  );
};
