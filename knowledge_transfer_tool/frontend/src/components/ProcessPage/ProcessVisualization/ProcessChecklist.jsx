import React from 'react';

// This component will show a checklist of populated fields or extraction status.
const ProcessChecklist = ({ processData }) => {
  // Match the backend's 9 user dimensions (including overview)
  const checklist = [
    { field: 'general_description', label: 'Overview' },
    { field: 'scope_included', label: 'Scope Included' },
    { field: 'scope_excluded', label: 'Scope Excluded' },
    { field: 'process_steps', label: 'Process Steps' },
    { field: 'inputs', label: 'Inputs' },
    { field: 'outputs', label: 'Outputs' },
    { field: 'kpis', label: 'KPIs' },
    { field: 'roles_responsibilities', label: 'Roles & Responsibilities' },
    { field: 'exceptions_special_cases', label: 'Exceptions & Special Cases' }
  ];

  const isFieldPopulated = (field) => {
    if (!processData) return false;
    const value = processData[field];
    if (Array.isArray(value)) {
      // Match backend's strict criteria: need at least 2 substantial items (30+ characters each)
      const substantial = value.filter(item => item && item.trim().length >= 30);
      return substantial.length >= 2;
    }
    // For text fields, need at least 100 characters
    return value && value.trim && value.trim().length >= 100;
  };

  const itemStyle = (populated) => ({
    padding: '5px 0',
    color: populated ? 'green' : '#aaa',
    textDecoration: populated ? 'none' : 'line-through',
  });

  const listStyle = {
    listStyleType: 'none',
    paddingLeft: 0,
    fontSize: '0.9em'
  };

  return (
    <div>
      <h5>Documentation Checklist</h5>
      <ul style={listStyle}>
        {checklist.map(item => (
          <li key={item.field} style={itemStyle(isFieldPopulated(item.field))}>
            {isFieldPopulated(item.field) ? '✓' : '✗'} {item.label}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ProcessChecklist;

 