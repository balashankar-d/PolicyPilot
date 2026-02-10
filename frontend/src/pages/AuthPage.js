import React from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AuthForm from '../components/AuthForm';
import './AuthPage.css';

const AuthPage = () => {
  const navigate = useNavigate();
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="auth-page-loading">
        <div className="auth-spinner"></div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/chat" replace />;
  }

  return (
    <div className="auth-page">
      {/* Left Panel - Branding */}
      <div className="auth-page-left">
        <button className="auth-back-btn" onClick={() => navigate('/')}>
          ← Back to Home
        </button>
        <div className="auth-page-branding">
          <div className="auth-brand-icon">📚</div>
          <h1>PolicyPilot</h1>
          <p className="auth-brand-tagline">Your intelligent document assistant powered by AI</p>
          
          <div className="auth-brand-features">
            <div className="auth-brand-feature">
              <span className="auth-feature-icon">📄</span>
              <div>
                <strong>Upload & Index</strong>
                <p>Drag and drop any PDF to get started</p>
              </div>
            </div>
            <div className="auth-brand-feature">
              <span className="auth-feature-icon">💬</span>
              <div>
                <strong>Ask Anything</strong>
                <p>Get instant answers from your documents</p>
              </div>
            </div>
            <div className="auth-brand-feature">
              <span className="auth-feature-icon">🔒</span>
              <div>
                <strong>Secure & Private</strong>
                <p>Your data stays safe with JWT authentication</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Form */}
      <div className="auth-page-right">
        <AuthForm />
      </div>
    </div>
  );
};

export default AuthPage;
