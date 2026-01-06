/**
 * DocumentUpload component - handles document upload, listing, and deletion for RAG.
 */
import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { DocumentInfo } from '../types';

interface DocumentUploadProps {
  userId: string;
  onUploadSuccess?: () => void;
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({ userId, onUploadSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [uploadError, setUploadError] = useState<string>('');
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(false);

  // Load documents on mount and after upload
  useEffect(() => {
    loadDocuments();
  }, [userId]);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const response = await api.listDocuments(userId);
      setDocuments(response.documents);
    } catch (error: any) {
      console.error('Failed to load documents:', error);
      // Don't show error if RAG services not available
      if (error.response?.status !== 503) {
        setUploadError('Failed to load documents');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.txt') && !file.name.endsWith('.md')) {
      setUploadError('Only .txt and .md files are supported');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setUploadError('');
    setUploadStatus('');
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setUploadError('');
    setUploadStatus('');

    try {
      const response = await api.uploadDocument(selectedFile, userId);

      setUploadStatus(
        `✓ Uploaded: ${response.filename} (${response.chunk_count} chunks, ${response.size_chars} chars)`
      );
      setSelectedFile(null);

      // Reset file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement;
      if (fileInput) fileInput.value = '';

      // Reload document list
      await loadDocuments();

      // Notify parent
      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (error: any) {
      console.error('Upload error:', error);
      setUploadError(
        error.response?.data?.detail || 'Upload failed. Please try again.'
      );
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string, filename: string) => {
    if (!confirm(`Delete "${filename}"? This will remove all ${documents.find(d => d.doc_id === docId)?.chunk_count || 0} chunks.`)) {
      return;
    }

    try {
      await api.deleteDocument(docId, userId);

      // Reload document list
      await loadDocuments();
      setUploadStatus(`✓ Deleted: ${filename}`);

      // Notify parent
      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (error: any) {
      console.error('Delete error:', error);
      setUploadError(
        error.response?.data?.detail || 'Delete failed. Please try again.'
      );
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return dateStr;
    }
  };

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>📄 Document Upload</h3>

      {/* Upload Section */}
      <div style={styles.uploadSection}>
        <input
          id="file-input"
          type="file"
          accept=".txt,.md"
          onChange={handleFileSelect}
          style={styles.fileInput}
          disabled={uploading}
        />

        {selectedFile && (
          <div style={styles.selectedFile}>
            Selected: {selectedFile.name}
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={!selectedFile || uploading}
          style={{
            ...styles.uploadButton,
            ...((!selectedFile || uploading) ? styles.uploadButtonDisabled : {}),
          }}
        >
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </div>

      {/* Status Messages */}
      {uploadStatus && (
        <div style={styles.successMessage}>{uploadStatus}</div>
      )}

      {uploadError && (
        <div style={styles.errorMessage}>{uploadError}</div>
      )}

      {/* Documents List */}
      <div style={styles.documentsSection}>
        <h4 style={styles.documentsTitle}>
          Uploaded Documents ({documents.length})
        </h4>

        {loading && (
          <div style={styles.loadingText}>Loading...</div>
        )}

        {!loading && documents.length === 0 && (
          <div style={styles.emptyText}>
            No documents uploaded yet.
            <br />
            <small>Upload .txt or .md files to add knowledge to the AI.</small>
          </div>
        )}

        {!loading && documents.length > 0 && (
          <div style={styles.documentsList}>
            {documents.map((doc) => (
              <div key={doc.doc_id} style={styles.documentItem}>
                <div style={styles.documentInfo}>
                  <div style={styles.documentName}>
                    {doc.filename}
                  </div>
                  <div style={styles.documentMeta}>
                    {doc.chunk_count} chunks · {doc.size_chars} chars
                  </div>
                  <div style={styles.documentDate}>
                    {formatDate(doc.ingested_at)}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(doc.doc_id, doc.filename)}
                  style={styles.deleteButton}
                  title="Delete document"
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    padding: '16px',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    marginBottom: '16px',
  },
  title: {
    margin: '0 0 16px 0',
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#333',
  },
  uploadSection: {
    marginBottom: '12px',
  },
  fileInput: {
    display: 'block',
    marginBottom: '8px',
    fontSize: '14px',
    width: '100%',
  },
  selectedFile: {
    fontSize: '12px',
    color: '#666',
    marginBottom: '8px',
    padding: '4px 8px',
    backgroundColor: '#e9ecef',
    borderRadius: '4px',
  },
  uploadButton: {
    padding: '8px 16px',
    backgroundColor: '#007bff',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    width: '100%',
  },
  uploadButtonDisabled: {
    backgroundColor: '#6c757d',
    cursor: 'not-allowed',
    opacity: 0.6,
  },
  successMessage: {
    padding: '8px 12px',
    backgroundColor: '#d4edda',
    color: '#155724',
    borderRadius: '4px',
    fontSize: '12px',
    marginBottom: '12px',
    border: '1px solid #c3e6cb',
  },
  errorMessage: {
    padding: '8px 12px',
    backgroundColor: '#f8d7da',
    color: '#721c24',
    borderRadius: '4px',
    fontSize: '12px',
    marginBottom: '12px',
    border: '1px solid #f5c6cb',
  },
  documentsSection: {
    marginTop: '16px',
    paddingTop: '16px',
    borderTop: '1px solid #dee2e6',
  },
  documentsTitle: {
    margin: '0 0 12px 0',
    fontSize: '14px',
    fontWeight: '600',
    color: '#495057',
  },
  loadingText: {
    fontSize: '12px',
    color: '#6c757d',
    fontStyle: 'italic',
  },
  emptyText: {
    fontSize: '12px',
    color: '#6c757d',
    fontStyle: 'italic',
    lineHeight: '1.5',
  },
  documentsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  documentItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px',
    backgroundColor: 'white',
    borderRadius: '6px',
    border: '1px solid #dee2e6',
  },
  documentInfo: {
    flex: 1,
    minWidth: 0,
  },
  documentName: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#212529',
    marginBottom: '4px',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  documentMeta: {
    fontSize: '11px',
    color: '#6c757d',
    marginBottom: '2px',
  },
  documentDate: {
    fontSize: '10px',
    color: '#adb5bd',
  },
  deleteButton: {
    padding: '4px 8px',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    fontSize: '18px',
    opacity: 0.6,
    transition: 'opacity 0.2s',
  },
};
