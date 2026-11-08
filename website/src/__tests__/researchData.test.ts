import { describe, it, expect } from 'vitest';
import researchData from '../data/researchData';

describe('Research Data Integrity & Provenance', () => {
  it('loads valid metadata with pinned hardware specifications', () => {
    expect(researchData.metadata).toBeDefined();
    expect(researchData.metadata.primary_hardware).toContain('GTX 1050 Ti');
    expect(researchData.metadata.llama_cpp_build).toBe('b12024');
  });

  it('contains verified models with positive VRAM and throughput', () => {
    expect(researchData.models.length).toBeGreaterThanOrEqual(4);
    researchData.models.forEach((model) => {
      expect(model.id).toBeTruthy();
      expect(model.parameters_b).toBeGreaterThan(0);
      expect(model.vram_peak_mib).toBeGreaterThan(0);
      expect(model.generation_tok_s).toBeGreaterThan(0);
      expect(model.prompt_eval_tok_s).toBeGreaterThan(0);
      expect(['measured', 'partial', 'analytical', 'ready', 'unknown']).toContain(
        model.evidence_status
      );
    });
  });

  it('verifies that all models run strictly on the GTX 1050 Ti primary testbed', () => {
    const nonGtxModels = researchData.models.filter((m) => !m.hardware.includes('1050 Ti'));
    expect(nonGtxModels.length).toBe(0);
    expect(researchData.models.length).toBe(6);
  });

  it('verifies that all primary GTX 1050 Ti models fit within 4096 MiB ceiling', () => {
    const gtxModels = researchData.models.filter((m) => m.hardware.includes('1050 Ti'));
    gtxModels.forEach((m) => {
      expect(m.vram_peak_mib).toBeLessThan(4096);
      expect(m.vram_budget_pct).toBeLessThan(100);
    });
  });

  it('contains deduplicated research questions across Tracks A through F', () => {
    expect(researchData.research_questions.length).toBeGreaterThanOrEqual(20);
    const trackSet = new Set(researchData.research_questions.map((rq) => rq.track.split(' ')[1]));
    expect(trackSet.has('A')).toBe(true);
    expect(trackSet.has('B')).toBe(true);
    expect(trackSet.has('C')).toBe(true);
    expect(trackSet.has('D')).toBe(true);
    expect(trackSet.has('E')).toBe(true);
    expect(trackSet.has('F')).toBe(true);
  });

  it('correctly classifies ready benchmarks without fabricated model outcomes', () => {
    const readyBenchmarks = researchData.benchmarks.filter((b) => b.evidence_status === 'ready');
    expect(readyBenchmarks.length).toBeGreaterThanOrEqual(3);
    readyBenchmarks.forEach((b) => {
      expect(b.results_summary.toLowerCase()).toContain('ready');
      expect(b.limitations.toLowerCase()).toContain('no model');
    });
  });
});
