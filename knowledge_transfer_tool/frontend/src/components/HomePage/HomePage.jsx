import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ProcessGrid from './ProcessGrid';
import { Search, BookOpen } from 'lucide-react';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";

import { Input } from "../ui/input";
import { Button } from "../ui/button";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "../ui/alert";

const HomePage = () => {
  const [processes, setProcesses] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingProcess, setIsCreatingProcess] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchProcesses = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/processes');
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setProcesses(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("Failed to fetch processes:", err);
        setError(err.message || 'Failed to fetch processes. Check API connection.');
        setProcesses([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProcesses();
  }, []);

  const handleCreateProcess = async () => {
    setIsCreatingProcess(true);
    setError(null);
    try {
      const response = await fetch('/api/processes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title: 'New Process', general_description: 'Newly created process, please update details.' }), 
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP error! status: ${response.status}`);
      }
      const newProcess = await response.json();
      navigate(`/process/${newProcess.id}`);
    } catch (err) {
      console.error("Failed to create process:", err);
      setError(err.message || 'Failed to create process.');
    } finally {
      setIsCreatingProcess(false);
    }
  };

  const handleProcessDelete = (deletedProcessId) => {
    // Remove the deleted process from the local state
    setProcesses(prevProcesses => 
      prevProcesses.filter(process => process.id !== deletedProcessId)
    );
  };

  const filteredProcesses = processes.filter(proc => {
    const searchTermLower = searchTerm.toLowerCase();
    const titleMatch = proc.title && proc.title.toLowerCase().includes(searchTermLower);
    const descriptionMatch = proc.general_description && proc.general_description.toLowerCase().includes(searchTermLower);
    const idMatch = proc.id && proc.id.toLowerCase().includes(searchTermLower);
    return titleMatch || descriptionMatch || idMatch;
  });
  
  const displayProcesses = searchTerm ? filteredProcesses : processes;

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
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 bg-primary rounded-lg">
                <BookOpen className="h-6 w-6 text-primary-foreground" />
              </div>
              <div>
                <CardTitle className="text-3xl font-bold">Know Transfer</CardTitle>
                <CardDescription>Manage and explore your business processes</CardDescription>
              </div>
            </div>
            <Button
              onClick={handleCreateProcess}
              disabled={isCreatingProcess}
              className="bg-primary hover:bg-primary/90"
            >
              {isCreatingProcess ? "Creating..." : "Create New Process"}
            </Button>
          </div>
          
          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search processes..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertTitle>Error</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </div>
        </CardHeader>

        {/* Scrollable content section */}
        <CardContent className="flex-1 overflow-hidden pt-0">
          <div className="h-full overflow-y-auto pr-2">
            {isLoading ? (
              <div className="flex justify-center items-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : (
              <div className="pb-4">
                <ProcessGrid processes={displayProcesses} onProcessDelete={handleProcessDelete} />
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default HomePage; 