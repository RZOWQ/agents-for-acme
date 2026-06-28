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
import { VegaEmbed } from 'react-vega';

export const markdownComponents = {
  code({ node, inline, className, children, ...props }) {
    const match = /language-([\w-]+)/.exec(className || '');
    const language = match ? match[1] : '';
    if (!inline) {
      if (language === 'vega-lite') {
        try {
          const rawSpec = JSON.parse(String(children).trim());
          
          if (Object.keys(rawSpec).length === 0) {
             throw new Error("Waiting for complete spec...");
          }

          const { _caption: insightCaption, title: chartTitle, ...specBody } = rawSpec;

          const markType = typeof specBody.mark === 'string'
            ? specBody.mark
            : (specBody.mark?.type || '');
          const isArc  = markType === 'arc';
          const isBar  = markType === 'bar';
          const isLine = markType === 'line';

          const chartWidth  = isArc ? 300 : 460;
          const chartHeight = isArc ? 300 : (isBar ? 220 : 250);

          const configuredSpec = {
            ...specBody,
            width:  chartWidth,
            height: chartHeight,
          };
          
          const cardIcon = isArc ? '🍩' : isBar ? '📊' : isLine ? '📈' : '⚡';

          return (
            <div className="inline-chart-container glass" style={{ width: '100%', maxWidth: '600px', overflow: 'hidden' }}>
              <div className="chart-card-title">{cardIcon} {chartTitle || 'Campaign Insights'}</div>
              <div className="vega-chart-container" style={{ width: '100%', minHeight: `${chartHeight + 20}px` }}>
                <VegaEmbed
                  spec={configuredSpec}
                  options={{ actions: false }}
                  style={{ width: '100%' }}
                />
              </div>
              {insightCaption && (
                <div style={{
                  fontSize: '12px',
                  color: 'var(--accent-secondary, #7dd3fc)',
                  padding: '6px 12px 10px',
                  lineHeight: '1.5',
                  borderTop: '1px solid rgba(255,255,255,0.07)',
                  marginTop: '4px',
                  whiteSpace: 'normal',
                  wordBreak: 'break-word',
                  overflowWrap: 'break-word',
                  width: '100%',
                  boxSizing: 'border-box',
                }}>
                  💡 {insightCaption}
                </div>
              )}
            </div>
          );
        } catch (e) {
          return <pre className={className} {...props}>{children}</pre>;
        }
      }
      if (language === 'metric-card') {
        try {
          const data = JSON.parse(String(children).trim());
          return (
            <div className="a2ui-metric-card glass" style={{ width: '100%', maxWidth: '350px', padding: '16px', margin: '12px 0', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '12px', background: 'rgba(255,255,255,0.03)', boxSizing: 'border-box', overflow: 'hidden' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', whiteSpace: 'normal', wordBreak: 'break-word' }}>{data.title}</div>
              <div style={{ fontSize: 'clamp(16px, 4vw, 32px)', fontWeight: 'bold', color: 'var(--accent-secondary)', marginTop: '8px', whiteSpace: 'normal', wordBreak: 'break-word', overflowWrap: 'break-word', lineHeight: '1.2', width: '100%' }}>{data.metric_value}</div>
            </div>
          );
        } catch (e) {
          return <pre className={className} {...props}>{children}</pre>;
        }
      }
      if (language === 'alert-banner') {
        try {
          const data = JSON.parse(String(children).trim());
          return (
            <div className="a2ui-alert-banner glass" style={{ width: '100%', maxWidth: '600px', padding: '14px 18px', margin: '12px 0', borderLeft: '4px solid #f59e0b', borderRadius: '8px', background: 'rgba(245,158,11,0.05)', boxSizing: 'border-box' }}>
              <div style={{ fontWeight: '600', color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                ⚠️ {data.title}
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-primary)', marginTop: '6px', lineHeight: '1.5', wordBreak: 'break-word', overflowWrap: 'break-word', whiteSpace: 'pre-wrap' }}>{data.text_content}</div>
            </div>
          );
        } catch (e) {
          return <pre className={className} {...props}>{children}</pre>;
        }
      }
    }
    return <code className={className} {...props}>{children}</code>;
  }
};
