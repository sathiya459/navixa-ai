import RouterIcon from "@mui/icons-material/Router";
import SecurityIcon from "@mui/icons-material/Security";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import DnsIcon from "@mui/icons-material/Dns";
import StorageIcon from "@mui/icons-material/Storage";
import PublicIcon from "@mui/icons-material/Public";
import DeviceHubIcon from "@mui/icons-material/DeviceHub";
import LanIcon from "@mui/icons-material/Lan";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";
import type { SvgIconComponent } from "@mui/icons-material";

import virtualNetworksIcon from "../../assets/icons/azure/Virtual_Networks.svg";
import subnetIcon from "../../assets/icons/azure/Subnet.svg";
import routeTablesIcon from "../../assets/icons/azure/Route_Tables.svg";
import virtualNetworkGatewaysIcon from "../../assets/icons/azure/Virtual_Network_Gateways.svg";
import firewallsIcon from "../../assets/icons/azure/Firewalls.svg";
import networkSecurityGroupsIcon from "../../assets/icons/azure/Network_Security_Groups.svg";
import networkInterfacesIcon from "../../assets/icons/azure/Network_Interfaces.svg";
import loadBalancersIcon from "../../assets/icons/azure/Load_Balancers.svg";
import privateEndpointIcon from "../../assets/icons/azure/Private_Endpoint.svg";
import virtualMachineIcon from "../../assets/icons/azure/Virtual_Machine.svg";
import connectionsIcon from "../../assets/icons/azure/Connections.svg";
import publicIpAddressesIcon from "../../assets/icons/azure/Public_IP_Addresses.svg";

/** Resource-type labels, matching backend/app/graph_engine/schema.py's
 * RESOURCE_TYPE_TO_LABEL vocabulary. */
export type ResourceLabel =
  | "Network"
  | "Subnet"
  | "RouteTable"
  | "Route"
  | "Gateway"
  | "Firewall"
  | "SecurityGroup"
  | "NetworkInterface"
  | "LoadBalancer"
  | "Endpoint"
  | "ComputeInstance"
  | "PeeringConnection"
  | "PublicIP";

const AZURE_ICON_BY_LABEL: Partial<Record<ResourceLabel, string>> = {
  Network: virtualNetworksIcon,
  Subnet: subnetIcon,
  RouteTable: routeTablesIcon,
  Gateway: virtualNetworkGatewaysIcon,
  Firewall: firewallsIcon,
  SecurityGroup: networkSecurityGroupsIcon,
  NetworkInterface: networkInterfacesIcon,
  LoadBalancer: loadBalancersIcon,
  Endpoint: privateEndpointIcon,
  ComputeInstance: virtualMachineIcon,
  PeeringConnection: connectionsIcon,
  PublicIP: publicIpAddressesIcon,
};

const MUI_ICON_BY_LABEL: Partial<Record<ResourceLabel, SvgIconComponent>> = {
  Network: LanIcon,
  Subnet: AccountTreeIcon,
  RouteTable: RouterIcon,
  Gateway: DeviceHubIcon,
  Firewall: SecurityIcon,
  SecurityGroup: SecurityIcon,
  NetworkInterface: DnsIcon,
  LoadBalancer: CompareArrowsIcon,
  Endpoint: StorageIcon,
  ComputeInstance: StorageIcon,
  PeeringConnection: CompareArrowsIcon,
  PublicIP: PublicIcon,
};

export type ResourceIcon =
  | { kind: "svg"; src: string }
  | { kind: "mui"; Icon: SvgIconComponent };

/** Azure resources render with real draw.io Azure icon SVGs; AWS/GCP/OCI
 * fall back to a semantically-matched MUI icon vocabulary, since draw.io's
 * AWS/GCP icon sets are stencil-XML rather than plain SVGs and aren't
 * reliably extractable. Every provider still renders correctly - this is
 * an icon-fidelity tradeoff, not a functional gap. */
export function getResourceIcon(provider: string, label: string): ResourceIcon {
  const resourceLabel = label as ResourceLabel;
  if (provider === "azure") {
    const src = AZURE_ICON_BY_LABEL[resourceLabel];
    if (src) return { kind: "svg", src };
  }
  const Icon = MUI_ICON_BY_LABEL[resourceLabel] ?? RouterIcon;
  return { kind: "mui", Icon };
}
