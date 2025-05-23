import React from 'react';
import { 
  FileText, 
  Target, 
  ArrowDown, 
  ArrowLeft, 
  ArrowRight,
  TrendingUp, 
  Users, 
  AlertTriangle,
  CheckCircle,
  Circle,
  Layers,
  BarChart3,
  Zap,
  Network,
  ListTodo
} from 'lucide-react';

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../ui/card";

import { Badge } from "../../ui/badge";
import VisualizationRenderer from './VisualizationRenderer';

// This component will display process fields.
// Editing functionality will be added later and will involve lifting state.
const ProcessDetails = ({ processData }) => {
  const [visualizationHtml, setVisualizationHtml] = React.useState('');
  const [isLoadingViz, setIsLoadingViz] = React.useState(false);
  const [vizError, setVizError] = React.useState(null);

  // Fetch visualization data
  React.useEffect(() => {
    if (processData && processData.id) {
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
  }, [processData]); // Re-fetch if processData changes

  // Calculate completion status
  const getProcessCompletion = () => {
    if (!processData) return { completed: 0, total: 0, percentage: 0, missing: [] };

    const categories = [
      { key: 'general_description', name: 'General Description', check: (data) => data.general_description && data.general_description.trim() },
      { key: 'scope', name: 'Scope', check: (data) => data.scope && data.scope.trim() },
      { key: 'process_steps', name: 'Process Steps', check: (data) => Array.isArray(data.process_steps) && data.process_steps.length > 0 },
      { key: 'inputs', name: 'Inputs', check: (data) => Array.isArray(data.inputs) && data.inputs.length > 0 },
      { key: 'outputs', name: 'Outputs', check: (data) => Array.isArray(data.outputs) && data.outputs.length > 0 },
      { key: 'kpis', name: 'Key Performance Indicators', check: (data) => Array.isArray(data.kpis) && data.kpis.length > 0 },
      { key: 'roles_responsibilities', name: 'Roles & Responsibilities', check: (data) => Array.isArray(data.roles_responsibilities) && data.roles_responsibilities.length > 0 },
      { key: 'exceptions_special_cases', name: 'Exceptions & Special Cases', check: (data) => Array.isArray(data.exceptions_special_cases) && data.exceptions_special_cases.length > 0 }
    ];

    const completed = categories.filter(cat => cat.check(processData)).length;
    const missing = categories.filter(cat => !cat.check(processData));
    const percentage = Math.round((completed / categories.length) * 100);

    return { completed, total: categories.length, percentage, missing };
  };

  const completion = getProcessCompletion();

  // processData is now directly from props, assumed to be populated by the parent.

  if (!processData) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>No process details available.</p>
      </div>
    );
  }

  const renderMetricCard = (title, value, icon, color = "default") => (
    <Card className="h-full">
      <CardContent className="p-4">
        <div className="flex items-center space-x-3">
          <div className={`flex items-center justify-center w-10 h-10 rounded-lg bg-${color === 'default' ? 'muted' : color}/10`}>
            {React.createElement(icon, { 
              className: `h-5 w-5 text-${color === 'default' ? 'muted-foreground' : color}` 
            })}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-lg font-semibold truncate">{value || 'Not specified'}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  const renderKPIsCard = () => {
    const kpis = processData.kpis;
    
    return (
      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center space-x-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            <span>Key Performance Indicators</span>
            {Array.isArray(kpis) && kpis.length > 0 && (
              <Badge variant="secondary" className="ml-auto">
                {kpis.length}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          {Array.isArray(kpis) && kpis.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {kpis.map((kpi, index) => (
                <div key={index} className="flex items-center space-x-3 p-3 bg-muted/30 rounded-lg border">
                  <div className="flex items-center justify-center w-8 h-8 bg-primary/10 rounded-full">
                    <TrendingUp className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{kpi || 'N/A'}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center space-x-2 text-muted-foreground">
              <Circle className="h-4 w-4" />
              <span className="text-sm">No KPIs defined</span>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderSection = (title, items, icon, emptyMessage = "None specified") => (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center space-x-2">
          {React.createElement(icon, { className: "h-5 w-5 text-primary" })}
          <span>{title}</span>
          {Array.isArray(items) && items.length > 0 && (
            <Badge variant="secondary" className="ml-auto">
              {items.length}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        {Array.isArray(items) && items.length > 0 ? (
          <div className="space-y-2">
            {items.map((item, index) => (
              <div key={index} className="flex items-start space-x-2">
                <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                <span className="text-sm">{item || 'N/A'}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center space-x-2 text-muted-foreground">
            <Circle className="h-4 w-4" />
            <span className="text-sm">{emptyMessage}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );

  const renderProcessSteps = () => {
    const steps = processData.process_steps;
    
    return (
      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center space-x-2">
            <Layers className="h-5 w-5 text-primary" />
            <span>Process Steps</span>
            {Array.isArray(steps) && steps.length > 0 && (
              <Badge variant="secondary" className="ml-auto">
                {steps.length} steps
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          {Array.isArray(steps) && steps.length > 0 ? (
            <div className="space-y-0">
              {steps.map((step, index) => (
                <div key={index}>
                  <div className="flex items-start space-x-3">
                    <div className="flex flex-col items-center">
                      <div className="flex items-center justify-center w-6 h-6 bg-primary text-primary-foreground rounded-full text-xs font-semibold flex-shrink-0">
                        {index + 1}
                      </div>
                      {index < steps.length - 1 && (
                        <div className="flex items-center justify-center w-6 h-8">
                          <ArrowDown className="h-4 w-4 text-muted-foreground" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1 pb-6">
                      <p className="text-sm">{step}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center space-x-2 text-muted-foreground">
              <Circle className="h-4 w-4" />
              <span className="text-sm">No steps defined yet</span>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderProgressTracker = () => (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center space-x-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          <span>Documentation Progress</span>
          {completion.missing.length > 0 && (
            <Badge variant="destructive" className="ml-auto">
              {completion.missing.length} missing
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="flex items-center space-x-3 mb-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              <div className="flex-1 bg-muted rounded-full h-2">
                <div 
                  className="bg-primary h-2 rounded-full transition-all duration-300" 
                  style={{ width: `${completion.percentage}%` }}
                ></div>
              </div>
              <span className="text-sm font-semibold">{completion.percentage}%</span>
            </div>
            <p className="text-xs text-muted-foreground">
              {completion.completed} of {completion.total} sections completed
            </p>
          </div>
        </div>

        {/* Missing Documentation Items */}
        {completion.missing.length > 0 ? (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground">Missing Documentation:</h4>
            {completion.missing.map((item, index) => (
              <div key={index} className="flex items-center space-x-2 p-2 bg-muted/30 rounded-lg border border-dashed">
                <Circle className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                <span className="text-xs text-muted-foreground">{item.name}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center space-x-2 text-green-600">
            <CheckCircle className="h-4 w-4" />
            <span className="text-sm font-medium">All documentation sections completed!</span>
          </div>
        )}
      </CardContent>
    </Card>
  );

  const renderMissingItemsChecklist = () => (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center space-x-2">
          <ListTodo className="h-5 w-5 text-primary" />
          <span>Missing Documentation</span>
          {completion.missing.length > 0 && (
            <Badge variant="destructive" className="ml-auto">
              {completion.missing.length} missing
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        {completion.missing.length > 0 ? (
          <div className="space-y-2">
            {completion.missing.map((item, index) => (
              <div key={index} className="flex items-center space-x-2 p-2 bg-muted/30 rounded-lg border border-dashed">
                <Circle className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                <span className="text-sm text-muted-foreground">{item.name}</span>
              </div>
            ))}
            <div className="mt-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-xs text-blue-700">
                💡 <strong>Tip:</strong> Use the AI Assistant to help complete these sections by asking specific questions about your process.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center space-x-2 text-green-600">
            <CheckCircle className="h-4 w-4" />
            <span className="text-sm font-medium">All documentation sections completed!</span>
          </div>
        )}
      </CardContent>
    </Card>
  );

  const renderVisualizationCard = () => (
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
            <VisualizationRenderer htmlContent={visualizationHtml} noContainer={true} />
          </div>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6" style={{ marginRight: '-17px', paddingRight: '17px' }}>
      {/* Progress Tracker */}
      {renderProgressTracker()}

      {/* Overview and Scope Grid */}
      <div className="grid grid-cols-2 gap-6 items-stretch">
        {/* Overview */}
        <Card className="shadow-sm h-full">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center space-x-2">
              <FileText className="h-5 w-5 text-primary" />
              <span>Overview</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="text-sm leading-relaxed text-muted-foreground">
              {processData.general_description || 'No description provided yet.'}
            </p>
          </CardContent>
        </Card>

        {/* Scope */}
        <Card className="shadow-sm h-full">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center space-x-2">
              <Target className="h-5 w-5 text-primary" />
              <span>Scope</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="text-sm leading-relaxed text-muted-foreground">
              {processData.scope || 'Not specified'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Process Steps */}
      {renderProcessSteps()}

      {/* Inputs and Outputs */}
      <div className="grid gap-6">
        {renderSection("Inputs", processData.inputs, ArrowLeft, "No inputs defined")}
        {renderSection("Outputs", processData.outputs, ArrowRight, "No outputs defined")}
      </div>

      {/* KPIs */}
      {renderKPIsCard()}

      {/* Roles & Responsibilities */}
      {renderSection("Roles & Responsibilities", processData.roles_responsibilities, Users, "No roles defined")}

      {/* Exceptions */}
      {renderSection("Exceptions & Special Cases", processData.exceptions_special_cases, AlertTriangle, "No exceptions defined")}

      {/* Visualization */}
      {renderVisualizationCard()}
    </div>
  );
};

export default ProcessDetails; 