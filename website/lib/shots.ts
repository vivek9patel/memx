export type ShotSpec = {
  file: string;
  caption: string;
};

/** PNGs in website/public/shots/. */
export const SHOTS = {
  summaryTable: {
    file: "01-summary-table.png",
    caption: "Diagnostic Summary: FAIL counts by memory-pipeline stage.",
  },
  debugQuestion: {
    file: "04-debug-question.png",
    caption: "memx debug on a FAIL: question, gold, candidate, retrieval, stage badge.",
  },
  debugSupermemory: {
    file: "06-debug-supermemory.png",
    caption: "Hosted adapter FAIL in debug: retrieval plus store diff.",
  },
  datasetsList: {
    file: "07-datasets-list.png",
    caption: "memx datasets list: names and cache paths.",
  },
  debugLongmemeval: {
    file: "08-debug-longmemeval.png",
    caption: "LongMemEval oracle FAIL: stage badge and session state diff.",
  },
  debugExtractionLme: {
    file: "09-debug-extraction-lme.png",
    caption:
      "c19f7a0b FAIL: retrieval and store have dinner/yoga, not 6:30; Stage 1.",
  },
  debugC19Pass: {
    file: "10-debug-c19f7a0b-pass.png",
    caption:
      "c19f7a0b PASS: retrieved fact includes getting home around 6:30 pm.",
  },
} as const satisfies Record<string, ShotSpec>;
