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

  // Fetch initial chat history
  useEffect(() => {
    if (processId) {
      console.log(`ChatInterface mounted for processId: ${processId}. Fetching chat history.`);
      const fetchHistory = async () => {
        setIsLoading(true);
        setError(null);
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
        } catch (err) {
          console.error("Error fetching chat history:", err);
          setError(`Could not load chat history: ${err.message}`);
          setMessages([{ id: `err-hist-${Date.now()}`, text: `Error: Could not load chat history. ${err.message}`, type: 'error', timestamp: new Date()}]);
        } finally {
          setIsLoading(false);
        }
      };
      fetchHistory();
    }
  }, [processId]);

  const handleSendMessage = async (messageData) => {
    if (!processId) {
      setError("Process ID is not available. Cannot send message.");
      setMessages(prev => [...prev, { id: `err-${Date.now()}`, text: "Error: Process ID missing.", type: 'error'}]);
      return;
    }
    setIsSending(true);
    setError(null);

    const userMessage = {
      id: `user-${Date.now()}`,
      text: messageData.type === 'text' ? messageData.content : `Uploaded ${messageData.type}: ${messageData.name || 'audio file'}`,
      type: 'user',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);

    let aiResponseMessage = { id: `ai-${Date.now()}`, type: 'ai', timestamp: new Date() };

    try {
      let response;
      let responseBody;

      if (messageData.type === 'text') {
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
        aiResponseMessage.text = responseBody.ai_chat_response || "No direct chat response.";
        // If structured data was extracted, mention it or use it.
        if (responseBody.extracted_process_data) {
          aiResponseMessage.text += `\n(AI also extracted some process data from your message.)`;
          // Trigger update in parent if data was extracted and potentially saved/updated by backend
          if (onProcessDataUpdate) {
             // Assuming backend might have updated the process, parent should re-fetch or merge
             onProcessDataUpdate(); 
          }
        }
      } else if (messageData.type === 'voice' || messageData.type === 'document') {
        const formData = new FormData();
        formData.append('file', messageData.content, messageData.name); // content is Blob or File

        response = await fetch(`/api/processes/${processId}/upload-file`, {
          method: 'POST',
          body: formData 
        });
        if (!response.ok) {
            const errData = await response.json().catch(() => ({ detail: "Unknown error during file upload." }));
            throw new Error(errData.detail || `File upload API error! Status: ${response.status}`);
        }
        responseBody = await response.json();
        aiResponseMessage.text = `File processed: ${responseBody.filename}.`;
        if(responseBody.transcript) aiResponseMessage.text += `\nTranscript: ${responseBody.transcript.substring(0,100)}...`;
        if(responseBody.extracted_text_snippet) aiResponseMessage.text += `\nExtracted Text: ${responseBody.extracted_text_snippet}`; 
        if(responseBody.extracted_process_data) aiResponseMessage.text += `\n(AI also extracted process data from the file.)`;
        if(responseBody.vector_store_status) aiResponseMessage.text += `\n(${responseBody.vector_store_status})`;
        
        // If file upload led to process data changes, trigger parent update
        if (responseBody.extracted_process_data && onProcessDataUpdate) {
            onProcessDataUpdate();
        }
      } else {
        throw new Error('Unknown message type');
      }
      setMessages(prev => [...prev, aiResponseMessage]);

    } catch (err) {
      console.error("Error in handleSendMessage:", err);
      setError(err.message);
      setMessages(prev => [...prev, { ...aiResponseMessage, text: `Error: ${err.message || 'Could not get AI response.'}`, type: 'error'}]);
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