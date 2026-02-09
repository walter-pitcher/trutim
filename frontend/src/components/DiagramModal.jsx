import { useState, useCallback, useRef, useEffect } from 'react';
import ReactFlow, {
  Background,
  Controls,
  addEdge,
  useNodesState,
  useEdgesState,
  ReactFlowProvider,
  Panel,
  MarkerType,
  useReactFlow,
  Handle,
  Position,
} from 'reactflow';
import { ContentCreateIcon, XIcon } from './icons';
import 'reactflow/dist/style.css';
import './DiagramModal.css';

const SHAPE_TYPES = {
  rectangle: { label: 'Rectangle', shape: 'rect' },
  rounded: { label: 'Rounded', shape: 'rounded' },
  diamond: { label: 'Diamond', shape: 'diamond' },
  ellipse: { label: 'Ellipse', shape: 'ellipse' },
  image: { label: 'Image', shape: 'image' },
};

const NODE_WIDTH = 140;
const NODE_HEIGHT = 48;

function ShapeNode({ data, selected, type, id }) {
  const { label = '', isEditing = false, imageUrl } = data;
  const shape = type || 'rectangle';
  const baseClass = 'diagram-shape-node';
  const shapeClass = `${baseClass}--${shape}`;
  const inputRef = useRef(null);
  const { setNodes } = useReactFlow();

  const handleDoubleClick = useCallback(() => {
    if (shape === 'image') return;
    setNodes((nds) =>
      nds.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, isEditing: true } } : { ...n, data: { ...n.data, isEditing: false } }
      )
    );
  }, [id, setNodes]);

  const handleBlur = useCallback(() => {
    const value = inputRef.current?.value?.trim() || 'Node';
    setNodes((nds) =>
      nds.map((n) =>
        n.id === id ? { ...n, data: { ...n.data, label: value, isEditing: false } } : n
      )
    );
  }, [id, setNodes]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        inputRef.current?.blur();
      }
    },
    []
  );

  if (shape === 'image') {
    return (
      <div
        className={`${baseClass} ${shapeClass} ${selected ? 'selected' : ''}`}
        draggable={false}
      >
        <Handle type="target" position={Position.Left} className="diagram-handle" />
        <Handle type="target" position={Position.Top} className="diagram-handle" />
        <Handle type="source" position={Position.Right} className="diagram-handle" />
        <Handle type="source" position={Position.Bottom} className="diagram-handle" />
        {imageUrl ? (
          <img src={imageUrl} alt={label} className="diagram-shape-node__img" />
        ) : (
          <span className="diagram-shape-node__placeholder">Img</span>
        )}
      </div>
    );
  }

  return (
    <div
      className={`${baseClass} ${shapeClass} ${selected ? 'selected' : ''}`}
      onDoubleClick={handleDoubleClick}
    >
      <Handle type="target" position={Position.Left} className="diagram-handle" />
      <Handle type="target" position={Position.Top} className="diagram-handle" />
      <Handle type="source" position={Position.Right} className="diagram-handle" />
      <Handle type="source" position={Position.Bottom} className="diagram-handle" />
      <div className="nodrag nopan">
        {isEditing ? (
          <input
            ref={inputRef}
            type="text"
            className="diagram-shape-node__input"
            defaultValue={label}
            autoFocus
            onBlur={handleBlur}
            onKeyDown={handleKeyDown}
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="diagram-shape-node__label">{label}</span>
        )}
      </div>
    </div>
  );
}

const nodeTypes = {
  rectangle: ShapeNode,
  rounded: ShapeNode,
  diamond: ShapeNode,
  ellipse: ShapeNode,
  image: ShapeNode,
};

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

let nodeId = 1;

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
    // Ensure nodes have required React Flow fields (position, etc.)
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

function ImageUrlInput({ onInsert, onCancel }) {
  const [url, setUrl] = useState('');
  return (
    <div className="diagram-image-url-row">
      <input
        type="url"
        placeholder="Paste image URL"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        className="diagram-image-url-input"
      />
      <button type="button" className="diagram-tool-btn" onClick={() => url && onInsert(url)}>
        Insert
      </button>
      <button type="button" className="diagram-tool-btn" onClick={onCancel}>
        Cancel
      </button>
    </div>
  );
}

function DiagramEditor({ onClose, onInsert, theme, initialData }) {
  const reactFlowWrapper = useRef(null);
  const reactFlowInstance = useRef(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    if (initialData) {
      try {
        const data = typeof initialData === 'string' ? JSON.parse(initialData) : initialData;
        if (data?.nodes?.length) {
          setNodes(data.nodes);
          const maxId = Math.max(0, ...data.nodes.map((n) => {
            const m = String(n.id || '').match(/node-(\d+)/);
            return m ? parseInt(m[1], 10) : 0;
          }));
          nodeId = maxId + 1;
        }
        if (data?.edges?.length) setEdges(data.edges);
      } catch (_) {}
    }
  }, [initialData]);
  const [showImagePicker, setShowImagePicker] = useState(false);
  const [pendingDropPosition, setPendingDropPosition] = useState(null);
  const [pendingDropShape, setPendingDropShape] = useState(null);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed } }, eds)),
    [setEdges]
  );

  const addNode = useCallback(
    (shape, position, imageUrl = null) => {
      const id = `node-${nodeId++}`;
      const pos = position || {
        x: 100 + (nodes.length % 3) * 180,
        y: 80 + Math.floor(nodes.length / 3) * 100,
      };
      const data = shape === 'image' ? { label: '', imageUrl } : { label: 'Node' };
      const newNode = {
        id,
        type: shape,
        position: pos,
        data,
      };
      setNodes((nds) => [...nds, newNode]);
    },
    [nodes.length, setNodes]
  );

  const onDragStart = useCallback((e, shape) => {
    e.dataTransfer.setData('application/reactflow', shape);
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      const shape = e.dataTransfer.getData('application/reactflow');
      if (!shape) return;
      const instance = reactFlowInstance.current;
      if (!instance) return;
      const position = instance.screenToFlowPosition({ x: e.clientX, y: e.clientY });
      if (shape === 'image') {
        setShowImagePicker(true);
        setPendingDropPosition(position);
        setPendingDropShape(shape);
      } else {
        addNode(shape, position);
      }
    },
    [addNode]
  );

  const onDragOver = useCallback((e) => e.preventDefault(), []);

  const handleImageSelect = useCallback(
    (url) => {
      if (pendingDropShape === 'image') {
        const pos = pendingDropPosition || {
          x: 100 + (nodes.length % 3) * 180,
          y: 80 + Math.floor(nodes.length / 3) * 100,
        };
        addNode('image', pos, url);
      }
      setShowImagePicker(false);
      setPendingDropPosition(null);
      setPendingDropShape(null);
    },
    [pendingDropPosition, pendingDropShape, addNode, nodes.length]
  );

  const handleImageFile = useCallback(
    (e) => {
      const file = e.target.files?.[0];
      if (!file?.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = () => handleImageSelect(reader.result);
      reader.readAsDataURL(file);
      e.target.value = '';
    },
    [handleImageSelect]
  );

  const deleteSelected = useCallback(() => {
    setNodes((nds) => nds.filter((n) => !n.selected));
    setEdges((eds) => eds.filter((e) => !e.selected));
  }, [setNodes, setEdges]);

  const clearAll = useCallback(() => {
    setNodes([]);
    setEdges([]);
  }, [setNodes, setEdges]);

  const handleExport = useCallback(() => {
    if (nodes.length === 0) return;
    setIsExporting(true);
    try {
      const flowData = JSON.stringify({ nodes, edges });
      onInsert?.(flowData);
      onClose?.();
    } finally {
      setIsExporting(false);
    }
  }, [nodes, edges, onInsert, onClose]);

  const hasContent = nodes.length > 0;

  return (
    <div className="diagram-modal-overlay" onClick={onClose}>
      <div className="diagram-modal diagram-modal--flow" onClick={(e) => e.stopPropagation()}>
        <div className="diagram-modal-header">
          <div className="diagram-modal-title">
            <ContentCreateIcon size={20} />
            <span>Diagram Editor</span>
          </div>
          <button type="button" onClick={onClose} className="diagram-modal-close" title="Close">
            <XIcon size={18} />
          </button>
        </div>

        <div className="diagram-modal-body">
          <div className="diagram-toolbar">
            <div className="diagram-toolbar-group">
              <span className="diagram-toolbar-label">Shapes</span>
              <div className="diagram-shapes">
                {Object.entries(SHAPE_TYPES).map(([key, { label, shape }]) => (
                  <button
                    key={key}
                    type="button"
                    className="diagram-shape-btn"
                    onDragStart={(e) => onDragStart(e, key)}
                    draggable
                    title={`Drag ${label} to canvas`}
                  >
                    {shape === 'image' ? (
                      <span className="diagram-shape-preview diagram-shape-preview--image">📷</span>
                    ) : (
                      <span className={`diagram-shape-preview diagram-shape-preview--${shape}`} />
                    )}
                    <span className="diagram-shape-label">{label}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="diagram-toolbar-divider" />
            <div className="diagram-toolbar-group">
              <button
                type="button"
                className="diagram-tool-btn diagram-tool-btn--danger"
                onClick={deleteSelected}
                title="Delete selected"
              >
                Delete
              </button>
              <button type="button" className="diagram-tool-btn" onClick={clearAll} title="Clear all">
                Clear
              </button>
            </div>
          </div>

          <div ref={reactFlowWrapper} className="diagram-flow-wrap">
            <ReactFlow
              className="diagram-flow"
              onInit={(inst) => { reactFlowInstance.current = inst; }}
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onDrop={onDrop}
              onDragOver={onDragOver}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              minZoom={0.2}
              maxZoom={2}
              defaultEdgeOptions={{
                type: 'smoothstep',
                markerEnd: { type: MarkerType.ArrowClosed },
                style: { stroke: 'var(--border)', strokeWidth: 2 },
              }}
              connectionLineStyle={{ stroke: 'var(--accent)', strokeWidth: 2 }}
              snapToGrid
              snapGrid={[10, 10]}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="var(--border)" gap={16} size={0.5} />
              <Controls
                className="diagram-controls"
                showInteractive={false}
                position="bottom-right"
              />
              <Panel position="top-left" className="diagram-hint">
                Drag shapes from toolbar to canvas. Connect nodes by dragging from handles. Double-click shape to edit text.
              </Panel>
            </ReactFlow>
          </div>
        </div>

        <div className="diagram-modal-actions">
          <button
            type="button"
            onClick={handleExport}
            disabled={!hasContent || isExporting}
            className="diagram-btn diagram-btn-insert"
          >
            {isExporting ? 'Exporting…' : 'Insert Diagram'}
          </button>
          <button type="button" onClick={onClose} className="diagram-btn diagram-btn-cancel">
            Cancel
          </button>
        </div>
      </div>

      {showImagePicker && (
        <div className="diagram-image-picker-overlay" onClick={() => { setShowImagePicker(false); setPendingDropPosition(null); setPendingDropShape(null); }}>
          <div className="diagram-image-picker" onClick={(e) => e.stopPropagation()}>
            <h4>Add Image Shape</h4>
            <div className="diagram-image-picker-actions">
              <label className="diagram-tool-btn">
                <input type="file" accept="image/*" onChange={handleImageFile} hidden />
                Upload Image
              </label>
              <span className="diagram-image-picker-or">or paste URL:</span>
              <ImageUrlInput onInsert={handleImageSelect} onCancel={() => { setShowImagePicker(false); setPendingDropPosition(null); setPendingDropShape(null); }} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DiagramModal(props) {
  return (
    <ReactFlowProvider>
      <DiagramEditor {...props} />
    </ReactFlowProvider>
  );
}
