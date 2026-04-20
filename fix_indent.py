import sys

with open('app.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    # Find the line "if manual_mode:" after selected_ids
    if "if manual_mode:" in line and "st.markdown" in lines[i+1]:
        start_idx = i
        break

# The block ends when we encounter a line with less than 12 spaces indentation or we hit the next elif
end_idx = start_idx
for i in range(start_idx, len(lines)):
    if "elif view_mode ==" in lines[i]:
        end_idx = i
        break

# Unindent all lines in the range by 4 spaces
for i in range(start_idx, end_idx):
    if lines[i].startswith("    "):
        lines[i] = lines[i][4:]

with open('app.py', 'w') as f:
    f.writelines(lines)
print("Done")
