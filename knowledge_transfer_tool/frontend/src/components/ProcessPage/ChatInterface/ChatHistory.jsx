import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';

const ChatHistory = ({ messages = [], isTyping = false }) => {
  const messagesEndRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const [isScrolling, setIsScrolling] = useState(false);
  const scrollTimeoutRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "auto" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    const handleScroll = () => {
      if (scrollContainerRef.current) {
        setIsScrolling(true);
        
        // Clear existing timeout
        if (scrollTimeoutRef.current) {
          clearTimeout(scrollTimeoutRef.current);
        }
        
        // Hide scrollbar after 1 second of no scrolling
        scrollTimeoutRef.current = setTimeout(() => {
          setIsScrolling(false);
        }, 1000);
      }
    };

    const scrollContainer = scrollContainerRef.current;
    if (scrollContainer) {
      scrollContainer.addEventListener('scroll', handleScroll);
      
      return () => {
        scrollContainer.removeEventListener('scroll', handleScroll);
        if (scrollTimeoutRef.current) {
          clearTimeout(scrollTimeoutRef.current);
        }
      };
    }
  }, []);

  const historyStyle = {
    flexGrow: 1,
    overflowY: 'auto',
    padding: '10px',
    minHeight: '200px', // Ensure it takes some space
  };

  const messageStyle = (isUser) => ({
    display: 'flex',
    justifyContent: isUser ? 'flex-end' : 'flex-start',
    marginBottom: '10px',
  });

  const messageBubbleStyle = (isUser, isRecording = false, isProcessing = false) => ({
    padding: '8px 12px',
    borderRadius: '15px',
    maxWidth: '70%',
    minWidth: 'auto',
    wordWrap: 'break-word',
    backgroundColor: isRecording ? '#ff6b6b' : (isProcessing ? '#ffd43b' : (isUser ? 'var(--primary-color)' : '#e9ecef')),
    color: isRecording || isProcessing ? 'white' : (isUser ? 'white' : '#333'),
    display: 'inline-block',
    opacity: isProcessing ? 0.8 : 1,
  });

  const typingIndicatorStyle = {
    display: 'flex',
    justifyContent: 'flex-start',
    marginBottom: '10px',
  };

  const typingBubbleStyle = {
    padding: '8px 12px',
    borderRadius: '15px',
    backgroundColor: '#e9ecef',
    color: '#333',
    display: 'flex',
    alignItems: 'center',
    height: '40px'
  };

  const sampleMessages = [
    { id: '1', text: 'Hello! How can I define the new onboarding process?', type: 'user' },
    { id: '2', text: 'Sure, I can help with that. What are the main steps involved?', type: 'ai' },
    { id: '3', text: 'First, HR needs to send the offer letter.', type: 'user' },
  ];

  const displayMessages = messages.length > 0 ? messages : sampleMessages;

  return (
    <div 
      ref={scrollContainerRef}
      style={historyStyle} 
      className={`chat-scroll-container ${isScrolling ? 'scrolling' : ''}`}
    >
      {displayMessages.map((msg, index) => (
        <div key={msg.id || index} style={messageStyle(msg.type === 'user')}>
          <div style={messageBubbleStyle(msg.type === 'user', msg.isRecording, msg.isProcessing)}>
            {msg.isRecording && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div className="recording-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <span>{msg.text}</span>
              </div>
            )}
            {msg.isProcessing && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div className="processing-spinner"></div>
                <span>{msg.text}</span>
              </div>
            )}
            {!msg.isRecording && !msg.isProcessing && (
              <ReactMarkdown 
                className="chat-message"
                components={{
                  // Customize markdown rendering for chat bubbles
                  p: ({ children }) => <div style={{ margin: 0 }}>{children}</div>,
                  ul: ({ children }) => <ul style={{ margin: '0', paddingLeft: '16px' }}>{children}</ul>,
                  ol: ({ children }) => <ol style={{ margin: '0', paddingLeft: '16px' }}>{children}</ol>,
                  code: ({ children }) => <code style={{ backgroundColor: 'rgba(0,0,0,0.1)', padding: '2px 4px', borderRadius: '4px' }}>{children}</code>,
                  pre: ({ children }) => <pre style={{ backgroundColor: 'rgba(0,0,0,0.1)', padding: '8px', borderRadius: '4px', margin: '4px 0', overflow: 'auto' }}>{children}</pre>,
                }}
              >
                {msg.text}
              </ReactMarkdown>
            )}
          </div>
        </div>
      ))}
      
      {/* Typing indicator */}
      {isTyping && (
        <div style={typingIndicatorStyle}>
          <div style={typingBubbleStyle}>
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      )}
      
      {/* Invisible element to scroll to */}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatHistory; 