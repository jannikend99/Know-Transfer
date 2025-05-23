import React, { useState, useEffect, useMemo } from 'react';
import ProcessDetails from './ProcessDetails';
import ProcessChecklist from './ProcessChecklist';
import VisualizationRenderer from './VisualizationRenderer';
import { Card, CardHeader, CardTitle, CardContent } from '../../ui/card';
import { Network } from 'lucide-react';
// import { fetchProcessDetails } from '../../../services/api'; // Placeholder

const ProcessVisualization = ({ processId, processData, showDetailsOnly = false, showVisualizationOnly = false }) => {
  const [visualizationHtml, setVisualizationHtml] = useState('');
  const [isLoadingViz, setIsLoadingViz] = useState(false);
  const [vizError, setVizError] = useState(null);

  // This useEffect will now be responsible for fetching the HTML visualization
  // if processData.visualization_graph is not directly available or is just a trigger.
  useEffect(() => {
    if (processData && processData.id && (showVisualizationOnly || (!showDetailsOnly && !showVisualizationOnly))) {
      // Option 1: If processData directly contains the HTML for visualization_graph
      if (processData.visualization_graph) {
        setVisualizationHtml(processData.visualization_graph);
        return; // HTML is already provided
      }

      // Option 2: Fetch from the /visualize endpoint if not directly in processData
      const fetchVisualization = async () => {
        setIsLoadingViz(true);
        setVizError(null);
        try {
          const response = await fetch(`/api/processes/${processData.id}/visualize`);
          if (!response.ok) {
            throw new Error(`HTTP error fetching visualization! status: ${response.status}`);
          }
          const htmlText = await response.text();
          setVisualizationHtml(htmlText);
        } catch (err) {
          console.error("Failed to fetch visualization:", err);
          setVizError(err.message || 'Could not load visualization.');
          setVisualizationHtml('<p style="color:red;">Could not load visualization.</p>');
        } finally {
          setIsLoadingViz(false);
        }
      };
      fetchVisualization();
    }
  }, [processData, showDetailsOnly, showVisualizationOnly]); // Re-fetch/re-evaluate if processData changes

  const vizPanelStyle = {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    backgroundColor: '#f9f9f9',
    padding: 'var(--spacing-unit, 16px)',
    boxSizing: 'border-box',
    gap: 'var(--spacing-unit, 16px)'
  };

  const detailsAndChecklistContainerStyle = {
    display: 'flex',
    flexDirection: 'row',
    gap: 'var(--spacing-unit, 16px)',
    maxHeight: '50%',
    overflow: 'hidden'
  };

  const detailsContainerStyle = {
    flex: '2 1 0px',
    overflowY: 'auto',
    paddingRight: 'calc(var(--spacing-unit, 16px) / 2)',
    border: '1px solid #e0e0e0',
    borderRadius: 'var(--border-radius)',
    padding: 'var(--spacing-unit)',
    backgroundColor: '#fff'
  };

  const checklistContainerStyle = {
    flex: '1 1 0px',
    overflowY: 'auto',
    paddingLeft: 'calc(var(--spacing-unit, 16px) / 2)',
    border: '1px solid #e0e0e0',
    borderRadius: 'var(--border-radius)',
    padding: 'var(--spacing-unit)',
    backgroundColor: '#fff'
  };

  const graphContainerStyle = {
    flexGrow: 1,
    display: 'flex',
    flexDirection: 'column'
  };

  if (!processData) {
    // Should ideally not happen if ProcessPage handles its loading/error states correctly
    return <p>Waiting for process data...</p>;
  }

  // Show only details (for the details section)
  if (showDetailsOnly) {
    return (
      <div>
        <ProcessDetails processId={processData.id} processData={processData} />
      </div>
    );
  }

  // Show only visualization (for the visualization section)
  if (showVisualizationOnly) {
    return (
      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center space-x-2">
            <Network className="h-5 w-5 text-primary" />
            <span>Process Visualization</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0 pb-0">
          {isLoadingViz && (
            <div className="flex items-center justify-center h-32 p-4">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
                <p className="text-sm text-muted-foreground">Loading visualization...</p>
              </div>
            </div>
          )}
          {vizError && (
            <div className="flex items-center justify-center h-32 p-4">
              <p className="text-sm text-destructive">Error: {vizError}</p>
            </div>
          )}
          {!isLoadingViz && !vizError && (
            <div className="min-h-96">
              <VisualizationRenderer htmlContent={visualizationHtml} />
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // Default: show all sections (for backward compatibility)
  return (
    <div className="space-y-6">
      {/* Process Details Dashboard */}
      <ProcessDetails processId={processData.id} processData={processData} />
      
      {/* Visualization Section */}
      <Card className="shadow-sm mb-0">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center space-x-2">
            <Network className="h-5 w-5 text-primary" />
            <span>Process Visualization</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0 pb-0">
          {isLoadingViz && (
            <div className="flex items-center justify-center h-32 p-4">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
                <p className="text-sm text-muted-foreground">Loading visualization...</p>
              </div>
            </div>
          )}
          {vizError && (
            <div className="flex items-center justify-center h-32 p-4">
              <p className="text-sm text-destructive">Error: {vizError}</p>
            </div>
          )}
          {!isLoadingViz && !vizError && (
            <div className="min-h-96">
              <VisualizationRenderer htmlContent={visualizationHtml} />
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ProcessVisualization; 