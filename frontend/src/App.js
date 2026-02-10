import React, { useState, useEffect } from 'react';
import Upload from './components/Upload';
import Chat from './components/Chat';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [isDocumentUploaded, setIsDocumentUploaded] = useState(false);
  const [systemStatus, setSystemStatus] = useState(null);

  // Check system status on component mount
  useEffect(() => {
    checkSystemStatus();
  }, []);

  const checkSystemStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/status');
      const status = await response.json();
      setSystemStatus(status);
      setIsDocumentUploaded(status.documents_in_store > 0);
    } catch (error) {
      console.error('Failed to check system status:', error);
    }
  };

  const handleUploadSuccess = (response) => {
    setIsDocumentUploaded(true);
    setMessages(prevMessages => [...prevMessages, {
      text: `✅ Successfully uploaded and processed document: ${response.chunks_created} chunks created`,
      sender: 'system',
      timestamp: new Date().toISOString()
    }]);
    checkSystemStatus(); // Refresh status
  };

  const handleUploadError = (error) => {
    setMessages(prevMessages => [...prevMessages, {
      text: `❌ Upload failed: ${error}`,
      sender: 'system',
      timestamp: new Date().toISOString()
    }]);
  };

  const handleNewMessage = (message) => {
    setMessages(prevMessages => [...prevMessages, message]);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>📚 RAG Chatbot</h1>
        <p>Upload a PDF and ask questions about its content</p>
        {systemStatus && (
          <div className="system-status">
            <span>Status: {systemStatus.status}</span>
            <span>Documents: {systemStatus.documents_in_store}</span>
          </div>
        )}
      </header>
      
      <main className="App-main">
        <div className="upload-section">
          <Upload 
            onUploadSuccess={handleUploadSuccess}
            onUploadError={handleUploadError}
          />
        </div>
        
        <div className="chat-section">
          <Chat 
            messages={messages}
            onNewMessage={handleNewMessage}
            isDocumentUploaded={isDocumentUploaded}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
