import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './LandingPage.css';

const LandingPage = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const handleGetStarted = () => {
    if (isAuthenticated) {
      navigate('/chat');
    } else {
      navigate('/auth');
    }
  };

  return (
    <div className="landing">
      {/* Navigation */}
      <nav className="landing-nav">
        <div className="nav-brand">
          <span className="nav-logo">📚</span>
          <span className="nav-title">PolicyPilot</span>
        </div>
        <div className="nav-actions">
          {isAuthenticated ? (
            <button className="nav-btn nav-btn-primary" onClick={() => navigate('/chat')}>
              Go to Dashboard
            </button>
          ) : (
            <>
              <button className="nav-btn nav-btn-ghost" onClick={() => navigate('/auth')}>
                Log In
              </button>
              <button className="nav-btn nav-btn-primary" onClick={() => navigate('/auth')}>
                Get Started
              </button>
            </>
          )}
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <div className="hero-badge">AI-Powered Document Intelligence</div>
          <h1 className="hero-title">
            Navigate Your Policies <br />
            <span className="hero-highlight">With Confidence</span>
          </h1>
          <p className="hero-subtitle">
            Upload your PDF documents and get instant, accurate answers powered by 
            advanced RAG (Retrieval-Augmented Generation) technology. No more 
            sifting through pages — just ask and get grounded responses.
          </p>
          <div className="hero-actions">
            <button className="btn btn-primary btn-lg" onClick={handleGetStarted}>
              Start Exploring →
            </button>
            <a href="#how-it-works" className="btn btn-outline btn-lg">
              See How It Works
            </a>
          </div>
          <div className="hero-stats">
            <div className="hero-stat">
              <span className="hero-stat-value">⚡</span>
              <span className="hero-stat-label">Instant Answers</span>
            </div>
            <div className="hero-stat">
              <span className="hero-stat-value">🎯</span>
              <span className="hero-stat-label">Context-Grounded</span>
            </div>
            <div className="hero-stat">
              <span className="hero-stat-value">🔒</span>
              <span className="hero-stat-label">Secure & Private</span>
            </div>
          </div>
        </div>
        <div className="hero-visual">
          <div className="hero-mockup">
            <div className="mockup-header">
              <div className="mockup-dots">
                <span></span><span></span><span></span>
              </div>
              <span className="mockup-title">PolicyPilot Chat</span>
            </div>
            <div className="mockup-body">
              <div className="mockup-msg mockup-msg-user">
                What is the refund policy for cancelled orders?
              </div>
              <div className="mockup-msg mockup-msg-bot">
                <div className="mockup-bot-icon">🤖</div>
                <div>Based on Section 4.2 of the policy document, cancelled orders are eligible for a full refund within 14 business days...</div>
              </div>
              <div className="mockup-msg mockup-msg-user">
                Are there any exceptions?
              </div>
              <div className="mockup-msg mockup-msg-bot">
                <div className="mockup-bot-icon">🤖</div>
                <div>Yes, per Section 4.3, customized items and digital downloads are non-refundable once...</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="how-it-works" id="how-it-works">
        <div className="section-container">
          <div className="section-header">
            <span className="section-badge">How It Works</span>
            <h2 className="section-title">Three Simple Steps to Smarter Documents</h2>
            <p className="section-subtitle">
              PolicyPilot transforms your static PDFs into an interactive, intelligent knowledge base.
            </p>
          </div>
          <div className="steps-grid">
            <div className="step-card">
              <div className="step-number">01</div>
              <div className="step-icon">📄</div>
              <h3>Upload Your PDF</h3>
              <p>Drag and drop any PDF document. PolicyPilot automatically extracts, chunks, and indexes the content for intelligent retrieval.</p>
            </div>
            <div className="step-card">
              <div className="step-number">02</div>
              <div className="step-icon">💬</div>
              <h3>Ask Questions</h3>
              <p>Type your question in natural language. Our system finds the most relevant sections using semantic search across your documents.</p>
            </div>
            <div className="step-card">
              <div className="step-number">03</div>
              <div className="step-icon">✨</div>
              <h3>Get Grounded Answers</h3>
              <p>Receive accurate, context-aware answers generated by AI — strictly grounded in your documents with source citations.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="features">
        <div className="section-container">
          <div className="section-header">
            <span className="section-badge">Features</span>
            <h2 className="section-title">Built for Accuracy & Efficiency</h2>
          </div>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">🧠</div>
              <h3>RAG Architecture</h3>
              <p>Retrieval-Augmented Generation ensures every answer is backed by actual document content — minimizing hallucinations.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🔍</div>
              <h3>Semantic Search</h3>
              <p>Powered by sentence-transformers (all-MiniLM-L6-v2) for deep contextual understanding beyond simple keyword matching.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">⚡</div>
              <h3>Groq-Powered LLM</h3>
              <p>Lightning-fast inference with Mixtral-8x7B via Groq API delivers high-quality responses in milliseconds.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🗄️</div>
              <h3>ChromaDB Vector Store</h3>
              <p>Persistent vector storage with ChromaDB ensures your documents remain indexed across sessions.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🔐</div>
              <h3>Secure Authentication</h3>
              <p>JWT-based authentication with user isolation — your documents and conversations are always private.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📊</div>
              <h3>Conversation Memory</h3>
              <p>Context-aware conversations that remember previous questions for natural, flowing dialogue.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="tech-stack">
        <div className="section-container">
          <div className="section-header">
            <span className="section-badge">Tech Stack</span>
            <h2 className="section-title">Modern, Production-Ready Architecture</h2>
          </div>
          <div className="stack-grid">
            <div className="stack-category">
              <h4>Frontend</h4>
              <div className="stack-items">
                <span className="stack-chip">React 18</span>
                <span className="stack-chip">React Router</span>
                <span className="stack-chip">Axios</span>
                <span className="stack-chip">CSS3</span>
              </div>
            </div>
            <div className="stack-category">
              <h4>Backend</h4>
              <div className="stack-items">
                <span className="stack-chip">FastAPI</span>
                <span className="stack-chip">Python 3.9+</span>
                <span className="stack-chip">Uvicorn</span>
                <span className="stack-chip">SQLite</span>
              </div>
            </div>
            <div className="stack-category">
              <h4>AI / ML</h4>
              <div className="stack-items">
                <span className="stack-chip">Groq API</span>
                <span className="stack-chip">Mixtral-8x7B</span>
                <span className="stack-chip">Sentence Transformers</span>
                <span className="stack-chip">ChromaDB</span>
              </div>
            </div>
            <div className="stack-category">
              <h4>DevOps</h4>
              <div className="stack-items">
                <span className="stack-chip">Docker</span>
                <span className="stack-chip">Nginx</span>
                <span className="stack-chip">JWT Auth</span>
                <span className="stack-chip">REST API</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="section-container">
          <div className="cta-content">
            <h2>Ready to Transform Your Document Workflow?</h2>
            <p>Start asking questions and get instant, accurate answers from your policy documents.</p>
            <button className="btn btn-primary btn-lg" onClick={handleGetStarted}>
              Get Started Free →
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="section-container">
          <div className="footer-content">
            <div className="footer-brand">
              <span className="nav-logo">📚</span>
              <span className="nav-title">PolicyPilot</span>
              <p className="footer-desc">AI-powered document intelligence for smarter policy navigation.</p>
            </div>
            <div className="footer-meta">
              <p>Built with ❤️ using React, FastAPI, ChromaDB & Groq</p>
              <p className="footer-copy">&copy; {new Date().getFullYear()} PolicyPilot. All rights reserved.</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
