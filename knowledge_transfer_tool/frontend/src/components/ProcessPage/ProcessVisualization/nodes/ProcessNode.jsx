import React from 'react';
import { Handle, Position } from 'reactflow';
import { FileText, ArrowRight, GitMerge } from 'lucide-react';

const ProcessNode = ({ data, isConnectable }) => {
  const getNodeStyle = () => {
    if (data.isConditionResult) {
      return {
        background: data.label.toLowerCase().includes('yes') ? '#d1fae5' : '#fee2e2',
        border: data.label.toLowerCase().includes('yes') ? '2px solid #10b981' : '2px solid #ef4444',
        color: data.label.toLowerCase().includes('yes') ? '#065f46' : '#991b1b',
      };
    }
    
    if (data.isMerge) {
      return {
        background: '#f3f4f6',
        border: '2px solid #6b7280',
        color: '#374151',
      };
    }
    
    if (data.isParallel) {
      return {
        background: '#f0f9ff',
        border: '2px solid #0284c7',
        color: '#0c4a6e',
      };
    }
    
    return {
      background: '#ffffff',
      border: '2px solid #e5e7eb',
      color: '#374151',
    };
  };

  const getIcon = () => {
    if (data.isMerge) return <GitMerge className="h-4 w-4" />;
    if (data.isParallel) return <ArrowRight className="h-4 w-4" />;
    return <FileText className="h-4 w-4" />;
  };

  return (
    <div 
      className="px-6 py-4 shadow-lg rounded-lg min-w-40 max-w-72"
      style={getNodeStyle()}
    >
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
        style={{ background: '#6b7280' }}
      />
      
      <div className="flex flex-col space-y-2">
        <div className="flex items-center space-x-2">
          {getIcon()}
          <div className="text-sm font-medium leading-tight">
            {data.label}
          </div>
        </div>
        
        {data.description && (
          <div className="text-xs text-gray-600 leading-tight">
            {data.description}
          </div>
        )}
        
        {data.stepNumber && (
          <div className="text-xs font-mono text-gray-500">
            Step {data.stepNumber}
          </div>
        )}
      </div>
      
      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={isConnectable}
        style={{ background: '#6b7280' }}
      />
    </div>
  );
};

export default ProcessNode; 