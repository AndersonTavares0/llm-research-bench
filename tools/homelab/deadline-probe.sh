#!/usr/bin/env bash
# Payload for validating per-lease deadline enforcement. Sleeps far longer than
# the policy file allows; the supervisor must end the lease.
echo "probe start $(date -u +%H:%M:%S)"
sleep 600
echo "probe end $(date -u +%H:%M:%S)"
