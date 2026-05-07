import { create } from "zustand";

type ReviewerState = {
  jobId: number | null;
  activeFieldId: number | null;
  setJobId: (jobId: number) => void;
  setActiveFieldId: (fieldId: number | null) => void;
};

export const useReviewerStore = create<ReviewerState>((set) => ({
  jobId: null,
  activeFieldId: null,
  setJobId: (jobId) => set({ jobId }),
  setActiveFieldId: (activeFieldId) => set({ activeFieldId })
}));
