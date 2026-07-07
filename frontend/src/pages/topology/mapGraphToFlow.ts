import type { Edge, Node } from "reactflow";
import type { GraphEdge, GraphNode } from "../../api/types";

const CHILD_WIDTH = 170;
const CHILD_HEIGHT = 50;
const CHILD_GAP_X = 20;
const CHILD_GAP_Y = 14;
const CONTAINER_PADDING_TOP = 50;
const CONTAINER_PADDING = 20;
const CONTAINER_GAP_X = 80;
const MIN_CONTAINER_WIDTH = 260;
const CHILDREN_PER_ROW = 3;

const EDGE_COLORS: Record<string, string> = {
  PEERED_WITH: "#0B3D91",
  PART_OF: "#90A4AE",
};

const UNGROUPED_CONTAINER_ID = "__ungrouped__";

/**
 * Converts NAVIXA Graph API (`GET /graph/jobs/{job_id}/topology`) nodes/edges
 * into a ReactFlow diagram where each Network renders as a container
 * ("group" node) with its PART_OF children nested and laid out in a grid
 * inside it (ReactFlow v11 native parentNode/extent support - parent nodes
 * must precede children in the returned array, which building networks
 * first already satisfies). PEERED_WITH edges connect network containers
 * directly. Nodes with no resolvable owning network (orphans, or providers
 * where membership can't be reliably derived - see
 * graph_engine/writer.py) are placed in a trailing "Ungrouped resources"
 * container rather than dropped, so nothing collected by Discover silently
 * disappears from the diagram.
 */
export function mapGraphToFlow(nodes: GraphNode[], edges: GraphEdge[]): { nodes: Node[]; edges: Edge[] } {
  const networkNodes = nodes.filter((n) => n.labels.includes("Network"));
  const partOfEdges = edges.filter((e) => e.type === "PART_OF");
  const networkIdOf = new Map<string, string>();
  for (const edge of partOfEdges) {
    networkIdOf.set(edge.source, edge.target);
  }

  const childrenByNetworkId = new Map<string, GraphNode[]>();
  const ungrouped: GraphNode[] = [];
  for (const node of nodes) {
    if (node.labels.includes("Network")) continue;
    const networkId = networkIdOf.get(node.id);
    if (networkId) {
      const list = childrenByNetworkId.get(networkId) ?? [];
      list.push(node);
      childrenByNetworkId.set(networkId, list);
    } else {
      ungrouped.push(node);
    }
  }

  const flowNodes: Node[] = [];
  let containerX = 0;

  for (const network of networkNodes) {
    const children = childrenByNetworkId.get(network.id) ?? [];
    const { width, height } = containerSize(children.length);

    const isHub = Boolean(network.properties.is_hub);
    flowNodes.push({
      id: network.id,
      type: "group",
      position: { x: containerX, y: 0 },
      style: {
        width,
        height,
        backgroundColor: isHub ? "rgba(11,61,145,0.06)" : "rgba(96,125,139,0.05)",
        border: `2px solid ${isHub ? "#0B3D91" : "#90A4AE"}`,
        borderRadius: 12,
      },
      data: {
        label: `${(network.properties.name as string) || network.properties.native_id}${isHub ? " (Hub)" : ""}`,
        provider: network.properties.provider,
        resourceLabel: "Network",
        isHub,
      },
    });

    children.forEach((child, index) => {
      flowNodes.push(childFlowNode(child, network.id, index));
    });

    containerX += width + CONTAINER_GAP_X;
  }

  if (ungrouped.length > 0) {
    const { width, height } = containerSize(ungrouped.length);
    flowNodes.push({
      id: UNGROUPED_CONTAINER_ID,
      type: "group",
      position: { x: containerX, y: 0 },
      style: {
        width,
        height,
        backgroundColor: "rgba(96,125,139,0.05)",
        border: "2px dashed #90A4AE",
        borderRadius: 12,
      },
      data: { label: "Ungrouped resources", provider: "", resourceLabel: "Network" },
    });
    ungrouped.forEach((child, index) => {
      flowNodes.push(childFlowNode(child, UNGROUPED_CONTAINER_ID, index));
    });
  }

  const flowEdges: Edge[] = edges
    .filter((edge) => edge.type !== "PART_OF")
    .map((edge) => {
      const color = EDGE_COLORS[edge.type] ?? "#78909C";
      const isPeering = edge.type === "PEERED_WITH";
      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.type,
        style: { stroke: color, strokeWidth: isPeering ? 2 : 1 },
        labelStyle: { fill: color, fontSize: 10 },
        animated: isPeering,
      };
    });

  return { nodes: flowNodes, edges: flowEdges };
}

function containerSize(childCount: number): { width: number; height: number } {
  if (childCount === 0) {
    return { width: MIN_CONTAINER_WIDTH, height: 110 };
  }
  const cols = Math.min(CHILDREN_PER_ROW, childCount);
  const rows = Math.ceil(childCount / CHILDREN_PER_ROW);
  const width = Math.max(
    MIN_CONTAINER_WIDTH,
    cols * CHILD_WIDTH + (cols - 1) * CHILD_GAP_X + CONTAINER_PADDING * 2,
  );
  const height = CONTAINER_PADDING_TOP + rows * CHILD_HEIGHT + (rows - 1) * CHILD_GAP_Y + CONTAINER_PADDING;
  return { width, height };
}

function childFlowNode(node: GraphNode, parentId: string, index: number): Node {
  const label = node.labels[0] ?? "Resource";
  const col = index % CHILDREN_PER_ROW;
  const row = Math.floor(index / CHILDREN_PER_ROW);
  return {
    id: node.id,
    type: "topology",
    parentNode: parentId,
    extent: "parent",
    position: {
      x: CONTAINER_PADDING + col * (CHILD_WIDTH + CHILD_GAP_X),
      y: CONTAINER_PADDING_TOP + row * (CHILD_HEIGHT + CHILD_GAP_Y),
    },
    style: { width: CHILD_WIDTH },
    data: {
      label: (node.properties.name as string) || (node.properties.native_id as string) || label,
      sublabel: label,
      provider: node.properties.provider,
      resourceLabel: label,
    },
  };
}
