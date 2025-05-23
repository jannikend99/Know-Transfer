import React, { useState } from 'react';

const TextInput = ({ onSendMessage }) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim()) {
      if (onSendMessage) {
        onSendMessage({ type: 'text', content: message });
      } else {
        // Fallback for when onSendMessage is not provided (e.g. during isolated development)
        alert(`Message sent (simulated): ${message}`);
      }
      setMessage('');
    } else {
      alert("Please enter a message.");
    }
  };

  const formStyle = {
    display: 'flex',
    gap: '10px',
  };

  const inputStyle = {
    flexGrow: 1,
    padding: '10px',
    border: '1px solid #ccc',
    borderRadius: 'var(--border-radius, 8px)',
    fontSize: '16px',
  };

  const buttonStyle = {
    padding: '10px 15px',
    border: 'none',
    backgroundColor: 'var(--primary-color)',
    color: 'white',
    borderRadius: 'var(--border-radius, 8px)',
    cursor: 'pointer',
    fontSize: '16px',
  };

  return (
    <form onSubmit={handleSubmit} style={formStyle}>
      <input 
        type="text" 
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type your message..."
        style={inputStyle}
      />
      <button type="submit" style={buttonStyle}>Send</button>
    </form>
  );
};

export default TextInput; 