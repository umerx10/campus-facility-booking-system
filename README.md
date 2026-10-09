
# Campus Facility Booking System (CFBS)

Joint Semester Project for:
- SE423: Software Construction and Development
- SE431: Software Quality Assurance

## Project Overview
A centralized system for managing university facility
reservations, availability, approvals, and notifications.

## Team Members
- Danish Ahmed (2023172) 
- Muhammad Bilal (2023392)
- Muhammad Hussnain Abbas (2023440)
- Muhammad Umer (2023539) - Team lead for Milestone 1

## Proposed Functional Modules
1. User & Access Management
2. Facility Management
3. Booking & Scheduling
4. Approval & Booking Rules
5. Notification Management

## Proposed Technology Stack
- Python
- FastAPI
- SQLite
- SQLAlchemy
- Pytest
- GitHub Actions

## Planned Design Patterns
- Factory - Notification creation
- Strategy - Booking policies
- Observer - Booking event notifications

## Branching Strategy
- main: Stable integrated code
- develop: Integration of reviewed features
- feature/*: Individual feature development

Feature changes will be developed in separate branches
and reviewed through pull requests before integration.

## Development Setup

1. Clone: `git clone https://github.com/umerx10/campus-facility-booking-system.git`
2. Create a virtual environment: `python -m venv .venv`
3. Activate it: `source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
4. Install dependencies: `pip install -r requirements.txt`
5. Run tests: `pytest` (no tests exist at Milestone 1)

Application run commands will be added with the first implementation in Milestone 2.

## Current Status
Milestone 1 - Proposal and architecture planning.
