import { Document, Page, pdfjs } from "react-pdf";
import { useState } from "react";
import type { ReviewField } from "../types";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

export function PDFViewer({ pdfUrl, activeField }: { pdfUrl: string; activeField: ReviewField | undefined }) {
  const [pages, setPages] = useState(0);
  const pageNumber = activeField?.source_page ?? 1;

  return (
    <div className="h-[calc(100vh-150px)] overflow-auto rounded-md border border-border bg-white p-3">
      <div className="mb-2 flex items-center justify-between text-sm text-muted">
        <span>PDF source</span>
        <span>Page {pageNumber} of {pages || "..."}</span>
      </div>
      <div className="relative">
        <Document file={pdfUrl} onLoadSuccess={({ numPages }) => setPages(numPages)}>
          <Page pageNumber={pageNumber} width={620} />
        </Document>
        {activeField?.source_bbox && (
          <div className="pointer-events-none absolute left-6 top-16 h-12 w-64 border-2 border-yellow-500 bg-yellow-300/40" title="Source highlight" />
        )}
      </div>
    </div>
  );
}
