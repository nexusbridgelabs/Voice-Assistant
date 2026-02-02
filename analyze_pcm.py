import struct
import math
import os

file_path = "backend/test_write/debug_input.pcm"
if not os.path.exists(file_path):
    print("File not found.")
    exit(1)

with open(file_path, "rb") as f:
    data = f.read()

count = len(data) // 2
shorts = struct.unpack(f"<{count}h", data)

# Basic Analysis
max_val = max(abs(s) for s in shorts)
min_val = min(shorts)
avg_val = sum(shorts) / count

# RMS
sum_squares = sum(s**2 for s in shorts)
rms = math.sqrt(sum_squares / count)

# Zero Crossings (frequency proxy)
zc = 0
for i in range(1, count):
    if (shorts[i] >= 0 and shorts[i-1] < 0) or (shorts[i] < 0 and shorts[i-1] >= 0):
        zc += 1

print(f"Analysis for {file_path}:")
print(f"- Samples: {count}")
print(f"- Max Amplitude: {max_val} (of 32768)")
print(f"- Avg Value (DC Offset): {avg_val:.2f}")
print(f"- RMS Volume: {rms:.2f}")
print(f"- Zero Crossings: {zc} ({zc/count:.2f} per sample)")

# Check for silence or noise
if max_val < 500:
    print("\nCONCLUSION: Audio is VERY QUIET or SILENT.")
elif rms < 200:
    print("\nCONCLUSION: Audio is likely SILENCE or BACKGROUND NOISE.")
elif zc / count > 0.5:
    print("\nCONCLUSION: Audio has VERY HIGH frequency. Likely WHITE NOISE or STATIC.")
else:
    print("\nCONCLUSION: Audio looks like a VALID SPEECH SIGNAL.")
