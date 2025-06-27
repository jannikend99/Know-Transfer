import React from 'react';
import { Handle, Position } from '@reactflow/core';
import { HelpCircle, GitBranch } from 'lucide-react';

const DecisionNode = ({ data, isConnectable }) => {
  return (
    <div className="relative">
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
        style={{ background: '#f59e0b', top: '-6px' }}
      />
      
      {/* Diamond shape - reduced size for better proportion */}
      <div 
        className="w-32 h-32 transform rotate-45 shadow-lg"
        style={{
          background: '#fff3cd',
          border: '2px solid #f59e0b',
          borderRadius: '8px',
        }}
      >
        {/* Content container - counter-rotate to keep text horizontal */}
        <div className="absolute inset-0 transform -rotate-45 flex flex-col items-center justify-center p-2">
          <div className="flex items-center space-x-1 mb-1">
            <HelpCircle className="h-3 w-3 text-amber-600" />
            <GitBranch className="h-3 w-3 text-amber-600" />
          </div>
          
          {/* Smaller text to fit proportionally */}
          <div className="text-xs font-medium text-amber-800 text-center leading-tight max-w-full">
            <div style={{ wordWrap: 'break-word', hyphens: 'auto', maxWidth: '80px' }}>
              {data.label && data.label.length > 20 
                ? `${data.label.substring(0, 20)}...` 
                : data.label || 'Decision'}
            </div>
          </div>
          
          {data.stepNumber && (
            <div className="text-xs font-mono text-amber-600 mt-1">
              #{data.stepNumber}
            </div>
          )}
        </div>
      </div>
      
      {/* Multiple output handles for yes/no branches */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="yes"
        isConnectable={isConnectable}
        style={{ 
          background: '#10b981', 
          bottom: '-6px',
          left: '35%',
          transform: 'translateX(-50%)',
        }}
      />
      
      <Handle
        type="source"
        position={Position.Bottom}
        id="no"
        isConnectable={isConnectable}
        style={{ 
          background: '#ef4444', 
          bottom: '-6px',
          right: '35%',
          transform: 'translateX(50%)',
        }}
      />
    </div>
  );
};

export default DecisionNode; 