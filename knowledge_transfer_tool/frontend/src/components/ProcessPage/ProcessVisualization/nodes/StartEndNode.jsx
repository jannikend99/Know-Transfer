import React from 'react';
import { Handle, Position } from '@reactflow/core';
import { Play, Square } from 'lucide-react';

const StartEndNode = ({ data, isConnectable }) => {
  const isStart = data.isStart;
  
  const getStyle = () => {
    return {
      background: isStart ? '#e8f5e8' : '#e3f2fd',
      border: isStart ? '3px solid #4caf50' : '3px solid #2196f3',
      color: isStart ? '#1b5e20' : '#0d47a1',
    };
  };

  return (
    <div 
      className="w-28 h-28 rounded-full shadow-lg flex flex-col items-center justify-center"
      style={getStyle()}
    >
      {!isStart && (
        <Handle
          type="target"
          position={Position.Top}
          isConnectable={isConnectable}
          style={{ 
            background: '#2196f3',
            top: '10px',
          }}
        />
      )}
      
      <div className="flex flex-col items-center space-y-1">
        {isStart ? (
          <Play className="h-6 w-6 fill-current" />
        ) : (
          <Square className="h-5 w-5 fill-current" />
        )}
        
        <div className="text-sm font-bold text-center">
          {data.label}
        </div>
      </div>
      
      {isStart && (
        <Handle
          type="source"
          position={Position.Bottom}
          isConnectable={isConnectable}
          style={{ 
            background: '#4caf50',
            bottom: '10px',
          }}
        />
      )}
    </div>
  );
};

export default StartEndNode; 