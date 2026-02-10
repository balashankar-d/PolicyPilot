import React from 'react';
import { useAuth } from '../context/AuthContext';
import './Auth.css';

const UserHeader = () => {
  const { user, logout } = useAuth();

  if (!user) return null;

  const getInitials = (name, email) => {
    if (name) {
      return name
        .split(' ')
        .map(n => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
    }
    return email[0].toUpperCase();
  };

  return (
    <div className="user-header">
      <div className="user-info">
        <div className="user-avatar">
          {getInitials(user.full_name, user.email)}
        </div>
        <div className="user-details">
          <span className="user-name">
            {user.full_name || user.email.split('@')[0]}
          </span>
          <span className="user-email">{user.email}</span>
        </div>
      </div>
      <button onClick={logout} className="logout-button">
        Logout
      </button>
    </div>
  );
};

export default UserHeader;
