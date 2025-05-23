import React from 'react';
import { Link } from 'react-router-dom';
import { BookOpen } from 'lucide-react';

// Basic Header component
const Header = () => {
  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center px-4">
        <Link to="/" className="flex items-center space-x-2">
          <BookOpen className="h-6 w-6" />
          <span className="font-bold">Knowledge Transfer Tool</span>
        </Link>
        <nav className="ml-auto flex items-center space-x-4">
          <Link 
            to="/" 
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
          >
            Home
          </Link>
          <a 
            href="https://github.com/yourusername/knowledge-transfer-tool" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
          >
            GitHub
          </a>
        </nav>
      </div>
    </header>
  );
};

export default Header; 