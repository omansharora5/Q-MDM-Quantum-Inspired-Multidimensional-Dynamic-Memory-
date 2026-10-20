"""Encode real captured UI states into a labelled, silent walkthrough."""
import hashlib
import json
import subprocess
from pathlib import Path


def main():
    import imageio_ffmpeg
    from PIL import Image, ImageDraw, ImageFont

    root = Path(__file__).resolve().parents[1]
    directory = root / "artifacts" / "demo-frames"
    captions = [
        ("01-conversation.png", "Exact synthetic messages, times and links to derived memories.", 10),
        ("02-before.png", "Before: the saved train decision points to its original source. Version 1.", 10),
        ("03-after.png", "After a real commit: coach plan, new source and links. Six added, five removed.", 12),
        ("04-history.png", "The older train source remains inspectable through version 1 and its dimensions.", 10),
        ("05-connect.png", "Agents connect through local MCP or REST. Native remote ChatGPT still needs HTTPS/OAuth.", 12),
        ("06-results.png", "2,592 synthetic retrieval trials. The graph methods tie; no PACE or QWAM advantage.", 12),
        ("07-failure.png", "Missing-fact zero-result rate: 50% for every method. No answer model or vendor comparison.", 12),
    ]
    font_path = Path("C:/Windows/Fonts/segoeui.ttf")
    font = ImageFont.truetype(str(font_path), 24) if font_path.exists() else ImageFont.load_default(size=24)
    rendered = directory / "rendered"
    rendered.mkdir(exist_ok=True)
    manifest = []
    for index, (name, caption, seconds) in enumerate(captions):
        source = directory / name
        with Image.open(source) as shot:
            shot = shot.convert("RGB")
            shot.thumbnail((1440, 1000))
            canvas = Image.new("RGB", (1440, 1100), "#0c1117")
            canvas.paste(shot, ((1440-shot.width)//2, (1000-shot.height)//2))
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 1010), caption, font=font, fill="#d7efb2")
        draw.text((24, 1050), "MnemoGraph v2 | Real UI still captures | SQLite development | Synthetic data | Silent walkthrough", font=font, fill="#aab7c7")
        frame = rendered / f"{index:02}.png"
        canvas.save(frame)
        manifest.append({"source":name, "sha256":hashlib.sha256(source.read_bytes()).hexdigest(), "caption":caption, "seconds":seconds})
    playlist = rendered / "frames.txt"
    lines = []
    for index, item in enumerate(manifest):
        lines += [f"file '{index:02}.png'", f"duration {item['seconds']}"]
    lines += [f"file '{len(manifest)-1:02}.png'"]
    playlist.write_text("\n".join(lines), encoding="utf-8")
    output = root / "artifacts" / "mnemograph-v2-walkthrough.mp4"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg,"-y","-f","concat","-safe","0","-i",str(playlist),"-r","12","-c:v","libx264",
                    "-preset","veryfast","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",str(output)],check=True,capture_output=True)
    subprocess.run([ffmpeg,"-v","error","-i",str(output),"-f","null","-"],check=True,capture_output=True)
    report = {"format":"Silent walkthrough assembled from real UI still captures, not continuous screen recording",
              "backend":"sqlite-development", "synthetic":True, "frames":manifest,
              "duration_seconds":sum(item["seconds"] for item in manifest),"decode_check":"passed",
              "video_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),"bytes":output.stat().st_size}
    (root / "artifacts" / "walkthrough-manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({key:value for key,value in report.items() if key!="frames"}))


if __name__ == "__main__":
    main()
