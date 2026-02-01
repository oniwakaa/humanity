"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ZoomIn, ZoomOut, Maximize, Filter, X, Tag, Brain, FileText, Network, ArrowRight, WandSparkles, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
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

/**
 * Apply Magic Wander layout algorithm
 * Uses grid-based positioning with connectivity-aware placement
 */
function applyMagicWanderLayout(
  nodes: SimulatedNode[],
  links: SimulatedLink[],
  dimensions: { width: number; height: number }
): SimulatedNode[] {
  if (nodes.length === 0) return [];
  
  // Calculate grid dimensions
  const gridSize = Math.ceil(Math.sqrt(nodes.length));
  const cellSize = Math.min(150, dimensions.width / gridSize, dimensions.height / gridSize);
  const offsetX = (dimensions.width - gridSize * cellSize) / 2;
  const offsetY = (dimensions.height - gridSize * cellSize) / 2;
  
  // Create a copy of nodes with connectivity scores
  const nodesWithConnectivity = nodes.map(node => {
    const connectedLinks = links.filter(link => 
      link.source.id === node.id || link.target.id === node.id
    );
    const connectivity = connectedLinks.length;
    return { ...node, connectivity };
  });
  
  // Sort nodes by connectivity (highly connected nodes first)
  const sortedNodes = [...nodesWithConnectivity].sort((a, b) => b.connectivity - a.connectivity);
  
  // Position nodes on grid using space-filling curve for better edge routing
  const resultNodes: SimulatedNode[] = [];
  
  for (let i = 0; i < sortedNodes.length; i++) {
    const node = sortedNodes[i];
    const col = i % gridSize;
    const row = Math.floor(i / gridSize);
    
    // Use a spiral pattern for more natural layout
    const spiralRadius = Math.sqrt(i) * 0.5;
    const spiralAngle = i * 0.1;
    const spiralX = Math.cos(spiralAngle) * spiralRadius;
    const spiralY = Math.sin(spiralAngle) * spiralRadius;
    
    // Combine grid and spiral for organic but organized layout
    const x = offsetX + col * cellSize + spiralX * cellSize * 0.3;
    const y = offsetY + row * cellSize + spiralY * cellSize * 0.3;
    
    resultNodes.push({
      ...node,
      x,
      y
    });
  }
  
  // Apply edge crossing reduction by adjusting connected nodes
  for (let iter = 0; iter < 3; iter++) {
    links.forEach(link => {
      const sourceNode = resultNodes.find(n => n.id === link.source.id);
      const targetNode = resultNodes.find(n => n.id === link.target.id);
      
      if (sourceNode && targetNode) {
        // Slightly adjust positions to reduce edge crossings
        const dx = targetNode.x - sourceNode.x;
        const dy = targetNode.y - sourceNode.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < cellSize * 0.8) {
          // Move nodes apart if too close
          const repelForce = 0.2;
          sourceNode.x -= dx * repelForce;
          sourceNode.y -= dy * repelForce;
          targetNode.x += dx * repelForce;
          targetNode.y += dy * repelForce;
        }
      }
    });
  }
  
  // Ensure nodes stay within bounds
  return resultNodes.map(node => ({
    ...node,
    x: Math.max(50, Math.min(dimensions.width - 50, node.x)),
    y: Math.max(50, Math.min(dimensions.height - 50, node.y))
  }));
}

export function GraphView({ data, className, onNodeClick }: GraphViewProps) {
  const router = useRouter();
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
  const [isFilterOpen, setIsFilterOpen] = useState(true);
  const [isMagicWanderActive, setIsMagicWanderActive] = useState(false);
  const [magicWanderSuccess, setMagicWanderSuccess] = useState(false);
  const animationRef = useRef<number>();
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0 });
  const transformStart = useRef({ x: 0, y: 0 });

  // Initialize simulation
  useEffect(() => {
    if (!containerRef.current) return;
    
    const { width, height } = containerRef.current.getBoundingClientRect();
    setDimensions({ width, height });

    // Initialize nodes with random positions across the entire canvas
    const initialNodes: SimulatedNode[] = data.nodes.map((node) => ({
      ...node,
      x: Math.random() * (width - 100) + 50,
      y: Math.random() * (height - 100) + 50,
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

    // Pre-warm the simulation to improve initial layout
    const preWarmSimulation = (nodes: SimulatedNode[], links: SimulatedLink[], iterations: number = 100) => {
      const centerX = width / 2;
      const centerY = height / 2;
      
      for (let iter = 0; iter < iterations; iter++) {
        for (let i = 0; i < nodes.length; i++) {
          const node = nodes[i];
          if (node.fx !== null && node.fy !== null) continue; // Skip fixed nodes

          // Repulsion force
          for (let j = 0; j < nodes.length; j++) {
            if (i === j) continue;
            const other = nodes[j];
            const dx = node.x - other.x;
            const dy = node.y - other.y;
            const distance = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = (5000 * (node.size || 20) * (other.size || 20)) / (distance * distance);
            const fx = (dx / distance) * force * 0.02;
            const fy = (dy / distance) * force * 0.02;
            node.vx += fx;
            node.vy += fy;
          }

          // Attraction to center (reduced)
          const dx = centerX - node.x;
          const dy = centerY - node.y;
          node.vx += dx * 0.0001;
          node.vy += dy * 0.0001;

          // Link attraction
          links.forEach((link) => {
            if (link.source.id === node.id || link.target.id === node.id) {
              const other = link.source.id === node.id ? link.target : link.source;
              const ldx = other.x - node.x;
              const ldy = other.y - node.y;
              const distance = Math.sqrt(ldx * ldx + ldy * ldy) || 1;
              const targetDistance = 150 + (node.size || 20) + (other.size || 20);
              const strength = (link.strength || 0.5) * 0.0015;
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
          node.x = Math.max(padding, Math.min(width - padding, node.x));
          node.y = Math.max(padding, Math.min(height - padding, node.y));
        }
      }
    };

    // Run pre-warming
    preWarmSimulation(initialNodes, initialLinks);

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

           // Repulsion force (nodes repel each other) - increased for better initial distribution
           for (let j = 0; j < newNodes.length; j++) {
             if (i === j) continue;
             const other = newNodes[j];
             const dx = node.x - other.x;
             const dy = node.y - other.y;
             const distance = Math.sqrt(dx * dx + dy * dy) || 1;
             const force = (5000 * (node.size || 20) * (other.size || 20)) / (distance * distance);
             const fx = (dx / distance) * force * 0.02;
             const fy = (dy / distance) * force * 0.02;
             node.vx += fx;
             node.vy += fy;
           }

           // Attraction to center - reduced to allow better spread
           const dx = centerX - node.x;
           const dy = centerY - node.y;
           node.vx += dx * 0.0001;
           node.vy += dy * 0.0001;

           // Link attraction - increased target distance for better initial spread
           links.forEach((link) => {
             if (link.source.id === node.id || link.target.id === node.id) {
               const other = link.source.id === node.id ? link.target : link.source;
               const ldx = other.x - node.x;
               const ldy = other.y - node.y;
               const distance = Math.sqrt(ldx * ldx + ldy * ldy) || 1;
               const targetDistance = 150 + (node.size || 20) + (other.size || 20);
               const strength = (link.strength || 0.5) * 0.0015;
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

  // Handle navigation to entry
  const handleNavigateToEntry = useCallback((node: SimulatedNode) => {
    if (!node.metadata?.entryId) return;
    
    // Determine navigation target based on entry type
    const entryType = node.metadata.entryType || "note";
    const entryId = node.metadata.entryId;
    
    switch (entryType) {
      case "reflection":
        router.push(`/app/story?entry=${entryId}`);
        break;
      case "conversation":
        router.push(`/app/diary?entry=${entryId}`);
        break;
      case "note":
      default:
        router.push(`/app/diary?entry=${entryId}`);
        break;
    }
  }, [router]);



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

  // Handle Magic Wander layout reorganization
  const handleMagicWander = useCallback(() => {
    setIsMagicWanderActive(true);
    setMagicWanderSuccess(false);
    
    // Pause current simulation by canceling animation frame
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    
    // Use only visible nodes for reorganization
    const nodesToOrganize = activeFilters.size === 0 ? nodes : nodes.filter(n => activeFilters.has(n.type));
    
    if (nodesToOrganize.length <= 1) {
      // Not enough nodes to reorganize
      setIsMagicWanderActive(false);
      return;
    }
    
    // Apply grid-based layout with edge crossing reduction
    const reorganizedNodes = applyMagicWanderLayout(nodesToOrganize, visibleLinks, dimensions);
    
    // Animate to new positions
    setNodes(prevNodes => {
      return prevNodes.map(node => {
        const reorganizedNode = reorganizedNodes.find(n => n.id === node.id);
        if (reorganizedNode) {
          return {
            ...node,
            x: reorganizedNode.x,
            y: reorganizedNode.y,
            vx: 0,
            vy: 0,
            fx: reorganizedNode.x, // Fix position temporarily
            fy: reorganizedNode.y
          };
        }
        return node;
      });
    });
    
    // After animation completes, release fixed positions and resume gentle simulation
    setTimeout(() => {
      setNodes(prevNodes => {
        return prevNodes.map(node => ({
          ...node,
          fx: null,
          fy: null
        }));
      });
      
      setIsMagicWanderActive(false);
      setMagicWanderSuccess(true);
      
      // Success indicator disappears after 2 seconds
      setTimeout(() => {
        setMagicWanderSuccess(false);
      }, 2000);
    }, 800);
  }, [nodes, visibleLinks, activeFilters, dimensions]);

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
           <Button
             variant="ghost"
             size="icon"
             onClick={handleMagicWander}
             disabled={isMagicWanderActive}
             className="h-8 w-8 relative"
           >
             {isMagicWanderActive ? (
               <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
             ) : (
               <WandSparkles className="h-4 w-4" />
             )}
             {magicWanderSuccess && (
               <AnimatePresence>
                 <motion.div
                   initial={{ scale: 0, rotate: -45 }}
                   animate={{ scale: 1, rotate: 0 }}
                   exit={{ scale: 0, rotate: 45 }}
                   transition={{ type: "spring", damping: 10, stiffness: 200 }}
                   className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-green-500 flex items-center justify-center border-2 border-white"
                 >
                   <Check className="h-3 w-3 text-white" />
                 </motion.div>
               </AnimatePresence>
             )}
           </Button>
         </Card>
       </div>

      {/* Filter Toggle Button */}
      <div className="absolute top-4 right-4 z-10">
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8 relative"
          onClick={() => setIsFilterOpen(prev => !prev)}
        >
          <Filter className={`h-4 w-4 transition-colors ${isFilterOpen ? 'text-primary' : 'text-muted-foreground'}`} />
          {activeFilters.size > 0 && (
            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">
              {activeFilters.size}
            </span>
          )}
        </Button>
      </div>
      
      {/* Toggleable Filter Panel */}
      <AnimatePresence>
        {isFilterOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="absolute top-16 right-4 z-10"
          >
            <Card className="p-3 w-48">
              <div className="flex items-center gap-2 mb-2">
                <Filter className="h-4 w-4 text-primary" />
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
          </motion.div>
        )}
      </AnimatePresence>

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
               {selectedNode.metadata?.entryId && (
                 <Button
                   variant="outline"
                   size="sm"
                   className="w-full mt-3 gap-2"
                   onClick={() => handleNavigateToEntry(selectedNode)}
                 >
                   <ArrowRight className="h-3 w-3" />
                   View Entry
                 </Button>
               )}
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
