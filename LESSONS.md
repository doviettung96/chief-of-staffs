# Lessons Learned

Gotchas worth never hitting twice. Read before debugging (grep by error text or tag);
append after resolving a non-obvious error. One atomic entry each, newest on top.

Format:
```
### <one-line title>
- Date: YYYY-MM-DD
- Symptom: what was observed (paste the actual error text)
- Root cause: why it really happened
- Rule: what to do - and what never to do again
- Tags: #build #windows #flaky #async ...
```

---

<!-- Add lessons below this line -->

### Windows Python: subprocess text=True decodes as cp1252 and crashes on git/gh output
- Date: 2026-07-26
- Symptom: `UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 in position ...`
  raised in a reader thread when capturing `git log` / `gh` output via
  `subprocess.run(..., text=True)` (seen while building projects/*/status.md).
- Root cause: with `text=True` and no explicit `encoding`, Python decodes child output
  with the locale codec — cp1252 on this machine — but git/gh emit UTF-8, so any
  non-Latin-1 byte (accented commit text, box-drawing, emoji) blows up.
- Rule: when capturing text from subprocess on Windows, always pass
  `encoding="utf-8", errors="replace"`. Never rely on the default locale codec.
- Tags: #windows #python #subprocess #encoding
