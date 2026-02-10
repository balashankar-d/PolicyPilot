import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthForm from './components/AuthForm';
import UserHeader from './components/UserHeader';
import Upload from './components/Upload';
import Chat from './components/Chat';
import './App.css';

const API_URL = 'http://localhost:8000';

function MainApp() {
  const [messages, setMessages] = useState([]);
  const [isDocumentUploaded, setIsDocumentUploaded] = useState(false);
  const [systemStatus, setSystemStatus] = useState(null);
  const [userStats, setUserStats] = useState(null);
  
  const { isAuthenticated, token, loading } = useAuth();

  // Check system status on component mount
  useEffect(() => {
    checkSystemStatus();
  }, []);

  // Fetch user stats when authenticated
  useEffect(() => {
    if (isAuthenticated && token) {
      fetchUserStats();
      checkUserDocuments();
    } else {
      setUserStats(null);
    }
  }, [isAuthenticated, token]);

  const checkSystemStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/status`);
      const status = await response.json();
      setSystemStatus(status);
      // For unauthenticated users, check global document count
      if (!isAuthenticated) {
        setIsDocumentUploaded(status.documents_in_store > 0);
      }
    } catch (error) {
      console.error('Failed to check system status:', error);
    }
  };

  const fetchUserStats = async () => {
    try {
      const response = await fetch(`${API_URL}/user/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const stats = await response.json();
        setUserStats(stats);
        setIsDocumentUploaded(stats.total_documents > 0);
      }
    } catch (error) {
      console.error('Failed to fetch user stats:', error);
    }
  };

  const checkUserDocuments = async () => {
    try {
      const response = await fetch(`${API_URL}/documents`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const documents = await response.json();
        setIsDocumentUploaded(documents.length > 0);
      }
    } catch (error) {
      console.error('Failed to check user documents:', error);
    }
  };

  const handleUploadSuccess = (response) => {
    setIsDocumentUploaded(true);
    setMessages(prevMessages => [...prevMessages, {
      text: `✅ Successfully uploaded and processed document: ${response.chunks_created} chunks created`,
      sender: 'system',
      timestamp: new Date().toISOString()
    }]);
    // Refresh stats and status
    if (isAuthenticated) {
      fetchUserStats();
    }
    checkSystemStatus();
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

  // Show loading while checking authentication
  if (loading) {
    return (
      <div className="App loading-screen">
        <div className="loading-spinner-large"></div>
        <p>Loading...</p>
      </div>
    );
  }

  // Show login/signup if not authenticated
  if (!isAuthenticated) {
    return <AuthForm />;
  }

  return (
    <div className="App">
      <UserHeader />
      
      {userStats && (
        <div className="user-stats">
          <div className="stat-item">
            <span className="stat-value">{userStats.total_documents}</span>
            <span className="stat-label">Documents</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{userStats.total_conversations}</span>
            <span className="stat-label">Conversations</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{userStats.successful_conversations}</span>
            <span className="stat-label">Successful</span>
          </div>
        </div>
      )}
      
      <header className="App-header">
        <h1>📚 PolicyPilot</h1>
        <p>Upload a PDF and ask questions about its content</p>
        {systemStatus && (
          <div className="system-status">
            <span>Status: {systemStatus.status}</span>
            <span>Version: {systemStatus.version}</span>
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

function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;
