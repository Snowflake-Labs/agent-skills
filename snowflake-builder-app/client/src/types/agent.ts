/**
 * TypeScript types for agent events and API responses.
 */

export interface AgentEvent {
  type: 'text' | 'thinking' | 'tool_use' | 'tool_result' | 'error' | 'done';
  content: string;
  tool_name?: string;
  tool_input?: string;
  conversation_id?: string;
  session_id?: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  project_id: string;
  title: string;
  claude_session_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  events?: AgentEvent[];
  timestamp: string;
}
