import React, { useState } from 'react';

interface Props {
  content: string;
}

export function ThinkingBlock({ content }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (!content) return null;

  return (
    <div className="thinking-block">
      <span className="thinking-toggle" onClick={() => setExpanded(!expanded)}>
        {expanded ? '▼' : '▶'} Thinking...
      </span>
      {expanded && <p style={{ marginTop: 8 }}>{content}</p>}
    </div>
  );
}
