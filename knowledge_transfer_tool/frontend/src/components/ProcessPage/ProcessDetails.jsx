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
} from "../ui/card";

import { Badge } from "../ui/badge";

// Helper function to format text with "Name: Description" pattern
const renderWithFormatting = (text) => {
  if (!text || typeof text !== 'string') return text;
  
  // Check if text matches "Name: Description" pattern
  const colonIndex = text.indexOf(':');
  if (colonIndex > 0 && colonIndex < text.length - 1) {
    const name = text.substring(0, colonIndex).trim();
    const description = text.substring(colonIndex + 1).trim();
    
    return (
      <span>
        <strong>{name}:</strong> {description}
      </span>
    );
  }
  
  return text;
};

// Special function for KPI formatting with multi-line support
const renderKPIWithFormatting = (text) => {
  if (!text || typeof text !== 'string') return text;

  // Try to parse KPI format with different separators: "Name: description | Target: value" or "Name: description. Target: value."
  const targetMatch = text.match(/^(.+?)[\.\|]\s*Target:\s*(.+?)\.?\s*$/i);
  if (targetMatch) {
    const [, beforeTarget, targetValue] = targetMatch;
    
    // Further parse the before-target part for "Name: description"
    const colonIndex = beforeTarget.indexOf(':');
    if (colonIndex > 0) {
      const name = beforeTarget.substring(0, colonIndex).trim();
      const description = beforeTarget.substring(colonIndex + 1).trim();
      
      return (
        <div className="space-y-1">
          <div><strong>{name}</strong></div>
          <div className="text-sm text-muted-foreground">{description}</div>
          <div className="text-sm italic">Target: {targetValue}</div>
        </div>
      );
    }
  }
  
  // Fallback to regular name:description formatting
  return renderWithFormatting(text);
};

const ProcessDetails = ({ processData }) => {
  // Calculate completion status
  const getProcessCompletion = () => {
    if (!processData) return { completed: 0, total: 0, percentage: 0, missing: [] };

    const categories = [
      { 
        key: 'general_description', 
        name: 'Overview', 
        check: (data) => {
          const desc = data.general_description;
          if (!desc || !desc.trim) return false;
          return desc.trim().length >= 100;
        }
      },
      { 
        key: 'scope_included', 
        name: 'Scope Included', 
        check: (data) => {
          const items = data.scope_included;
          if (!Array.isArray(items) || items.length === 0) return false;
          const substantial = items.filter(item => item && item.trim().length >= 30);
          return substantial.length >= 2;
        }
      },
      { 
        key: 'scope_excluded', 
        name: 'Scope Excluded', 
        check: (data) => {
          const items = data.scope_excluded;
          if (!Array.isArray(items) || items.length === 0) return false;
          const substantial = items.filter(item => item && item.trim().length >= 30);
          return substantial.length >= 2;
        }
      },
      { 
        key: 'process_steps', 
        name: 'Process Steps', 
        check: (data) => {
          const steps = data.process_steps;
          if (!Array.isArray(steps) || steps.length === 0) return false;
          const substantial = steps.filter(step => step && step.trim().length >= 30);
          return substantial.length >= 2;
        }
      },
      { 
        key: 'inputs', 
        name: 'Inputs', 
        check: (data) => {
          const items = data.inputs;
          if (!Array.isArray(items) || items.length === 0) return false;
          const substantial = items.filter(item => item && item.trim().length >= 30);
          return substantial.length >= 2;
        }
      },
      { 
        key: 'outputs', 
        name: 'Outputs', 
        check: (data) => {
          const items = data.outputs;
          if (!Array.isArray(items) || items.length === 0) return false;
          const substantial = items.filter(item => item && item.trim().length >= 30);
          return substantial.length >= 2;
        }
      },
      { 
        key: 'kpis', 
        name: 'Key Performance Indicators', 
        check: (data) => {
          const items = data.kpis;
          if (!Array.isArray(items) || items.length === 0) return false;
          const substantial = items.filter(item => item && item.trim().length >= 30);
          return substantial.length >= 2;
        }
      },
      { 
        key: 'roles_responsibilities', 
        name: 'Roles & Responsibilities', 
        check: (data) => {
          const items = data.roles_responsibilities;
          if (!Array.isArray(items) || items.length === 0) return false;
          const substantial = items.filter(item => item && item.trim().length >= 30);
          return substantial.length >= 2;
        }
      },
      { 
        key: 'exceptions_special_cases', 
        name: 'Exceptions & Special Cases', 
        check: (data) => {
          const items = data.exceptions_special_cases;
          if (!Array.isArray(items) || items.length === 0) return false;
          const substantial = items.filter(item => item && item.trim().length >= 30);
          return substantial.length >= 2;
        }
      }
    ];

    const completed = categories.filter(cat => cat.check(processData)).length;
    const missing = categories.filter(cat => !cat.check(processData));
    const percentage = Math.round((completed / categories.length) * 100);

    return { completed, total: categories.length, percentage, missing };
  };

  const completion = getProcessCompletion();

  if (!processData) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p>No process details available.</p>
      </div>
    );
  }

  const renderSection = (title, items, icon, emptyMessage = "None specified", useKPIFormatting = false) => (
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
          useKPIFormatting ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {items.map((item, index) => (
                <div key={index} className="flex items-start space-x-3 p-4 bg-muted/30 rounded-lg border hover:shadow-sm transition-shadow">
                  <div className="flex items-center justify-center w-8 h-8 bg-primary/10 rounded-full flex-shrink-0">
                    <TrendingUp className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    {renderKPIWithFormatting(item)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {items.map((item, index) => (
                <div key={index} className="flex items-start space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <div className="text-sm flex-1">
                    {renderWithFormatting(item)}
                  </div>
                </div>
              ))}
            </div>
          )
        ) : (
          <div className="flex items-center space-x-2 text-muted-foreground">
            <Circle className="h-4 w-4" />
            <span className="text-sm">{emptyMessage}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );

  const renderScopeSection = (title, items, icon, emptyMessage) => (
    <div>
      <h4 className="text-sm font-medium text-muted-foreground mb-2 flex items-center space-x-1">
        {React.createElement(icon, { className: "h-3 w-3" })}
        <span>{title}:</span>
      </h4>
      {Array.isArray(items) && items.length > 0 ? (
        <div className="space-y-1">
          {items.map((item, index) => (
            <div key={index} className="flex items-start space-x-2">
              <CheckCircle className="h-3 w-3 text-green-500 mt-0.5 flex-shrink-0" />
              <span className="text-xs text-muted-foreground">{renderWithFormatting(item)}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground italic">{emptyMessage}</p>
      )}
    </div>
  );

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

  return (
    <div className="space-y-6 min-w-0 overflow-x-hidden" style={{ marginRight: '-17px', paddingRight: '17px' }}>
      {/* Progress Tracker */}
      {renderProgressTracker()}

      {/* Overview and Scope Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch min-w-0">
        {/* Overview */}
        <Card className="shadow-sm h-full">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center space-x-2">
              <FileText className="h-5 w-5 text-primary" />
              <span>Overview</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="text-sm leading-relaxed text-muted-foreground break-words">
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
          <CardContent className="pt-0 space-y-4">
            {renderScopeSection("Included", processData.scope_included, CheckCircle, "Not specified")}
            {renderScopeSection("Excluded", processData.scope_excluded, Circle, "Not specified")}
          </CardContent>
        </Card>
      </div>

      {/* Process Steps */}
      {renderSection("Process Steps", processData.process_steps, ListTodo, "No steps defined")}

      {/* Inputs and Outputs */}
      <div className="grid gap-6 min-w-0">
        {renderSection("Inputs", processData.inputs, ArrowLeft, "No inputs defined")}
        {renderSection("Outputs", processData.outputs, ArrowRight, "No outputs defined")}
      </div>

      {/* KPIs with special formatting */}
      {renderSection("Key Performance Indicators", processData.kpis, BarChart3, "No KPIs defined", true)}

      {/* Roles & Responsibilities */}
      {renderSection("Roles & Responsibilities", processData.roles_responsibilities, Users, "No roles defined")}

      {/* Exceptions */}
      {renderSection("Exceptions & Special Cases", processData.exceptions_special_cases, AlertTriangle, "No exceptions defined")}
    </div>
  );
};

export default ProcessDetails; 