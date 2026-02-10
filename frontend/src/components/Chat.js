import React, { useState, useRef, useEffect } from 'react';
import Message from './Message';
import './Chat.css';

const Chat = ({ messages, onNewMessage, isDocumentUploaded }) => {
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const query = inputValue.trim();
    if (!query) {
      return;
    }

    // Add user message
    const userMessage = {
      text: query,
      sender: 'user',
      timestamp: new Date().toISOString()
    };
    
    onNewMessage(userMessage);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to get response');
      }

      const result = await response.json();
      
      // Add bot response
      const botMessage = {
        text: result.answer,
        sender: 'bot',
        timestamp: new Date().toISOString(),
        sources: result.sources || [],
        success: result.success
      };
      
      onNewMessage(botMessage);

    } catch (error) {
      console.error('Query error:', error);
      
      // Add error message
      const errorMessage = {
        text: 'Sorry, I encountered an error while processing your question. Please try again.',
        sender: 'bot',
        timestamp: new Date().toISOString(),
        sources: [],
        success: false
      };
      
      onNewMessage(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h3>💬 Chat</h3>
        {!isDocumentUploaded && (
          <p className="chat-prompt">Please upload a PDF document to start chatting</p>
        )}
      </div>
      
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <p>No messages yet. Upload a document and ask a question!</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <Message key={index} message={message} />
          ))
        )}
        
        {isLoading && (
          <div className="loading-message">
            <div className="message bot-message">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <form onSubmit={handleSubmit} className="input-form">
        <div className="input-container">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              isDocumentUploaded 
                ? "Ask a question about the uploaded document..." 
                : "Please upload a document first"
            }
            disabled={!isDocumentUploaded || isLoading}
            rows={1}
            className="message-input"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || !isDocumentUploaded || isLoading}
            className="send-button"
          >
            {isLoading ? '⏳' : '➤'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default Chat;
