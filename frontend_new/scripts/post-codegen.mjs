import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const generatedPath = path.resolve(__dirname, '../src/generated/releasarr.ts');

let content = readFileSync(generatedPath, 'utf8');

content = content.replace(/BaseMediaRequest\.and\(/g, 'BaseMediaRequest.merge(');
writeFileSync(generatedPath, content);
