# TerraMarkets Portfolio Summary

## What It Is

TerraMarkets is a full-stack research prototype for prediction-market-style forecasting across Earth science, commodities, macroeconomic events, and public-data-driven indicators. It connects event markets, public datasets, simulated forecast agents, and market-implied probability views in one analyst-facing application.

## Why It Matters

Many important economic and environmental risks are described by fragmented public datasets rather than clean decision tools. TerraMarkets explores how normalized observations, citations, event definitions, and price-implied probabilities can make uncertainty easier to inspect, debate, and monitor.

## Technologies Used

- Next.js and React frontend for market, dataset, bot, and portfolio workflows
- FastAPI backend with Pydantic schemas and SQLAlchemy models
- Alembic migrations and SQLite-first local development, with a path to Postgres
- Pytest coverage for API flows, ingestion behavior, demo markets, and bot arena logic
- Public-data ingestion pipelines for climate, geohazard, space-weather, and agricultural signals

## Financial And Economic Concepts Demonstrated

- Market-implied probabilities and multi-outcome event pricing
- LMSR-style automated market-maker mechanics for prototype liquidity
- Portfolio exposure, simulated balances, and position tracking
- Forecast thesis generation and source-backed probability reasoning
- Public-data-driven event modeling for climate, commodities, and macro-adjacent indicators

## Future Improvements

- Add formal forecast calibration metrics and backtesting views
- Expand datasets for commodities, inflation, labor, energy, and climate-risk indicators
- Move production deployments to managed Postgres with stronger operational runbooks
- Improve session security and admin controls before any public multi-user deployment
- Add polished screenshots, demo data snapshots, and reproducible presentation scripts
