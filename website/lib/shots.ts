export type ShotSpec = {
  file: string;
  caption: string;
};

/** Filenames match TODO-docs-screenshots.md (website/public/shots/). */
export const SHOTS = {
  summaryTable: {
    file: "01-summary-table.png",
    caption: "Diagnostic Summary: FAIL counts by memory-pipeline stage.",
  },
  hostedProgress: {
    file: "03-run-hosted-progress.png",
    caption: "Hosted ingest in progress (queue ingest or waiting on SuperMemory / Mem0).",
  },
  debugQuestion: {
    file: "04-debug-question.png",
    caption: "memx debug on a FAIL: question, gold, candidate, retrieval, stage badge.",
  },
  taxonomyCloseup: {
    file: "05-taxonomy-closeup.png",
    caption: "Close crop of the four taxonomy stages and counts.",
  },
  debugSupermemory: {
    file: "06-debug-supermemory.png",
    caption: "SuperMemory FAIL in debug: retrieval plus profile diff.",
  },
  datasetsList: {
    file: "07-datasets-list.png",
    caption: "memx datasets list: names and cache paths.",
  },
  debugLongmemeval: {
    file: "08-debug-longmemeval.png",
    caption: "LongMemEval oracle FAIL: stage badge and session state diff.",
  },
  skipIngest: {
    file: "09-skip-ingest.png",
    caption: "Re-score with --skip-ingest (query existing store, no ingest/wait).",
  },
} as const satisfies Record<string, ShotSpec>;
