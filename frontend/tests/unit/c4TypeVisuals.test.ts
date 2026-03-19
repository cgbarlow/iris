import { describe, it, expect } from 'vitest';
import { C4_TYPE_GLYPHS } from '../../src/lib/c4/c4TypeVisuals';

const C4_TYPES = [
  'person',
  'software_system',
  'software_system_external',
  'container',
  'c4_component',
  'code_element',
  'deployment_node',
  'infrastructure_node',
  'container_instance',
];

describe('C4 Type Visuals', () => {
  it('has glyph data for all 9 C4 types', () => {
    for (const type of C4_TYPES) {
      expect(C4_TYPE_GLYPHS[type], `missing glyph for ${type}`).toBeDefined();
    }
  });

  it('each glyph has required fields', () => {
    for (const type of C4_TYPES) {
      const glyph = C4_TYPE_GLYPHS[type];
      expect(glyph.label).toBeTruthy();
      expect(glyph.viewBox).toBeTruthy();
      expect(glyph.path).toBeTruthy();
    }
  });
});
