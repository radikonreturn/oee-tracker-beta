# OEE Tracker Next-Gen

> ⚠️ **BETA RELEASE** ⚠️
> This application is currently in **Beta** and under active development. It is **not yet ready for end-user production environments**. Features may change, and bugs are expected. Use for testing and evaluation purposes only.

A modern, production-ready Overall Equipment Effectiveness (OEE) tracking application. This project has been migrated from a legacy Streamlit monolith to a fully decoupled architecture featuring a scalable FastAPI backend and a highly dynamic, reactive React frontend.

## Architecture

The project is split into two main components:

- **Backend (`/backend`)**: A RESTful API built with **FastAPI** and **SQLAlchemy**. It handles database interactions, complex metrics calculations, anomaly detection, and data ingestion (SCADA, ERP, CSV, Barcode) via strict **Pydantic** schemas.
- **Frontend (`/frontend`)**: A modern Single Page Application (SPA) built with **React**, **Vite**, and **TailwindCSS**. It features an advanced dark industrial UI, real-time KPI tracking, and interactive visualizations powered by **ApexCharts**.

## Features

- **Live Monitoring Dashboard**: Real-time KPI cards (OEE, Availability, Performance, Quality, TEEP), Machine Fleet gauges, and interactive OEE Trend charts.
- **Manual Data Entry**: A dynamic form for manual shift logging with live OEE preview calculations supporting multiple models (Nakajima, Time Balance, Product Balance).
- **Data Ingestion Hub (5-Tab)**:
  - **Excel/CSV Upload**: Fuzzy-matching column mapping for bulk shift uploads.
  - **SCADA Integration**: Automated data extraction pipelines.
  - **Barcode/QR Processing**: Decode scanner payloads automatically.
  - **ERP Sync**: Hooks for SAP/ERP system pooling.
  - **Import Logs**: Detailed views into integration health and anomalies.
- **Alerts & Diagnostics**: System thresholds to flag TOC (Theory of Constraints) bottlenecks and alert operators to critical downtime anomalies.

## Prerequisites

- **Python 3.8+**
- **Node.js 18+** & **npm**

## Setup & Installation

### 1. Backend Setup

Open a terminal and navigate to the project directory:

```bash
cd oee_tracker
```

Create a virtual environment (recommended) and install the dependencies:

```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Frontend Setup

Open a separate terminal and navigate to the frontend directory:

```bash
cd oee_tracker/frontend
npm install
```

## Running the Application

You will need two terminals running concurrently to host both the backend API and the frontend UI.

### Start the FastAPI Backend
In your first terminal (with the virtual environment activated):

```bash
cd oee_tracker
python -m uvicorn backend.main:app --reload --port 8000
```
*The API will be available at `http://127.0.0.1:8000`. You can view the automatic Swagger documentation at `http://127.0.0.1:8000/docs`.*

### Start the React Frontend
In your second terminal:

```bash
cd oee_tracker/frontend
npm run dev
```
*The UI will typically be bound to `http://localhost:5173`. Open this URL in your browser.*

## Tech Stack

- **Backend**: FastAPI, Python, SQLAlchemy, SQLite (Default), Pandas
- **Frontend**: React, Vite, TailwindCSS (v4 @theme), React Router DOM, ApexCharts, Lucide React (Icons)
- **API Communication**: Axios
