import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { RefreshCw, Network, ZoomIn, ZoomOut, Move } from 'lucide-react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { Card, CardHeader, CardTitle, CardContent } from '../../ui/card';
import { Button } from '../../ui/button';

const MermaidVisualization = ({ processData, onRecreateVisualization }) => {
  const mermaidRef = useRef();
  const transformRef = useRef();
  const [mermaidCode, setMermaidCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Initialize Mermaid
  useEffect(() => {
    try {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose',
        themeVariables: {
          primaryColor: '#3b82f6',
          primaryTextColor: '#ffffff',
          primaryBorderColor: '#e5e7eb',
          lineColor: '#6b7280',
          secondaryColor: '#f3f4f6',
          tertiaryColor: '#f9fafb',
          background: '#ffffff',
          mainBkg: '#ffffff',
          secondBkg: '#f9fafb',
          tertiaryBkg: '#f3f4f6',
        },
        flowchart: {
          useMaxWidth: false,
          htmlLabels: false,
          curve: 'basis',
          padding: 20
        },
        markdownAutoWrap: false,
        htmlLabels: false
      });
    } catch (err) {
      console.error('Error initializing Mermaid:', err);
    }
  }, []);

  // Clean text for Mermaid compatibility - Aggressive cleaning
  const cleanTextForMermaid = (text) => {
    if (!text) return "";
    
    console.log('[DEBUG] Original text:', text.substring(0, 100));
    
    let cleanText = String(text).trim();
    
    // Remove HTML/XML tags
    cleanText = cleanText.replace(/<[^>]+>/g, '');
    
    // Remove markdown formatting aggressively
    cleanText = cleanText.replace(/!\[.*?\]\(.*?\)/g, '');  // Remove images
    cleanText = cleanText.replace(/\[.*?\]\(.*?\)/g, '');   // Remove links
    cleanText = cleanText.replace(/\*\*(.+?)\*\*/g, '$1');  // Remove bold
    cleanText = cleanText.replace(/\*(.+?)\*/g, '$1');      // Remove italic
    cleanText = cleanText.replace(/`(.+?)`/g, '$1');        // Remove code
    cleanText = cleanText.replace(/#{1,6}\s*/g, '');        // Remove headers
    
    // Remove bullet points and list markers more aggressively
    cleanText = cleanText.replace(/^[\s]*[-•*+]\s*/gm, '');
    cleanText = cleanText.replace(/^[\s]*\d+\.\s*/gm, '');
    cleanText = cleanText.replace(/^[\s]*[a-zA-Z]\.\s*/gm, '');
    
    // Remove problematic characters
    cleanText = cleanText.replace(/"/g, "'").replace(/\n/g, ' ').replace(/\r/g, ' ').replace(/\t/g, ' ');
    cleanText = cleanText.replace(/\[/g, '(').replace(/\]/g, ')');
    cleanText = cleanText.replace(/\{/g, '(').replace(/\}/g, ')');
    cleanText = cleanText.replace(/</g, '(').replace(/>/g, ')');
    cleanText = cleanText.replace(/\|/g, '-').replace(/&/g, 'and');
    cleanText = cleanText.replace(/:/g, ' -').replace(/;/g, ',');
    
    // Remove any remaining special characters that could break Mermaid
    cleanText = cleanText.replace(/[^\w\s\-\.,()\']/g, ' ');
    
    // Remove multiple spaces and normalize
    cleanText = cleanText.replace(/\s+/g, ' ').trim();
    
    // If after all cleaning we have nothing meaningful, provide a fallback
    if (!cleanText || cleanText.length < 3) {
      cleanText = 'Process step';
    }
    
    console.log('[DEBUG] Cleaned text:', cleanText.substring(0, 100));
    
    return cleanText;
  };

  // Detect if a step contains decision/branching language
  const isDecisionStep = (stepText) => {
    const decisionKeywords = [
      'if ', 'when ', 'decide', 'choice', 'option', 'either', 'or ',
      'depending on', 'based on', 'determine', 'check if', 'verify',
      'approve', 'reject', 'yes/no', 'true/false', 'condition'
    ];
    const lowerText = stepText.toLowerCase();
    return decisionKeywords.some(keyword => lowerText.includes(keyword));
  };

  // Detect if a step contains parallel/concurrent language
  const isParallelStep = (stepText) => {
    const parallelKeywords = [
      'simultaneously', 'parallel', 'concurrent', 'at the same time',
      'meanwhile', 'in parallel', 'both ', 'all at once', 'together'
    ];
    const lowerText = stepText.toLowerCase();
    return parallelKeywords.some(keyword => lowerText.includes(keyword));
  };

  // Generate Mermaid code from process steps with branching support
  const generateMermaidFromSteps = (steps) => {
    if (!Array.isArray(steps) || steps.length === 0) {
      return `graph TD
    Start(( START )) --> NoSteps
    NoSteps["No Process Steps Defined"] --> Helper
    Helper["Use AI Assistant to add steps"] --> End
    End(( END ))
    
    style Start fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    style End fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style NoSteps fill:#fff3cd,stroke:#ffc107,stroke-width:2px
    style Helper fill:#e3f2fd,stroke:#1976d2,stroke-width:2px`;
    }

    let mermaidGraph = 'graph TD\n';
    let currentNode = 'Start';
    
    // Add start node
    mermaidGraph += '    Start(( START ))\n';
    
    steps.forEach((step, index) => {
      const nodeId = `Step${index + 1}`;
      let cleanStep = cleanTextForMermaid(step);
      
      if (cleanStep.length > 50) {
        cleanStep = cleanStep.slice(0, 47) + '...';
      }
      
      if (!cleanStep) {
        cleanStep = `Process Step ${index + 1}`;
      }

      if (isDecisionStep(step)) {
        // Create decision diamond
        mermaidGraph += `    ${nodeId}{{"${cleanStep}"}}\n`;
        mermaidGraph += `    ${currentNode} --> ${nodeId}\n`;
        
        // Create branches
        const yesNode = `${nodeId}Yes`;
        const noNode = `${nodeId}No`;
        const mergeNode = `Merge${index + 1}`;
        
        mermaidGraph += `    ${yesNode}["Yes: Continue"]\n`;
        mermaidGraph += `    ${noNode}["No: Alternative"]\n`;
        mermaidGraph += `    ${mergeNode}(( ))\n`;
        
        mermaidGraph += `    ${nodeId} -->|Yes| ${yesNode}\n`;
        mermaidGraph += `    ${nodeId} -->|No| ${noNode}\n`;
        mermaidGraph += `    ${yesNode} --> ${mergeNode}\n`;
        mermaidGraph += `    ${noNode} --> ${mergeNode}\n`;
        
        currentNode = mergeNode;
        
      } else if (isParallelStep(step)) {
        // Create parallel branches
        mermaidGraph += `    ${nodeId}["${cleanStep}"]\n`;
        mermaidGraph += `    ${currentNode} --> ${nodeId}\n`;
        
        const branch1 = `${nodeId}A`;
        const branch2 = `${nodeId}B`;
        const mergeNode = `Merge${index + 1}`;
        
        mermaidGraph += `    ${branch1}["Parallel Task A"]\n`;
        mermaidGraph += `    ${branch2}["Parallel Task B"]\n`;
        mermaidGraph += `    ${mergeNode}(( ))\n`;
        
        mermaidGraph += `    ${nodeId} --> ${branch1}\n`;
        mermaidGraph += `    ${nodeId} --> ${branch2}\n`;
        mermaidGraph += `    ${branch1} --> ${mergeNode}\n`;
        mermaidGraph += `    ${branch2} --> ${mergeNode}\n`;
        
        currentNode = mergeNode;
        
      } else {
        // Regular process step
        mermaidGraph += `    ${nodeId}["${cleanStep}"]\n`;
        mermaidGraph += `    ${currentNode} --> ${nodeId}\n`;
        currentNode = nodeId;
      }
    });

    // Connect final node to end
    mermaidGraph += '    End(( END ))\n';
    mermaidGraph += `    ${currentNode} --> End\n\n`;

    // Add styling
    mermaidGraph += '    style Start fill:#e8f5e8,stroke:#4caf50,stroke-width:2px\n';
    mermaidGraph += '    style End fill:#e3f2fd,stroke:#2196f3,stroke-width:2px\n';
    
    // Style process steps and decision nodes
    steps.forEach((step, index) => {
      const nodeId = `Step${index + 1}`;
      if (isDecisionStep(step)) {
        mermaidGraph += `    style ${nodeId} fill:#fff3cd,stroke:#f59e0b,stroke-width:2px\n`;
        mermaidGraph += `    style ${nodeId}Yes fill:#d1fae5,stroke:#10b981,stroke-width:1px\n`;
        mermaidGraph += `    style ${nodeId}No fill:#fee2e2,stroke:#ef4444,stroke-width:1px\n`;
        mermaidGraph += `    style Merge${index + 1} fill:#f3f4f6,stroke:#6b7280,stroke-width:1px\n`;
      } else if (isParallelStep(step)) {
        mermaidGraph += `    style ${nodeId} fill:#e0f2fe,stroke:#0ea5e9,stroke-width:2px\n`;
        mermaidGraph += `    style ${nodeId}A fill:#f0f9ff,stroke:#0284c7,stroke-width:1px\n`;
        mermaidGraph += `    style ${nodeId}B fill:#f0f9ff,stroke:#0284c7,stroke-width:1px\n`;
        mermaidGraph += `    style Merge${index + 1} fill:#f3f4f6,stroke:#6b7280,stroke-width:1px\n`;
      } else {
        mermaidGraph += `    style ${nodeId} fill:#f9f9f9,stroke:#666,stroke-width:1px\n`;
      }
    });

    return mermaidGraph;
  };

  // Fetch Mermaid code from backend or generate from steps
  const fetchMermaidVisualization = async () => {
    if (!processData || !processData.id) return;

    setIsLoading(true);
    setError(null);

    try {
      // Use frontend generation with actual process data
      console.log('[DEBUG] Using frontend generation with process steps:', processData.process_steps);
      const generatedCode = generateMermaidFromSteps(processData.process_steps);
      setMermaidCode(generatedCode);
    } catch (err) {
      console.error('Error fetching Mermaid visualization:', err);
      // Even simpler fallback
      const simpleFallback = `graph TD
    A[Simple Test] --> B[Working]
    style A fill:#f9f9f9,stroke:#666,stroke-width:1px
    style B fill:#f9f9f9,stroke:#666,stroke-width:1px`;
      setMermaidCode(simpleFallback);
    } finally {
      setIsLoading(false);
    }
  };

  // Render Mermaid diagram
  useEffect(() => {
    if (mermaidCode && mermaidRef.current) {
      const renderDiagram = async () => {
        try {
          // Generate unique ID for this diagram
          const diagramId = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
          
          // Validate mermaid code before rendering
          if (!mermaidCode.trim()) {
            throw new Error('Empty diagram code');
          }
          
          // Render the diagram
          const { svg } = await mermaid.render(diagramId, mermaidCode);
          
          // Only update if the content has actually changed
          if (mermaidRef.current.innerHTML !== svg) {
            mermaidRef.current.innerHTML = svg;
          }
          
          setError(null);
        } catch (err) {
          console.error('Error rendering Mermaid diagram:', err);
          setError('Failed to render diagram: ' + err.message);
          
          // Create a fallback error display
          mermaidRef.current.innerHTML = `
            <div class="p-4 border border-red-300 bg-red-50 rounded text-center">
              <div class="text-red-700">
                <p class="text-sm font-medium">Failed to render Mermaid diagram</p>
                <p class="text-xs mt-1"><strong>Error:</strong> ${err.message}</p>
              </div>
            </div>
          `;
        }
      };

      renderDiagram();
    }
  }, [mermaidCode]);

  // Initial load
  useEffect(() => {
    fetchMermaidVisualization();
  }, [processData]);

  const handleRecreateVisualization = async () => {
    if (onRecreateVisualization) {
      setIsLoading(true);
      try {
        await onRecreateVisualization();
        // Refetch after recreation
        setTimeout(() => {
          fetchMermaidVisualization();
        }, 1000);
      } catch (err) {
        console.error('Error recreating visualization:', err);
        setError('Failed to recreate visualization');
      } finally {
        setIsLoading(false);
      }
    } else {
      // Just regenerate from current data
      fetchMermaidVisualization();
    }
  };

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center space-x-2">
            <Network className="h-5 w-5 text-primary" />
            <span>Process Flow Diagram</span>
          </CardTitle>
          <div className="flex items-center space-x-2">
            {/* Zoom/Pan Controls */}
            {!isLoading && !error && mermaidCode && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => transformRef.current?.zoomIn()}
                  className="p-2"
                  title="Zoom In"
                >
                  <ZoomIn className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => transformRef.current?.zoomOut()}
                  className="p-2"
                  title="Zoom Out"
                >
                  <ZoomOut className="h-4 w-4" />
                </Button>
              </>
            )}
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
          <div className="flex items-center justify-center h-32">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
              <p className="text-sm text-muted-foreground">Generating visualization...</p>
            </div>
          </div>
        )}
        
        {error && (
          <div className="flex items-center justify-center h-32">
            <p className="text-sm text-destructive">Error: {error}</p>
          </div>
        )}
        
        {!isLoading && !error && (
          <div className="min-h-64 w-full relative overflow-hidden bg-white">
            <TransformWrapper
              ref={transformRef}
              initialScale={0.8}
              minScale={0.2}
              maxScale={4}
              centerOnInit={true}
              limitToBounds={false}
              boundsByDirection={false}
              wheel={{ wheelDisabled: false }}
              pan={{ 
                disabled: false,
                limitToWrapperBounds: false,
                lockAxisX: false,
                lockAxisY: false
              }}
              doubleClick={{ disabled: true }}
              pinch={{ disabled: false }}
            >
              <TransformComponent
                wrapperStyle={{
                  width: '100%',
                  height: '500px',
                  cursor: 'grab'
                }}
                contentStyle={{
                  width: 'auto',
                  height: 'auto',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  minWidth: '100%',
                  minHeight: '100%'
                }}
              >
                <div 
                  ref={mermaidRef} 
                  className="w-full h-full flex justify-center items-center"
                  style={{ minHeight: '200px' }}
                />
              </TransformComponent>
            </TransformWrapper>
            
            {/* Instructions overlay */}
            <div className="absolute top-2 left-2 bg-white/90 backdrop-blur-sm rounded px-2 py-1 text-xs text-gray-600 shadow-sm">
              <div className="flex items-center space-x-1">
                <Move className="h-3 w-3" />
                <span>Drag to pan • Scroll to zoom</span>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default MermaidVisualization; 