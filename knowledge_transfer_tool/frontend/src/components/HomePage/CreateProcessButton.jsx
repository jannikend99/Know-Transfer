import React from 'react';
import Button from '@mui/material/Button';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';

const CreateProcessButton = ({ onClick, isLoading }) => {
  return (
    <Button 
      variant="contained" 
      color="primary" 
      startIcon={<AddCircleOutlineIcon />} 
      onClick={onClick}
      disabled={isLoading}
      sx={{ 
        // minWidth: '200px', // Optional: set a min-width if desired
        // height: '48px' // Optional: adjust height to match TextField if needed
      }}
    >
      Create New Process
    </Button>
  );
};

export default CreateProcessButton; 