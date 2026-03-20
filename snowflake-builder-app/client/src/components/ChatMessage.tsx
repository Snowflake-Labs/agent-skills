import React from 'react';
import type { ChatMessage as ChatMessageType } from '../types/agent';
import { ThinkingBlock } from './ThinkingBlock';
import { ToolOutput } from './ToolOutput';

interface Props {
  message: ChatMessageType;
}

export function ChatMessage({ message }: Props) {
  const thinkingEvents = message.events?.filter((e) => e.type === 'thinking') || [];
  const toolEvents = message.events?.filter((e) => e.type === 'tool_use' || e.type === 'tool_result') || [];
  const thinkingText = thinkingEvents.map((e) => e.content).join('');

  return (
    <div className={`chat-message ${message.role}`}>
      <div className="role-label">{message.role === 'user' ? 'You' : 'Snowflake Agent'}</div>
      {thinkingText && <ThinkingBlock content={thinkingText} />}
      {toolEvents.length > 0 && <ToolOutput events={toolEvents} />}
      <div dangerouslySetInnerHTML={{ __html: simpleMarkdown(message.content) }} />
    </div>
  );
}

/** Minimal markdown → HTML (code blocks, bold, inline code). */
function simpleMarkdown(text: string): string {
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>');
}
