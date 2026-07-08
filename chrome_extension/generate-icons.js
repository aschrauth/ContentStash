import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const selectedOption = '02-bookmark-stash';
const sizes = [16, 32, 48, 128];
const sourceDir = join(__dirname, 'icon-options', 'png', selectedOption);
const outputDirs = [join(__dirname, 'public'), join(__dirname, 'dist')];

for (const outputDir of outputDirs) {
  mkdirSync(outputDir, { recursive: true });

  for (const size of sizes) {
    const fileName = `stash${size}.png`;
    copyFileSync(join(sourceDir, fileName), join(outputDir, fileName));
    console.log(`Updated ${join(outputDir, fileName)}`);
  }
}

console.log(`Icon generation complete: ${selectedOption}`);
