# Documentation and Learning System

Last updated: 2026-07-30

## Purpose

OpsMind documentation serves three audiences:

- A contributor maintaining the system
- An operator deploying or troubleshooting it
- A reviewer evaluating engineering judgment and learning evidence

## Documentation Types

### Product

Capture users, workflows, requirements, acceptance criteria, and known
limitations.

### Architecture

Capture component boundaries, data flows, security boundaries, deployment
topology, and durable decisions.

### Engineering

Capture local setup, coding standards, testing strategy, data contracts, and
dependency practices.

### Operations

Capture deployment, observability, alerts, backups, incident response, cost
controls, and recovery procedures.

### Learning Evidence

Capture experiments, certification links, mistakes, tradeoffs, and what can be
demonstrated independently.

## Documentation Rules

- Write for a future reader without access to the original chat.
- Distinguish planned, implemented, verified, and production-ready states.
- Prefer links to executable checks or evidence over unsupported claims.
- Record why a decision was made, not only what was selected.
- Date phase reviews and time-sensitive investigations.
- Update or replace stale guidance when implementation changes.

## Learning Loop

For each meaningful capability:

1. Define the user or operational problem.
2. Identify the competency being practiced.
3. Implement the smallest useful slice.
4. Test and observe it.
5. Explain the design and alternatives.
6. Record gaps and the next experiment.

## Evidence Portfolio

Useful evidence includes:

- Reviewed source and tests
- Reproducible commands and environments
- Architecture diagrams and decision records
- Metrics, traces, and incident exercises
- Cost estimates and budget controls
- Model evaluation and limitation reports
- Phase reviews that connect outcomes to competencies
