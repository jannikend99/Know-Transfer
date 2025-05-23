import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { ArrowRight, Trash2, Calendar, BarChart3 } from 'lucide-react';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "../ui/card";

import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "../ui/alert-dialog";

const ProcessCard = ({ process, onDelete }) => {
  const [isDeleting, setIsDeleting] = useState(false);

  // Generate a title: use process.title if available, then general_description, then ID
  let displayTitle = 'Untitled Process';
  if (process.title) {
    displayTitle = process.title;
  } else if (process.general_description) {
    const words = process.general_description.split(' ');
    displayTitle = words.slice(0, 5).join(' '); // Shorter title from description
    if (words.length > 5) displayTitle += '...';
  } else if (process.id) {
    displayTitle = `Process ${process.id.substring(0, 8)}`;
  }

  // Clean description preview - limit to 120 characters
  const displayDescription = process.general_description || 'No description available.';
  const truncatedDescription = displayDescription.length > 120 
    ? displayDescription.substring(0, 120).trim() + '...' 
    : displayDescription;

  // Calculate completion status
  const getProcessCompletion = () => {
    if (!process) return { completed: 0, total: 0, percentage: 0 };

    const categories = [
      { key: 'general_description', check: (data) => data.general_description && data.general_description.trim() },
      { key: 'scope', check: (data) => data.scope && data.scope.trim() },
      { key: 'process_steps', check: (data) => Array.isArray(data.process_steps) && data.process_steps.length > 0 },
      { key: 'inputs', check: (data) => Array.isArray(data.inputs) && data.inputs.length > 0 },
      { key: 'outputs', check: (data) => Array.isArray(data.outputs) && data.outputs.length > 0 },
      { key: 'kpis', check: (data) => Array.isArray(data.kpis) && data.kpis.length > 0 },
      { key: 'roles_responsibilities', check: (data) => Array.isArray(data.roles_responsibilities) && data.roles_responsibilities.length > 0 },
      { key: 'exceptions_special_cases', check: (data) => Array.isArray(data.exceptions_special_cases) && data.exceptions_special_cases.length > 0 }
    ];

    const completed = categories.filter(cat => cat.check(process)).length;
    const percentage = Math.round((completed / categories.length) * 100);

    return { completed, total: categories.length, percentage };
  };

  const completion = getProcessCompletion();

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      const response = await fetch(`/api/processes/${process.id}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete process');
      }
      
      // Call the parent component's delete handler
      if (onDelete) {
        onDelete(process.id);
      }
    } catch (error) {
      console.error('Error deleting process:', error);
      // You might want to show an error toast here
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Card className="h-full flex flex-col hover:shadow-lg transition-shadow duration-300 group">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg font-semibold line-clamp-1 group-hover:text-primary transition-colors">
              {displayTitle}
            </CardTitle>
            <div className="flex items-center text-xs text-muted-foreground mt-1">
              <Calendar className="h-3 w-3 mr-1" />
              {process.created_at ? new Date(process.created_at).toLocaleDateString() : 'N/A'}
            </div>
          </div>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity border border-transparent hover:border-red-500 hover:bg-transparent"
                disabled={isDeleting}
              >
                <Trash2 className="h-4 w-4 text-foreground hover:text-red-500 transition-colors" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Process</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete "{displayTitle}"? This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDelete}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  {isDeleting ? 'Deleting...' : 'Delete'}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardHeader>
      
      <CardContent className="flex-grow pb-4">
        <div className="h-16 mb-3">
          <CardDescription className="text-sm text-muted-foreground line-clamp-3 leading-relaxed h-full overflow-hidden">
            {truncatedDescription}
          </CardDescription>
        </div>
        <div className="flex items-center mt-2">
          <div className="flex items-center space-x-2 flex-1">
            <BarChart3 className="h-3 w-3 text-primary" />
            <div className="flex-1 bg-muted rounded-full h-1.5 max-w-16">
              <div 
                className="bg-primary h-1.5 rounded-full transition-all duration-300" 
                style={{ width: `${completion.percentage}%` }}
              ></div>
            </div>
            <span className="text-xs font-medium text-muted-foreground">
              {completion.percentage}%
            </span>
          </div>
          <Badge 
            variant={completion.percentage === 100 ? "default" : "secondary"} 
            className="ml-2 text-xs"
          >
            {completion.completed}/{completion.total}
          </Badge>
        </div>
      </CardContent>
      
      <CardFooter className="pt-0">
        <Button
          asChild
          variant="outline"
          className="w-full group/button"
        >
          <RouterLink to={`/process/${process.id}`}>
            View Details
            <ArrowRight className="ml-2 h-4 w-4 group-hover/button:translate-x-1 transition-transform" />
          </RouterLink>
        </Button>
      </CardFooter>
    </Card>
  );
};

export default ProcessCard; 