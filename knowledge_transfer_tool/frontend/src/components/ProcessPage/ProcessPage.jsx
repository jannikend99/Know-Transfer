import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Home, BookOpen, Edit3, Check, X, Download, FileText, Loader2 } from 'lucide-react';
import ChatInterface from './ChatInterface/ChatInterface';
import ProcessDetails from './ProcessVisualization/ProcessDetails';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "../ui/alert";

// Basic ProcessPage component
const ProcessPage = () => {
  let { processId } = useParams();
  const navigate = useNavigate();
  const [processData, setProcessData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editedTitle, setEditedTitle] = useState('');
  const [isDownloadingPDF, setIsDownloadingPDF] = useState(false);
  const [downloadMessage, setDownloadMessage] = useState('');

  const fetchProcessDetails = async () => {
    if (!processId) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/processes/${processId}`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Process not found.');
        } else {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
      }
      const data = await response.json();
      setProcessData(data);
      setEditedTitle(data.title || data.general_description?.split(' ').slice(0, 5).join(' ') || 'Untitled Process');
    } catch (err) {
      console.error(`Failed to fetch process ${processId}:`, err);
      setError(err.message || 'Failed to fetch process details.');
      setProcessData(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProcessDetails();
  }, [processId]); // Re-fetch if processId changes

  // Callback for ChatInterface to notify that process data might have been updated by an AI operation
  const handleProcessDataNeedsUpdate = () => {
    console.log("ProcessPage: Received notification to update process data. Re-fetching...");
    fetchProcessDetails(); // Re-fetch the process data
  };

  const handleGoHome = () => {
    navigate('/');
  };

  const handleSaveTitle = async () => {
    try {
      const response = await fetch(`/api/processes/${processId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title: editedTitle }),
      });
      
      if (response.ok) {
        const updatedProcess = await response.json();
        setProcessData(updatedProcess);
        setIsEditingTitle(false);
      }
    } catch (err) {
      console.error("Failed to update process title:", err);
    }
  };

  const handleCancelEdit = () => {
    setEditedTitle(processData?.title || 'Untitled Process');
    setIsEditingTitle(false);
  };

  const handleDownloadPDF = async () => {
    setIsDownloadingPDF(true);
    setDownloadMessage('');
    
    try {
      const response = await fetch(`/api/processes/${processId}/export-pdf`, {
        method: 'GET',
      });
      
      if (response.ok) {
        // Create blob from response
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        
        // Create download link
        const link = document.createElement('a');
        link.href = url;
        link.download = `${displayTitle.replace(/[^a-zA-Z0-9]/g, '_')}_Process_Documentation.pdf`;
        document.body.appendChild(link);
        link.click();
        
        // Cleanup
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        // Show success message
        setDownloadMessage('PDF downloaded successfully!');
        setTimeout(() => setDownloadMessage(''), 3000);
      } else {
        console.error('Failed to generate PDF');
        setDownloadMessage('Failed to generate PDF. Please try again.');
        setTimeout(() => setDownloadMessage(''), 5000);
      }
    } catch (err) {
      console.error('Error downloading PDF:', err);
      setDownloadMessage('Error downloading PDF. Please check your connection.');
      setTimeout(() => setDownloadMessage(''), 5000);
    } finally {
      setIsDownloadingPDF(false);
    }
  };

  // Generate a display title
  let displayTitle = 'Untitled Process';
  if (processData?.title) {
    displayTitle = processData.title;
  } else if (processData?.general_description) {
    const words = processData.general_description.split(' ');
    displayTitle = words.slice(0, 5).join(' ');
    if (words.length > 5) displayTitle += '...';
  } else if (processData?.id) {
    displayTitle = `Process ${processData.id.substring(0, 8)}`;
  }

  if (isLoading) {
    return (
      <div className="h-screen flex flex-col bg-background overflow-hidden p-6">
        <Card className="h-full flex flex-col shadow-sm">
          <CardContent className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-muted-foreground">Loading process details...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen flex flex-col bg-background overflow-hidden p-6">
        <Card className="h-full flex flex-col shadow-sm">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="flex items-center justify-center w-10 h-10 bg-primary rounded-lg">
                  <BookOpen className="h-6 w-6 text-primary-foreground" />
                </div>
                <CardTitle className="text-2xl font-bold">Process Details</CardTitle>
              </div>
              <div className="flex-shrink-0">
                <div className="flex items-center space-x-3">
                  <Button
                    onClick={handleDownloadPDF}
                    disabled={isDownloadingPDF}
                    variant="outline"
                    className="flex items-center space-x-2"
                  >
                    {isDownloadingPDF ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <FileText className="h-4 w-4" />
                    )}
                    <span>
                      {isDownloadingPDF ? 'Generating PDF...' : 'Download PDF'}
                    </span>
                  </Button>
                  <Button
                    onClick={handleGoHome}
                    variant="outline"
                    className="flex items-center space-x-2"
                  >
                    <Home className="h-4 w-4" />
                    <span>Home</span>
                  </Button>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex-1 flex items-center justify-center">
            <Alert variant="destructive" className="max-w-md">
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!processData) {
    // This case might be hit if fetch completes with no error but data is still null (e.g. API returns empty for some reason)
    return (
      <div className="h-screen flex flex-col bg-background overflow-hidden p-6">
        <Card className="h-full flex flex-col shadow-sm">
          <CardContent className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <p className="text-muted-foreground">Process data could not be loaded or found.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div 
      className="h-screen flex flex-col bg-background overflow-hidden p-6" 
      style={{ 
        overscrollBehavior: 'none',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        touchAction: 'none'
      }}
    >
      <Card className="h-full flex flex-col shadow-sm">
        {/* Header section */}
        <CardHeader className="flex-shrink-0">
          <div className="flex items-center justify-between gap-6">
            <div className="flex items-center space-x-3 flex-1 min-w-0">
              <div className="flex items-center justify-center w-10 h-10 bg-primary rounded-lg">
                <BookOpen className="h-6 w-6 text-primary-foreground" />
              </div>
              <div className="flex-1 min-w-0 mr-4">
                {isEditingTitle ? (
                  <div className="flex items-center space-x-3">
                    <Input
                      value={editedTitle}
                      onChange={(e) => setEditedTitle(e.target.value)}
                      className="text-2xl font-bold h-auto py-1 px-2 flex-1"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveTitle();
                        if (e.key === 'Escape') handleCancelEdit();
                      }}
                      autoFocus
                    />
                    <div className="flex items-center space-x-2 flex-shrink-0">
                      <Button size="sm" onClick={handleSaveTitle} className="h-8 w-8 p-0">
                        <Check className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={handleCancelEdit} className="h-8 w-8 p-0">
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center space-x-2 group">
                    <h1 className="text-2xl font-bold">{displayTitle}</h1>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setIsEditingTitle(true)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 p-0"
                    >
                      <Edit3 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>
            </div>
            <div className="flex-shrink-0">
              <div className="flex items-center space-x-3">
                <Button
                  onClick={handleDownloadPDF}
                  disabled={isDownloadingPDF}
                  variant="outline"
                  className="flex items-center space-x-2"
                >
                  {isDownloadingPDF ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <FileText className="h-4 w-4" />
                  )}
                  <span>
                    {isDownloadingPDF ? 'Generating PDF...' : 'Download PDF'}
                  </span>
                </Button>
                <Button
                  onClick={handleGoHome}
                  variant="outline"
                  className="flex items-center space-x-2"
                >
                  <Home className="h-4 w-4" />
                  <span>Home</span>
                </Button>
              </div>
            </div>
          </div>
        </CardHeader>

        {/* Download notification */}
        {downloadMessage && (
          <div className="mx-6 mb-2">
            <Alert className={`${downloadMessage.includes('successfully') ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
              <AlertDescription className={`${downloadMessage.includes('successfully') ? 'text-green-800' : 'text-red-800'}`}>
                {downloadMessage}
              </AlertDescription>
            </Alert>
          </div>
        )}

        {/* Content section */}
        <CardContent className="flex-1 overflow-hidden pt-0">
          <div className="h-full flex gap-6">
            {/* Chat Interface - Left Side - 1/3 width */}
            <div className="w-1/3 min-w-0 flex-shrink-0 h-full">
              <ChatInterface 
                processId={processId} 
                processData={processData} 
                onProcessDataUpdate={handleProcessDataNeedsUpdate}
              />
            </div>
            
            {/* Right Side - Process Details & Visualization - 2/3 width */}
            <div className="w-2/3 min-w-0 h-full">
              <div 
                className="h-full overflow-y-auto overflow-x-hidden" 
                style={{ 
                  overscrollBehavior: 'contain',
                  touchAction: 'pan-y',
                  scrollbarGutter: 'stable'
                }}
              >
                <div className="space-y-6 min-w-0">
                  <ProcessDetails processData={processData} />
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ProcessPage; 