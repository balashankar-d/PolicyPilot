import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import './ProfileSettings.css';

const API_URL = 'http://localhost:8000';

const ProfileSettings = ({ onClose }) => {
  const { token } = useAuth();
  const [profile, setProfile] = useState({
    name: '',
    state: '',
    occupation: '',
    income: '',
    age: '',
    category: '',
  });
  const [memories, setMemories] = useState({});
  const [newMemoryKey, setNewMemoryKey] = useState('');
  const [newMemoryValue, setNewMemoryValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [activeTab, setActiveTab] = useState('profile');

  const fetchProfile = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/profile`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setProfile({
          name: data.name || '',
          state: data.state || '',
          occupation: data.occupation || '',
          income: data.income || '',
          age: data.age ?? '',
          category: data.category || '',
        });
      }
    } catch (err) {
      console.error('Failed to load profile:', err);
    }
  }, [token]);

  const fetchMemories = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/memory`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setMemories(data.memories || {});
      }
    } catch (err) {
      console.error('Failed to load memories:', err);
    }
  }, [token]);

  useEffect(() => {
    fetchProfile();
    fetchMemories();
  }, [fetchProfile, fetchMemories]);

  const handleProfileChange = (field, value) => {
    setProfile((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    setMessage('');
    try {
      const payload = { ...profile };
      if (payload.age === '') {
        delete payload.age;
      } else {
        payload.age = parseInt(payload.age, 10) || undefined;
      }
      // Remove empty strings so the API doesn't overwrite with blanks
      Object.keys(payload).forEach((k) => {
        if (payload[k] === '' || payload[k] === undefined) delete payload[k];
      });

      const res = await fetch(`${API_URL}/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        setMessage('Profile saved ✓');
        setTimeout(() => setMessage(''), 3000);
      } else {
        const err = await res.json();
        setMessage(`Error: ${err.detail}`);
      }
    } catch (err) {
      setMessage('Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const handleAddMemory = async () => {
    if (!newMemoryKey.trim() || !newMemoryValue.trim()) return;
    try {
      const res = await fetch(`${API_URL}/memory`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ key: newMemoryKey.trim(), value: newMemoryValue.trim() }),
      });
      if (res.ok) {
        setNewMemoryKey('');
        setNewMemoryValue('');
        fetchMemories();
      }
    } catch (err) {
      console.error('Failed to add memory:', err);
    }
  };

  const handleDeleteMemory = async (key) => {
    try {
      const res = await fetch(`${API_URL}/memory/${encodeURIComponent(key)}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) fetchMemories();
    } catch (err) {
      console.error('Failed to delete memory:', err);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('Clear all memories? This cannot be undone.')) return;
    try {
      await fetch(`${API_URL}/memory`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchMemories();
    } catch (err) {
      console.error('Failed to clear memories:', err);
    }
  };

  const CATEGORY_OPTIONS = [
    '', 'Student', 'Farmer', 'Senior Citizen', 'Women', 'SC/ST',
    'OBC', 'EWS', 'Differently Abled', 'Entrepreneur', 'Government Employee', 'Other',
  ];

  return (
    <div className="profile-overlay">
      <div className="profile-panel">
        {/* Header */}
        <div className="profile-header">
          <h2>⚙️ Settings</h2>
          <button className="profile-close" onClick={onClose} title="Close">
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="profile-tabs">
          <button
            className={`profile-tab ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            👤 Profile
          </button>
          <button
            className={`profile-tab ${activeTab === 'memory' ? 'active' : ''}`}
            onClick={() => setActiveTab('memory')}
          >
            🧠 Memory
          </button>
        </div>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="profile-body">
            <p className="profile-hint">
              Your profile helps PolicyPilot personalize answers to your situation.
            </p>

            <div className="profile-grid">
              <label>
                <span>Name</span>
                <input
                  value={profile.name}
                  onChange={(e) => handleProfileChange('name', e.target.value)}
                  placeholder="Your name"
                />
              </label>
              <label>
                <span>State</span>
                <input
                  value={profile.state}
                  onChange={(e) => handleProfileChange('state', e.target.value)}
                  placeholder="e.g. Maharashtra"
                />
              </label>
              <label>
                <span>Occupation</span>
                <input
                  value={profile.occupation}
                  onChange={(e) => handleProfileChange('occupation', e.target.value)}
                  placeholder="e.g. Teacher, Farmer"
                />
              </label>
              <label>
                <span>Annual Income</span>
                <input
                  value={profile.income}
                  onChange={(e) => handleProfileChange('income', e.target.value)}
                  placeholder="e.g. ₹2.5 Lakh"
                />
              </label>
              <label>
                <span>Age</span>
                <input
                  type="number"
                  value={profile.age}
                  onChange={(e) => handleProfileChange('age', e.target.value)}
                  placeholder="e.g. 30"
                  min="1"
                  max="120"
                />
              </label>
              <label>
                <span>Category</span>
                <select
                  value={profile.category}
                  onChange={(e) => handleProfileChange('category', e.target.value)}
                >
                  {CATEGORY_OPTIONS.map((c) => (
                    <option key={c} value={c}>
                      {c || '— Select —'}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="profile-actions">
              <button
                className="profile-save"
                onClick={handleSaveProfile}
                disabled={saving}
              >
                {saving ? 'Saving…' : 'Save Profile'}
              </button>
              {message && <span className="profile-msg">{message}</span>}
            </div>
          </div>
        )}

        {/* Memory Tab */}
        {activeTab === 'memory' && (
          <div className="profile-body">
            <p className="profile-hint">
              Memories are facts PolicyPilot remembers about you across conversations.
              They are also auto-extracted from your messages.
            </p>

            {/* Existing memories */}
            <div className="memory-list">
              {Object.keys(memories).length === 0 ? (
                <p className="memory-empty">No memories stored yet.</p>
              ) : (
                Object.entries(memories).map(([key, value]) => (
                  <div className="memory-item" key={key}>
                    <div className="memory-content">
                      <span className="memory-key">{key}</span>
                      <span className="memory-value">{value}</span>
                    </div>
                    <button
                      className="memory-delete"
                      onClick={() => handleDeleteMemory(key)}
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Add new memory */}
            <div className="memory-add">
              <input
                value={newMemoryKey}
                onChange={(e) => setNewMemoryKey(e.target.value)}
                placeholder="Key (e.g. preferred_language)"
                className="memory-add-key"
              />
              <input
                value={newMemoryValue}
                onChange={(e) => setNewMemoryValue(e.target.value)}
                placeholder="Value (e.g. Hindi)"
                className="memory-add-value"
              />
              <button className="memory-add-btn" onClick={handleAddMemory}>
                + Add
              </button>
            </div>

            {Object.keys(memories).length > 0 && (
              <button className="memory-clear" onClick={handleClearAll}>
                Clear All Memories
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfileSettings;
