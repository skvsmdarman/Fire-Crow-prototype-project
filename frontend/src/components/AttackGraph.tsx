"use client";
import React, { useEffect, useState } from 'react';
import ReactFlow, { Node, Edge, Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';
import { buildApiUrl } from '../shared/api/baseUrl';

interface AttackGraphProps {
  jobId: string;
  token: string;
}

interface AttackGraphNode {
  id: string;
  label: string;
  severity?: string;
}

interface AttackGraphResponse {
  nodes: AttackGraphNode[];
  edges: Edge[];
}

export default function AttackGraph({ jobId, token }: AttackGraphProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(buildApiUrl(`/audit/job/${jobId}/graph`), {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(async (res) => {
        if (!res.ok) {
          throw new Error('Attack graph unavailable');
        }
        return res.json();
      })
      .then((data: AttackGraphResponse) => {
        setError(null);
        setNodes(data.nodes.map((n) => ({
          id: n.id,
          data: { label: n.label, severity: n.severity },
          position: { x: Math.random() * 500, y: Math.random() * 300 },
          style: { background: n.severity === 'critical' ? '#ff4444' : '#ffaa44' }
        })));
        setEdges(data.edges);
      })
      .catch(() => {
        setNodes([]);
        setEdges([]);
        setError('Attack graph unavailable for this audit yet.');
      });
  }, [jobId, token]);

  if (error) {
    return <div style={{ padding: '20px', color: 'var(--muted)', fontSize: '13px', textAlign: 'center' }}>{error}</div>;
  }

  return (
    <div style={{ height: '500px', width: '100%' }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
