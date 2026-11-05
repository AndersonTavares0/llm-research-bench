#!/usr/bin/env bash
# Lease-controller stress test against the deterministic fake backend.
#
# Exercises the production code path (`gpu-lab-controller` + `gpu_lab_controller.py`)
# with `GPU_LAB_BACKEND=fake`, so no real service is touched. Covers: pre-bind
# reap, lease expiry, hard deadline, supervisor death after bind, concurrent
# acquisition, and a supervisor killed during acquisition (fault injection).
#
# Run as root on the GPU Lab guest (CT108):  bash lease-selftest.sh
set -euo pipefail

CTL=${CTL:-/usr/local/libexec/gpu-lab-controller}
ROOT=${ROOT:-/tmp/gpu-lab-selftest}
STATE=$ROOT/state.json
FAKE=$ROOT/fake
rm -rf "$ROOT"
mkdir -p "$FAKE"
export GPU_LEASE_STATE=$STATE GPU_LAB_BACKEND=fake GPU_LAB_FAKE_DIR=$FAKE

ctl() { "$CTL" "$@" >/dev/null; }
field() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(eval(sys.argv[2]))' "$STATE" "$1"; }
prod() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["production_present"])' "$FAKE/physical.json"; }
ok() { echo "PASS $*"; }
die() { echo "FAIL $*" >&2; exit 1; }

# A real, long-lived process to act as supervisor/owner.
sleep 600 >/dev/null 2>&1 & OWNER=$!
trap 'kill $OWNER ${SUP:-} 2>/dev/null || true' EXIT

# 1. Acquire stops production and leaves no supervisor record before bind.
ctl acquire s1 s1-a1 job "$OWNER" --ttl 5 --deadline 120
[ "$(field 'd["state"]')" = acquiring_lab ] || die "acquire did not reach acquiring_lab"
[ "$(field 'd["attempt"]["supervisor"]')" = None ] || die "supervisor should be null pre-bind"
[ "$(prod)" = False ] || die "production should be stopped while leased"
ok "acquire preempts production, supervisor null pre-bind"

# 2. Reap in the acquire window must not restore production (the fixed bug).
ctl reap
[ "$(field 'd["state"]')" = acquiring_lab ] || die "pre-bind reap wrongly converged"
[ "$(prod)" = False ] || die "pre-bind reap restored production"
ok "pre-bind reap is a no-op (bug regression)"

# 3. Lease expiry before bind converges to production. The reaper renews a
# healthy attempt to the fixed JOB_LEASE_TTL_S, so force the expiry explicitly.
python3 - "$STATE" <<'PYEXPIRE'
import json, sys, time
path = sys.argv[1]
d = json.load(open(path))
d["attempt"]["lease_expires_boottime_ns"] = time.clock_gettime_ns(time.CLOCK_BOOTTIME) - 10**9
json.dump(d, open(path, "w"), sort_keys=True)
PYEXPIRE
"$CTL" reap >/dev/null
[ "$(field 'd["state"]')" = production ] || die "expired lease did not converge"
[ "$(prod)" = True ] || die "production not restored after lease expiry"
ok "lease expiry restores production"

# 4. Hard deadline wins over a live supervisor.
ctl acquire s4 s4-a1 job "$OWNER" --ttl 300 --deadline 0
"$CTL" reap >/dev/null
[ "$(field 'd["state"]')" = production ] || die "hard deadline did not converge"
ok "hard deadline restores production"

# 5. Supervisor death after bind converges with supervisor_gone.
ctl acquire s5 s5-a1 job "$OWNER" --ttl 600 --deadline 600
GEN=$(field 'd["attempt"]["generation"]')
python3 - "$FAKE/physical.json" s5 "$GEN" <<'PY'
import json, sys
path, session, gen = sys.argv[1], sys.argv[2], int(sys.argv[3])
d = json.load(open(path))
base = d.get("next_pid", 1000)
d["next_pid"] = base + 10
d.setdefault("containers", {})[session] = gen
d.setdefault("scopes", {})[str(gen)] = True
d["processes"] = [p for p in d.get("processes", []) if p.get("session") != session] + [
    {"pid": base + 1, "comm": "podman", "generation": gen, "inside": True, "session": session},
    {"pid": base + 2, "comm": "conmon", "generation": gen, "inside": True, "session": session},
    {"pid": base + 3, "comm": "pasta.avx2", "generation": gen, "inside": True, "session": session},
    {"pid": base + 4, "comm": "bash", "generation": gen, "inside": True, "session": session},
]
json.dump(d, open(path, "w"))
PY
sleep 600 >/dev/null 2>&1 & SUP=$!
ctl bind s5 s5-a1 "$GEN" "$SUP"
[ "$(field 'd["state"]')" = lab ] || die "bind did not reach lab"
kill "$SUP" 2>/dev/null || true
sleep 1
"$CTL" reap >/dev/null
[ "$(field 'd["state"]')" = production ] || die "dead supervisor did not converge"
ok "supervisor death after bind restores production"

# 6. Concurrent acquisitions: at most one may hold the lease.
ctl acquire s6 s6-a1 job "$OWNER" --ttl 300 --deadline 300
set +e
"$CTL" acquire s7 s7-a1 job "$OWNER" --ttl 300 --deadline 300 >/dev/null 2>&1
RC=$?
set -e
[ "$RC" -ne 0 ] || die "second concurrent acquire was accepted"
[ "$(field 'd["attempt"]["session_id"]')" = s6 ] || die "lease owner changed under contention"
ok "concurrent acquire refused without stealing the lease"
ctl release s6 test_cleanup

# 7. Supervisor killed during acquisition (fault injection before grant).
rm -rf /tmp/gpu-lab-fault
GPU_LAB_FAULT=before_grant GPU_LAB_FAULT_DIR=/tmp/gpu-lab-fault \
  "$CTL" acquire s8 s8-a1 job "$OWNER" --ttl 5 --deadline 60 >/dev/null 2>&1 &
FAULT_PID=$!
for _ in $(seq 1 50); do [ -f /tmp/gpu-lab-fault/before_grant.reached ] && break; sleep 0.2; done
[ -f /tmp/gpu-lab-fault/before_grant.reached ] || die "fault point before_grant never reached"
kill -9 "$FAULT_PID" 2>/dev/null || true
wait "$FAULT_PID" 2>/dev/null || true
python3 - "$STATE" <<'PYEXPIRE'
import json, sys, time
path = sys.argv[1]
d = json.load(open(path))
d["attempt"]["lease_expires_boottime_ns"] = time.clock_gettime_ns(time.CLOCK_BOOTTIME) - 10**9
json.dump(d, open(path, "w"), sort_keys=True)
PYEXPIRE
"$CTL" reap >/dev/null
[ "$(field 'd["state"]')" = production ] || die "killed mid-acquire did not converge"
[ "$(prod)" = True ] || die "production not restored after killed acquire"
ok "killed acquisition converges via lease TTL"

echo "ALL LEASE SELFTESTS PASSED"
