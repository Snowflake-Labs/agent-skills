import React, { useState } from 'react';
import type { AgentEvent } from '../types/agent';

interface Props {
  content: string;
  toolEvents?: AgentEvent[];
}

export function ThinkingBlock({ content, toolEvents }: Props) {
  const [expanded, setExpanded] = useState(false);

  const toolUses = toolEvents?.filter((e) => e.type === 'tool_use') || [];
  const hasContent = !!content || toolUses.length > 0;

  if (!hasContent) return null;

  const label = toolUses.length > 0
    ? `Thinking... (${toolUses.length} tool${toolUses.length > 1 ? 's' : ''} used)`
    : 'Thinking...';

  return (
    <div className="thinking-block">
      <span className="thinking-toggle" onClick={() => setExpanded(!expanded)}>
        {expanded ? '▼' : '▶'} {label}
      </span>
      {expanded && content && (
        <p className="thinking-text" style={{ marginTop: 8 }}>{content}</p>
      )}
    </div>
  );
}
