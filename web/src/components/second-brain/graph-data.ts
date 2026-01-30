/**
 * Data types and utilities for the Second Brain graph visualization.
 */

export interface GraphNode {
  id: string;
  label: string;
  type: "entry" | "tag" | "topic" | "date";
  size?: number;
  color?: string;
  metadata?: {
    entryDate?: string;
    snippet?: string;
    tags?: string[];
  };
}

export interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  strength?: number;
  type?: "tag" | "topic" | "temporal" | "semantic";
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

/**
 * Generate mock data for testing the graph visualization.
 * In production, this would be replaced with actual backend data.
 */
export function generateMockGraphData(): GraphData {
  const entries: GraphNode[] = [
    { id: "entry-1", label: "Morning Reflection", type: "entry", size: 20, metadata: { entryDate: "2024-01-15", snippet: "Felt energized today..." } },
    { id: "entry-2", label: "Work Challenges", type: "entry", size: 18, metadata: { entryDate: "2024-01-14", snippet: "Difficult meeting with..." } },
    { id: "entry-3", label: "Weekend Plans", type: "entry", size: 15, metadata: { entryDate: "2024-01-13", snippet: "Looking forward to..." } },
    { id: "entry-4", label: "Gratitude Entry", type: "entry", size: 22, metadata: { entryDate: "2024-01-12", snippet: "Thankful for family..." } },
    { id: "entry-5", label: "Creative Ideas", type: "entry", size: 16, metadata: { entryDate: "2024-01-11", snippet: "New project concept..." } },
    { id: "entry-6", label: "Evening Thoughts", type: "entry", size: 14, metadata: { entryDate: "2024-01-10", snippet: "Wind down routine..." } },
  ];

  const tags: GraphNode[] = [
    { id: "tag-work", label: "Work", type: "tag", size: 12, color: "#60a5fa" },
    { id: "tag-personal", label: "Personal", type: "tag", size: 12, color: "#f472b6" },
    { id: "tag-creative", label: "Creative", type: "tag", size: 10, color: "#a78bfa" },
    { id: "tag-gratitude", label: "Gratitude", type: "tag", size: 10, color: "#34d399" },
    { id: "tag-health", label: "Health", type: "tag", size: 10, color: "#fbbf24" },
  ];

  const topics: GraphNode[] = [
    { id: "topic-growth", label: "Growth", type: "topic", size: 15, color: "#22d3ee" },
    { id: "topic-relationships", label: "Relationships", type: "topic", size: 14, color: "#fb7185" },
    { id: "topic-productivity", label: "Productivity", type: "topic", size: 13, color: "#a3e635" },
  ];

  const links: GraphLink[] = [
    // Entry to tag connections
    { source: "entry-1", target: "tag-personal", type: "tag", strength: 1 },
    { source: "entry-1", target: "topic-growth", type: "topic", strength: 0.8 },
    { source: "entry-2", target: "tag-work", type: "tag", strength: 1 },
    { source: "entry-2", target: "topic-productivity", type: "topic", strength: 0.9 },
    { source: "entry-3", target: "tag-personal", type: "tag", strength: 0.8 },
    { source: "entry-3", target: "tag-creative", type: "tag", strength: 0.6 },
    { source: "entry-4", target: "tag-gratitude", type: "tag", strength: 1 },
    { source: "entry-4", target: "topic-relationships", type: "topic", strength: 0.7 },
    { source: "entry-5", target: "tag-creative", type: "tag", strength: 1 },
    { source: "entry-5", target: "topic-growth", type: "topic", strength: 0.6 },
    { source: "entry-6", target: "tag-personal", type: "tag", strength: 0.7 },
    { source: "entry-6", target: "tag-health", type: "tag", strength: 0.5 },
    // Tag to topic connections
    { source: "tag-work", target: "topic-productivity", type: "semantic", strength: 0.7 },
    { source: "tag-personal", target: "topic-growth", type: "semantic", strength: 0.6 },
    { source: "tag-gratitude", target: "topic-relationships", type: "semantic", strength: 0.8 },
  ];

  return {
    nodes: [...entries, ...tags, ...topics],
    links,
  };
}
