import React from 'react';
import type { Conversation } from '../types/agent';

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export function ConversationList({ conversations, activeId, onSelect, onNew }: Props) {
  return (
    <div>
      <h2>Conversations</h2>
      <button className="new-button" onClick={onNew}>
        + New Conversation
      </button>
      {conversations.map((conv) => (
        <div
          key={conv.id}
          className={`sidebar-item ${conv.id === activeId ? 'active' : ''}`}
          onClick={() => onSelect(conv.id)}
        >
          {conv.title || 'Untitled'}
        </div>
      ))}
      {conversations.length === 0 && (
        <div style={{ fontSize: 13, color: 'var(--sf-text-muted)', padding: '8px 12px' }}>
          No conversations yet
        </div>
      )}
    </div>
  );
}
