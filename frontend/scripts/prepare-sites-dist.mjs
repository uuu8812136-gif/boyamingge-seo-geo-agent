import { cp, mkdir, readdir, rename, rm } from 'node:fs/promises';
import { resolve } from 'node:path';

const root = process.cwd();
const openNextDir = resolve(root, '.open-next');
const distDir = resolve(root, 'dist');
const serverDir = resolve(distDir, 'server');
const assetsDir = resolve(distDir, 'assets');

await rm(distDir, { recursive: true, force: true });
await mkdir(serverDir, { recursive: true });
await mkdir(assetsDir, { recursive: true });

for (const entry of await readdir(openNextDir, { withFileTypes: true })) {
  if (entry.name === 'assets' || entry.name === 'cache') continue;

  await cp(
    resolve(openNextDir, entry.name),
    resolve(serverDir, entry.name),
    { recursive: entry.isDirectory() },
  );
}

await rename(resolve(serverDir, 'worker.js'), resolve(serverDir, 'index.js'));
await cp(resolve(openNextDir, 'assets'), assetsDir, { recursive: true });

const cacheDir = resolve(openNextDir, 'cache');
const cacheAssetsDir = resolve(assetsDir, 'cdn-cgi', '_next_cache');
await mkdir(cacheAssetsDir, { recursive: true });
await cp(cacheDir, cacheAssetsDir, { recursive: true });
