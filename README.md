# 🛡️ MediaRescue

**A free, open-source photo and video reconstruction tool for Windows.**

MediaRescue helps users rebuild photos and videos from untrusted sources into fresh media files, reducing the amount of original file structure and metadata carried into the new files.

Designed for people transferring media from old phones, backups, external drives, or other potentially untrusted sources.

> ⚠️ **Important:** MediaRescue is not an antivirus engine, Pegasus detector, or malware removal tool. Successful reconstruction does not guarantee that a file is free from malicious content or unknown exploits.

## ✨ Features

- 🖼️ Reconstructs supported photos as fresh JPEG or PNG files
- 🎬 Re-encodes supported videos into H.264/AAC MP4 files
- 🔒 Keeps original files untouched
- 🧹 Excludes original metadata and unnecessary data streams from reconstructed outputs
- 📁 Supports processing folders and subfolders
- 🚫 Rejects files that cannot be processed
- 📋 Generates a CSV report of the results
- 🖥️ Runs on Windows 11

## 📸 Supported formats

| Type | Input formats | Output |
|---|---|---|
| Photos | JPG, JPEG, PNG, BMP, WebP, GIF, HEIC, HEIF, AVIF | JPG / PNG |
| Videos | MP4, MOV, M4V, AVI, MKV, WebM, 3GP | MP4 |

Some formats require additional decoder support. Animated and multi-frame images are rejected. Support varies depending on the installed versions of the decoding libraries.

## 📥 Installation

### Requirements

- Windows 11
- Python 3
- FFmpeg
- Pillow
- pillow-heif

### Install dependencies

Install Python and FFmpeg from their official distribution sources.

Then run:

```powershell
python -m pip install -r requirements.txt
```

Verify FFmpeg:

```powershell
ffmpeg -version
```

## 🚀 Usage

Download or clone this repository.

Create separate input and output folders:

```text
C:\MediaRescue\
  Originals\
  Clean\
```

Place the media you want to rebuild in `Originals`.

Run:

```powershell
python media_rescue.py "C:\MediaRescue\Originals" "C:\MediaRescue\Clean"
```

The program produces:

```text
Clean/
  Photos/
  Videos/
  report.csv
```

Review the report before using the reconstructed media.

Only consider transferring successfully rebuilt files. Keep rejected and unsupported originals separate.

## 🔐 Security limitations

MediaRescue aims to reduce risks associated with transferring original media files, but it cannot establish that a file is safe.

- It does not detect or remove Pegasus or other mobile spyware.
- It is not a replacement for Microsoft Defender or another antivirus product.
- Unknown vulnerabilities in image or video decoders may still be exploitable during conversion.
- Malformed files may fail to process.
- Reconstruction can change image or video quality, orientation, and metadata.
- The current application does not provide a secure sandbox for processing untrusted files.

For high-risk sources, run the program inside an isolated, updated virtual machine, and scan input and output files with trusted antivirus software.

## 🔏 Privacy

MediaRescue processes files locally using Python image libraries and FFmpeg.

The project itself does not intentionally upload media to an online service.

Do not submit personal or sensitive media in public bug reports.

## 🛠️ Roadmap

- [ ] Graphical Windows interface
- [ ] Standalone Windows executable
- [ ] Progress bar and cancel button
- [ ] Improved media validation
- [ ] Automated tests
- [ ] Optional Microsoft Defender integration
- [ ] Human-readable scan reports

## 🤝 Contributing

Contributions, bug reports, and suggestions are welcome.

Please avoid including personal media in issues or pull requests.

For potential security vulnerabilities, follow the instructions in `SECURITY.md` rather than publicly posting exploit details.

## 📄 License

See the `LICENSE` file for the terms under which this project is distributed.

---

**Disclaimer:** MediaRescue is a media reconstruction utility, not a forensic security product. It cannot certify that devices or media are free of spyware.
