"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ZoomIn, ZoomOut, Maximize, Filter, X, Tag, Brain, FileText, Network } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { GraphNode, GraphLink, GraphData } from "./graph-data";

interface GraphViewProps {
  data: GraphData;
  className?: string;
  onNodeClick?: (node: GraphNode) => void;
}

interface SimulatedNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx?: number | null;
  fy?: number | null;
}

interface SimulatedLink extends GraphLink {
  source: SimulatedNode;
  target: SimulatedNode;
}

const NODE_COLORS: Record<string, string> = {
  entry: "#94a3b8",   // Slate 400
  tag: "#60a5fa",     // Blue 400
  topic: "#a78bfa",   // Violet 400
  date: "#34d399",    // Emerald 400
};

const NODE_ICONS: Record<string, React.ReactNode> = {
  entry: <FileText className="w-3 h-3" />,
  tag: <Tag className="w-3 h-3" />,
  topic: <Brain className="w-3 h-3" />,
  date: <Network className="w-3 h-3" />,
};

export function GraphView({ data, className, onNodeClick }: GraphViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [nodes, setNodes] = useState<SimulatedNode[]>([]);
  const [links, setLinks] = useState<SimulatedLink[]>([]);
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragNode, setDragNode] = useState<SimulatedNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<SimulatedNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<SimulatedNode | null>(null);
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set());
  const animationRef = useRef<number>();
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });
  const transformStart = useRef({ x: 0, y: 0 });

  // Initialize simulation
  useEffect(() => {
    if (!containerRef.current) return;
    
    const { width, height } = containerRef.current.getBoundingClientRect();
    setDimensions({ width, height });

    // Initialize nodes with random positions near center
    const initialNodes: SimulatedNode[] = data.nodes.map((node) => ({
      ...node,
      x: width / 2 + (Math.random() - 0.5) * 200,
      y: height / 2 + (Math.random() - 0.5) * 200,
      vx: 0,
      vy: 0,
    }));

    // Initialize links with node references
    const initialLinks: SimulatedLink[] = data.links.map((link) => {
      const sourceNode = initialNodes.find((n) => n.id === link.source) || initialNodes[0];
      const targetNode = initialNodes.find((n) => n.id === link.target) || initialNodes[1];
      return {
        ...link,
        source: sourceNode,
        target: targetNode,
      };
    });

    setNodes(initialNodes);
    setLinks(initialLinks);
  }, [data]);

  // Force simulation loop
  useEffect(() => {
    if (nodes.length === 0) return;

    const simulate = () => {
      setNodes((prevNodes) => {
        const newNodes = [...prevNodes];
        const centerX = dimensions.width / 2;
        const centerY = dimensions.height / 2;

        // Apply forces
        for (let i = 0; i < newNodes.length; i++) {
          const node = newNodes[i];
          if (node.fx !== null && node.fy !== null) continue; // Skip fixed nodes

          // Repulsion force (nodes repel each other)
          for (let j = 0; j < newNodes.length; j++) {
            if (i === j) continue;
            const other = newNodes[j];
            const dx = node.x - other.x;
            const dy = node.y - other.y;
            const distance = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = (3000 * (node.size || 20) * (other.size || 20)) / (distance * distance);
            const fx = (dx / distance) * force * 0.01;
            const fy = (dy / distance) * force * 0.01;
            node.vx += fx;
            node.vy += fy;
          }

          // Attraction to center
          const dx = centerX - node.x;
          const dy = centerY - node.y;
          node.vx += dx * 0.0005;
          node.vy += dy * 0.0005;

          // Link attraction
          links.forEach((link) => {
            if (link.source.id === node.id || link.target.id === node.id) {
              const other = link.source.id === node.id ? link.target : link.source;
              const ldx = other.x - node.x;
              const ldy = other.y - node.y;
              const distance = Math.sqrt(ldx * ldx + ldy * ldy) || 1;
              const targetDistance = 100 + (node.size || 20) + (other.size || 20);
              const strength = (link.strength || 0.5) * 0.001;
              node.vx += (ldx / distance) * (distance - targetDistance) * strength;
              node.vy += (ldy / distance) * (distance - targetDistance) * strength;
            }
          });

          // Apply velocity with damping
          node.vx *= 0.85;
          node.vy *= 0.85;
          node.x += node.vx;
          node.y += node.vy;

          // Boundary constraints
          const padding = 50 + (node.size || 20);
          node.x = Math.max(padding, Math.min(dimensions.width - padding, node.x));
          node.y = Math.max(padding, Math.min(dimensions.height - padding, node.y));
        }

        return newNodes;
      });

      animationRef.current = requestAnimationFrame(simulate);
    };

    animationRef.current = requestAnimationFrame(simulate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [nodes.length, links, dimensions]);

  // Update links when nodes move
  useEffect(() => {
    setLinks((prevLinks) =>
      prevLinks.map((link) => ({
        ...link,
        source: nodes.find((n) => n.id === (link.source as SimulatedNode).id) || link.source,
        target: nodes.find((n) => n.id === (link.target as SimulatedNode).id) || link.target,
      }))
    );
  }, [nodes]);

  // Handle zoom
  const handleZoom = useCallback((delta: number) => {
    setTransform((prev) => {
      const newK = Math.max(0.3, Math.min(3, prev.k + delta));
      return { ...prev, k: newK };
    });
  }, []);

  const handleReset = useCallback(() => {
    setTransform({ x: 0, y: 0, k: 1 });
  }, []);

  // Handle pan
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.target === svgRef.current || (e.target as HTMLElement).tagName === "svg") {
      isPanning.current = true;
      panStart.current = { x: e.clientX, y: e.clientY };
      transformStart.current = { x: transform.x, y: transform.y };
    }
  }, [transform]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isPanning.current) {
      const dx = (e.clientX - panStart.current.x) / transform.k;
      const dy = (e.clientY - panStart.current.y) / transform.k;
      setTransform((prev) => ({
        ...prev,
        x: transformStart.current.x + dx,
        y: transformStart.current.y + dy,
      }));
    }

    if (isDragging && dragNode) {
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const x = (e.clientX - rect.left - transform.x) / transform.k;
      const y = (e.clientY - rect.top - transform.y) / transform.k;

      setNodes((prev) =>
        prev.map((n) =>
          n.id === dragNode.id ? { ...n, x, y, fx: x, fy: y } : n
        )
      );
    }
  }, [isDragging, dragNode, transform]);

  const handleMouseUp = useCallback(() => {
    isPanning.current = false;
    if (isDragging && dragNode) {
      setNodes((prev) =>
        prev.map((n) => (n.id === dragNode.id ? { ...n, fx: null, fy: null } : n))
      );
      setIsDragging(false);
      setDragNode(null);
    }
  }, [isDragging, dragNode]);

  // Handle node drag
  const handleNodeMouseDown = useCallback((e: React.MouseEvent, node: SimulatedNode) => {
    e.stopPropagation();
    setIsDragging(true);
    setDragNode(node);
  }, []);

  // Handle node click
  const handleNodeClick = useCallback((node: SimulatedNode) => {
    setSelectedNode(node);
    onNodeClick?.(node);
  }, [onNodeClick]);

  // Filter nodes
  const toggleFilter = useCallback((type: string) => {
    setActiveFilters((prev) => {
      const newFilters = new Set(prev);
      if (newFilters.has(type)) {
        newFilters.delete(type);
      } else {
        newFilters.add(type);
      }
      return newFilters;
    });
  }, []);

  const visibleNodes = activeFilters.size === 0 
    ? nodes 
    : nodes.filter((n) => activeFilters.has(n.type));

  const visibleLinks = activeFilters.size === 0
    ? links
    : links.filter(
        (l) =>
          activeFilters.has(l.source.type) &&
          activeFilters.has(l.target.type)
      );

  return (
    <div
      ref={containerRef}
      className={cn("relative w-full h-full overflow-hidden bg-background/50 rounded-lg", className)}
    >
      {/* Controls */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
        <Card className="p-2 flex flex-col gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => handleZoom(0.2)}
            className="h-8 w-8"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => handleZoom(-0.2)}
            className="h-8 w-8"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleReset}
            className="h-8 w-8"
          >
            <Maximize className="h-4 w-4" />
          </Button>
        </Card>
      </div>

      {/* Filters */}
      <div className="absolute top-4 right-4 z-10">
        <Card className="p-3">
          <div className="flex items-center gap-2 mb-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Filter</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {["entry", "tag", "topic"].map((type) => (
              <Button
                key={type}
                variant={activeFilters.has(type) ? "default" : "outline"}
                size="sm"
                onClick={() => toggleFilter(type)}
                className={cn(
                  "text-xs capitalize",
                  activeFilters.has(type) && "bg-primary text-primary-foreground"
                )}
              >
                {type}
              </Button>
            ))}
            {activeFilters.size > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setActiveFilters(new Set())}
                className="text-xs"
              >
                <X className="h-3 w-3 mr-1" />
                Clear
              </Button>
            )}
          </div>
        </Card>
      </div>

      {/* Node details panel */}
      <AnimatePresence>
        {selectedNode && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="absolute bottom-4 right-4 z-10"
          >
            <Card className="p-4 w-64">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className="p-1.5 rounded-full"
                    style={{
                      backgroundColor: selectedNode.color || NODE_COLORS[selectedNode.type],
                    }}
                  >
                    {NODE_ICONS[selectedNode.type]}
                  </div>
                  <span className="font-medium text-sm">{selectedNode.label}</span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => setSelectedNode(null)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>
              <div className="text-xs text-muted-foreground">
                <p className="capitalize">Type: {selectedNode.type}</p>
                {selectedNode.metadata?.entryDate && (
                  <p>Date: {selectedNode.metadata.entryDate}</p>
                )}
                {selectedNode.metadata?.snippet && (
                  <p className="mt-2 line-clamp-3">{selectedNode.metadata.snippet}</p>
                )}
                {selectedNode.metadata?.tags && selectedNode.metadata.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {selectedNode.metadata.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-1.5 py-0.5 bg-secondary rounded text-[10px]"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Graph SVG */}
      <svg
        ref={svgRef}
        className="w-full h-full cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.k})`}>
          {/* Links */}
          {visibleLinks.map((link, i) => (
            <line
              key={`link-${i}`}
              x1={link.source.x}
              y1={link.source.y}
              x2={link.target.x}
              y2={link.target.y}
              stroke="currentColor"
              strokeOpacity={0.2}
              strokeWidth={1 + (link.strength || 0.5)}
              className="text-muted-foreground"
            />
          ))}

          {/* Nodes */}
          {visibleNodes.map((node) => (
            <g
              key={node.id}
              transform={`translate(${node.x}, ${node.y})`}
              className="cursor-pointer"
              onMouseDown={(e) => handleNodeMouseDown(e, node)}
              onClick={() => handleNodeClick(node)}
              onMouseEnter={() => setHoveredNode(node)}
              onMouseLeave={() => setHoveredNode(null)}
            >
              {/* Node circle */}
              <circle
                r={(node.size || 20) / 2}
                fill={node.color || NODE_COLORS[node.type]}
                stroke="currentColor"
                strokeWidth={selectedNode?.id === node.id ? 3 : hoveredNode?.id === node.id ? 2 : 1}
                className={cn(
                  "transition-all duration-200",
                  selectedNode?.id === node.id ? "text-primary" : "text-background"
                )}
                style={{
                  filter: hoveredNode?.id === node.id ? "brightness(1.1)" : undefined,
                }}
              />
              
              {/* Node icon */}
              <foreignObject
                x={-6}
                y={-6}
                width={12}
                height={12}
                className="pointer-events-none"
              >
                <div
                  className="flex items-center justify-center w-full h-full"
                  style={{ color: "#ffffff" }}
                >
                  {NODE_ICONS[node.type]}
                </div>
              </foreignObject>

              {/* Node label */}
              <text
                dy={(node.size || 20) / 2 + 12}
                textAnchor="middle"
                className="text-[10px] fill-current text-foreground font-medium pointer-events-none"
                style={{
                  textShadow: "0 1px 2px rgba(0,0,0,0.5)",
                }}
              >
                {node.label}
              </text>
            </g>
          ))}
        </g>
      </svg>

      {/* Legend */}
      <div className="absolute bottom-4 left-4">
        <Card className="p-3">
          <div className="flex flex-col gap-2">
            {Object.entries(NODE_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="text-xs capitalize text-muted-foreground">{type}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
