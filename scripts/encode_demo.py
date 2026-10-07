"""Encode captured browser states as a GIF without changing their contents."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def encode(manifest_path: Path, output: Path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frames = []
    durations = []
    for scene in manifest["scenes"]:
        with Image.open(manifest_path.parent / scene["file"]) as image:
            frames.append(image.convert("RGB").quantize(colors=256, dither=Image.Dither.NONE))
        durations.append(scene["duration_ms"])
    if not frames or any(frame.size != frames[0].size for frame in frames):
        raise ValueError("Capture requires equally sized nonempty frames")
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(output, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True, disposal=1)
    # Decode every composited frame to check animation timing and visual fidelity.
    with Image.open(output) as gif:
        if gif.n_frames != len(frames) or gif.info.get("loop") != 0:
            raise ValueError("GIF frame count or loop metadata is incorrect")
        total = 0
        for index, expected in enumerate(frames):
            gif.seek(index)
            total += gif.info["duration"]
            difference = ImageChops.difference(gif.convert("RGB"), expected.convert("RGB"))
            if max(ImageStat.Stat(difference).mean) > 1:
                raise ValueError(f"GIF frame {index} differs from the captured state")
        if total != sum(durations) or not 20_000 <= total <= 30_000:
            raise ValueError("GIF timing must preserve the 20–30 second capture")
    if output.stat().st_size > 5_000_000:
        raise ValueError("GIF exceeds the 5 MB documentation budget")
    # A still preview gives readers an alternative to the animation.
    with Image.open(manifest_path.parent / manifest["scenes"][0]["file"]) as poster:
        poster.save(output.with_name("demo-poster.png"))
    metadata = {"schema_version": 1, "source": "Scripted real Chromium workflow against isolated local API and worker",
                "demo": "Fictional Northstar; scripted fixture acceptance, not human validation",
                "size": list(frames[0].size), "frames": len(frames), "duration_ms": sum(durations),
                "bytes": output.stat().st_size, "scenes": [{"caption": scene["caption"], "duration_ms": scene["duration_ms"]} for scene in manifest["scenes"]]}
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(frames)} frames, {sum(durations) / 1000:g} seconds, {output.stat().st_size:,} bytes: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=Path("docs/media/demo.gif"))
    args = parser.parse_args()
    encode(args.manifest, args.output)
