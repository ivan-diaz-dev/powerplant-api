# PowerPlant-API

## The project

### In short
Calculate how much power each of a multitude of different [powerplants](https://en.wikipedia.org/wiki/Power_station) need to produce (a.k.a. the production-plan) when the [load](https://en.wikipedia.org/wiki/Load_profile) is given and taking into account the cost of the underlying energy sources (gas,  kerosine) and the Pmin and Pmax of each powerplant.

## Installation

1. **Create the virtual environment**

   ```bash
   python3 -m venv venv
   ```

2. **Activate the virtual environment**

   ```bash
   source venv/bin/activate
   ```

3. **Install dependencies**

   pyproject.toml -> contains the project dependencies.

   ```bash
   python -m pip install --upgrade pip
   pip install --upgrade setuptools
   pip install --group all --upgrade
   ```


## Run App

### Local

   ```bash
   python -m app.main
   ```

### Docker

   ```bash
   docker build -f docker/Dockerfile -t powerplant-api .
   docker compose up --build
   ```

## Project structure

```
powerplant-api/
├── app/
│   ├── api/                     # FastAPI router and endpoints
│   ├── core/                    # Settings, logging utilities, error types
│   ├── models/                  # Pydantic request/response schemas
│   ├── services/                # Business logic
└── pyproject.toml               # Project metadata & dependency groups
```

- Docstrings and inline comments stay in English.
- Logging is centralized via `app.core.logging.configure_logging`, using the level specified by the `POWERPLANT_LOG_LEVEL` environment variable (defaults to `INFO`).

## API usage

Endpoint: `POST /productionplan`

- Request body must match the schema of `example_payloads/payload*.json`.

Use interactive docs at `http://ip:8888/docs` (Swagger UI) and `http://127.0.0.1:8888/redoc` for schema inspection.
