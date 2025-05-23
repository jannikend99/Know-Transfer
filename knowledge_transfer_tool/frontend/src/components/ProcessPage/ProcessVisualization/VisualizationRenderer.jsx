import React from 'react';

// This component will render HTML for visualizations.
const VisualizationRenderer = ({ htmlContent, noContainer = false }) => {
  const containerStyle = {
    flexGrow: 1,
    border: '1px solid #ccc',
    borderRadius: 'var(--border-radius, 8px)',
    padding: 'var(--spacing-unit, 16px)',
    backgroundColor: '#fff',
    overflow: 'auto', // In case the HTML content is large
    minHeight: '200px', // Ensure it has some visible height
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  };

  const noContainerStyle = {
    padding: '0 1.5rem 1.5rem 1.5rem'
  };

  const placeholderStyle = {
    color: '#aaa',
    textAlign: 'center'
  };

  if (!htmlContent) {
    return (
      <div style={noContainer ? noContainerStyle : containerStyle}>
        <p style={placeholderStyle}>AI-generated visualization will appear here once available.</p>
      </div>
    );
  }

  if (noContainer) {
    return (
      <div style={noContainerStyle}>
        <style dangerouslySetInnerHTML={{
          __html: `
            .process-box {
              border: none !important;
              background-color: transparent !important;
              background: none !important;
              padding: 0 !important;
              margin: 0 !important;
              border-radius: 0 !important;
              box-shadow: none !important;
            }
          `
        }} />
        <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
      </div>
    );
  }

  return (
    <div 
      style={containerStyle} 
      dangerouslySetInnerHTML={{ __html: htmlContent }} 
    />
  );
};

export default VisualizationRenderer; 