import React from 'react';

const ChatHistory = ({ messages = [] }) => {
  const historyStyle = {
    flexGrow: 1,
    overflowY: 'auto',
    padding: '10px',
    border: '1px solid #f0f0f0',
    borderRadius: 'var(--border-radius, 8px)',
    marginBottom: 'var(--spacing-unit, 16px)',
    minHeight: '200px', // Ensure it takes some space
    backgroundColor: '#f9f9f9'
  };

  const messageStyle = (isUser) => ({
    textAlign: isUser ? 'right' : 'left',
    marginBottom: '10px',
    padding: '8px 12px',
    borderRadius: '15px',
    maxWidth: '70%',
    wordWrap: 'break-word',
    backgroundColor: isUser ? 'var(--primary-color)' : '#e9ecef',
    color: isUser ? 'white' : '#333',
    marginLeft: isUser ? 'auto' : '0',
    marginRight: isUser ? '0' : 'auto',
  });

  const sampleMessages = [
    { id: '1', text: 'Hello! How can I define the new onboarding process?', type: 'user' },
    { id: '2', text: 'Sure, I can help with that. What are the main steps involved?', type: 'ai' },
    { id: '3', text: 'First, HR needs to send the offer letter.', type: 'user' },
  ];

  const displayMessages = messages.length > 0 ? messages : sampleMessages;

  return (
    <div style={historyStyle}>
      {displayMessages.map((msg, index) => (
        <div key={msg.id || index} style={messageStyle(msg.type === 'user')}>
          {msg.text}
        </div>
      ))}
      {/* Add a ref here to scroll to bottom for new messages */}
    </div>
  );
};

export default ChatHistory; 