import React, { useState, useEffect, useRef } from 'react';
import { VegaEmbed } from 'react-vega';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './App.css';

// Automatically resolve backend URL
const BACKEND_URL = window.location.port === '5173' ? 'http://localhost:8000' : '';

import { markdownComponents } from './components/MarkdownComponents';
import { CustomerSupportWidget } from './components/CustomerSupportWidget';

function App() {
  // --- Marketing Agent States ---
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState({ label: 'Starting...', progress: 5 });
  const streamedTextRef = useRef('');
  const messagesEndRef = useRef(null);

  // --- Customer Chatbot States ---
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [customerMessages, setCustomerMessages] = useState([]);
  const [customerInput, setCustomerInput] = useState('');
  const [customerSessionId, setCustomerSessionId] = useState(null);
  const [customerLoading, setCustomerLoading] = useState(false);
  const customerMessagesEndRef = useRef(null);

  // Initialize Marketing Agent session on mount
  useEffect(() => {
    async function initSession() {
      try {
        const res = await fetch(`${BACKEND_URL}/apps/app/users/user/sessions`, {
          method: 'POST',
        });
        const data = await res.json();
        if (data && data.id) {
          setSessionId(data.id);
          setMessages([
            {
              id: 'init',
              sender: 'assistant',
              text: 'Hello! I am the ACME Corp Media Marketing Agent. How can I help you design your next campaign today?',
            },
          ]);
        }
      } catch (e) {
        console.error('Failed to initialize marketing session:', e);
      }
    }
    initSession();
  }, []);

  // Initialize Customer Agent session when chat is opened
  useEffect(() => {
    if (!isChatOpen || customerSessionId) return;

    async function initCustomerSession() {
      try {
        const res = await fetch(`${BACKEND_URL}/customer-apps/customer_app/users/user/sessions`, {
          method: 'POST',
        });
        const data = await res.json();
        if (data && data.id) {
          setCustomerSessionId(data.id);
          setCustomerMessages([
            {
              id: 'c-init',
              sender: 'assistant',
              text: 'Hello! I am your ACME Corp Media Customer Assistant. Ask me to find podcast episodes or look up popular search trends!',
            },
          ]);
        }
      } catch (e) {
        console.error('Failed to initialize customer session:', e);
      }
    }
    initCustomerSession();
  }, [isChatOpen]);

  // Auto-scroll messages (Marketing)
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Auto-scroll messages (Customer)
  useEffect(() => {
    customerMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [customerMessages, customerLoading]);

  // Stage map: ADK agent author → progress label + percent
  const STAGE_MAP = {
    planner_agent:             { label: 'Planning your campaign...', progress: 15 },
    sql_generator_agent:       { label: 'Generating data query...', progress: 35 },
    proposal_generator_agent:  { label: 'Crafting campaign proposal...', progress: 62 },
    critic_agent:              { label: 'Reviewing proposal quality...', progress: 80 },
    refiner_agent:             { label: 'Refining the proposal...', progress: 88 },
  };

  // Handle Marketing Send
  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || !sessionId || loading) return;

    const userMessage = { id: Date.now().toString(), sender: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setLoadingStage({ label: 'Starting...', progress: 5 });
    streamedTextRef.current = '';

    try {
      const response = await fetch(`${BACKEND_URL}/run_sse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_name: 'app',
          user_id: 'user',
          session_id: sessionId,
          streaming: true,
          new_message: {
            role: 'user',
            parts: [{ text: userMessage.text }]
          }
        }),
      });

      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(trimmedLine.slice(6).trim());
              const part = eventData.content?.parts?.[0];
              const author = eventData.author || '';

              // Update stage from author
              if (author && STAGE_MAP[author]) {
                setLoadingStage(STAGE_MAP[author]);
              }

              // Buffer the latest full text (each event replaces previous)
              if (part?.text) {
                streamedTextRef.current = part.text;
                // Detect final formatting stage by content signature
                if (part.text.startsWith('##') || part.text.includes('Campaign:')) {
                  setLoadingStage({ label: 'Preparing your results...', progress: 95 });
                }
              }
            } catch (err) {}
          }
        }
      }
    } catch (err) {
      console.error('Error during streaming:', err);
    } finally {
      setLoading(false);
      const finalText = streamedTextRef.current;
      if (finalText) {
        setMessages((prev) => [
          ...prev,
          { id: Date.now().toString(), sender: 'assistant', text: finalText }
        ]);
      }
      streamedTextRef.current = '';
      setLoadingStage({ label: 'Starting...', progress: 5 });
    }
  };

  // Handle Customer Send
  const handleCustomerSend = async (e) => {
    e.preventDefault();
    if (!customerInput.trim() || !customerSessionId || customerLoading) return;

    const userMessage = { id: Date.now().toString(), sender: 'user', text: customerInput };
    setCustomerMessages((prev) => [...prev, userMessage]);
    setCustomerInput('');
    setCustomerLoading(true);

    let currentAssistantMsgId = null;

    try {
      const response = await fetch(`${BACKEND_URL}/customer-run_sse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_name: 'customer_app',
          user_id: 'user',
          session_id: customerSessionId,
          streaming: true,
          new_message: {
            role: 'user',
            parts: [{ text: userMessage.text }]
          }
        }),
      });

      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(trimmedLine.slice(6).trim());
              const part = eventData.content?.parts?.[0];
              
              if (part) {
                if (part.text) {
                  if (!currentAssistantMsgId) {
                    currentAssistantMsgId = Date.now().toString();
                    setCustomerMessages((prev) => [
                      ...prev,
                      { id: currentAssistantMsgId, sender: 'assistant', text: part.text }
                    ]);
                  } else {
                    setCustomerMessages((prev) =>
                      prev.map((msg) =>
                        msg.id === currentAssistantMsgId
                          ? { ...msg, text: part.text }
                          : msg
                      )
                    );
                  }
                }
              }
            } catch (err) {}
          }
        }
      }
    } catch (err) {
      console.error('Error during streaming:', err);
    } finally {
      setCustomerLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="brand-section">
          <div className="brand-logo">
            <span className="logo-symbol">A</span>
            <h1 className="logo-text">ACME</h1>
          </div>
          <span className="brand-subtitle">Enterprise Control</span>
        </div>

        <nav className="nav-links">
          <a className="nav-link">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>
            Dashboard
          </a>
          <a className="nav-link">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            Workflows
          </a>
          <a className="nav-link active">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
            Marketing
          </a>
          <a className="nav-link">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            Talent Onboarding
          </a>
          <a className="nav-link">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
            AI Insights
          </a>
        </nav>

        <div className="sidebar-footer">
          <a className="nav-link">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
            Settings
          </a>
          <a className="nav-link">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            Support
          </a>
          <div className="user-profile">
            <img className="user-avatar" src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&q=80" alt="Executive User" />
            <div className="user-info">
              <span className="user-name">Executive User</span>
              <span className="user-role">Premium Access</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Chat View */}
      <main className="chat-pane">
        <header className="chat-header">
          <div className="header-title-area">
            <h2>Campaign Overview</h2>
            <p>Real-time campaign creation and visual insights</p>
          </div>
          <div className="header-actions">
            <button className="action-btn">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            </button>
            <button className="action-btn">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
            </button>
            <button className="action-btn primary-action">
              <span>+ Launch Campaign</span>
            </button>
          </div>
        </header>

        <div className="chat-messages">
          {messages.map((msg) => {
            if (msg.sender === 'user') {
              return (
                <div key={msg.id} className="message-bubble user">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                </div>
              );
            } else if (msg.sender === 'assistant') {
              return (
                <div key={msg.id} className="message-bubble assistant">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{msg.text}</ReactMarkdown>
                </div>
              );
            }
            return null;
          })}
          {loading && (
            <div className="loading-progress-bubble glass">
              <div className="loading-stage-row">
                <span className="loading-pulse-dot" />
                <span className="loading-stage-label">{loadingStage.label}</span>
                <span className="loading-pct">{loadingStage.progress}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${loadingStage.progress}%` }} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSend} className="chat-input-container">
          <input
            type="text"
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={sessionId ? "Ask the agent to create a campaign..." : "Initializing session..."}
            disabled={!sessionId || loading}
          />
          <button type="submit" className="send-button" disabled={!sessionId || loading || !input.trim()}>
            Send
          </button>
        </form>
      </main>

      {/* Floating Chat Button (Bottom-Right) */}
      <CustomerSupportWidget
        isChatOpen={isChatOpen}
        setIsChatOpen={setIsChatOpen}
        customerMessages={customerMessages}
        customerLoading={customerLoading}
        customerInput={customerInput}
        setCustomerInput={setCustomerInput}
        customerSessionId={customerSessionId}
        customerMessagesEndRef={customerMessagesEndRef}
        handleCustomerSend={handleCustomerSend}
      />
    </div>
  );
}

export default App;
