# Security Policy

## Supported Versions

MediaRescue is an open-source media reconstruction utility.

Security fixes will generally be provided for the latest available release.

| Version | Supported |
|---|---|
| Latest release | ✅ |
| Older releases | ❌ |

## Reporting a Vulnerability

Security is important to this project because MediaRescue processes potentially untrusted media files.

If you discover a security vulnerability, please **do not publicly disclose the technical details in a GitHub issue** before the maintainers have had an opportunity to investigate it.

Instead, report the vulnerability privately using GitHub's security advisory system, if enabled.

You can find this under:

**Repository → Security → Advisories → Report a vulnerability**

If private vulnerability reporting is unavailable, contact the maintainer through a private contact method listed in the repository.

### What to Include

Please provide:

- A description of the vulnerability
- The affected MediaRescue version
- Your Windows version
- Steps to reproduce the issue
- The potential security impact
- Any relevant error messages or logs

Do not include private photos, videos, passwords, or other sensitive information.

## Security Limitations

MediaRescue rebuilds supported photos and videos by decoding and re-encoding their content.

However, MediaRescue:

- Is not an antivirus program
- Does not detect or remove Pegasus spyware
- Cannot guarantee reconstructed files are malware-free
- Does not provide a secure sandbox
- May be exposed to vulnerabilities in image and video decoding libraries

Users should keep Python, Pillow, pillow-heif, FFmpeg, and their operating systems updated.

For higher-risk media, we recommend running MediaRescue inside an isolated, updated virtual machine.

## Responsible Disclosure

We encourage responsible reporting of vulnerabilities and appreciate contributions that improve application security.

Please allow maintainers a reasonable opportunity to investigate and address issues before publishing exploit details.

## Privacy

MediaRescue processes media locally and does not intentionally upload files to external services.

Users should avoid sharing personal media, file paths, or sensitive logs in public GitHub issues.

## Disclaimer

MediaRescue is provided without any guarantee that it will detect malicious content or prevent compromise.

Successfully rebuilding a file does not establish that the file is safe.
