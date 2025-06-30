import React from 'react';
// import logo from './logo.svg'; // Example logo, can be removed or replaced
// import './App.css'; // Example App specific CSS, can be removed or replaced
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import 'reactflow/dist/style.css';
import HomePage from './components/HomePage/HomePage'; // Placeholder
import ProcessPage from './components/ProcessPage/ProcessPage'; // Placeholder
import Layout from './components/shared/Layout'; // Placeholder for Layout

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/process/:processId" element={<ProcessPage />} />
          {/* Add other routes here */}
        </Routes>
      </Layout>
    </Router>
  );
}

export default App; 