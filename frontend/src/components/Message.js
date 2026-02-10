import React from 'react';
import './Message.css';

const Message = ({ message }) => {
  const { text, sender, timestamp, sources, success } = message;
  
  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className={`message ${sender}-message`}>
      <div className="message-content">
        <div className="message-text">
          {text}
        </div>
        
        {sources && sources.length > 0 && (
          <div className="message-sources">
            <small>
              📄 Sources: {sources.join(', ')}
            </small>
          </div>
        )}
        
        <div className="message-timestamp">
          {formatTimestamp(timestamp)}
        </div>
      </div>
      
      <div className="message-avatar">
        {sender === 'user' ? '👤' : sender === 'bot' ? '🤖' : 'ℹ️'}
      </div>
    </div>
  );
};

export default Message;
