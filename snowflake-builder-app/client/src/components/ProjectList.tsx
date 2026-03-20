import React from 'react';
import type { Project } from '../types/agent';

interface Props {
  projects: Project[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export function ProjectList({ projects, activeId, onSelect, onNew }: Props) {
  return (
    <div style={{ marginBottom: 24 }}>
      <h2>Projects</h2>
      <button className="new-button" onClick={onNew}>
        + New Project
      </button>
      {projects.map((proj) => (
        <div
          key={proj.id}
          className={`sidebar-item ${proj.id === activeId ? 'active' : ''}`}
          onClick={() => onSelect(proj.id)}
        >
          {proj.name}
        </div>
      ))}
    </div>
  );
}
