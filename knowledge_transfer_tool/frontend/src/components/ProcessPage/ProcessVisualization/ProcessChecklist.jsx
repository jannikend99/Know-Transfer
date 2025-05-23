import React from 'react';

// This component will show a checklist of populated fields or extraction status.
const ProcessChecklist = ({ processData }) => {
  const checklist = [
    { field: 'general_description', label: 'General Description' },
    { field: 'process_steps', label: 'Process Steps' },
    { field: 'scope', label: 'Scope' },
    { field: 'inputs', label: 'Inputs' },
    { field: 'outputs', label: 'Outputs' },
    { field: 'kpis', label: 'KPIs' },
    { field: 'roles_responsibilities', label: 'Roles & Responsibilities' },
    { field: 'exceptions_special_cases', label: 'Exceptions & Special Cases' },
    { field: 'visualization_graph', label: 'Visualization Graph' }
  ];

  const isFieldPopulated = (field) => {
    if (!processData) return false;
    const value = processData[field];
    if (Array.isArray(value)) {
      return value.length > 0;
    }
    return !!value; // True if value is truthy (not null, undefined, empty string, 0, false)
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
      <h5>Extraction Checklist</h5>
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

 