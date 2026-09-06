import fs from "fs";
import path from "path";
import type { ShotSpec } from "@/lib/shots";

export function Shot({ file, caption }: ShotSpec) {
  const onDisk = fs.existsSync(path.join(process.cwd(), "public", "shots", file));
  return (
    <figure className="shot">
      {onDisk ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={`/shots/${file}`} alt={caption} />
      ) : (
        <div className="shot-slot" />
      )}
      <figcaption>{caption}</figcaption>
    </figure>
  );
}
