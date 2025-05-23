import React, { useState, useRef } from 'react';
import { Upload, FileText } from 'lucide-react';
import { Button } from "../../ui/button";

const DocumentUpload = ({ onSendDocument, disabled }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Basic validation (can be expanded)
      const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      if (allowedTypes.includes(file.type)) {
        setSelectedFile(file);
        console.log('File selected:', file.name);
        // Automatically upload when file is selected
        handleUpload(file);
      } else {
        alert('Invalid file type. Please upload PDF or DOCX only.');
        setSelectedFile(null);
        if(fileInputRef.current) fileInputRef.current.value = null;
      }
    }
  };

  const handleUpload = (file = selectedFile) => {
    if (file) {
      setIsUploading(true);
      console.log(`Processing upload of ${file.name}...`);
      // Small delay to show loading state, then send
      setTimeout(() => {
        if (onSendDocument) {
          onSendDocument({ type: 'document', content: file, name: file.name });
        } else {
          alert(`Document "${file.name}" ready for processing (simulated).`);
        }
        setSelectedFile(null);
        setIsUploading(false);
        if(fileInputRef.current) fileInputRef.current.value = null;
      }, 500);
    }
  };

  const handleButtonClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <>
      <input 
        type="file" 
        ref={fileInputRef}
        onChange={handleFileChange} 
        accept=".pdf,.docx" 
        style={{ display: 'none' }}
        disabled={disabled || isUploading}
      />
      <Button
        variant="outline"
        size="sm"
        onClick={handleButtonClick}
        disabled={disabled || isUploading}
        className="flex items-center space-x-2"
      >
        {isUploading ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
            <span>Uploading...</span>
          </>
        ) : (
          <>
            <Upload className="h-4 w-4" />
            <span>Upload Doc</span>
          </>
        )}
      </Button>
    </>
  );
};

export default DocumentUpload; 