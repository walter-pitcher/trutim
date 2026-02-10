import { useState, useEffect } from 'react';
import ReactFlow, { Background, ReactFlowProvider } from 'reactflow';
import 'reactflow/dist/style.css';
import './DiagramModal.css';

/** Read-only shape node for display in messages (no handles - preview only) */
function ViewShapeNode({ data, type }) {
  const { label = '', imageUrl } = data;
  const shape = type || 'rectangle';
  const baseClass = 'diagram-shape-node';
  const shapeClass = `${baseClass}--${shape}`;
  if (shape === 'image') {
    return (
      <div className={`${baseClass} ${shapeClass}`}>
        {imageUrl ? (
          <img src={imageUrl} alt={label} className="diagram-shape-node__img" />
        ) : (
          <span className="diagram-shape-node__placeholder">Img</span>
        )}
      </div>
    );
  }
  return (
    <div className={`${baseClass} ${shapeClass}`}>
      <span className="diagram-shape-node__label">{label}</span>
    </div>
  );
}

const viewNodeTypes = {
  rectangle: ViewShapeNode,
  rounded: ViewShapeNode,
  diamond: ViewShapeNode,
  ellipse: ViewShapeNode,
  image: ViewShapeNode,
};

/** Decode HTML entities that may appear in flowData (e.g. from data attributes or AI output). */
function decodeHtmlEntities(str) {
  if (typeof str !== 'string') return str;
  const entityMap = {
    '&quot;': '"',
    '&#34;': '"',
    '&amp;': '&',
    '&#38;': '&',
    '&lt;': '<',
    '&#60;': '<',
    '&gt;': '>',
    '&#62;': '>',
    '&#39;': "'",
  };
  return str.replace(/&(?:quot|#34|amp|#38|lt|#60|gt|#62|#39);/g, (m) => entityMap[m] ?? m);
}

/** Validate and normalize flow diagram structure (React Flow format). */
function parseFlowData(raw) {
  if (raw == null) return null;
  const str = typeof raw === 'string' ? raw : String(raw);
  const trimmed = str.trim();
  if (!trimmed) return null;
  const decoded = decodeHtmlEntities(trimmed);
  try {
    const parsed = JSON.parse(decoded);
    if (!parsed || typeof parsed !== 'object') return null;
    const nodes = Array.isArray(parsed.nodes) ? parsed.nodes : [];
    const edges = Array.isArray(parsed.edges) ? parsed.edges : [];
    const normalizedNodes = nodes.map((n, i) => {
      if (!n || typeof n !== 'object') return null;
      const pos = n.position ?? { x: 0, y: 0 };
      return {
        id: String(n.id ?? `node-${i}`),
        type: n.type ?? 'rectangle',
        position: { x: Number(pos.x) || 0, y: Number(pos.y) || 0 },
        data: n.data ?? { label: '' },
      };
    }).filter(Boolean);
    return { nodes: normalizedNodes, edges };
  } catch {
    return null;
  }
}

/** Display a flow diagram from JSON (read-only). Export for use in MessageContent. */
export function FlowDiagramView({ flowData, theme = 'light' }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const result = parseFlowData(flowData);
    if (result) {
      setData(result);
      setError(null);
    } else {
      setData(null);
      setError(flowData?.trim() ? 'Invalid diagram data' : 'Empty diagram');
    }
  }, [flowData]);

  if (error) return <div className="message-content-flowdiagram-error">{error}</div>;
  if (!data) return <div className="message-content-flowdiagram-loading">Loading diagram…</div>;

  return (
    <div className="message-content-flowdiagram-inner" style={{ width: '100%', minWidth: 480, height: 360 }}>
      <ReactFlowProvider>
        <ReactFlow
          nodes={data.nodes}
          edges={data.edges}
          nodeTypes={viewNodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.2}
          maxZoom={2}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          proOptions={{ hideAttribution: true }}
          className="-diagram-flow diagram-flow--view"
          style={{ width: '100%', height: '100%' }}
        >
          <Background color="var(--border)" gap={16} size={0.5} />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
