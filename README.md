# News Fetcher & Semantic Search

AI-powered news aggregation and semantic search across multiple sources.  
The pipeline fetches articles, runs LLM analysis (summaries, topics, sentiment), builds a lightweight vector index, and lets you query with natural language.

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](#)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](#)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326ce5.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](#)

---

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project layout](#project-layout)
- [Setup](#setup)
- [Quick start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Docker](#docker)
- [Kubernetes](#kubernetes)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview

**What it does**
- Fetches news from several sources (e.g., BBC, The Guardian, Reuters, NPR, etc.).
- Analyzes each article with OpenAI: summary, topics, sentiment, optional entities/urgency.
- Stores raw/analysis outputs to disk and builds a simple vector DB for semantic search.
- Offers an interactive CLI to search/ask questions over the corpus.

**Who it’s for**
- Developers/researchers who want a reference pipeline for semantic search over news.
- Teams building simple intel dashboards or topic trackers.

---

## Architecture

