import React, { useState, useEffect, useRef } from 'react';
import { Send, Mic, Upload, MessageSquare } from 'lucide-react';
import ChatHistory from './ChatHistory';
import TextInput from './TextInput';
import VoiceInput from './VoiceInput';
import DocumentUpload from './DocumentUpload';

import {
  Card,
  CardContent,
} from "../../ui/card";

import { Button } from "../../ui/button";
import { Input } from "../../ui/input";

// ChatInterface now receives processData which contains the ID and other details
const ChatInterface = ({ processId: propProcessId, processData, onProcessDataUpdate }) => {
  const processId = processData?.id || propProcessId; // Prefer ID from full processData if available

  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Helper function to fetch and update chat history
  const fetchChatHistory = async () => {
    if (!processId) return;
    
    try {
      const response = await fetch(`/api/processes/${processId}/chat-history`);
      if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: 'Failed to fetch chat history, server error.'}));
        throw new Error(errData.detail || `HTTP error! status: ${response.status}`);
      }
      const history = await response.json();
      
      // Transform backend history to frontend message format
      const formattedHistory = history.map(msg => ({
        id: msg.id, // Use the UUID from backend
        text: msg.content,
        type: msg.sender_type, // 'user', 'ai', 'system'
        timestamp: new Date(msg.created_at) // Ensure it's a Date object
      }));
      
      setMessages(formattedHistory);
      return formattedHistory;
    } catch (err) {
      console.error("Error fetching chat history:", err);
      setError(`Could not load chat history: ${err.message}`);
      setMessages([{ id: `err-hist-${Date.now()}`, text: `Error: Could not load chat history. ${err.message}`, type: 'error', timestamp: new Date()}]);
      return [];
    }
  };

  // Initialize chat history and welcome message
  useEffect(() => {
    if (processId) {
      console.log(`ChatInterface mounted for processId: ${processId}. Fetching chat history.`);
      const initializeChat = async () => {
        setIsLoading(true);
        setError(null);
        
        const history = await fetchChatHistory();
        
        // If no chat history exists, send a welcome message to backend
        if (history.length === 0) {
          try {
            const welcomeResponse = await fetch(`/api/processes/${processId}/chat`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ text: "SYSTEM_WELCOME_MESSAGE" })
            });
            
            if (welcomeResponse.ok) {
              // Refresh chat history to get the saved welcome message
              await fetchChatHistory();
            } else {
              console.error("Failed to create welcome message");
            }
          } catch (err) {
            console.error("Error creating welcome message:", err);
          }
        }
        
        setIsLoading(false);
      };
      
      initializeChat();
    }
  }, [processId]);

  const handleSendMessage = async (messageData) => {
    if (!processId) {
      setError("Process ID is not available. Cannot send message.");
      return;
    }
    
    setIsSending(true);
    setError(null);

    // Show user message immediately for both text and file uploads (optimistic UI)
    let optimisticUserMessage = null;
    if (messageData.type === 'text') {
      optimisticUserMessage = {
        id: `user-optimistic-${Date.now()}`,
        text: messageData.content,
        type: 'user',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, optimisticUserMessage]);
    } else if (messageData.type === 'voice' || messageData.type === 'document') {
      optimisticUserMessage = {
        id: `user-optimistic-${Date.now()}`,
        text: `Uploaded: ${messageData.name}`,
        type: 'user',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, optimisticUserMessage]);
    }

    try {
      let response;
      let responseBody;

      if (messageData.type === 'text') {
        // Send text message to backend
        response = await fetch(`/api/processes/${processId}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: messageData.content })
        });
        
        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: "Unknown error during chat." }));
          throw new Error(errData.detail || `Chat API error! Status: ${response.status}`);
        }
        
        responseBody = await response.json();
        
        // Add AI response immediately without refreshing entire history
        const aiMessage = {
          id: `ai-${Date.now()}`,
          text: responseBody.ai_chat_response || "No response from AI.",
          type: 'ai',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMessage]);
        
        // If structured data was extracted, trigger parent update
        if (responseBody.extracted_process_data && onProcessDataUpdate) {
          onProcessDataUpdate();
        }
        
      } else if (messageData.type === 'voice' || messageData.type === 'document') {
        // Send file to backend (processing happens in background)
        const formData = new FormData();
        formData.append('file', messageData.content, messageData.name);

        response = await fetch(`/api/processes/${processId}/upload-file`, {
          method: 'POST',
          body: formData 
        });
        
        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: "Unknown error during file upload." }));
          throw new Error(errData.detail || `File upload API error! Status: ${response.status}`);
        }
        
        responseBody = await response.json();
        
        // Add AI response when processing is complete
        if (responseBody.ai_response) {
          const aiMessage = {
            id: `ai-${Date.now()}`,
            text: responseBody.ai_response,
            type: 'ai',
            timestamp: new Date()
          };
          setMessages(prev => [...prev, aiMessage]);
        }
        
        // If file upload led to process data changes, trigger parent update
        if (responseBody.extracted_process_data && onProcessDataUpdate) {
          onProcessDataUpdate();
        }
      } else {
        throw new Error('Unknown message type');
      }

    } catch (err) {
      console.error("Error in handleSendMessage:", err);
      setError(err.message);
      
      // Remove optimistic user message if there was an error
      if (optimisticUserMessage) {
        setMessages(prev => prev.filter(msg => msg.id !== optimisticUserMessage.id));
      }
      
      // Add error message locally if backend communication failed
      const errorMessage = {
        id: `error-${Date.now()}`,
        text: `Error: ${err.message || 'Could not process message.'}`,
        type: 'error',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsSending(false);
    }
  };

  const handleTextSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !isSending) {
      handleSendMessage({ type: 'text', content: message });
      setMessage('');
    }
  };

  return (
    <Card className="h-full flex flex-col shadow-sm">
      {/* Chat History */}
      <CardContent className="flex-1 overflow-hidden p-6">
        <div className="h-full flex flex-col">
          <div 
            className="flex-1 overflow-auto mb-4"
            style={{ 
              overscrollBehavior: 'contain',
              touchAction: 'pan-y'
            }}
          >
            <ChatHistory messages={messages} isTyping={isSending} />
          </div>

          {/* Input Area */}
          <div className="flex-shrink-0 space-y-3 pt-3">
            {/* Text Input with integrated controls */}
            <form onSubmit={handleTextSubmit} className="relative">
              <Input
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Type your message..."
                disabled={isSending || !processId}
                className="flex-1 pr-24"
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                <VoiceInput onSendVoice={handleSendMessage} disabled={isSending || !processId} />
                <DocumentUpload onSendDocument={handleSendMessage} disabled={isSending || !processId} />
                <Button 
                  type="submit" 
                  disabled={!message.trim() || isSending || !processId}
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </form>

            {/* Error Messages Only */}
            {error && (
              <div className="text-center">
                <p className="text-sm text-destructive">Error: {error}</p>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default ChatInterface; 