"use client";
import React, { useEffect, useState } from 'react';
import { shortRepoName, formatDateTime } from '../shared/utils/format';
import { apiClient } from '../shared/api/client';
import { ENDPOINTS } from '../shared/api/endpoints';

interface LeaderboardEntry {
  repo_url: string;
  score: number;
  security_score?: number;
  completed_at: string | null;
  critical_count: number;
}

export default function Leaderboard() {
  const [data, setData] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .get<LeaderboardEntry[]>(ENDPOINTS.leaderboard.list)
      .then((data) => {
        setData(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'var(--green)';
    if (score >= 70) return 'var(--amber)';
    return 'var(--red)';
  };

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--muted)' }} className="mono">
        Loading Leaderboard...
      </div>
    );
  }

  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px', overflow: 'hidden' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', background: 'rgba(255,255,255,0.01)' }}>
        <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Security Leaderboard</h3>
        <p style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '2px' }}>Top secure repositories in this workspace</p>
      </div>

      <div style={{ padding: '10px 0' }}>
        {data.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--muted)', fontSize: '13px' }}>
            No scored repositories found. Run an audit to generate a security score.
          </div>
        ) : (
          data.map((entry, idx) => (
            <div
              key={entry.repo_url}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 20px',
                borderBottom: idx === data.length - 1 ? 'none' : '1px solid var(--border)',
                transition: 'background 0.2s'
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.01)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <span className="mono" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--muted)', width: '24px' }}>
                  #{idx + 1}
                </span>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text)' }}>
                    {shortRepoName(entry.repo_url)}
                  </div>
                  <div className="mono" style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '2px' }}>
                    {entry.completed_at ? formatDateTime(entry.completed_at) : 'recently'} • {entry.critical_count} critical
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ width: '80px', height: '6px', background: 'var(--dim)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${entry.score}%`, height: '100%', background: getScoreColor(entry.score), borderRadius: '3px' }} />
                </div>
                <span className="mono" style={{ fontSize: '13px', fontWeight: 700, color: getScoreColor(entry.score) }}>
                  {entry.score.toFixed(0)}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
