import React from 'react';

// Basic layout component
const Layout = ({ children }) => {
  return (
    <div className="h-screen overflow-hidden bg-background font-sans antialiased">
      {children}
    </div>
  );
};

export default Layout; 