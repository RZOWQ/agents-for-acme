// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function CustomerSupportWidget({
  isChatOpen,
  setIsChatOpen,
  customerMessages,
  customerLoading,
  customerInput,
  setCustomerInput,
  customerSessionId,
  customerMessagesEndRef,
  handleCustomerSend
}) {
  return (
    <>
      {/* Floating Toggle Button */}
      <button 
        className="floating-chat-btn pulse-glow"
        onClick={() => setIsChatOpen(!isChatOpen)}
        aria-label="Toggle Customer Support Chat"
      >
        {isChatOpen ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
        )}
      </button>

      {/* Floating Chat Widget Box */}
      {isChatOpen && (
        <div className="floating-chat-widget glass slide-in">
          <header className="widget-header">
            <div className="widget-title-area">
              <h4>ACME Customer Support</h4>
              <span className="online-badge">Online</span>
            </div>
          </header>
          
          <div className="widget-messages">
            {customerMessages.map((msg) => (
              <div key={msg.id} className={`widget-bubble ${msg.sender === 'user' ? 'user' : 'assistant'}`}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
              </div>
            ))}
            {customerLoading && (
              <div className="widget-bubble assistant">
                <div className="typing-indicator mini">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                </div>
              </div>
            )}
            <div ref={customerMessagesEndRef} />
          </div>

          <form onSubmit={handleCustomerSend} className="widget-input-container">
            <input
              type="text"
              className="widget-input"
              value={customerInput}
              onChange={(e) => setCustomerInput(e.target.value)}
              placeholder={customerSessionId ? "Ask for podcast suggestions..." : "Connecting..."}
              disabled={!customerSessionId || customerLoading}
            />
            <button 
              type="submit" 
              className="widget-send-btn" 
              disabled={!customerSessionId || customerLoading || !customerInput.trim()}
            >
              ➔
            </button>
          </form>
        </div>
      )}
    </>
  );
}
