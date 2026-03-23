import React, { useState, useCallback, useRef, useEffect } from 'react';
import { ChatInput } from './components/ChatInput';
import { ChatMessage } from './components/ChatMessage';
import { DatabaseSelector } from './components/DatabaseSelector';
import { useSSEStream } from './hooks/useSSEStream';
import { invokeAgent, fetchDatabases } from './services/api';
import type { ChatMessage as ChatMsg, AgentEvent, DatabaseInfo } from './types/agent';

const DEFAULT_PROJECT_ID = 'default';

export default function App() {
  const [activeConversation, setActiveConversation] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [databases, setDatabases] = useState<DatabaseInfo[]>([]);
  const [dbLoading, setDbLoading] = useState(true);
  const [selectedDatabase, setSelectedDatabase] = useState<string | null>(null);
  const [selectedSchema, setSelectedSchema] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const currentEventsRef = useRef<AgentEvent[]>([]);

  const { events, isStreaming, error, startStream, reset: resetStream } = useSSEStream();

  // Auto-scroll on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, events]);

  // Load databases on mount
  useEffect(() => {
    fetchDatabases()
      .then(setDatabases)
      .catch((err) => console.error('Failed to load databases:', err))
      .finally(() => setDbLoading(false));
  }, []);

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
        const response = await invokeAgent(
          message,
          DEFAULT_PROJECT_ID,
          activeConversation || undefined,
          selectedDatabase || undefined,
          selectedSchema || undefined,
        );
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
    [activeConversation, selectedDatabase, selectedSchema, startStream, resetStream],
  );

  const handleContextChange = useCallback(
    (db: string | null, schema: string | null) => {
      setSelectedDatabase(db);
      setSelectedSchema(schema);
      // Reset conversation when context changes
      setActiveConversation(null);
      setMessages([]);
      resetStream();
    },
    [resetStream],
  );

  return (
    <div className="app-layout">
      <div className="sidebar">
        <DatabaseSelector
          databases={databases}
          loading={dbLoading}
          selectedDatabase={selectedDatabase}
          selectedSchema={selectedSchema}
          onSelect={handleContextChange}
        />
      </div>
      <div className="main-content">
        <div className="header">
          <div className="header-title">
            <h1>Snowflake Claude Agent</h1>
            <a
              className="app-readme-link"
              href="https://github.com/Snowflake-Labs/snowflake-ai-kit/tree/main/builder-apps/claude-agent"
              target="_blank"
              rel="noopener noreferrer"
            >
              Learn more about the app ↗
            </a>
          </div>
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
              <h2>Snowflake Claude Agent App</h2>
              <p>
                A Claude Code agent interface with integrated Snowflake tools.
                Ask me to query data, explore schemas, manage pipelines, or build on Snowflake.
              </p>
              {selectedDatabase && selectedSchema ? (
                <div style={{ color: 'var(--sf-text-muted)', fontSize: 13 }}>
                  Context: {selectedDatabase}.{selectedSchema}
                </div>
              ) : (
                <div style={{ color: 'var(--sf-text-muted)', fontSize: 13 }}>
                  Select a database and schema to set context
                </div>
              )}
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
