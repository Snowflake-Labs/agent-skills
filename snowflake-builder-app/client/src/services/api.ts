/**
 * API client for the Snowflake Builder App backend.
 */

import type { Project, Conversation } from '../types/agent';

const BASE = '/api';

export async function fetchProjects(): Promise<Project[]> {
  const res = await fetch(`${BASE}/projects`);
  if (!res.ok) throw new Error(`Failed to fetch projects: ${res.statusText}`);
  return res.json();
}

export async function createProject(name: string, description = ''): Promise<Project> {
  const res = await fetch(`${BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) throw new Error(`Failed to create project: ${res.statusText}`);
  return res.json();
}

export async function fetchConversations(projectId: string): Promise<Conversation[]> {
  const res = await fetch(`${BASE}/projects/${projectId}/conversations`);
  if (!res.ok) throw new Error(`Failed to fetch conversations: ${res.statusText}`);
  return res.json();
}

/**
 * Invoke the agent and return an EventSource-like readable stream.
 */
export async function invokeAgent(
  message: string,
  projectId: string,
  conversationId?: string,
): Promise<Response> {
  return fetch(`${BASE}/invoke_agent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      project_id: projectId,
      conversation_id: conversationId,
    }),
  });
}
