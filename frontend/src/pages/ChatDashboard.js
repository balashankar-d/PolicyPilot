import React, { useState, useEffect } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Upload from '../components/Upload';
import Chat from '../components/Chat';
import ProfileSettings from '../components/ProfileSettings';
import './ChatDashboard.css';

const API_URL = 'http://localhost:8000';

const ChatDashboard = () => {
  const [messages, setMessages] = useState([]);
  const [isDocumentUploaded, setIsDocumentUploaded] = useState(false);
  const [systemStatus, setSystemStatus] = useState(null);
  const [userStats, setUserStats] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showProfile, setShowProfile] = useState(false);

  const { isAuthenticated, token, loading, user, logout } = useAuth();
  const navigate = useNavigate();

  // Check system status on mount
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
        headers: { 'Authorization': `Bearer ${token}` }
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
        headers: { 'Authorization': `Bearer ${token}` }
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
    setMessages(prev => [...prev, {
      text: `✅ Successfully uploaded and processed document: ${response.chunks_created} chunks created`,
      sender: 'system',
      timestamp: new Date().toISOString()
    }]);
    if (isAuthenticated) fetchUserStats();
    checkSystemStatus();
  };

  const handleUploadError = (error) => {
    setMessages(prev => [...prev, {
      text: `❌ Upload failed: ${error}`,
      sender: 'system',
      timestamp: new Date().toISOString()
    }]);
  };

  const handleNewMessage = (message) => {
    setMessages(prev => [...prev, message]);
  };

  const getInitials = (name, email) => {
    if (name) {
      return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    return email ? email[0].toUpperCase() : '?';
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  // Show loading
  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="dashboard-spinner"></div>
        <p>Loading your workspace...</p>
      </div>
    );
  }

  // Redirect if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  return (
    <div className="dashboard">
      {/* Top Bar */}
      <header className="dashboard-topbar">
        <div className="topbar-left">
          <button 
            className="sidebar-toggle" 
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title="Toggle sidebar"
          >
            {sidebarOpen ? '◀' : '▶'}
          </button>
          <div className="topbar-brand" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
            <span className="topbar-logo">📚</span>
            <span className="topbar-title">PolicyPilot</span>
          </div>
        </div>
        <div className="topbar-right">
          {systemStatus && (
            <div className="topbar-status">
              <span className={`status-dot ${systemStatus.status === 'healthy' ? 'online' : ''}`}></span>
              <span className="status-text">{systemStatus.status === 'healthy' ? 'System Online' : systemStatus.status}</span>
            </div>
          )}
          <div className="topbar-user">
            <div className="topbar-avatar">
              {user && getInitials(user.full_name, user.email)}
            </div>
            <div className="topbar-user-info">
              <span className="topbar-user-name">
                {user?.full_name || user?.email?.split('@')[0]}
              </span>
              <span className="topbar-user-email">{user?.email}</span>
            </div>
          </div>
          <button className="topbar-settings" onClick={() => setShowProfile(true)} title="Profile & Memory Settings">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </button>
          <button className="topbar-logout" onClick={handleLogout} title="Logout">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        </div>
      </header>

      <div className="dashboard-body">
        {/* Sidebar */}
        <aside className={`dashboard-sidebar ${sidebarOpen ? 'open' : 'collapsed'}`}>
          {/* Stats */}
          <div className="sidebar-section">
            <h4 className="sidebar-label">Your Stats</h4>
            <div className="stats-cards">
              <div className="stat-card">
                <span className="stat-card-value">{userStats?.total_documents ?? 0}</span>
                <span className="stat-card-label">Documents</span>
              </div>
              <div className="stat-card">
                <span className="stat-card-value">{userStats?.total_conversations ?? 0}</span>
                <span className="stat-card-label">Conversations</span>
              </div>
              <div className="stat-card">
                <span className="stat-card-value">{userStats?.successful_conversations ?? 0}</span>
                <span className="stat-card-label">Successful</span>
              </div>
            </div>
          </div>

          {/* Upload */}
          <div className="sidebar-section">
            <h4 className="sidebar-label">Upload Document</h4>
            <Upload 
              onUploadSuccess={handleUploadSuccess}
              onUploadError={handleUploadError}
            />
          </div>

          {/* System Info */}
          {systemStatus && (
            <div className="sidebar-section sidebar-system">
              <h4 className="sidebar-label">System</h4>
              <div className="system-info">
                <div className="system-row">
                  <span>Version</span>
                  <span>{systemStatus.version}</span>
                </div>
                <div className="system-row">
                  <span>Documents</span>
                  <span>{systemStatus.documents_in_store}</span>
                </div>
              </div>
            </div>
          )}
        </aside>

        {/* Main Chat Area */}
        <main className="dashboard-main">
          <Chat 
            messages={messages}
            onNewMessage={handleNewMessage}
            isDocumentUploaded={isDocumentUploaded}
          />
        </main>
      </div>

      {/* Profile & Memory Settings Overlay */}
      {showProfile && (
        <ProfileSettings onClose={() => setShowProfile(false)} />
      )}
    </div>
  );
};

export default ChatDashboard;
