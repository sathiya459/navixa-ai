import { toPng } from "html-to-image";
import { jsPDF } from "jspdf";
import { getNodesBounds, getViewportForBounds, type ReactFlowInstance } from "reactflow";

/**
 * Exports the full diagram (not just the currently visible viewport) as a
 * PDF. Computes a transform that fits every node regardless of current
 * pan/zoom, temporarily applies it to `.react-flow__viewport`, rasterizes
 * with html-to-image, then embeds the PNG into a jsPDF document sized to
 * match its aspect ratio.
 */
export async function exportTopologyToPdf(reactFlowInstance: ReactFlowInstance): Promise<void> {
  const nodes = reactFlowInstance.getNodes();
  if (nodes.length === 0) return;

  const bounds = getNodesBounds(nodes);
  const width = Math.ceil(bounds.width + 80);
  const height = Math.ceil(bounds.height + 80);
  const viewport = getViewportForBounds(bounds, width, height, 0.5, 2, 0.1);

  const viewportEl = document.querySelector(".react-flow__viewport") as HTMLElement | null;
  if (!viewportEl) return;

  const previousTransform = viewportEl.style.transform;
  viewportEl.style.width = `${width}px`;
  viewportEl.style.height = `${height}px`;
  viewportEl.style.transform = `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.zoom})`;

  try {
    const dataUrl = await toPng(viewportEl, {
      width,
      height,
      backgroundColor: "#ffffff",
    });

    const orientation = width >= height ? "landscape" : "portrait";
    const doc = new jsPDF({ orientation, unit: "px", format: [width, height] });
    doc.addImage(dataUrl, "PNG", 0, 0, width, height);
    doc.save("topology.pdf");
  } finally {
    viewportEl.style.transform = previousTransform;
    viewportEl.style.width = "";
    viewportEl.style.height = "";
  }
}
