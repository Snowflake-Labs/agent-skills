import React, { useState, useCallback, useRef, useEffect } from 'react';
import { ChatInput } from './components/ChatInput';
import { ChatMessage } from './components/ChatMessage';
import { ConversationList } from './components/ConversationList';
import { ProjectList } from './components/ProjectList';
import { useSSEStream } from './hooks/useSSEStream';
import { invokeAgent, createProject, fetchProjects, fetchConversations } from './services/api';
import type { ChatMessage as ChatMsg, Project, Conversation, AgentEvent } from './types/agent';

const DEFAULT_PROJECT_ID = 'default';

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeProject, setActiveProject] = useState<string>(DEFAULT_PROJECT_ID);
  const [activeConversation, setActiveConversation] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const currentEventsRef = useRef<AgentEvent[]>([]);

  const { events, isStreaming, error, startStream, reset: resetStream } = useSSEStream();

  // Auto-scroll on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, events]);

  // Accumulate streaming events into assistant message
  useEffect(() => {
    if (events.length === 0) return;

    currentEventsRef.current = events;
    const textEvents = events.filter((e) => e.type === 'text');
    const content = textEvents.map((e) => e.content).join('');

    // Track conversation ID from events
    const convId = events.find((e) => e.conversation_id)?.conversation_id;
    if (convId && !activeConversation) {
      setActiveConversation(convId);
    }

    setMessages((prev) => {
      const copy = [...prev];
      const lastIdx = copy.length - 1;
      if (lastIdx >= 0 && copy[lastIdx].role === 'assistant') {
        copy[lastIdx] = { ...copy[lastIdx], content, events: [...events] };
      }
      return copy;
    });
  }, [events, activeConversation]);

  const handleSend = useCallback(
    async (message: string) => {
      // Add user message
      const userMsg: ChatMsg = {
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      };

      // Add placeholder assistant message
      const assistantMsg: ChatMsg = {
        role: 'assistant',
        content: '',
        events: [],
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      resetStream();
      currentEventsRef.current = [];

      try {
        const response = await invokeAgent(message, activeProject, activeConversation || undefined);
        if (!response.ok) {
          const err = await response.text();
          setMessages((prev) => {
            const copy = [...prev];
            copy[copy.length - 1] = {
              ...copy[copy.length - 1],
              content: `Error: ${err}`,
            };
            return copy;
          });
          return;
        }
        startStream(response);
      } catch (err) {
        setMessages((prev) => {
          const copy = [...prev];
          copy[copy.length - 1] = {
            ...copy[copy.length - 1],
            content: `Connection error: ${err instanceof Error ? err.message : String(err)}`,
          };
          return copy;
        });
      }
    },
    [activeProject, activeConversation, startStream, resetStream],
  );

  const handleNewProject = useCallback(async () => {
    const name = prompt('Project name:');
    if (!name) return;
    try {
      const project = await createProject(name);
      setProjects((prev) => [...prev, project]);
      setActiveProject(project.id);
      setActiveConversation(null);
      setMessages([]);
    } catch (err) {
      console.error('Failed to create project:', err);
    }
  }, []);

  const handleNewConversation = useCallback(() => {
    setActiveConversation(null);
    setMessages([]);
    resetStream();
  }, [resetStream]);

  return (
    <div className="app-layout">
      <div className="sidebar">
        <ProjectList
          projects={projects}
          activeId={activeProject}
          onSelect={(id) => {
            setActiveProject(id);
            setActiveConversation(null);
            setMessages([]);
          }}
          onNew={handleNewProject}
        />
        <ConversationList
          conversations={conversations}
          activeId={activeConversation}
          onSelect={(id) => setActiveConversation(id)}
          onNew={handleNewConversation}
        />
      </div>
      <div className="main-content">
        <div className="header">
          <span className="logo">Snowflake</span>
          <h1>Builder App</h1>
          {isStreaming && (
            <div className="streaming-indicator">
              <div className="dot" />
              <div className="dot" />
              <div className="dot" />
            </div>
          )}
        </div>
        <div className="chat-container">
          {messages.length === 0 && (
            <div className="empty-state">
              <h2>Snowflake Builder App</h2>
              <p>
                A Claude Code agent interface with integrated Snowflake tools.
                Ask me to query data, explore schemas, manage pipelines, or build on Snowflake.
              </p>
              <div style={{ color: 'var(--sf-text-muted)', fontSize: 13 }}>
                Try: "Show me all databases" or "What tables are in SNOWFLAKE_SAMPLE_DATA.TPCH_SF1?"
              </div>
            </div>
          )}
          {messages.map((msg, i) => (
            <ChatMessage key={i} message={msg} />
          ))}
          {error && (
            <div style={{ color: 'var(--sf-red)', padding: '8px 24px', fontSize: 14 }}>
              Stream error: {error}
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
