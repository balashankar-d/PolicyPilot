import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useAuth } from '../context/AuthContext';
import './Upload.css';

const API_URL = 'http://localhost:8000';

const Upload = ({ onUploadSuccess, onUploadError }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const { token, isAuthenticated } = useAuth();

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    
    if (!file) {
      return;
    }

    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      const error = 'Only PDF files are allowed';
      setUploadStatus({ type: 'error', message: error });
      onUploadError(error);
      return;
    }

    setIsUploading(true);
    setUploadStatus({ type: 'info', message: 'Uploading and processing...' });

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Use authenticated endpoint if logged in, otherwise use legacy endpoint
      const endpoint = isAuthenticated 
        ? `${API_URL}/documents/upload` 
        : `${API_URL}/upload_pdf`;
      
      const headers = {};
      if (isAuthenticated && token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
        headers
      });

      if (!response.ok) {
        let errorMessage = 'Upload failed';
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
          try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorMessage;
          } catch (jsonError) {
            console.error('Failed to parse error JSON:', jsonError);
          }
        } else {
          const errorText = await response.text();
          console.error('Non-JSON error response:', errorText);
          errorMessage = `Server error (${response.status}): ${response.statusText}`;
        }
        
        throw new Error(errorMessage);
      }

      const result = await response.json();
      
      setUploadStatus({ 
        type: 'success', 
        message: `Successfully processed ${file.name}` 
      });
      
      onUploadSuccess(result);

    } catch (error) {
      console.error('Upload error:', error);
      const errorMessage = error.message || 'Failed to upload file';
      setUploadStatus({ type: 'error', message: errorMessage });
      onUploadError(errorMessage);
    } finally {
      setIsUploading(false);
    }
  }, [onUploadSuccess, onUploadError, token, isAuthenticated]);

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isDragReject
  } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: false,
    disabled: isUploading
  });

  return (
    <div className="upload-container">
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'drag-active' : ''} ${
          isDragReject ? 'drag-reject' : ''
        } ${isUploading ? 'uploading' : ''}`}
      >
        <input {...getInputProps()} />
        
        <div className="dropzone-content">
          {isUploading ? (
            <>
              <div className="spinner"></div>
              <p>Processing PDF...</p>
            </>
          ) : isDragActive ? (
            <>
              <p>📁 Drop the PDF here...</p>
            </>
          ) : (
            <>
              <p>📄 Drag & drop a PDF file here, or click to select</p>
              <button type="button" className="upload-button">
                Choose PDF File
              </button>
            </>
          )}
        </div>
      </div>

      {uploadStatus && (
        <div className={`upload-status ${uploadStatus.type}`}>
          {uploadStatus.message}
        </div>
      )}
    </div>
  );
};

export default Upload;
