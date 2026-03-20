import React from 'react';
import type { AgentEvent } from '../types/agent';

interface Props {
  events: AgentEvent[];
}

export function ToolOutput({ events }: Props) {
  const toolUses = events.filter((e) => e.type === 'tool_use');
  const toolResults = events.filter((e) => e.type === 'tool_result');

  if (toolUses.length === 0) return null;

  return (
    <>
      {toolUses.map((tool, i) => {
        const result = toolResults[i];
        return (
          <div key={i} className="tool-output">
            <div className="tool-name">{tool.tool_name}</div>
            {tool.tool_input && (
              <pre>
                <code>{formatJson(tool.tool_input)}</code>
              </pre>
            )}
            {result && (
              <pre>
                <code>{formatJson(result.content)}</code>
              </pre>
            )}
          </div>
        );
      })}
    </>
  );
}

function formatJson(str: string): string {
  try {
    const parsed = JSON.parse(str);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return str;
  }
}
