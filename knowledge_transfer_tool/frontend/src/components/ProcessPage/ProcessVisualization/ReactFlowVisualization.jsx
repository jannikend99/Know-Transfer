import React, { useCallback, useRef, useState, useEffect } from 'react';
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  addEdge,
  Panel,
  MarkerType,
} from '@reactflow/core';
import { MiniMap } from '@reactflow/minimap';
import { Controls } from '@reactflow/controls';
import { Background } from '@reactflow/background';
import { RefreshCw, Network, Maximize2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../../ui/card';
import { Button } from '../../ui/button';

// Custom node types
import DecisionNode from './nodes/DecisionNode';
import ProcessNode from './nodes/ProcessNode';
import StartEndNode from './nodes/StartEndNode';
import ParallelNode from './nodes/ParallelNode';

const nodeTypes = {
  process: ProcessNode,
  decision: DecisionNode,
  startEnd: StartEndNode,
  parallel: ParallelNode,
};

const ReactFlowVisualization = ({ processData, onRecreateVisualization }) => {
  const reactFlowWrapper = useRef(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Clean text for node labels
  const cleanTextForNode = (text) => {
    if (!text) return "";
    
    let cleanText = String(text).trim();
    
    // Remove HTML/XML tags
    cleanText = cleanText.replace(/<[^>]+>/g, '');
    
    // Remove markdown formatting
    cleanText = cleanText.replace(/!\[.*?\]\(.*?\)/g, '');
    cleanText = cleanText.replace(/\[.*?\]\(.*?\)/g, '');
    cleanText = cleanText.replace(/\*\*(.+?)\*\*/g, '$1');
    cleanText = cleanText.replace(/\*(.+?)\*/g, '$1');
    cleanText = cleanText.replace(/`(.+?)`/g, '$1');
    cleanText = cleanText.replace(/#{1,6}\s*/g, '');
    
    // Remove bullet points and list markers
    cleanText = cleanText.replace(/^[\s]*[-•*+]\s*/gm, '');
    cleanText = cleanText.replace(/^[\s]*\d+\.\s*/gm, '');
    cleanText = cleanText.replace(/^[\s]*[a-zA-Z]\.\s*/gm, '');
    
    // Normalize whitespace
    cleanText = cleanText.replace(/\s+/g, ' ').trim();
    
    if (!cleanText || cleanText.length < 3) {
      cleanText = 'Process step';
    }
    
    return cleanText;
  };

  // Detect step types
  const isDecisionStep = (stepText) => {
    const decisionKeywords = [
      'if ', 'when ', 'decide', 'choice', 'option', 'either', 'or ',
      'depending on', 'based on', 'determine', 'check if', 'verify',
      'approve', 'reject', 'yes/no', 'true/false', 'condition'
    ];
    const lowerText = stepText.toLowerCase();
    return decisionKeywords.some(keyword => lowerText.includes(keyword));
  };

  const isParallelStep = (stepText) => {
    const parallelKeywords = [
      'simultaneously', 'parallel', 'concurrent', 'at the same time',
      'meanwhile', 'in parallel', 'both ', 'all at once', 'together'
    ];
    const lowerText = stepText.toLowerCase();
    return parallelKeywords.some(keyword => lowerText.includes(keyword));
  };

  // Generate React Flow data from process steps
  const generateFlowFromSteps = (steps) => {
    if (!Array.isArray(steps) || steps.length === 0) {
      const emptyNodes = [
        {
          id: 'start',
          type: 'startEnd',
          position: { x: 200, y: 50 },
          data: { label: 'START', isStart: true },
        },
        {
          id: 'empty',
          type: 'process',
          position: { x: 150, y: 150 },
          data: { 
            label: 'No Process Steps Defined',
            description: 'Use AI Assistant to add process steps'
          },
        },
        {
          id: 'end',
          type: 'startEnd',
          position: { x: 200, y: 250 },
          data: { label: 'END', isStart: false },
        },
      ];

      const emptyEdges = [
        {
          id: 'e-start-empty',
          source: 'start',
          target: 'empty',
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
        },
        {
          id: 'e-empty-end',
          source: 'empty',
          target: 'end',
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
        },
      ];

      return { nodes: emptyNodes, edges: emptyEdges };
    }

    const nodes = [];
    const edges = [];
    
    // Layout configuration for organized arrangement
    const layout = {
      startX: 300,
      startY: 80,
      rowHeight: 140,
      colWidth: 250,
      branchOffset: 200,
      centerCol: 1, // Main flow in column 1 (middle)
    };

    let currentRow = 0;
    let currentNodeId = 'start';

    // Add start node
    nodes.push({
      id: 'start',
      type: 'startEnd',
      position: { x: layout.startX, y: layout.startY },
      data: { label: 'START', isStart: true },
    });

    currentRow++;

    // Process each step with organized positioning  
    steps.forEach((step, index) => {
      const nodeId = `step-${index}`;
      const cleanStep = cleanTextForNode(step);
      const baseY = layout.startY + (currentRow * layout.rowHeight);
      
      if (isDecisionStep(step)) {
        // Decision node in center column
        const decisionNode = {
          id: nodeId,
          type: 'decision',
          position: { x: layout.startX, y: baseY },
          data: {
            label: cleanStep,
            question: cleanStep,
            stepNumber: index + 1,
          },
        };
        nodes.push(decisionNode);

        // Connect from previous node
        edges.push({
          id: `e-${currentNodeId}-${nodeId}`,
          source: currentNodeId,
          target: nodeId,
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
        });

        currentRow++;

        // Yes and No branches in organized columns
        const yesNodeId = `${nodeId}-yes`;
        const noNodeId = `${nodeId}-no`;
        const branchY = layout.startY + (currentRow * layout.rowHeight);

        // Yes branch (left column)
        nodes.push({
          id: yesNodeId,
          type: 'process',
          position: { x: layout.startX - layout.branchOffset, y: branchY },
          data: { 
            label: 'Yes Path',
            description: 'Continue with approval',
            isConditionResult: true,
          },
        });

        // No branch (right column) 
        nodes.push({
          id: noNodeId,
          type: 'process',
          position: { x: layout.startX + layout.branchOffset, y: branchY },
          data: { 
            label: 'No Path',
            description: 'Alternative handling', 
            isConditionResult: true,
          },
        });

        // Decision branch edges
        edges.push({
          id: `e-${nodeId}-${yesNodeId}`,
          source: nodeId,
          target: yesNodeId,
          type: 'smoothstep',
          label: 'Yes',
          labelStyle: { fill: '#10b981', fontWeight: 600 },
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: '#10b981' },
        });

        edges.push({
          id: `e-${nodeId}-${noNodeId}`,
          source: nodeId,
          target: noNodeId,
          type: 'smoothstep',
          label: 'No',
          labelStyle: { fill: '#ef4444', fontWeight: 600 },
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: '#ef4444' },
        });

        currentRow++;

        // Merge node back to center column
        const mergeNodeId = `${nodeId}-merge`;
        const mergeY = layout.startY + (currentRow * layout.rowHeight);

        nodes.push({
          id: mergeNodeId,
          type: 'process',
          position: { x: layout.startX, y: mergeY },
          data: { 
            label: 'Continue Process',
            description: 'Paths merge here',
            isMerge: true,
          },
        });

        // Merge edges - clean vertical lines
        edges.push({
          id: `e-${yesNodeId}-${mergeNodeId}`,
          source: yesNodeId,
          target: mergeNodeId,
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
        });

        edges.push({
          id: `e-${noNodeId}-${mergeNodeId}`,
          source: noNodeId,
          target: mergeNodeId,
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
        });

        currentNodeId = mergeNodeId;

      } else if (isParallelStep(step)) {
        // Parallel node in center column
        const parallelNode = {
          id: nodeId,
          type: 'parallel',
          position: { x: layout.startX, y: baseY },
          data: {
            label: cleanStep,
            description: 'Parallel execution',
            stepNumber: index + 1,
          },
        };
        nodes.push(parallelNode);

        // Connect from previous node
        edges.push({
          id: `e-${currentNodeId}-${nodeId}`,
          source: currentNodeId,
          target: nodeId,
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
        });

        currentRow++;

        // Parallel branches in organized columns
        const branch1Id = `${nodeId}-branch1`;
        const branch2Id = `${nodeId}-branch2`;
        const branchY = layout.startY + (currentRow * layout.rowHeight);

        // Branch 1 (left column)
        nodes.push({
          id: branch1Id,
          type: 'process',
          position: { x: layout.startX - layout.branchOffset, y: branchY },
          data: { 
            label: 'Parallel Task A',
            description: 'First parallel task',
            isParallel: true,
          },
        });

        // Branch 2 (right column)
        nodes.push({
          id: branch2Id,
          type: 'process',
          position: { x: layout.startX + layout.branchOffset, y: branchY },
          data: { 
            label: 'Parallel Task B',
            description: 'Second parallel task',
            isParallel: true,
          },
        });

        // Parallel branch edges
        edges.push({
          id: `e-${nodeId}-${branch1Id}`,
          source: nodeId,
          target: branch1Id,
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: '#0ea5e9' },
        });

        edges.push({
          id: `e-${nodeId}-${branch2Id}`,
          source: nodeId,
          target: branch2Id,
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: '#0ea5e9' },
        });

        currentRow++;

        // Sync node back to center column
        const syncNodeId = `${nodeId}-sync`;
        const syncY = layout.startY + (currentRow * layout.rowHeight);

        nodes.push({
          id: syncNodeId,
          type: 'process',
          position: { x: layout.startX, y: syncY },
          data: { 
            label: 'Synchronize',
            description: 'Wait for all parallel tasks',
            isMerge: true,
          },
        });

        // Sync edges - clean lines back to center
        edges.push({
          id: `e-${branch1Id}-${syncNodeId}`,
          source: branch1Id,
          target: syncNodeId,
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
        });

        edges.push({
          id: `e-${branch2Id}-${syncNodeId}`,
          source: branch2Id,
          target: syncNodeId,
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
        });

        currentNodeId = syncNodeId;

      } else {
        // Regular process step in center column
        const regularNode = {
          id: nodeId,
          type: 'process',
          position: { x: layout.startX, y: baseY },
          data: {
            label: `${index + 1}. ${cleanStep}`,
            description: step.length > 50 ? step : null,
            stepNumber: index + 1,
          },
        };
        nodes.push(regularNode);

        // Connect from previous node
        edges.push({
          id: `e-${currentNodeId}-${nodeId}`,
          source: currentNodeId,
          target: nodeId,
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
        });

        currentNodeId = nodeId;
      }

      currentRow++;
    });

    // Add end node in center column
    const endY = layout.startY + (currentRow * layout.rowHeight);
    nodes.push({
      id: 'end',
      type: 'startEnd',
      position: { x: layout.startX, y: endY },
      data: { label: 'END', isStart: false },
    });

    edges.push({
      id: `e-${currentNodeId}-end`,
      source: currentNodeId,
      target: 'end',
      type: 'smoothstep',
      markerEnd: { type: MarkerType.ArrowClosed },
    });

    return { nodes, edges };
  };

  // Fetch visualization data from backend or generate from steps
  const fetchFlowVisualization = async () => {
    if (!processData || !processData.id) return;

    setIsLoading(true);
    setError(null);

    try {
      // Always try to fetch from backend first (it will return cached data if available)
      const response = await fetch(`/api/processes/${processData.id}/reactflow`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const flowData = await response.json();
        console.log('[DEBUG] Successfully loaded React Flow data from backend');
        setNodes(flowData.nodes || []);
        setEdges(flowData.edges || []);
      } else {
        console.error('[DEBUG] Failed to fetch React Flow data from backend');
        // Fallback to frontend generation only if backend fails
        const { nodes: generatedNodes, edges: generatedEdges } = generateFlowFromSteps(processData.process_steps);
        setNodes(generatedNodes);
        setEdges(generatedEdges);
      }
    } catch (err) {
      console.error('[DEBUG] Error fetching React Flow visualization:', err);
      // Fallback to frontend generation
      const { nodes: generatedNodes, edges: generatedEdges } = generateFlowFromSteps(processData.process_steps);
      setNodes(generatedNodes);
      setEdges(generatedEdges);
    } finally {
      setIsLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchFlowVisualization();
  }, [processData]);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const handleRecreateVisualization = async () => {
    if (onRecreateVisualization) {
      setIsLoading(true);
      try {
        await onRecreateVisualization();
        // Refetch after recreation
        setTimeout(() => {
          fetchFlowVisualization();
        }, 1000);
      } catch (err) {
        console.error('Error recreating visualization:', err);
        setError('Failed to recreate visualization');
      } finally {
        setIsLoading(false);
      }
    } else {
      // Just regenerate from current data
      fetchFlowVisualization();
    }
  };



  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center space-x-2">
            <Network className="h-5 w-5 text-primary" />
            <span>Interactive Process Flow</span>
          </CardTitle>
          <div className="flex items-center space-x-2">
            <Button
              onClick={handleRecreateVisualization}
              variant="outline"
              size="sm"
              disabled={isLoading}
              className="flex items-center space-x-2"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Recreate</span>
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {isLoading && (
          <div className="flex items-center justify-center h-[600px]">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
              <p className="text-sm text-muted-foreground">Generating visualization...</p>
            </div>
          </div>
        )}
        
        {error && (
          <div className="flex items-center justify-center h-[600px]">
            <p className="text-sm text-destructive">Error: {error}</p>
          </div>
        )}
        
        {!isLoading && !error && (
          <div className="w-full h-[600px] border border-gray-200 rounded-lg bg-gray-50" ref={reactFlowWrapper}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              nodeTypes={nodeTypes}
              fitView
              attributionPosition="bottom-left"
              defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
              minZoom={0.1}
              maxZoom={3}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={true}
            >
              <Controls showInteractive={false} />
              <MiniMap 
                nodeStrokeColor={(n) => {
                  if (n.type === 'startEnd') return '#4caf50';
                  if (n.type === 'decision') return '#f59e0b';
                  if (n.type === 'parallel') return '#0ea5e9';
                  return '#666';
                }}
                nodeColor={(n) => {
                  if (n.type === 'startEnd') return '#e8f5e8';
                  if (n.type === 'decision') return '#fff3cd';
                  if (n.type === 'parallel') return '#e0f2fe';
                  return '#f9f9f9';
                }}
                nodeBorderRadius={8}
                maskColor="rgb(240, 240, 240, 0.6)"
                position="bottom-right"
              />
              <Background variant="dots" gap={40} size={0.5} color="#e5e7eb" />
              <Panel position="top-left" className="bg-white/90 backdrop-blur-sm rounded px-2 py-1 text-xs text-gray-600 shadow-sm">
                <div className="flex items-center space-x-1">
                  <Maximize2 className="h-3 w-3" />
                  <span>Drag to pan • Scroll to zoom • Click nodes for details</span>
                </div>
              </Panel>
            </ReactFlow>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default ReactFlowVisualization; 