// tests/skillDatabase.test.ts - verifies that all core skill manifests are loaded
import { expect, test } from 'vitest';
import { SKILL_DATABASE } from '../knowledge';
import fs from 'fs';
import path from 'path';

test('SKILL_DATABASE length matches number of core skill JSON files', () => {
  const coreSkillsDir = path.resolve(__dirname, '../core_skills');
  const jsonFiles = fs.readdirSync(coreSkillsDir).filter((f) => f.endsWith('.json'));
  expect(SKILL_DATABASE.length).toBe(jsonFiles.length);
});
