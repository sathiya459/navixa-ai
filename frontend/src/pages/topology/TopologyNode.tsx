import { Handle, Position, type NodeProps } from "reactflow";
import { Box, Typography } from "@mui/material";
import { getResourceIcon } from "./resourceIcons";

export interface TopologyNodeData {
  label: string;
  sublabel?: string;
  provider: string;
  resourceLabel: string;
  isHub?: boolean;
}

export function TopologyNode({ data }: NodeProps<TopologyNodeData>) {
  const icon = getResourceIcon(data.provider, data.resourceLabel);

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        padding: "6px 10px",
        borderRadius: 1.5,
        border: "1px solid",
        borderColor: data.isHub ? "primary.main" : "divider",
        backgroundColor: data.isHub ? "primary.main" : "background.paper",
        color: data.isHub ? "primary.contrastText" : "text.primary",
        minWidth: 150,
        boxShadow: 1,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ visibility: "hidden" }} />
      <Handle type="source" position={Position.Right} style={{ visibility: "hidden" }} />
      {icon.kind === "svg" ? (
        <img src={icon.src} alt="" width={20} height={20} />
      ) : (
        <icon.Icon fontSize="small" />
      )}
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="caption" sx={{ fontWeight: 600, display: "block", lineHeight: 1.2 }} noWrap>
          {data.label}
          {data.isHub ? " (Hub)" : ""}
        </Typography>
        {data.sublabel && (
          <Typography variant="caption" sx={{ opacity: 0.75, display: "block", lineHeight: 1.2 }} noWrap>
            {data.sublabel}
          </Typography>
        )}
      </Box>
    </Box>
  );
}
