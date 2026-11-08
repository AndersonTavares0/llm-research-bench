import { describe, it, expect } from 'vitest';

describe('Scientific Calculations & Guardrails', () => {
  it('correctly computes memory headroom from 4096 MiB ceiling', () => {
    const vramPeak = 3069;
    const headroom = Math.max(0, 4096 - vramPeak);
    expect(headroom).toBe(1027);
  });

  it('verifies strict hardware equality check for testbed integrity', () => {
    const hwA: string = 'NVIDIA GeForce GTX 1050 Ti (4096 MiB)';
    const hwB: string = 'NVIDIA GeForce GTX 1050 Ti (4096 MiB)';
    const hwDiff: string = 'NVIDIA GeForce RTX 4090 (24576 MiB)';
    const isIdentical = (a: string, b: string) => a === b;
    expect(isIdentical(hwA, hwB)).toBe(true);
    expect(isIdentical(hwA, hwDiff)).toBe(false);
  });

  it('correctly calculates percentage delta between model arms', () => {
    const baseline = 27.4;
    const candidate = 46.3;
    const diff = candidate - baseline;
    const pct = ((diff / baseline) * 100).toFixed(1);
    expect(diff).toBeCloseTo(18.9, 1);
    expect(pct).toBe('69.0');
  });

  it('computes non-dominated Pareto frontier points for trade-offs', () => {
    // Multi-objective: Speed (higher is better) vs VRAM (lower is better)
    const points = [
      { id: 'm1', speed: 97.5, vram: 1510.0 }, // Fast, medium VRAM (Trade-off frontier point)
      { id: 'm2', speed: 37.5, vram: 620.7 },  // Slower, but lowest VRAM (Trade-off frontier point)
      { id: 'm3', speed: 20.0, vram: 1510.0 }, // Dominated by m1 (same VRAM, but lower speed)
      { id: 'm4', speed: 30.0, vram: 2000.0 }, // Dominated by m2 (higher VRAM AND lower speed)
    ];

    const isDominated = (pt: typeof points[0], all: typeof points) => {
      return all.some(
        (other) =>
          other.id !== pt.id &&
          other.speed >= pt.speed &&
          other.vram <= pt.vram &&
          (other.speed > pt.speed || other.vram < pt.vram)
      );
    };

    expect(isDominated(points[0], points)).toBe(false); // Non-dominated (fastest)
    expect(isDominated(points[1], points)).toBe(false); // Non-dominated (lowest memory)
    expect(isDominated(points[2], points)).toBe(true);  // Dominated by m1
    expect(isDominated(points[3], points)).toBe(true);  // Dominated by m2
  });
});
