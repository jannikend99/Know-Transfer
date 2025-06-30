import React from 'react';
import { Handle, Position } from 'reactflow';
import { Zap, Shuffle } from 'lucide-react';

const ParallelNode = ({ data, isConnectable }) => {
  return (
    <div 
      className="px-4 py-3 shadow-lg rounded-lg min-w-40 max-w-64"
      style={{
        background: '#e0f2fe',
        border: '2px solid #0ea5e9',
        color: '#0c4a6e',
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
        style={{ background: '#0ea5e9' }}
      />
      
      <div className="flex flex-col space-y-2">
        <div className="flex items-center justify-center space-x-2">
          <Zap className="h-4 w-4 text-sky-600" />
          <Shuffle className="h-4 w-4 text-sky-600" />
        </div>
        
        <div className="text-sm font-medium text-center leading-tight">
          {data.label}
        </div>
        
        {data.description && (
          <div className="text-xs text-sky-700 text-center leading-tight">
            {data.description}
          </div>
        )}
        
        {data.stepNumber && (
          <div className="text-xs font-mono text-sky-600 text-center">
            Step {data.stepNumber}
          </div>
        )}
        
        <div className="text-xs text-sky-600 text-center font-medium">
          ⚡ PARALLEL ⚡
        </div>
      </div>
      
      {/* Multiple output handles for parallel branches */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="branch1"
        isConnectable={isConnectable}
        style={{ 
          background: '#0ea5e9', 
          bottom: '-5px',
          left: '30%',
        }}
      />
      
      <Handle
        type="source"
        position={Position.Bottom}
        id="branch2"
        isConnectable={isConnectable}
        style={{ 
          background: '#0ea5e9', 
          bottom: '-5px',
          right: '30%',
        }}
      />
    </div>
  );
};

export default ParallelNode; 