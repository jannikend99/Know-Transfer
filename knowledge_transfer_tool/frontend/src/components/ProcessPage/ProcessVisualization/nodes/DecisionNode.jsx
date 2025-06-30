import React from 'react';
import { Handle, Position } from 'reactflow';
import { HelpCircle, GitBranch } from 'lucide-react';

const DecisionNode = ({ data, isConnectable }) => {
  return (
    <div 
      className="px-6 py-4 shadow-lg rounded-lg min-w-40 max-w-72"
      style={{
        background: '#fed7aa',
        border: '2px solid #f97316',
        color: '#9a3412',
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
        style={{ background: '#f97316' }}
      />
      
      <div className="flex flex-col space-y-2">
        <div className="flex items-center space-x-2">
          <HelpCircle className="h-4 w-4" />
          <div className="text-sm font-medium leading-tight">
            {data.label || 'Decision'}
          </div>
        </div>
        
        {data.question && data.question !== data.label && (
          <div className="text-xs text-orange-700 leading-tight">
            {data.question}
          </div>
        )}
        
        {data.stepNumber && (
          <div className="text-xs font-mono text-orange-600">
            Step {data.stepNumber}
          </div>
        )}
      </div>
      
      {/* Output handles for yes/no branches */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="yes"
        isConnectable={isConnectable}
        style={{ 
          background: '#10b981', 
          bottom: '-6px',
          left: '30%',
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
          right: '30%',
          transform: 'translateX(50%)',
        }}
      />
    </div>
  );
};

export default DecisionNode; 