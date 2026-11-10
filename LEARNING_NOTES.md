# Learning Notes

Updated after each phase. Plain English, my words to grow into.

## Time tracking

| Session | Date | Hours | Running total |
|---|---|---|---|
| Phases 0-2 build | 2026-11-10 | _to fill in_ | _to fill in_ |

Estimates: project 58-80 hours, learning 70-90, rebuild 15-20.

---

## Phases 0-2

### New words

- **Terminal**: a text window where you type commands to the computer.
- **Python**: the programming language we write the project in.
- **Virtual environment (`.venv`)**: a private box of tools for this project, so it doesn't clash with anything else on the computer.
- **Package / `pip`**: ready-made code written by others (e.g. pandas); `pip` installs it. `requirements.txt` lists what the project needs.
- **Git / commit**: Git is a save-history for a project. A commit is one labelled save point.
- **`.gitignore`**: a list of files Git must never save or share. Our `.env` (secret key) is on it.
- **`.env` file**: where the secret API key lives, outside the code.
- **API / API key**: a way for one program to ask another for something (here, asking Claude). The key is the password.
- **Demo mode**: the project runs without a key, using a simple stand-in for Claude.
- **Synthetic data**: invented data that looks real. No real people involved.
- **Seed**: a starting number that makes "random" data come out the same every time.
- **Ground truth**: the answer key. We know the correct values, so we can check how well the clean-up did.
- **CSV**: a plain-text spreadsheet; one row per line, values separated by commas.
- **pandas / DataFrame**: a Python tool for working with tables of data.
- **Data quality dimensions**: completeness (is it filled in?), uniqueness (no repeats?), validity (is it a real value?), consistency (same format everywhere?).
- **PII**: personally identifiable information (names, phones, emails, addresses). Masked before AI sees anything.
- **Masking**: replacing personal details with labels like `[PHONE]`.
- **Pydantic**: a tool that checks data is the shape we expect (used on the AI's answers).
- **Token**: a chunk of text an AI reads or writes. Cost is counted in tokens.
- **Regex**: a pattern for finding text, e.g. "something that looks like an email".
- **Logging**: writing down every change so it can be checked later.

### What each part does

- `src/ai_client.py`: the one place that talks to Claude. Works in demo mode without a key, and counts cost.
- `src/generate_data.py`: invents 300 enquiries, then deliberately breaks them the way old systems do. Saves the correct answers separately.
- `src/pii.py`: finds and hides personal details in free text.
- `src/ai_assist.py`: asks for a category suggestion on the few rows rules can't fix (masked text only; stored as a suggestion).
- `src/data_quality.py`: the clean-up. Fixes what is certain, flags the rest, logs every change, scores before vs after, and checks itself against the answer key.

### 3 interview talking points

1. **"I measured data quality before and after, in numbers"**: consistency went from about 65% to 100%, and I explained why completeness couldn't (I refuse to invent data).
2. **"I tested my clean-up against an answer key"**: I generated synthetic data with known correct values, so I could show 1 wrong value in about 3,300 cells instead of just claiming it worked, and I can name the one mistake and why it happened.
3. **"Personal details are masked before anything goes to an AI, and AI output is a suggestion, not a decision"**: that is the trust and governance story public-sector employers worry about.

### Honest description of my part

Built with AI assistance (Claude Code). I have not yet written this code myself; that comes in the rebuild stage. What I can say today: I understand what each step does and why, and I can explain the results.

### Quiz (answer in your own words)

1. Why does the clean-up empty a bad phone number instead of guessing the right one?
2. What is the ground truth, and why can we only have it because the data is synthetic?
3. What gets sent to the AI, and what never does?
