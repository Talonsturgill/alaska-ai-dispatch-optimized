#!/usr/bin/env bash
# Verification for the 2026-07-29 Character idle fix (repeat-offender: frozen held figures).
# Renders the SAME two nearby frames of CraftShowcase (which holds a pose="point" figure)
# under the NEW code and under the OLD gate, so the fix is proven by pixels, not by argument.
set -uo pipefail
cd /home/user/alaska-ai-weekly
export PROPS='{}'

R() { bash scripts/render.sh still "$1" CraftShowcase "$2" --draft >/dev/null 2>&1; }

echo "== NEW code =="
R 40 /home/user/alaska-ai-weekly/out/verify/new_f40.png
R 46 /home/user/alaska-ai-weekly/out/verify/new_f46.png

echo "== reverting to OLD gate =="
cp video-engine/src/lib/Character.tsx /tmp/Character.new.tsx
python3 - <<'EOF'
p='video-engine/src/lib/Character.tsx'
s=open(p).read()
assert '  const idle = !walking;' in s
s=s.replace('  const idle = !walking;',
            "  const idle = (pose === 'stand' || pose === 'arms-crossed') && !walking;")
open(p,'w').write(s)
print('reverted')
EOF

echo "== OLD code =="
R 40 /home/user/alaska-ai-weekly/out/verify/old_f40.png
R 46 /home/user/alaska-ai-weekly/out/verify/old_f46.png

echo "== restoring NEW code =="
cp /tmp/Character.new.tsx video-engine/src/lib/Character.tsx
grep -c 'const idle = !walking;' video-engine/src/lib/Character.tsx
echo DONE
