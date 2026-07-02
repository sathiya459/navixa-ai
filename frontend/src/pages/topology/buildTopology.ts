import type { Edge, Node } from "reactflow";
import type { NetworkResource } from "../../api/types";

const NODE_WIDTH = 220;
const NODE_GAP = 60;

/**
 * Builds a NAVIXA Topology graph directly from NAVIXA Discover's normalized
 * inventory. This is a Phase 2 approximation - once NAVIXA Graph (Neo4j) is
 * live in Phase 3, topology should be served from the graph engine instead
 * of re-derived client-side from raw attributes.
 */
export function buildTopology(
  resources: NetworkResource[],
  hubIds: string[],
): { nodes: Node[]; edges: Edge[] } {
  const networks = resources.filter((r) => r.resource_type === "network");
  const subnets = resources.filter((r) => r.resource_type === "subnet");
  const peerings = resources.filter((r) => r.resource_type === "peering_connection");

  const hubIdSet = new Set(hubIds.map((id) => id.trim()).filter(Boolean));

  const nodes: Node[] = networks.map((network, index) => {
    const isHub = hubIdSet.has(network.native_id);
    const subnetCount = subnets.filter((subnet) =>
      JSON.stringify(subnet.attributes).includes(network.native_id),
    ).length;

    return {
      id: network.id,
      position: { x: index * (NODE_WIDTH + NODE_GAP), y: isHub ? 0 : 180 },
      data: {
        label: `${network.name ?? network.native_id}${isHub ? " (Hub)" : ""}\n${subnetCount} subnet(s)`,
      },
      style: {
        background: isHub ? "#0B3D91" : "#E3F2FD",
        color: isHub ? "#fff" : "#0B3D91",
        border: "1px solid #0B3D91",
        borderRadius: 8,
        padding: 10,
        width: NODE_WIDTH,
        whiteSpace: "pre-line" as const,
        fontSize: 12,
      },
    };
  });

  const networkByNativeId = new Map(networks.map((n) => [n.native_id, n]));

  const edges: Edge[] = [];
  for (const peering of peerings) {
    const { sourceId, targetId } = extractPeeringEndpoints(peering);
    const source = sourceId ? networkByNativeId.get(sourceId) : undefined;
    const target = targetId ? networkByNativeId.get(targetId) : undefined;
    if (!source || !target || source.id === target.id) continue;

    const sourceIsHub = hubIdSet.has(source.native_id);
    const targetIsHub = hubIdSet.has(target.native_id);
    const isUnauthorized = !sourceIsHub && !targetIsHub;

    edges.push({
      id: peering.id,
      source: source.id,
      target: target.id,
      label: isUnauthorized ? "unauthorized peering" : "peering",
      style: { stroke: isUnauthorized ? "#D32F2F" : "#0B3D91" },
      labelStyle: { fill: isUnauthorized ? "#D32F2F" : "#0B3D91", fontSize: 11 },
      animated: isUnauthorized,
    });
  }

  return { nodes, edges };
}

/** Best-effort extraction across providers' differing peering attribute shapes. */
function extractPeeringEndpoints(peering: NetworkResource): {
  sourceId: string | null;
  targetId: string | null;
} {
  const attrs = peering.attributes as Record<string, unknown>;
  const nested = (key: string): Record<string, unknown> | undefined =>
    attrs[key] as Record<string, unknown> | undefined;
  const str = (value: unknown): string | null => (typeof value === "string" ? value : null);

  // AWS: RequesterVpcInfo.VpcId / AccepterVpcInfo.VpcId
  if (attrs.RequesterVpcInfo || attrs.AccepterVpcInfo) {
    return {
      sourceId: str(nested("RequesterVpcInfo")?.VpcId),
      targetId: str(nested("AccepterVpcInfo")?.VpcId),
    };
  }

  // Azure: peering embedded on a VNet, with `vnet_id` (owning) and a remote
  // virtual network reference.
  if (attrs.vnet_id || attrs.remoteVirtualNetwork) {
    return {
      sourceId: str(attrs.vnet_id),
      targetId: str(nested("remoteVirtualNetwork")?.id),
    };
  }

  // GCP: peering embedded on a Network, with `network` (owning) and
  // `network` field on the peering pointing at the peer network selfLink.
  if (attrs.network) {
    return {
      sourceId: str(attrs.network),
      targetId: str(attrs.networkUrl) ?? str(attrs.network),
    };
  }

  return { sourceId: null, targetId: null };
}
