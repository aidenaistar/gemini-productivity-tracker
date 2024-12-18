# Productivity Tracker

A simple Python tool that tracks your productivity by taking periodic screenshots and analyzing them using AI.
The tool takes a screenshot every second, emulating a 1 FPS video. Screenshots are batched every minute and analyzed by Gemini. At the end of the session the tool will provide a summary of summaries.
It is designed to make use of the Gemini free tier.

## Quick Setup

1. Clone the repository:
```bash
git clone https://github.com/aidenaistar/gemini-productivity-tracker
cd gemini-productivity-tracker
```

2. Install requirements:
```bash
pip install -r requirements.txt
```

3. Create a .env file with your Google API key:
```bash
echo "GOOGLE_API_KEY=your_key_here" > .env
```

4. Run the tracker:
```bash
python main.py [options]
```

## Usage Examples

Basic usage (uses API key from .env):
```bash
python main.py
```

Specify duration:
```bash
python main.py --duration 30
```

Override API key from command line:
```bash
python main.py --api-key YOUR_API_KEY --duration 45
```

## Command Line Options

- `--api-key`: Google API key (optional if set in .env)
- `--duration`: Duration in minutes (default: 60)
- `--output`: Output directory (default: ./output)

## Output

The tool creates an output directory with the following structure:

```
output/
└── YYYYMMDD/
    ├── HHMMSS/
    │   ├── screenshot_HHMMSS.png
    │   └── summary.txt
    └── session_summary_HHMMSS.txt
```

## Cases that are not covered
- Working overnight
- Per-session summary

## Other use cases
You can freely modify the prompts in the folder to alter the output as you wish. You can also modify the code, it is not like I can stop you.